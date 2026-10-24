// Ideation on the phone (docs/specs/65-ideation.md §8, decisions §78): a party whose goals are pitches, judged and never built. **Its field** takes the party's columns' place under the goals bar:
// its pitches in three sections, its leader's three stages — *Pitch* (new, held, tonight, failed), *Views* (the four views' heads over each pitch, lit one by one as each answers) and *Decision* (the case
// against and the Investor under way, then the answer's word — *Invest* · *Reshape* · *Pass* — and the pitches sent, naming their goal), with *Passed (n)* folded at its end. **A pitch's sheet**: the
// pitch; the four views one under another (head, *For*, *Against*, its question); the case against; the decision (its answer large, why, the kill reasons in words, where and as what type, the first
// step, the cheapest test, the goal it repeats). Its buttons say what happens: **Send to <party>** with the party picked beside it (a party of the library the project lacks: New party opens with it),
// **Change and judge again**, **Pass** (a reason if you like), **Drop**; **Try again** after a failure, **Judge again** for a passed one, **Judge now** for one held or kept for tonight. The views' and the
// Investor's words are in the text face; the pixel face is for the headings and the buttons (CLAUDE.md).
import { h, sheet } from "./util.js";
import { elem, sign } from "./shell-marks.js";
import { whoHead } from "./shell-who.js";
import { motionOn, pulse } from "./shell-motion.js";
import { answeredOf, goalStateWords, partyNameOf, pitchLine, pitchStage, whereWords } from "./shell-goals-words.js";

const PITCH_CHARS = 2000;                            // pitches.PITCH_CHARS: a pitch's one box
const WHY_CHARS = 300;                               // pitches.WHY_CHARS: the person's line when they pass
const RANK = { judged: 0, judging: 1, failed: 2, raw: 3, sent: 4 };

/** Whether a party of the Map is Ideation (its goals are pitches). */
export const isIdeation = (g) => Boolean(g?.ideation);
/** A pitch of the Map by its slug (a node whose `pitch` the host sends), else null. */
export const pitchNode = (st, slug) => (st.map?.nodes || []).find((n) => n.slug === slug && n.pitch) || null;
const errorOf = (st, slug) => (st.board?.ideas || []).find((i) => i.slug === slug)?.state_error || "";

