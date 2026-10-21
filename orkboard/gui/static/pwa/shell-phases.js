// The field's phases and stacks as data (docs/specs/50-parties-and-goals.md §3.4, §6.5): a member's open tasks lie in rows by phase — *now* (a task at its goal's current wave: the lowest
// wave among the goal's open tasks), *next* (one wave after), *later* (two or more) — and in each row one stack per goal, in the Board's order. What a task waits for and what waits for it
// are two short lines (the phone draws no arrows). Pure: no node is made here.
export const PHASES = ["now", "next", "later"];

const open = (t) => t.state !== "merged" && t.state !== "dropped";

/** The lowest wave among a goal's open tasks: its current wave (1 with none open). */
export function lowWave(node) {
  const waves = (node.tasks || []).filter(open).map((t) => t.wave || 1);
  return waves.length ? Math.min(...waves) : 1;
}

/** 0 now, 1 next, 2 later: how many waves a task is after its goal's current one. */
export const phaseOf = (task, low) => Math.max(0, Math.min(PHASES.length - 1, (task.wave || 1) - low));

/** A member's task items (each with its `idea` and `phase`, in its column's order) as rows by phase: [{phase, stacks: [{key, idea, phase, items, top, n}]}]; a row that has nothing is left
 *  out. `order`: the goals' slugs in the Board's order. A stack is one goal's tasks of the member at one phase; its first item is the front card. */
export function rowsOf(items, order) {
  const rows = [];
  PHASES.forEach((phase, k) => {
    const stacks = [];
    for (const idea of order) {
      const mine = items.filter((i) => i.idea === idea && i.phase === k);
      if (mine.length) stacks.push({ key: `${idea}|${phase}`, idea, phase, items: mine, top: mine[0], n: mine.length });
    }
    if (stacks.length) rows.push({ phase, stacks });
  });
  return rows;
}

/** What a task waits for and what waits for it, in words: `{before: "waits for Challenge store" | "waits for the build" | "", after: "1 waits for it" | "2 wait for it" | ""}`. A task it waited
 *  for that is merged is not waited for any more. */
export function depWords(node, t) {
  const tasks = node.tasks || [];
  const byId = new Map(tasks.map((x) => [x.id, x]));
  const waitsOn = (t.after || []).map((id) => byId.get(id)).filter((x) => x && open(x)).map((x) => x.short || x.title);
  let before = "";
  if (waitsOn.length) before = `waits for ${waitsOn.length === 1 ? waitsOn[0] : waitsOn.length === 2 ? `${waitsOn[0]} and ${waitsOn[1]}` : `${waitsOn[0]} and ${waitsOn.length - 1} more`}`;
  else if (!(t.after || []).length && t.band === "check" && t.state === "waiting") before = "waits for the build";
  const n = tasks.filter((x) => open(x) && (x.after || []).includes(t.id)).length;
  return { before, after: n ? `${n} ${n === 1 ? "waits" : "wait"} for it` : "" };
}
