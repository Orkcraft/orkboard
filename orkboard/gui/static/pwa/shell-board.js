// The Board tab (docs/specs/35-goals-window.md §11, one column; 33-v1-shell.md §6; decisions §53): the Target chip in its header; the Map
// — the goals as tabs with how far each is, the goal shown (the top bar's: the one this phone showed last, else the first) as a trail
// from its % through its ideas left to its flag (shell-map.js). Needs you is a tab of its own, with Review (board.js). Operations takes
// the tab's place, Board back. A tap opens the idea's spec, or a task, on its own screen; every dialog is a sheet. A secret or a file is
// entered only over this paired link (29a).
import { h, sheet } from "./util.js";
import { steady } from "./shell-util.js";
import { makeGoalSheet } from "./shell-goal.js";
import { makeIdeas, BUSY } from "./shell-ideas.js";
import { makeOps, OPS_VIEW } from "./shell-ops.js";
import { makeMap } from "./shell-map.js";
import { TARGETS, targetWord } from "./shell-words.js";
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

  /** The Map — the Board's trails — is read again when the board's rev moves, not on a clock of its own (spec 39 §4.8). */
  async function loadMap() {
    const rev = st.board?.rev;
    if (mapRev === undefined) {                       // the first time this Board is shown: *new* since the last time
      map.enter();
      ctx.send("ideas.log", { event: "opened", what: "map", device: "phone" });
    }
    mapRev = rev;
    const r = await ctx.send("ideas.map");
    if (mapRev !== rev || st.view === OPS_VIEW) return;
    if (r.ok && r.result && !r.result.error) { st.map = r.result; st.mapError = ""; }
    else st.mapError = r.error || r.result?.error || "Loading…";
    core.draw();
  }
  /** The Map is the Board: showing it is showing the Board. */
  function showMap() {
    st.view = "";
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

  /** The New… and Settings buttons beside Operations' heading, with no project open. */
  function opsButtons() {
    return h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", onclick: () => ops.openMenu() }, "New…"),
      h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", "aria-label": "Operations settings", onclick: () => ops.openGear() }, "Settings"));
  }

  return {
    el: pane,
    editGoal: (slug) => goalSheet.open(slug),
    ops,
    sheets: [...goalSheet.sheets, ...ops.sheets, ...ideas.sheets, ...map.sheets, targetSheet.el],
    showMap,
    fab: ideas.fab,
    /** New idea's button is on the Board of a goal (not Operations', nor the Map's). */
    fabOn: () => Boolean(st.board) && !st.view,
    draw() {
      if (!fresh(JSON.stringify([st.board, st.track, st.mapGoal, st.view, st.ops, st.boardError, st.map, st.mapError, st.roles?.roles?.length]))) return;
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
      if (!inOps && mapRev !== st.board.rev) { if (mapRev === undefined) { st.map = null; st.mapError = ""; } loadMap(); }
      const gear = h("button", { class: "ork-btn gear", type: "button", "aria-haspopup": "dialog", "aria-label": "Operations settings", onclick: () => ops.openGear() }, "Settings");
      const back = h("div", { class: "row goal-pick" }, inOps ? h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", onclick: () => ops.openMenu() }, "New…") : null,
        h("button", { class: "ork-btn", type: "button", "aria-label": "Back to the Board", onclick: () => { st.view = ""; core.draw(); } }, "Board"));
      pane.replaceChildren(h("div", { class: "pane-head" }, h("h2", {}, inOps ? "Operations" : "Board"), inOps ? gear : target),
        ...(inOps ? [back, ...ops.section()] : map.section()), unpair);
    },
  };
}
