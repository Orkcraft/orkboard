// The v1 shell on a phone (docs/specs/33-v1-shell.md §6, §8; decisions §45.2, §62; spec 49 §10): the one face when the compact snapshot's `focus` is "board", with no
// tab bar. One screen: the top bar (the menu, the project, Today, what is left of the AI tools), the goal's window under it — the goals as chips, the goal's header, the
// ideas bar, the stage switch and the party's columns (shell-arena.js) — and what waits for you along the bottom: the stops, then the results to look at, fanned, a tap
// popping one out with its quick answers (shell-stops.js): every stop of the project, the most urgent in the middle (spec 54). The menu opens the drawer: Stop all, Spend, the projects and the settings (Agents, a screen of its own, is a row of This project). An
// idea's spec, a plan, a task, a result's code or the gate opens on its own full screen over the board, with Back (and the system back gesture) and its actions pinned at
// the bottom. It speaks the host's commands (§5) through the phone's protocol (app.js `send`) and reads again when the snapshot's `ideas_rev` changes (and every POLL_MS while
// the Taskmaster or a task works). Always Office's calm look.
import { h } from "./util.js";
import { makeTop, keptGoal } from "./shell-top.js";
import { makeBoardTab, BUSY } from "./shell-board.js";
import { makeAgents } from "./shell-agents.js";
import { makeAgentSheet } from "./shell-agent.js";
import { makeReview } from "./shell-review.js";
import { makePreview } from "./shell-preview.js";
import { makeNeeds } from "./shell-needs.js";
import { makeStops } from "./shell-stops.js";
import { makeFab } from "./shell-fab.js";
import { firstStopGoal, partiesOf } from "./shell-arena-words.js";
import { makePitch, pitchNode } from "./shell-pitch.js";

const POLL_MS = 10000;
const LIVE = new Set(["running", "testing"]);

export { stateWords } from "./shell-board.js";
export { price } from "./shell-preview.js";

