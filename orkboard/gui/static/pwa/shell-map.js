// The Map on the phone (docs/specs/48-map-ideas.md §3, §7, decisions §61): one goal, the one the top bar shows. Its header is the goal
// (title, priority, state, how far it is in %, *n of m ideas done*, *done when*, ≈$, today's merges), under it one line with the whole
// party and each member's state. Below, the goal's ideas in trail order: the one open is expanded (shell-map-idea.js: its card, its
// waves, its lanes), the rest are one line (the head of who is on it, the title, *<stage> · <state words>*, a mark); the done ones fold
// into Done (n). One idea is open at a time (an accordion): the first at work or waiting for the person, until a tap picks another.
// *new* marks what changed since the Map was last shown on this phone. A name is its short one on two lines at most (spec 41 §3), the
// title in the element's title and label. A node that waits for the person alone has one button (spec 41 §4). Results are merged on
// the idea's card, not in Review (decisions §61.7).
import { h, icon, sheet } from "./util.js";
import { foot } from "./shell-forms.js";
import { rowState } from "./shell-ideas.js";
import { goalState, partyFold } from "./shell-goal.js";
import { makeIdeaBlock, stageOf, STAGE_WORDS, memberWords } from "./shell-map-idea.js";
import { PRIORITY_WORDS, hhmm } from "./shell-words.js";
import { whoHead } from "./shell-who.js";
import { price } from "./shell-preview.js";

export const MAP_VIEW = "map";

const NEEDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed" };
const seenKey = (project) => `orkboard.map.seen.${project || ""}`;

/** "18:00" from a bare "HH:MM" or an ISO time. */
const until = (u) => (/^\d{1,2}:\d{2}$/.test(String(u || "")) ? u : hhmm(u));

/** Why a node that is not done does not move, in words (the Map's own words: §4.3's, as the Agents' chips). "" when it moves. */
export function waitsWords(node) {
  const w = node.waits;
  if (!w || node.state === "done") return "";
  const at = until(w.until);
  if (w.kind === "you") return NEEDS[node.needs_you] || "needs you";
  if (w.kind === "idea") return `waits for ${w.title || w.ref}`;
  if (w.kind === "files") return `same files as ${w.title || w.ref}`;
  if (w.kind === "limits") return at ? `waits for limits · after ${at}` : "waits for limits";
  if (w.kind === "reserve") return at ? `keeps your reserve · after ${at}` : "keeps your reserve";
  if (w.kind === "night") return "tonight";
  if (w.kind === "stopped") return "stopped";
  if (w.kind === "week") return `waits: the week is behind${w.until ? ` · until ${dayAt(w.until)}` : ""}`;
  return "";
}

/** "Mon 09:00" from a local `YYYY-MM-DDTHH:MM`; "" when it does not read. */
const dayAt = (iso) => {
  const d = new Date(iso);
  return !iso || Number.isNaN(d.getTime()) ? "" : `${d.toLocaleDateString("en-US", { weekday: "short" })} ${hhmm(iso)}`;
};

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** *7 ideas · 23 results · 19 the first time · ≈$38 · 9 days* (spec 42 §2.3): under a met goal's flag; a part that is null is left out. */
export function tallyWords(t) {
  if (!t) return "";
  return [count(t.ideas, "idea", "ideas"), count(t.results, "result", "results"), `${t.first_time} the first time`,
    t.usd != null && `≈$${Math.round(t.usd)}`, t.days != null && count(t.days, "day", "days")].filter(Boolean).join(" · ");
}

