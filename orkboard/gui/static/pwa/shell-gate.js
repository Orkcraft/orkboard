// The gate's screen on the phone (docs/specs/49-one-window.md §2.1, §5.6, §10.2): dev → main, the one press that merges dev into main (decisions §49.5). What dev holds that
// main lacks is `ideas.gate`'s: the ideas with a merged task among those commits, with their goals, and the counts of commits and files; **Merge dev into main** is
// `ideas.gate_merge`. Nothing reaches main without the person. After the merge the screen says *main has every idea of dev* and the button is gone.
import { h } from "./util.js";

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The gate's words for a reading of `ideas.gate` (`{into, main, commits, files, ideas}`): the line under the title and whether anything waits. */
export function gateWords(g) {
  const n = (g.ideas || []).length, waits = g.commits > 0 || n > 0;
  return { waits, line: waits ? `${n ? plural(n, "idea") : plural(g.commits, "commit")} in ${g.into} wait for ${g.main}` : `${g.main} has every idea of ${g.into}` };
}

/** The screen's title, body and pinned actions for the reading `g`. `core`: the board's frame; `act(name, args, said)`: the preview's own (flashes, reads again). */
export function gateScreen(g, core, act) {
  const { waits, line } = gateWords(g);
  const goals = Object.fromEntries((core.st.map?.goals || []).map((x) => [x.slug, x.title]));
  const body = [
    h("p", { class: "muted", "data-gate": waits ? "waits" : "done" }, line),
    h("h3", {}, waits ? `In ${g.into}, not in ${g.main}` : `In ${g.main}`),
    (g.ideas || []).length ? h("ul", { class: "gate-ideas" }, ...g.ideas.map((i) => h("li", {},
      h("button", { class: "linkish gate-idea", type: "button", "data-idea": i.slug, onclick: () => core.open({ kind: "idea", slug: i.slug }, "gate") },
        h("span", { class: "ok", "aria-hidden": "true" }, "✓ "), i.title),
      h("small", { class: "muted" }, ` ${[goals[i.goal] || i.goal, plural(i.tasks, "task")].filter(Boolean).join(" · ")}`))))
      : h("p", { class: "muted" }, waits ? "No idea of the Board: the commits are not a task's." : "Nothing."),
    waits ? h("p", { class: "muted" }, `${plural(g.commits, "commit")} · ${plural(g.files, "file")} changed`) : null,
    h("p", { class: "muted" }, "Nothing reaches main without you."),
  ].filter(Boolean);
  const actions = waits ? [h("button", { class: "ork-btn primary big", type: "button", "data-act": "gate-merge",
    onclick: async (e) => { e.currentTarget.disabled = true; const r = await act("ideas.gate_merge", {}, `Merged: ${g.main} has every idea of ${g.into}.`); if (r?.note) core.flash(r.note); } },
  `Merge ${g.into} into ${g.main}`)] : [];
  return { title: [h("span", { class: "muted" }, "The gate "), `${g.into} → ${g.main}`], body, actions };
}