/** The field of an Ideation party: `core` the board's frame (st, openPitch). Returns {draw(model) → node}. */
export function makePitchField(core) {
  const st = core.st;
  const lit = new Map();                             // pitch → the views seen answered at the last draw: one that turns is lit once

  /** The four views' heads of a pitch, lit as each has answered (the newly answered one lit once). */
  function viewHeads(n) {
    const before = lit.get(n.slug), now = new Set();
    const heads = (n.pitch?.views || []).map((v) => {
      const img = whoHead(v.head, true);
      if (!img) return null;
      img.dataset.view = v.slug;
      img.title = `${v.name}: ${v.answered ? "answered" : "reading"}`;
      img.classList.add("pitchrow__view");
      if (v.answered) { img.classList.add("is-lit"); now.add(v.slug); }
      return img;
    }).filter(Boolean);
    lit.set(n.slug, now);
    const fresh = before && motionOn() ? heads.filter((img) => img.classList.contains("is-lit") && !before.has(img.dataset.view)) : [];
    if (fresh.length) requestAnimationFrame(() => fresh.forEach(pulse));
    return h("span", { class: "pitchrow__views", "aria-hidden": "true" }, ...heads);
  }

  function row(n) {
    const d = n.pitch?.decision, judging = n.state === "judging";
    // a judged one's answer stands at its end: its line says where it would go, else its first kill reason
    const line = n.state === "judged" && d ? whereWords(d) || d.kills?.[0]?.words || "waits for you" : pitchLine(n, errorOf(st, n.slug), (s) => partyNameOf(st, s));
    const end = n.state === "judged" && d ? h("b", { class: "pitchrow__answer", "data-answer": d.answer }, d.word)
      : n.state === "failed" ? h("span", { class: "pitchrow__mark" }, sign("cross", "failed")) : n.state === "sent" ? h("span", { class: "pitchrow__mark" }, sign("after", "sent")) : null;
    return h("button", { class: `pitchrow is-${n.state}`, type: "button", "data-idea": n.slug, "data-state": n.state, "aria-label": `${n.title}: ${n.state === "judged" && d ? `${d.word}, ` : ""}${line}`,
      onclick: () => core.openPitch(n.slug, "map") },
    elem(n.element, { dim: n.state === "raw" }),
    h("span", { class: "pitchrow__body" }, h("span", { class: "pitchrow__title" }, n.short || n.title), h("span", { class: "pitchrow__line" }, line), judging ? viewHeads(n) : null),
    end);
  }

  return {
    /** The field of the Ideation party `m` (shell-arena-words.js `modelOf`): its three stages, each with its heads and its pitches; the filter of the Goals sheet holds. */
    draw(m) {
      const keep = (n) => !m.picks.length || m.picks.includes(n.slug);
      const nodes = m.nodes.filter(keep).sort((a, b) => (RANK[a.state] ?? 5) - (RANK[b.state] ?? 5));
      const passed = m.nodes.filter((n) => n.state === "passed");
      const heads = { planning: [m.lead], implementation: m.build, checking: m.check };
      const section = ([key, word], stage) => {
        const mine = nodes.filter((n) => n.state !== "passed" && pitchStage(n) === stage);
        const kids = mine.length ? mine.map(row) : [h("p", { class: "cap pitchsec__empty" }, stage === "planning" ? "No new pitch. The create button adds one." : stage === "implementation" ? "No pitch is being read." : "No decision yet.")];
        const fold = stage === "checking" && passed.length ? h("details", { class: "pitch-passed", "data-act": "passed" },
          h("summary", {}, `Passed (${m.goal.passed || passed.length})`), ...passed.map(row)) : null;
        return h("section", { class: "pitchsec", "aria-label": word, "data-band": key, "data-stage": stage },
          h("div", { class: "pitchsec__head" }, h("span", { class: "pitchsec__heads", "aria-hidden": "true" }, ...(heads[stage] || []).filter(Boolean).map((x) => whoHead(x.head, true))),
            h("h3", {}, word), h("span", { class: "ork-count" }, String(mine.length))),
          ...kids, fold);
      };
      const stages = ["planning", "implementation", "checking"];
      return h("div", { class: "pitchfield", role: "group", "aria-label": `${m.goal.title}: its pitches` }, ...m.bands.map((b, i) => section(b, stages[i])));
    },
  };
}