/** `ctx`: {send, deliver, flash, unpair}. Returns {el, sheets, content(), render(snapshot), dispose()}. */
export function makeBoard(ctx) {
  const st = { board: null, review: null, agents: null, roles: null, snap: null, track: "", view: "", ops: null, boardError: "", preview: null, cards: [],
    map: null, mapError: "", today: null, gate: null, band: "", focus: "", hand: "", picks: {}, flagLine: null, lit: new Set(), prices: {} };
  let poll = 0;
  let seenRev;                          // the snapshot's ideas_rev read last
  let seenSnap;                         // the snapshot's rev read last (the project switcher's)
  let loading = false;
  let again = false;                    // the snapshot said the Board changed while it was being read
  let pushed = false;                   // the preview put a step in the history: the system back gesture closes it

  // The listener lets a phone send a burst of ten commands and then five a second (a reading is seven commands): a command it refused for that, and so did not run, is sent once
  // more a moment later, not left undone or stale until the next change.
  const TOO_FAST = /Too many commands/i;
  async function sendPaced(name, args) {
    const r = await ctx.send(name, args);
    if (r.ok || !TOO_FAST.test(r.error || "")) return r;
    await new Promise((done) => setTimeout(done, 1200));
    return ctx.send(name, args);
  }
  const read = (name) => sendPaced(name);

  const core = {
    st,
    /** A command of the contract; null (and the plain-words error said) when it fails. `onError(text)`: where the error is said instead of the toast (a toast lies under a raised card). */
    async call(name, args, onError) {
      const r = await sendPaced(name, args);
      if (!r.ok || r.result?.error) { (onError || ctx.flash)(r.error || r.result?.error); return null; }
      return r.result ?? {};
    },
    refresh, open, close, back, reset, go,
    editGoal(slug) { boardTab.editGoal(slug); },
    /** The parties of the project as the party's deck and its sheet say them (spec 52 §5.3), and a pick in it. */
    parties() { return partiesOf(st, keptGoal(st.snap?.project)); },
    /** The party's deck, a new node for the end of the stage switch (shell-where.js). */
    partyDeck() { return top.deck(); },
    pick(slug) { boardTab.pick(slug); },
    pickOps() { boardTab.pickOps(); },
    editTeam(g) { boardTab.editTeam(g); },
    /** An agent's dialog (model, at once, instruction, Takes), from a member's card (spec 54 §6.2). */
    editAgent(slug) { agentSheet.open(slug); },
    /** New goal, the party shown first (spec 53 §2); the form picks its goal type. */
    newIdea() { boardTab.openNew(st.track); },
    /** New party with a party of the library picked (`preset`: its id); `after(slug)` once it is made (a pitch sent to a party the project lacks, spec 65 §5). */
    newParty(preset, after) { boardTab.newParty(preset, after); },
    /** A pitch's sheet (spec 65 §8). */
    openPitch(slug, via = "") { logOpened("idea", `pitch:${slug}`, via); pitch.open(slug); },
    /** Edit the party of a goal: the goal as `ideas.goal` sends it, in the team's sheet. */
    async editParty(slug) { const got = await core.call("ideas.goal", { slug }); if (got) core.editTeam(got); },
    openInto() { review.openInto(); },
    setToday(data) { top.today.set(data); },
    log: (what, ref, via) => logOpened(what, ref, via),
    draw() { drawAll(); },
    flash(text) { ctx.flash(text); },
  };

  const top = makeTop(core, ctx);
  const boardTab = makeBoardTab(core, ctx);
  const agents = makeAgents(core);
  const agentSheet = makeAgentSheet(core);                 // the dialog of Agents' Edit, opened from a member's card too
  const review = makeReview(core);
  const needs = makeNeeds(core, ctx);
  const fab = makeFab(core);
  const stops = makeStops(core, ctx, needs, boardTab.ops);
  const preview = makePreview(core, ctx, { agents: agents.el });
  const pitch = makePitch(core, ctx);                      // a pitch of Ideation opens in its sheet, wherever it is opened from
  const el = h("div", { class: "board v1" }, top.el, boardTab.el, stops.el, fab.el, preview.el);

  /** What the person opened, for the day's analysis (docs/specs/33-v1-shell.md §9): the host's one loggable event. The listener
   *  allows a device only a few commands a second, so the lines go out one at a time, a moment apart, behind the ones that matter. */
  const opened = [];
  let draining = 0;
  function logOpened(what, ref, via = "") {
    opened.push({ event: "opened", what, ref: String(ref || ""), device: "phone", ...(via ? { via } : {}) });
    if (!draining) draining = setTimeout(drain, 800);
  }
  async function drain() {
    const next = opened.shift();
    if (next) await ctx.send("ideas.log", next);
    draining = opened.length ? setTimeout(drain, 800) : 0;
  }

  // -- the last look (spec 42 §1.3): `orkboard.look.<project>` holds when the person last pressed or had the page in front of them ----------
  const AWAY_H = 6;
  const WRITE_GAP_MS = 60 * 1000;                       // a press moves the look at most once a minute
  let lastWrite = 0;
  let lookBusy = false;
  let lookProject;                                      // the project the look was last asked about
  const lookKey = () => (st.snap?.project ? `orkboard.look.${st.snap.project}` : "");
  const readLook = (key) => { try { return Number(localStorage.getItem(key)) || 0; } catch { return 0; } };
  function touch(now = Date.now()) {
    const key = lookKey();
    if (!key) return;
    try { localStorage.setItem(key, String(now)); } catch { /* the page works without it */ }
    lastWrite = now;
  }
  /** The page is in front of the person: when the last look is AWAY_H hours old, ask what happened since; else keep the look fresh. */
  async function away() {
    const key = lookKey();
    if (!key || lookBusy || document.visibilityState === "hidden") return;
    const last = readLook(key), now = Date.now();
    if (!last) { touch(now); return; }                  // no last look: written, nothing shown
    if (now - last < AWAY_H * 3600 * 1000) { if (now - lastWrite >= WRITE_GAP_MS) touch(now); return; }
    lookBusy = true;
    try {
      const r = await ctx.send("ideas.recap", { since: last });
      if (!r.ok || !r.result || r.result.error || key !== lookKey()) return;       // not answered: asked again at the next press
      touch(Date.now());
      if (r.result.merged && !r.result.empty) {
        const card = { kind: "recap", data: r.result, logged: st.cards.length === 0 };
        st.cards = [...st.cards, card];
        if (card.logged) logOpened("recap", `${r.result.hours}h`);       // else it waits behind Last week's card: logged when that closes
        drawAll();
      }
    } finally { lookBusy = false; }
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") touch(); else away(); });
  window.addEventListener("pagehide", () => touch());
  for (const type of ["pointerdown", "keydown"]) window.addEventListener(type, () => away(), true);

  /** Needs you, now what lies along the bottom: the goal of the first stop is shown and the stop popped out (a push's arrival, a card's link). */
  let wantStop = false;
  function showStop() {
    const slug = firstStopGoal(st);
    if (!slug) return false;
    boardTab.show(slug);
    return stops.pop();
  }
  function go(id) {
    logOpened("tab", id);
    if (id === "needs") { if (!showStop()) wantStop = !st.board || !st.map; }
    else if (id === "agents") open({ kind: "agents" });
    window.scrollTo(0, 0);
  }

  function drawAll() {
    top.draw();
    boardTab.draw();
    agents.draw();
    stops.draw();
    fab.show(Boolean(st.board) && !st.view);                 // a party's: not Operations'
    preview.redraw();
    pitch.sync();
    if (wantStop && st.board && st.map) { wantStop = false; showStop(); }
  }

  // -- the preview on its own screen: opened over the tab, Back (or the system gesture) to it -----------------------
  function open(p, via = "") {
    if (p.kind === "idea" && pitchNode(st, p.slug)) { core.openPitch(p.slug, via); return; }      // a pitch has no spec, plan or tasks: its sheet says what it has
    if (p.kind === "agents") logOpened("tab", "agents");
    else if (p.kind !== "doc") logOpened(p.kind === "goal" ? "idea" : p.kind === "plan" && p.todo ? "todo" : p.kind,
      p.kind === "goal" ? `goal:${p.slug}` : p.task ? `${p.slug}/${p.task}` : p.todo ? `${p.slug}/${p.todo}` : p.slug || "", via);
    if (!st.preview) {
      try { history.pushState({ preview: true }, ""); pushed = true; } catch { pushed = false; }
    }
    st.preview = p;
    el.classList.add("is-open");
    preview.show(p);
  }
  function hideNow() {
    st.preview = null;
    el.classList.remove("is-open");
    preview.hide();
  }
  function close() { if (pushed) history.back(); else hideNow(); }
  function back() { close(); }
  window.addEventListener("popstate", () => { pushed = false; if (st.preview) hideNow(); });

  /** Another project is shown: what was read of the last one is dropped before the new one is read. */
  function reset() {
    st.board = st.review = st.agents = st.roles = st.today = st.gate = null;
    st.track = st.view = st.boardError = st.band = st.focus = st.hand = "";
    st.picks = {};
    st.flagLine = null;
    st.lit = new Set();
    st.prices = {};
    st.map = null;
    st.mapError = "";
    st.cards = [];
  }

  // -- reading the town ------------------------------------------------------------------------------------------

  async function refresh() {
    const [b, r, a, ro, m, td, g] = await Promise.all(["ideas.board", "ideas.review_list", "ideas.agents", "ideas.roles", "ideas.map", "ideas.today", "ideas.gate"].map(read));
    const ok = (x) => x.ok && x.result && !x.result.error;
    if (ok(b)) st.board = b.result;
    if (ok(r)) st.review = r.result;
    if (ok(a)) st.agents = a.result;
    if (ok(ro)) st.roles = ro.result;
    if (ok(m)) { st.map = m.result; st.mapError = ""; } else if (!st.map) st.mapError = m.error || m.result?.error || "Loading…";
    if (ok(td)) st.today = td.result;
    if (ok(g)) st.gate = g.result;
    st.boardError = !st.board && !ok(b) ? b.error || b.result?.error || "Loading…" : "";
    if (!ok(b) || !ok(m)) seenRev = undefined;           // not read (a page that starts from what it kept, before the socket opens): the next snapshot reads again, never "the same as read"
    drawAll();
    if (st.preview) preview.reload();
    schedule();
  }

  /** Reads the Board for the snapshot's `ideas_rev`, and once more when the snapshot said it changed meanwhile. */
  function readBoard() {
    loading = true;
    seenRev = st.snap?.ideas_rev;
    refresh().finally(() => { loading = false; if (again) { again = false; readBoard(); } });
  }

  function schedule() {
    clearTimeout(poll);
    const busy = (st.board?.ideas || []).some((i) => BUSY.has(i.state)) || (st.board?.tracks || []).some((t) => t.state === "reading")
      || (st.agents?.roles || []).some((r) => (r.chips || []).some((c) => LIVE.has(c.state)));
    if (busy) poll = setTimeout(refresh, POLL_MS);
  }

  drawAll();

  return {
    el,
    sheets: [...top.sheets, ...boardTab.sheets, ...needs.sheets, ...review.sheets, ...agents.sheets, agentSheet.el, ...stops.sheets, ...pitch.sheets],
    // What is acted on only while the town answers: not the bar's Stop all, nor New idea (kept with no signal).
    content: () => [boardTab.el, ...stops.content(), preview.el],
    /** A push's arrival (board-app.js `arrive`): the goal of the first stop is shown and the stop popped out, as soon as the Board has been read. */
    showNeeds: () => go("needs"),
    render(s) {
      st.snap = s;
      if (s.project !== lookProject) { lookProject = s.project; st.cards = []; away(); }       // another project is shown, or the page starts
      top.render(s, s.rev !== seenSnap ? s.rev : undefined);
      boardTab.ops.sync(s.ops_rev ?? 0);
      seenSnap = s.rev;
      if (seenRev !== undefined && s.ideas_rev === seenRev) return;
      if (loading) { again = true; return; }                  // the Board changed while it was being read: read once more when this ends (the host says it once)
      readBoard();
    },
    dispose() { clearTimeout(poll); },
  };
}
