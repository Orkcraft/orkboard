// The Board tab (docs/specs/35-goals-window.md §11, one column; 33-v1-shell.md §6): the Target chip in its header; Goals — a select with New
// goal beside it, and the chosen goal's summary line, Open and Edit; Needs you; the Ideas. A tap opens the idea's spec, or the plan,
// on its own screen; every dialog is a sheet. A secret or a file is entered only over this paired link (29a).
import { h, sheet } from "./util.js";
import { steady } from "./shell-util.js";
import { makeGoalSheet, GOAL_STATE } from "./shell-goal.js";
import { makeNeeds } from "./shell-needs.js";
import { makeIdeas, BUSY } from "./shell-ideas.js";
import { PRIORITY_WORDS, TARGETS, targetWord } from "./shell-words.js";

export { BUSY };

const STATE_WORDS = { raw: "new", reading: "the Taskmaster is reading", asks: "asks you", ready: "ready", planning: "the Taskmaster is planning",
  plan: "plan ready", working: "working", done: "done", failed: "needs you" };
const GOAL_SHORT = { reading: "reading", asks: "asks you", ready: "ready" };

export function stateWords(idea) {
  const p = idea.progress;
  if (idea.state === "working" && p && p.total) return `working ${p.done}/${p.total}`;
  return STATE_WORDS[idea.state] || idea.state;
}

export function makeBoardTab(core, ctx) {
  const st = core.st;
  const pane = h("section", { class: "pane board-tab-pane", "aria-label": "Board" });
  const fresh = steady(pane);
  const goals = () => (st.board?.tracks || []).filter((t) => t.slug !== "general");

  const goalSheet = makeGoalSheet(core);
  const needs = makeNeeds(core, ctx);
  const ideas = makeIdeas(core, ctx, goalSheet);

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

  // -- goals (§11.1): a select with New goal beside it; a chosen goal shows its summary's first line, Open and Edit ------
  function goalsBlock() {
    const list = goals();
    const pick = h("select", { class: "ok-input", "aria-label": "Goal" }, h("option", { value: "" }, "All goals"),
      ...list.map((g) => h("option", { value: g.slug }, [g.title, PRIORITY_WORDS[g.priority] || "Normal", GOAL_SHORT[g.state]].filter(Boolean).join(" · "))));
    pick.value = st.track;
    pick.addEventListener("change", () => { st.track = pick.value; core.draw(); });
    const kids = [h("div", { class: "row goal-pick" }, pick, h("button", { class: "ok-btn", type: "button", onclick: () => goalSheet.open() }, "New goal"))];
    const g = list.find((x) => x.slug === st.track);
    if (g) {
      const line = String(g.summary || "").split("\n").find((l) => l.trim()) || (g.state === "reading" ? "The Taskmaster is reading the goal…" : "");
      kids.push(h("div", { class: "card goal-now", "data-goal": g.slug },
        line ? h("p", { class: "goal-line" }, line) : null,
        h("span", { class: "goal-meta" }, h("span", { class: `prio prio-${g.priority}` }, PRIORITY_WORDS[g.priority] || "Normal"),
          GOAL_STATE[g.state] ? h("span", { class: `state-word ${g.state === "reading" ? "work" : g.state}` }, GOAL_STATE[g.state]) : null),
        h("div", { class: "row" }, h("button", { class: "ok-btn", type: "button", onclick: () => core.open({ kind: "goal", slug: g.slug }) }, "Open"),
          h("button", { class: "ok-btn", type: "button", "aria-label": `Edit goal ${g.title}`, onclick: () => goalSheet.open(g.slug) }, "Edit"))));
    }
    return h("div", { class: "goals" }, h("h3", {}, "Goals"), ...kids);
  }

  return {
    el: pane,
    editGoal: (slug) => goalSheet.open(slug),
    sheets: [goalSheet.el, ...needs.sheets, ...ideas.sheets, targetSheet.el],
    draw() {
      if (!fresh(JSON.stringify([st.board, st.track]))) return;
      if (!st.board) { pane.replaceChildren(h("h2", {}, "Board"), h("p", { class: "muted" }, "Loading…")); return; }
      if (st.track && !goals().some((t) => t.slug === st.track)) st.track = "";
      target.replaceChildren(h("span", { class: "word" }, "Target:"), " ", h("b", {}, targetWord(st.board.target)));
      target.setAttribute("aria-label", `Target: ${targetWord(st.board.target)}`);
      pane.replaceChildren(h("div", { class: "pane-head" }, h("h2", {}, "Board"), target), goalsBlock(), ...needs.draw(), ...ideas.section(),
        h("p", { class: "muted foot-line" }, h("button", { class: "linkish", type: "button", onclick: () => ctx.unpair() }, "Unpair this phone")));
    },
  };
}