/** *met, says Product manager · 18 October* (spec 42 §2.4). */
export function flagWords(f) {
  const d = new Date(f.at);
  return [`met, says ${f.by}`, Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`].filter(Boolean).join(" · ");
}

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** `core`: the board's frame; `goalSheet`: New goal. Returns {section(), enter()}. */
export function makeMap(core, goalSheet) {
  const st = core.st;
  let since = 0;                                        // the time the Map was last shown before this time (ms); 0: never, nothing is new

  /** The Map is shown now: what changed after the last time is *new* until the next time. */
  function enter() {
    const key = seenKey(st.snap?.project);
    let prev = 0;
    try { prev = Number(localStorage.getItem(key)) || 0; localStorage.setItem(key, String(Date.now())); } catch { /* the Map works without it */ }
    since = prev;
  }

  // -- the flag raised once on this phone, and the Flags fold (spec 42 §2) -----------------------------------------------------
  const flagsKey = () => `orkboard.flags.${st.snap?.project || ""}`;
  const foldKey = () => `orkboard.map.flags.${st.snap?.project || ""}`;
  const raisedList = () => {
    try {
      const got = JSON.parse(localStorage.getItem(flagsKey()) || "null");
      return Array.isArray(got) ? got.filter((x) => typeof x === "string") : null;
    } catch { return null; }
  };
  const keepRaised = (slugs) => {
    try { localStorage.setItem(flagsKey(), JSON.stringify([...new Set([...(raisedList() || []), ...slugs])])); } catch { /* raised again next time */ }
  };
  let watch = null;                                      // the one trail on screen waits to raise its flag
  let unwatch = null;                                    // takes its observer and its listener away

  /** A phone with no list adds every met goal without raising any (the first start after this part). */
  function seedRaised(goals) {
    if (raisedList() === null) keepRaised(goals.filter((g) => g.verdict?.met).map((g) => g.slug));
  }

  /** The chosen goal's flag is raised once, when its trail is on screen (this tab shown, the page visible): six steps up from the foot
   *  of its box (not under reduced motion); the slug is kept and `opened` `flag` is logged. */
  function raiseWhenSeen(goal, end) {
    unwatch?.();                                         // the section is drawn again and again: the last one's listener goes first
    const list = goal.verdict?.met ? raisedList() : null;
    if (!list || list.includes(goal.slug)) return;
    let done = false, inView = false;                    // whether the observer last saw the trail on screen
    const raise = () => {
      if (done || !inView || document.visibilityState !== "visible") return;
      done = true;
      unwatch?.();
      keepRaised([goal.slug]);
      core.call("ideas.log", { event: "opened", what: "flag", ref: goal.slug, device: "phone" });
      const mark = end.querySelector(".trail-flag");
      if (mark && !reducedMotion()) { mark.classList.add("is-raising"); setTimeout(() => mark.classList.remove("is-raising"), 700); }
    };
    document.addEventListener("visibilitychange", raise);
    unwatch = () => {
      done = true;
      watch?.disconnect();
      watch = null;
      document.removeEventListener("visibilitychange", raise);
      unwatch = null;
    };
    if (typeof IntersectionObserver === "function") {
      watch = new IntersectionObserver((seen) => { inView = seen[seen.length - 1].isIntersecting; raise(); });
      watch.observe(end);
    } else { inView = true; raise(); }
  }

  let flagsAt = null;                                    // {rev, list}: the flags as `ideas.flags` gave them for this Map
  /** *Flags (3)*, the goals met, a fold at the foot of the Map; the list is asked for when it is opened. */
  function flagsFold(goals) {
    const met = goals.filter((g) => g.verdict?.met).length;
    if (!met) return null;
    const list = h("ul", { class: "map-flags-list" });
    let open = false;
    try { open = localStorage.getItem(foldKey()) === "open"; } catch { /* closed */ }
    const fill = (flags) => list.replaceChildren(...flags.map((f) => h("li", {}, h("button", { class: "map-flag", type: "button", onclick: () => core.open({ kind: "goal", slug: f.goal }, "flags") },
      h("span", { class: "map-flag-mark", "aria-hidden": "true" }, icon("flag")),
      h("span", { class: "map-flag-body" }, h("b", {}, f.title), h("small", { class: "muted" }, flagWords(f)), h("small", { class: "muted" }, tallyWords(f.tally)))),
      partyFold(core, f.goal))));
    async function load() {
      const rev = st.map?.rev;
      if (flagsAt && flagsAt.rev === rev) { fill(flagsAt.list); return; }
      const got = await core.call("ideas.flags");
      if (got) { flagsAt = { rev, list: got.flags || [] }; fill(flagsAt.list); }
    }
    const el = h("details", { class: "map-flags", "aria-label": "Flags", open: open ? "" : null }, h("summary", {}, `Flags (${met})`), list);
    el.addEventListener("toggle", () => {
      try { localStorage.setItem(foldKey(), el.open ? "open" : "closed"); } catch { /* not kept */ }
      if (el.open) load();
    });
    if (open) load();
    return el;
  }

  /** How far a goal is, in %: its ideas done, and the share of the tasks done of each idea at work. */
  function progressOf(mine) {
    if (!mine.length) return 0;
    const done = mine.filter((n) => n.state === "done").length;
    const part = mine.filter((n) => n.state !== "done" && n.progress?.total > 0).reduce((s, n) => s + n.progress.done / n.progress.total, 0);
    return Math.round(((done + part) / mine.length) * 100);
  }

  // -- skipping a check, on the trail: a checker's chip is a button (a finger's size); it asks first, saying what it spares ---------
  let skipping = null;                                 // {node, check, planned}
  const skipText = h("p", {});
  const skipBtn = h("button", { class: "ork-btn primary big", type: "button" }, "Skip it");
  const skipSheet = sheet("Skip the check?", skipText,
    foot(h("button", { class: "ork-btn big", type: "button", onclick: () => skipSheet.close() }, "Keep it"), skipBtn));
  skipBtn.addEventListener("click", async () => {
    const s_ = skipping;
    skipSheet.close();
    if (s_ && await core.call("ideas.check_skip", { slug: s_.node.slug, by: s_.check.by })) core.refresh();
  });
  const spares = (c) => { const usd = Number(st.roles?.tier_costs?.[c.tier]); return usd > 0 ? ` It spares ≈ $${usd.toFixed(2)}.` : ""; };
  function askSkip(node, check, planned) {
    skipping = { node, check, planned };
    skipText.textContent = `${check.name} does not check “${node.title}”.${spares(check)} `
      + (planned ? "Its task is taken out of the plan before it runs; it comes back with the idea's next plan." : "The plan is made without it; you can take it again until then.");
    skipSheet.open();
  }
  const skippable = (c) => c.applies && !c.skipped && (!c.state || ["waiting", "ready", "held"].includes(c.state));

  /** The one button a node that waits for the person alone has (spec 41 §4): {label, text, aria, run} or null. */
  function actionOf(node) {
    if (node.state === "done") return null;
    const slug = node.slug, title = node.title;
    const go = (name, args, done) => async () => { if (await core.call(name, { slug, ...args, via: "map" })) { core.flash(done); core.refresh(); } };
    if (node.needs_you === "plan" && !(node.waits_on || []).length) {
      const n = (node.tasks || []).length, cost = price(node.estimate);
      return { icon: "play", text: cost, aria: `Start “${title}”: ${n} ${n === 1 ? "task" : "tasks"}${cost ? `, about ${cost.replace(/^~/, "")}` : ""}`,
        run: go("ideas.start", {}, "Started."), key: "start" };
    }
    if (node.state === "plan" && node.start_at === "night" && !node.needs_you) {
      return { icon: "play", text: "Start now", aria: `Start “${title}” now, instead of tonight`, run: go("ideas.start_now", {}, "Started."), key: "start-now" };
    }
    if (node.state === "raw" && ["night", "hold"].includes(node.queue) && !node.held_until) {
      return { icon: null, text: "Process now", aria: `Process “${title}” now`, run: go("ideas.queue", { queue: "now" }, "The Taskmaster drafts it now."), key: "process-now" };
    }
    return null;
  }

  let shown = "";                                       // the goal on screen: another goal starts with its own first idea open
  const blocks = makeIdeaBlock(core, { askSkip, tick: () => { st.mapTick = (st.mapTick || 0) + 1; core.draw(); } });
  // st.mapOpen: the idea open: undefined until the person picks one (then the first that needs a look), "-" none; the Board redraws when it moves

  /** An idea is shown open at first when it is at work or waits for the person (spec 48 §3). */
  const wantsLook = (n) => ["implementation", "checking"].includes(stageOf(n)) || Boolean(n.needs_you) || (n.results || []).length > 0;

  /** *Implementation · working 1/3*: the stage, then the Board row's words, then what only the Map adds. */
  function wordsOf(node, titleOf) {
    const s = rowState(node, titleOf), why = waitsWords(node);
    const isNew = since && node.updated && Date.parse(node.updated) > since;
    const on = (node.checks || []).filter((c) => c.applies), passed = on.filter((c) => c.state === "passed").length;
    const text = [node.state === "done" ? "" : STAGE_WORDS[stageOf(node)], s.text, why && why !== s.text && !s.text.includes(why) ? why : "", node.by_itself ? "by itself" : "",
      node.estimate ? `≈$${node.estimate.usd_low.toFixed(2)}–${node.estimate.usd_high.toFixed(2)}` : "", on.length ? `checks ${passed}/${on.length}` : "", isNew ? "new" : ""];
    return { spin: s.spin, isNew, words: text.filter(Boolean).join(" · ") };
  }

  /** A one-line row: the head of who is on it, its title, its stage, a mark; a tap opens it in place. */
  function row(node, titleOf, leader) {
    const w = wordsOf(node, titleOf), needsHand = node.needs_you && node.state !== "done";
    const act = actionOf(node);
    const left = (node.tasks || []).filter((t) => t.state !== "merged" && t.state !== "dropped");
    const run = left.find((x) => x.state === "running" || x.state === "testing") || left[0];
    const head = run?.head || leader?.head || null;
    const timed = ["night", "limits", "reserve", "week"].includes(node.waits?.kind);
    return h("li", { class: `map-row state-${node.state}${needsHand ? " needs-hand" : ""}${node.waits && !needsHand ? " is-waiting" : ""}${node.state === "proposed" ? " is-proposed" : ""}${act ? " has-act" : ""}`,
      "data-slug": node.slug },
      h("div", { class: "map-line" },
        h("button", { class: "map-open trail-chip", type: "button", "aria-expanded": "false", "aria-label": `${node.title}: ${w.words}`, "data-words": w.words, title: node.title,
          onclick: () => { st.mapOpen = node.slug; core.draw(); } },
          head ? whoHead(head, true) : h("span", { class: "trail-chip-nohead", "aria-hidden": "true" }),
          h("span", { class: "idea-title" }, node.short || node.title),
          h("small", { class: "idea-stage muted" }, STAGE_WORDS[stageOf(node)]),
          needsHand ? h("span", { class: "trail-mark is-gate", "aria-hidden": "true" }, icon("warning-diamond"))
            : w.spin ? h("span", { class: "spin trail-mark", "aria-hidden": "true" }, "↻")
              : timed ? h("span", { class: "trail-mark", "aria-hidden": "true" }, icon("clock")) : null,
          w.isNew ? h("span", { class: "map-new", "aria-hidden": "true" }, "new") : null),
        act ? h("button", { class: "ork-btn map-act", type: "button", "data-act": act.key, "aria-label": act.aria, onclick: act.run },
          act.icon ? icon(act.icon) : null, act.text ? h("span", {}, act.text) : null) : null));
  }

  /** A done idea: a ✓, how many of its tasks are in dev, and that it waits for main until it is in main. */
  function doneRow(node) {
    const k = (node.tasks || []).length;
    return h("li", { class: "map-row state-done", "data-slug": node.slug },
      h("button", { class: "map-open trail-chip", type: "button", "aria-label": `${node.title}: done${k ? `, ${k} of ${k} tasks in dev` : ""}, in dev, waits for main`, title: node.title,
        onclick: () => core.open({ kind: "idea", slug: node.slug }, "map") },
        h("span", { class: "trail-mark ok", "aria-hidden": "true" }, icon("check")), h("span", { class: "idea-title" }, node.short || node.title),
        h("small", { class: "muted" }, k ? `${k} of ${k} tasks in dev · ` : "", "in dev · waits for main")));
  }

  /** The party in one line: the leader and each member, a head with its name and its state in words; only a stop is yellow. */
  function partyLine(goal) {
    const party = goal.party || [];
    if (!party.length) return null;
    return h("ul", { class: "map-party", "aria-label": "Party" }, ...party.map((m) => {
      const words = memberWords(m.state, m.why);
      return h("li", { class: `map-member${m.state === "needs" ? " is-stop" : ""}`, "data-member": m.slug, "data-state": m.state, "aria-label": `${m.name}, ${words}` },
        whoHead(m.head, true), h("span", { class: "member-name" }, m.name), h("small", { class: m.state === "needs" ? "" : "muted" }, words));
    }));
  }

  function goalSection(goal, nodes, titleOf) {
    const mine = nodes.filter((n) => n.goal === goal.slug);
    const open = mine.filter((n) => n.state !== "done"), done = mine.filter((n) => n.state === "done");
    const money = goal.usd == null ? "—" : `≈$${Math.round(goal.usd)} so far`;
    const pct = progressOf(mine);
    const flag = goal.verdict ? (goal.verdict.met ? "is-met" : "is-not") : "";
    const board = (st.board?.tracks || []).find((t) => t.slug === goal.slug), onBoard = Boolean(board);
    const line = String(board?.summary || "").split("\n").find((l) => l.trim()) || "";
    const endWords = goal.verdict ? (goal.verdict.met ? `Met · ${goal.verdict.by}` : `Not met yet · ${goal.verdict.by}`) : open.length ? "The goal" : "Its ideas are done";
    const endMark = h("div", { class: `trail-end ${flag}`, "aria-label": `The flag: ${endWords}` }, h("span", { class: "trail-flag" }, icon("flag")), h("span", {}, endWords));
    raiseWhenSeen(goal, endMark);
    blocks.observe(goal.slug, mine);
    const target = open.find((n) => n.slug === st.mapOpen) || (st.mapOpen === "-" ? null : open.find(wantsLook)) || null;
    const today = goal.today && goal.today.merged ? ` · today ${goal.today.merged} merged · ≈$${goal.today.usd.toFixed(2)}` : "";
    return h("section", { class: "map-goal", "data-goal": goal.slug, "aria-label": goal.title },
      line ? h("p", { class: "goal-line" }, line) : null,
      h("p", { class: "map-goal-meta" }, h("span", { class: `prio prio-${goal.priority}` }, PRIORITY_WORDS[goal.priority] || "Normal"),
        goalState(goal) ? h("span", { class: `state-word ${goal.state === "reading" ? "work" : goal.state}` }, goalState(goal)) : null,
        h("span", {}, money + today),
        h("button", { class: "ork-btn small", type: "button", "aria-label": `Open goal ${goal.title}`, onclick: () => core.open({ kind: "goal", slug: goal.slug }) }, "Open"),
        onBoard ? h("button", { class: "ork-btn small", type: "button", "aria-label": `Edit goal ${goal.title}`, onclick: () => goalSheet.open(goal.slug) }, "Edit") : null),
      h("div", { class: "trail-start" }, h("b", { class: "trail-pct", "aria-label": `${pct} % of the way` }, `${pct} %`),
        h("i", { class: "map-bar", "aria-hidden": "true" }, h("i", { class: `map-goal-tab-fill p${Math.round(pct / 10) * 10}` })),
        h("span", { class: "muted" }, `${done.length} of ${mine.length} ideas done`)),
      (goal.done_when || []).length ? h("details", { class: "map-done-when" }, h("summary", {}, `Done when · ${goal.done_when[0]}`),
        h("ul", {}, ...goal.done_when.map((l) => h("li", {}, l)))) : null,
      partyLine(goal),
      open.length ? h("ol", { class: "map-ideas-list" }, ...open.map((n) => (n === target
        ? h("li", { class: "map-open-idea" }, blocks.block(n, goal, wordsOf(n, titleOf).words, n.needs_you ? "" : waitsWords(n), () => { st.mapOpen = "-"; core.draw(); }))
        : row(n, titleOf, goal.leader))))
        : h("p", { class: "muted trail-empty" }, "No idea left on the way."),
      endMark,
      goal.verdict?.met && goal.verdict.tally ? h("p", { class: "muted trail-tally" }, tallyWords(goal.verdict.tally)) : null,
      done.length ? h("details", { class: "done-ideas" }, h("summary", {}, `Done (${done.length})`),
        h("ol", { class: "ideas map-ideas" }, ...done.map(doneRow))) : null);
  }

  /** The Map's nodes for the Board tab: the goal the top bar shows, or why there is none. */
  function section() {
    if (st.mapError) return [h("p", { class: "muted" }, st.mapError)];
    if (!st.map) return [h("p", { class: "muted" }, "Loading…")];
    const goals = st.map.goals;
    if (!goals.length) {
      return [h("p", { class: "muted" }, "No goals yet."), h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open() }, "New goal")];
    }
    const titles = new Map(st.map.nodes.map((n) => [n.slug, n.title]));
    const titleOf = (slug) => titles.get(slug) || slug;
    const on = goals.find((g) => g.slug === st.track) || goals[0];
    if (shown !== on.slug) { shown = on.slug; st.mapOpen = undefined; }
    seedRaised(goals);
    return [goalSection(on, st.map.nodes, titleOf), flagsFold(goals)].filter(Boolean);
  }

  return { section, enter, sheets: [skipSheet.el, ...blocks.sheets] };
}
