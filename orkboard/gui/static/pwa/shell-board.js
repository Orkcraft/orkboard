// The Board tab (docs/specs/35-goals-window.md §11, one column; 33-v1-shell.md §6): the Target chip in its header; the goal shown (chosen in
// the top bar: the one this phone showed last, else the first) — its head, summary line, how far its ideas are, Open and Edit; then its
// Ideas, the done ones folded at the end. Needs you is a screen of its own (board.js). Operations and the Map take the tab's place, Board
// back. A tap opens the idea's spec, or the plan, on its own screen; every dialog is a sheet. A secret or a file is entered only over
// this paired link (29a).
import { h, sheet } from "./util.js";
import { steady } from "./shell-util.js";
import { makeGoalSheet, GOAL_STATE } from "./shell-goal.js";
import { makeIdeas, BUSY } from "./shell-ideas.js";
import { makeOps, OPS_VIEW } from "./shell-ops.js";
import { makeMap, MAP_VIEW } from "./shell-map.js";
import { PRIORITY_WORDS, TARGETS, targetWord } from "./shell-words.js";
import { CRAFT_WORDS, goalHead } from "./shell-who.js";
import { keptGoal } from "./shell-top.js";

export { BUSY };

const STATE_WORDS = { raw: "new", reading: "the Taskmaster is reading", asks: "asks you", ready: "ready", planning: "the Taskmaster is planning",
  plan: "plan ready", working: "working", done: "done", failed: "needs you" };

export function stateWords(idea) {
  const p = idea.progress;
  if (idea.state === "working" && p && p.total) return `working ${p.done}/${p.total}`;
  return STATE_WORDS[idea.state] || idea.state;
}

