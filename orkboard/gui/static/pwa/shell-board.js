// The Board on the phone (docs/specs/35-goals-window.md §11; 33-v1-shell.md §6; decisions §53, §62; spec 49 §10): the goal's window (shell-arena.js) with the
// pieces it opens — the goal's and the party's sheets, Operations, New idea, the cards at the top (While you were away, Last week) and the flags. A tap on a
// task, an idea or a stop opens it on its own full screen; every dialog is a sheet. A secret or a file is entered only over this paired link (29a).
import { makeGoalSheet } from "./shell-goal.js";
import { makeIdeas, BUSY } from "./shell-ideas.js";
import { makeOps } from "./shell-ops.js";
import { makeArena } from "./shell-arena.js";
import { makeCards, pushWeek, isoWeek } from "./shell-cards.js";

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
  const goalSheet = makeGoalSheet(core);
  const ops = makeOps(core, ctx);
  const ideas = makeIdeas(core, ctx, goalSheet);
  const cards = makeCards(core);
  const arena = makeArena(core, ctx, { goalSheet, ops, ideas, cards });
  let mapLogged = false;                             // `opened` `map` is logged once per page load (spec 49 §9)

  // -- Last week (spec 42 §7.3): the first look of a new ISO week shows the card; `orkboard.week.<project>` holds the last week shown ---------
  let weekFor = "";                                  // the project the week was checked for
  let weekBusy = false;
  async function weekCheck() {
    const project = st.snap?.project;
    if (!project || weekBusy || !st.board || document.visibilityState === "hidden") return;
    const key = `orkboard.week.${project}`, last = isoWeek(new Date(Date.now() - 7 * 86400000));
    let kept = null;
    try { kept = localStorage.getItem(key); } catch { return; }
    weekFor = project;
    if (kept === last) return;
    const write = (week) => { try { localStorage.setItem(key, week); } catch { /* the page works without it */ } };
    if (kept === null) { write(last); return; }          // no key: written, nothing shown
    weekBusy = true;
    try {
      const got = await core.call("ideas.week");
      if (!got || project !== st.snap?.project) return;
      write(got.week);                               // the week `ideas.week` answered, not this device's idea of last week
      if (!got.empty && got.week !== kept) pushWeek(core, got);
    } finally { weekBusy = false; }
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") weekCheck(); });

  return {
    el: arena.el,
    editGoal: (slug) => goalSheet.open(slug),
    editTeam: (g) => goalSheet.editTeam(g),
    ops,
    show: arena.show,
    openNew: (goal) => ideas.openNew(goal),
    sheets: [...goalSheet.sheets, ...ops.sheets, ...ideas.sheets, ...arena.sheets],
    draw() {
      if (st.board && st.snap?.project && st.snap.project !== weekFor) weekCheck();
      if (st.map && !mapLogged) { mapLogged = true; ctx.send("ideas.log", { event: "opened", what: "map", device: "phone" }); }
      arena.draw();
    },
  };
}