/** A pitch's sheet. `core`: the board's frame (st, call, refresh, open, newParty, log); `ctx`: {flash}. Returns {sheets, open(slug, party?), sync()}. */
export function makePitch(core, ctx) {
  const st = core.st;
  const body = h("div", { class: "pitch" });
  const acts = h("div", { class: "sheet-foot pitch__acts" });
  const sh = sheet("Pitch", body, acts);
  sh.el.classList.add("pitch-sheet");
  let slug = "", page = null, readRev, seq = 0;
  let mode = "", draft = "", why = "", party = "", note = "", err = "";    // what the sheet has open (change · pass · drop), the words typed, the party picked, a line said

  async function read() {
    const mine = ++seq;
    readRev = st.snap?.ideas_rev;
    const r = await core.call("ideas.page", { slug }, (e) => { err = e; });
    if (mine !== seq || !sh.el.open) return;
    if (r) page = r;
    draw(false);
  }

  /** The pitch as it stands: the Map's node (read with every change of the Board), else the page's. */
  const now = () => {
    const n = pitchNode(st, slug);
    return { state: n?.state || page?.state || "", pitch: n?.pitch || page?.pitch || null, title: n?.title || page?.title || slug, node: n };
  };
  const gist = () => (page?.sections || []).find((s) => s.name === "Gist")?.text || now().title;
  /** The parties a pitch may go to: the project's but General and Ideation's, and the party of the library the decision named when the project lacks it. */
  function targets(d) {
    const list = (st.map?.goals || []).filter((g) => g.slug !== "general" && !isIdeation(g)).map((g) => ({ id: g.slug, name: g.short || g.title, preset: false }));
    const w = d?.where;
    if (w?.party && w.preset && !list.some((t) => t.id === w.party)) list.push({ id: w.party, name: w.name || w.party, preset: true });
    return list;
  }

  const sec = (name, ...kids) => h("section", { class: "pitch__sec", "aria-label": name, "data-sec": name }, h("h3", {}, name), ...kids);
  const list = (items, cls = "") => h("ul", { class: `pitch__list${cls ? ` ${cls}` : ""}` }, ...items.map((t) => h("li", {}, t)));
  const said = (label, text) => (text ? h("p", { class: "pitch__said" }, h("b", {}, `${label}: `), text) : null);

  function viewCard(v, judging) {
    return h("article", { class: `pitchview${v.answered ? "" : " is-waiting"}`, "data-view": v.slug, "aria-label": v.name },
      h("div", { class: "pitchview__head" }, whoHead(v.head), h("b", {}, v.name), v.size ? h("span", { class: "ork-count", title: "How big the Engineering view reads it" }, `Size ${v.size}`) : null),
      ...(v.answered ? [h("p", { class: "pitchview__label" }, "For"), (v.for || []).length ? list(v.for) : h("p", { class: "cap" }, "Nothing for it."),
        h("p", { class: "pitchview__label" }, "Against"), (v.against || []).length ? list(v.against) : h("p", { class: "cap" }, "Nothing against it."),
        v.question ? h("p", { class: "pitchview__ask" }, h("b", {}, "It asks: "), v.question) : null]
        : [h("p", { class: "cap" }, judging ? "Reading the pitch…" : "Not read yet.")]));
  }

  function decisionBlock(p, state) {
    const d = p.decision;
    const before = (p.before || []).length ? h("p", { class: "cap", "data-sec": "before" }, `Before: ${p.before.map((b) => b.word).join(" · ")}`) : null;
    if (!d) return [h("p", { class: "cap" }, state === "judging" ? `${p.investor?.name || "The Investor"} decides once the views and the case against are in.` : "Not decided yet."), before].filter(Boolean);
    return [
      h("p", { class: "pitch__answer", "data-answer": d.answer }, whoHead(p.investor?.head), " ", d.word),
      d.reshaped ? h("p", { class: "cap" }, "Code made the invest a reshape: its kill reasons say why.") : null,
      (d.why || []).length ? list(d.why) : null,
      (d.kills || []).length ? h("div", { class: "pitch__kills" }, h("p", { class: "pitchview__label" }, "Kill reasons"), list(d.kills.map((k) => k.words))) : null,
      said("Where", whereWords(d) || (d.answer === "pass" ? "" : "you pick the party")),
      said("First step", d.first), said("Cheapest test", d.test), d.like ? said("It repeats", d.like.title || d.like.slug) : null,
      before,
    ].filter(Boolean);
  }

  /** A sent pitch's goal as it is now, under the decision (spec 68 §2.4, §7.2): *At work in Mobile app · 3 of 7*, *In main*, *In Release 1.4*, *Out in 1.4*, *Dropped*; a press opens the goal. */
  function goalLine(p, node) {
    const gs = p.goal_state || node?.goal_state;
    if (!gs) return null;
    const words = goalStateWords(gs, (s) => partyNameOf(st, s)), gone = gs.state === "dropped";
    return h("button", { class: "pitch__goal", type: "button", "data-act": "goal-line", "data-goal": gs.goal, disabled: gone, "aria-label": `Its goal: ${words}`,
      onclick: () => { sh.close(); core.open({ kind: "idea", slug: gs.goal }, "pitch"); } },
    h("b", {}, "Its goal"), h("span", { class: "pitch__goalwords" }, words), gone ? null : h("i", { class: "ork-chev right", "aria-hidden": "true" }));
  }

  // -- what the person does ---------------------------------------------------------------------------------------------------------------------------------
  const btn = (label, run, { primary = false, danger = false, act = "", tip = "" } = {}) => h("button", { class: `ork-btn${primary ? " primary" : ""}${danger ? " danger" : ""}`, type: "button",
    "data-act": act || null, title: tip || null, onclick: run }, label);
  /** A command of the pitch: its refusal said in the sheet (a toast lies under it), the Board read again. */
  async function run(name, args, done) {
    err = ""; note = "";
    const r = await core.call(name, { slug, ...args }, (e) => { err = e || "Not done"; draw(); });
    if (!r) return null;
    mode = ""; note = done || "";
    await core.refresh();
    if (sh.el.open) read();
    return r;
  }
  function send(t) {
    if (t.preset) {                                  // a party of the library the project lacks: made first, then the pitch's sheet opens on it
      ctx.flash(`Make the ${t.name} party first`);
      const back = slug;
      sh.close();
      core.newParty(t.id, (made) => open(back, made));
      return;
    }
    run("ideas.pitch_send", { party: t.id }, `Sent: a new goal in ${t.name}. Its leader drafts it now.`);
  }

  /** The buttons by the pitch's state; the Send row is pinned at the foot, the rest end the sheet. */
  function actions(state, p) {
    const d = p?.decision;
    if (mode === "change") {
      const box = h("textarea", { class: "ork-field", rows: "4", maxlength: String(PITCH_CHARS), "aria-label": "The pitch, changed" });
      box.value = draft;
      const go = btn("Judge again", () => { if (draft.trim()) run("ideas.pitch_again", { text: draft.trim() }, "Judged again: the views read it now."); }, { primary: true, act: "again" });
      go.disabled = !draft.trim();
      box.addEventListener("input", () => { draft = box.value; go.disabled = !draft.trim(); });
      return { foot: [h("label", { class: "field pitch__edit" }, h("span", { class: "field-label" }, "Change the pitch"), box), btn("Cancel", () => { mode = ""; draw(); }), go], rest: [] };
    }
    if (mode === "pass") {
      const box = h("input", { class: "ork-field", type: "text", maxlength: String(WHY_CHARS), "aria-label": "Why you pass (optional)", placeholder: "Why not? (optional, one line)" });
      box.value = why;
      box.addEventListener("input", () => { why = box.value; });
      return { foot: [h("label", { class: "field pitch__edit" }, h("span", { class: "field-label" }, "Pass: kept with its why, read by every later pitch"), box),
        btn("Cancel", () => { mode = ""; draw(); }), btn("Pass", () => run("ideas.pitch_pass", why.trim() ? { why: why.trim() } : {}, "Passed: it is kept with its why."), { primary: true, act: "pass-it" })], rest: [] };
    }
    if (mode === "drop") {
      return { foot: [h("p", { class: "pitch__ask", role: "alert" }, "Drop this pitch? Its page goes and nothing keeps its why: Pass keeps it."),
        btn("Keep it", () => { mode = ""; draw(); }), btn("Drop it", async () => {
          err = "";
          const r = await core.call("ideas.drop", { slug }, (e) => { err = e || "Not dropped"; draw(); });
          if (!r) return;
          sh.close();
          ctx.flash("Dropped.");
          core.refresh();
        }, { danger: true, act: "drop-it" })], rest: [] };
    }
    const change = () => btn("Change and judge again", () => { mode = "change"; draft = gist(); draw(); }, { act: "change", tip: "Change its words; the views read it anew" });
    const drop = () => btn("Drop", () => { mode = "drop"; draw(); }, { act: "drop", tip: "Its page goes" });
    if (state === "judged") {
      const ts = targets(d);
      if (!ts.some((t) => t.id === party)) party = (d?.where?.party && ts.some((t) => t.id === d.where.party) ? d.where.party : ts[0]?.id) || "";
      const pick = h("select", { class: "ork-field", "aria-label": "The party to send it to" }, ...ts.map((t) => h("option", { value: t.id, ...(t.id === party ? { selected: true } : {}) },
        `${t.name}${t.preset ? " (a new party)" : ""}${d?.where?.party === t.id ? " · as decided" : ""}`)));
      const chosen = () => ts.find((t) => t.id === party);
      const go = btn(`Send to ${chosen()?.name || "a party"}`, () => chosen() && send(chosen()), { primary: true, act: "send", tip: "A new goal in that party, drafted now; the views go with it" });
      go.disabled = !ts.length;
      pick.addEventListener("change", () => { party = pick.value; go.textContent = `Send to ${chosen()?.name || "a party"}`; });
      return { foot: [pick, go], rest: [change(), btn("Pass", () => { mode = "pass"; why = ""; draw(); }, { act: "pass", tip: "Kept with its why; the next pitch like it is judged against it" }), drop()] };
    }
    if (state === "failed") return { foot: [btn("Try again", () => run("ideas.judge", {}, "The views read it again."), { primary: true, act: "try-again" })], rest: [change(), drop()] };
    if (state === "passed") return { foot: [btn("Judge again", () => run("ideas.pitch_again", {}, "Judged again: the views read it now."), { primary: true, act: "judge-again" })], rest: [drop()] };
    if (state === "raw") return { foot: [btn("Judge now", () => run("ideas.judge", {}, "The views read it now."), { primary: true, act: "judge-now" })], rest: [drop()] };
    if (state === "sent" && p?.sent?.goal) return { foot: [btn("Open the goal", () => { sh.close(); core.open({ kind: "idea", slug: p.sent.goal }, "pitch"); }, { primary: true, act: "open-goal" })], rest: [] };
    return { foot: [], rest: [] };
  }

  function stateWords(state, p) {
    const n = now().node || { state, pitch: p, queue: page?.queue, held_until: page?.held_until, goal_state: p?.goal_state };
    return { judging: "Being judged", judged: "Judged: waits for you", sent: "Sent", passed: "Passed", failed: "Failed", raw: "Not judged yet" }[state] + ` · ${pitchLine(n, page?.state_error || errorOf(st, slug), (s) => partyNameOf(st, s))}`;
  }

  let drawn = "";
  /** Drawn again when what it shows changed, or at once (`force`) for the person's own press: a box being typed in stays as it is while the Board is read again. */
  function draw(force = true) {
    if (!sh.el.open) return;
    const { state, pitch: p, title, node } = now();
    const sig = JSON.stringify([slug, state, p, page, node?.goal_state, mode, note, err, (st.map?.goals || []).map((g) => g.slug)]);
    if (!force && sig === drawn) return;
    drawn = sig;
    sh.title(title);
    if (!p) { body.replaceChildren(h("p", { class: err ? "warn" : "muted" }, err || "Opening…")); acts.replaceChildren(); acts.hidden = true; return; }
    const judging = state === "judging";
    const { foot, rest } = actions(state, p);
    const kept = sh.el.querySelector(".sheet-in")?.scrollTop ?? 0;
    body.replaceChildren(...[
      h("p", { class: "cap pitch__state", role: "status", "data-state": state }, stateWords(state, p)),
      sec("The pitch", h("p", { class: "pitch__words" }, gist())),
      sec(`Views · ${answeredOf(p)} of ${(p.views || []).length}`, ...(p.views || []).map((v) => viewCard(v, judging))),
      sec("The case against", ...(p.case ? [h("p", { class: "pitch__who" }, whoHead(p.skeptic?.head), " ", h("b", {}, p.skeptic?.name || "Skeptic")),
        h("p", { class: "pitch__words" }, p.case.case || "—"),
        (p.case.kills || []).length ? h("div", { class: "pitch__kills" }, h("p", { class: "pitchview__label" }, "Kill reasons"), list(p.case.kills.map((k) => k.words))) : null].filter(Boolean)
        : [h("p", { class: "cap" }, judging ? `${p.skeptic?.name || "The Skeptic"} argues once the four views are in.` : "Not made yet.")])),
      sec("Decision", ...decisionBlock(p, state), goalLine(p, node)),
      p.sent ? sec("Sent", h("p", { class: "pitch__said" }, `To ${p.sent.name || p.sent.party}${p.sent.type ? `, as ${p.sent.type}` : ""}: ${p.sent.title || p.sent.goal}`)) : null,
      p.passed ? sec("Passed", h("p", { class: "pitch__said" }, p.passed.why || "No reason given."), p.passed.as_decided ? h("p", { class: "cap" }, "As the Investor said.") : null) : null,
      rest.length ? h("div", { class: "pitch__more", role: "group", "aria-label": "More" }, ...rest) : null,
      note ? h("p", { class: "muted pitch__note", role: "status" }, note) : null,
    ].filter(Boolean));
    acts.replaceChildren(...foot, ...(err ? [h("p", { class: "warn pitch__err", role: "alert" }, err)] : []));
    acts.hidden = !foot.length && !err;
    acts.classList.toggle("is-edit", Boolean(mode));
    const inner = sh.el.querySelector(".sheet-in");
    if (inner) inner.scrollTop = kept;
  }

  /** Opens the pitch `which`; `pick`: the party to have picked in its select (a party just made for it). */
  function open(which, pick = "") {
    const fresh = which !== slug || !sh.el.open;
    slug = which;
    if (fresh) { page = null; mode = ""; draft = ""; why = ""; note = ""; err = ""; party = pick || ""; }
    if (pick) party = pick;
    sh.open();
    draw();
    read();
  }
  sh.el.addEventListener("close", () => { seq += 1; mode = ""; });

  return {
    sheets: [sh.el],
    open,
    /** The Board was read again: an open sheet draws what the Map says now and reads its page again when the Board changed. */
    sync() {
      if (!sh.el.open) return;
      if (st.snap?.ideas_rev !== readRev) read(); else draw(false);
    },
  };
}