export function makeBoardTab(core, ctx) {
  const st = core.st;
  const pane = h("section", { class: "pane board-tab-pane", "aria-label": "Board" });
  const fresh = steady(pane);
  const goals = () => (st.board?.tracks || []).filter((t) => t.slug !== "general" || t.count);   // General once it holds ideas (older ones)

  const goalSheet = makeGoalSheet(core);
  const ops = makeOps(core, ctx);
  const ideas = makeIdeas(core, ctx, goalSheet);
  const map = makeMap(core, goalSheet);
  let mapRev;                                        // the board's rev the Map was read at

  /** The Map is read again when the board's rev moves, not on a clock of its own (spec 39 §4.8). */
  async function loadMap() {
    const rev = st.board?.rev;
    mapRev = rev;
    const r = await ctx.send("ideas.map");
    if (mapRev !== rev || st.view !== MAP_VIEW) return;
    if (r.ok && r.result && !r.result.error) { st.map = r.result; st.mapError = ""; }
    else st.mapError = r.error || r.result?.error || "Loading…";
    core.draw();
  }
  function showMap() {
    st.view = MAP_VIEW;
    mapRev = undefined;
    map.enter();
    ctx.send("ideas.log", { event: "opened", what: "map", device: "phone" });
    core.draw();
  }

  // -- the Target: the Board's one setting (§1), in the header ------------------------------------------------------
  const picks = TARGETS.map(([id, word, line]) => {
    const input = h("input", { type: "radio", name: "target", value: id, "aria-label": word });
    input.addEventListener("change", async () => {
      if (await core.call("ideas.board_set", { target: id })) { targetSheet.close(); core.refresh(); }
    });
    return [id, input, h("label", { class: "target-pick" }, input, h("span", { class: "need-text" }, h("b", {}, word), h("small", {}, line)))];
  });
  const targetSheet = sheet("Target", h("p", { class: "muted" }, "One setting for the whole route: the Board, Agents and Review."), ...picks.map((p) => p[2]));
  const target = h("button", { class: "target-chip", type: "button", "aria-haspopup": "dialog", onclick: () => {
    for (const [id, input] of picks) input.checked = id === (st.board?.target || "balance");
    targetSheet.open();
  } });

  // -- the goal shown (§11.1, chosen in the top bar, shell-top.js): its card — the summary's first line, its craft, priority and state,
  // Open and Edit — and how far its ideas are, in words. With no goal yet: New goal.
  function goalBlock() {
    const g = goals().find((x) => x.slug === st.track);
    if (!g) {
      return h("div", { class: "card goal-now" }, h("p", {}, "No goal yet. A goal says what the ideas are for; the Taskmaster reads it first."),
        h("div", { class: "row" }, h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open() }, "New goal")));
    }
    const line = String(g.summary || "").split("\n").find((l) => l.trim()) || (g.state === "reading" ? "The Taskmaster is reading the goal…" : "");
    const mine = (st.board.ideas || []).filter((i) => i.track === g.slug);
    const done = mine.filter((i) => i.state === "done").length, working = mine.filter((i) => i.state === "working").length;
    return h("div", { class: "card goal-now", "data-goal": g.slug },
      line ? h("p", { class: "goal-line" }, line) : null,
      h("span", { class: "goal-meta" }, goalHead(g, true), h("span", { class: "craft-word" }, CRAFT_WORDS[g.craft] || CRAFT_WORDS.engineering),
        h("span", { class: `prio prio-${g.priority}` }, PRIORITY_WORDS[g.priority] || "Normal"),
        GOAL_STATE[g.state] ? h("span", { class: `state-word ${g.state === "reading" ? "work" : g.state}` }, GOAL_STATE[g.state]) : null),
      mine.length ? h("p", { class: "goal-progress muted" }, `${done} of ${mine.length} ideas done${working ? ` · ${working} working` : ""}`) : null,
      h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => core.open({ kind: "goal", slug: g.slug }) }, "Open"),
        h("button", { class: "ork-btn", type: "button", "aria-label": `Edit goal ${g.title}`, onclick: () => goalSheet.open(g.slug) }, "Edit")));
  }

  /** The New… and Settings buttons beside Operations' heading, with no project open. */
  function opsButtons() {
    return h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", onclick: () => ops.openMenu() }, "New…"),
      h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", "aria-label": "Operations settings", onclick: () => ops.openGear() }, "Settings"));
  }

  return {
    el: pane,
    editGoal: (slug) => goalSheet.open(slug),
    ops,
    sheets: [...goalSheet.sheets, ...ops.sheets, ...ideas.sheets, targetSheet.el],
    showMap,
    fab: ideas.fab,
    /** New idea's button is on the Board of a goal (not Operations', nor the Map's). */
    fabOn: () => Boolean(st.board) && !st.view,
    draw() {
      if (!fresh(JSON.stringify([st.board, st.track, st.view, st.ops, st.boardError, st.map, st.mapError]))) return;
      const unpair = h("p", { class: "muted foot-line" }, h("button", { class: "linkish", type: "button", onclick: () => ctx.unpair() }, "Unpair this phone"));
      if (!st.board && st.boardError) {                // no project open: Operations is the person's, so it is offered all the same
        pane.replaceChildren(h("div", { class: "pane-head" }, h("h2", {}, "Board")), h("p", { class: "muted" }, st.boardError),
          h("div", { class: "section-head" }, h("h3", {}, "Operations"), opsButtons()), ...ops.section(), unpair);
        return;
      }
      if (!st.board) { pane.replaceChildren(h("h2", {}, "Board"), h("p", { class: "muted" }, "Loading…")); return; }
      if (!goals().some((t) => t.slug === st.track)) {             // the goal this phone showed last, else the first
        const kept = keptGoal(st.snap?.project);
        st.track = (goals().find((t) => t.slug === kept) || goals()[0])?.slug || "";
        if (st.tab === "board") queueMicrotask(() => core.draw());                // the top bar names it
      }
      target.replaceChildren(h("span", { class: "word" }, "Target:"), " ", h("b", {}, targetWord(st.board.target)));
      target.setAttribute("aria-label", `Target: ${targetWord(st.board.target)}`);
      const inOps = st.view === OPS_VIEW;
      const inMap = st.view === MAP_VIEW;
      if (inMap && mapRev !== st.board.rev) { if (mapRev === undefined) { st.map = null; st.mapError = ""; } loadMap(); }
      const gear = h("button", { class: "ork-btn gear", type: "button", "aria-haspopup": "dialog", "aria-label": "Operations settings", onclick: () => ops.openGear() }, "Settings");
      const back = h("div", { class: "row goal-pick" }, inOps ? h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", onclick: () => ops.openMenu() }, "New…") : null,
        h("button", { class: "ork-btn", type: "button", "aria-label": "Back to the Board", onclick: () => { st.view = ""; core.draw(); } }, "Board"));
      pane.replaceChildren(h("div", { class: "pane-head" }, h("h2", {}, inMap ? "Map" : inOps ? "Operations" : "Board"), inOps ? gear : target),
        ...(inOps ? [back, ...ops.section()] : inMap ? [back, ...map.section()] : [goalBlock(), ...ideas.section()]), unpair);
    },
  };
}
