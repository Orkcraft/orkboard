// The gate's screen on the phone (docs/specs/49-one-window.md §2.1, §5.6, §10.2; spec 50 §6.3): dev → main, the one press that merges dev into main (decisions §49.5). What dev holds that
// main lacks is `ideas.gate`'s: the goals with a merged task among those commits, with their parties, and the counts of commits and files; **Merge dev into main** is
// `ideas.gate_merge`. Nothing reaches main without the person. After the merge the screen says *main has every goal of dev* and the button is gone; the box of the merge's press is kept 10 s,
// where the flags the merge raised travel from (docs/specs/64-flags-raised.md §1.3).
import { h } from "./util.js";
import { sign } from "./shell-marks.js";

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const KEPT_MS = 10000;                                // the person merged a moment ago: the press's box is the flags' source this long

let pressed = null;
/** The box of the gate's merge press (the screen may be gone by the time the flag line stands). */
export const gatePress = {
  /** The merge was pressed on `el`: its box (client coordinates) is kept. */
  press(el) {
    const r = el.getBoundingClientRect();
    pressed = r.width > 0 ? { box: { left: r.left, top: r.top, width: r.width, height: r.height }, at: Date.now() } : null;
  },
  /** The merge was refused: nothing was raised. */
  drop() { pressed = null; },
  /** The press's box (null once it is 10 s old). */
  box() {
    if (pressed && Date.now() - pressed.at > KEPT_MS) pressed = null;
    return pressed ? pressed.box : null;
  },
};

/** The gate's words for a reading of `ideas.gate` (`{into, main, commits, files, ideas}`): the line under the title and whether anything waits. */
export function gateWords(g) {
  const n = (g.ideas || []).length, waits = g.commits > 0 || n > 0;
  return { waits, line: waits ? `${n ? plural(n, "goal") : plural(g.commits, "commit")} in ${g.into} wait for ${g.main}` : `${g.main} has every goal of ${g.into}` };
}

/** The screen's title, body and pinned actions for the reading `g`. `core`: the board's frame; `act(name, args, said)`: the preview's own (flashes, reads again). */
export function gateScreen(g, core, act) {
  const { waits, line } = gateWords(g);
  const parties = Object.fromEntries((core.st.map?.goals || []).map((x) => [x.slug, x.title]));
  const body = [
    h("p", { class: "muted", "data-gate": waits ? "waits" : "done" }, line),
    h("h3", {}, waits ? `In ${g.into}, not in ${g.main}` : `In ${g.main}`),
    (g.ideas || []).length ? h("ul", { class: "gate-ideas" }, ...g.ideas.map((i) => h("li", {},
      h("button", { class: "linkish gate-idea", type: "button", "data-idea": i.slug, onclick: () => core.open({ kind: "idea", slug: i.slug }, "gate") },
        sign("check"), " ", i.title),
      h("small", { class: "muted" }, ` ${[parties[i.goal] || i.goal, plural(i.tasks, "task")].filter(Boolean).join(" · ")}`))))
      : h("p", { class: "muted" }, waits ? "No goal of the Board: the commits are not a task's." : "Nothing."),
    waits ? h("p", { class: "muted" }, `${plural(g.commits, "commit")} · ${plural(g.files, "file")} changed`) : null,
    h("p", { class: "muted" }, "Nothing reaches main without you."),
  ].filter(Boolean);
  const actions = waits ? [h("button", { class: "ork-btn primary big", type: "button", "data-act": "gate-merge",
    onclick: async (e) => {
      gatePress.press(e.currentTarget);                // before the button is disabled and the screen redrawn: the flags raised travel from here
      e.currentTarget.disabled = true;
      const r = await act("ideas.gate_merge", {}, `Merged: ${g.main} has every goal of ${g.into}.`);
      if (!r) gatePress.drop();
      else if (r.note) core.flash(r.note);
    } },
  `Merge ${g.into} into ${g.main}`)] : [];
  return { title: [h("span", { class: "muted" }, "The gate "), g.into, " ", sign("after"), " ", g.main], body, actions };
}
