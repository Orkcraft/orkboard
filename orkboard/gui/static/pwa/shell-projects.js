// The projects, in the sheet of the top bar's project button (docs/specs/37-board-and-line.md §8, spec 52 §5.1; shell-where.js): *this one* first (the project shown, marked), then the projects open
// at the computer, as rows — the name and what waits (what is working, what needs you, what waits in Review) — and a line that says where projects are opened; a tap switches this phone to one (`projects.use`). A project is opened and closed at
// the computer, never from the phone. Read again when the snapshot's `rev` moves. (The menu — Stop all, Spend, Agents and the settings — is shell-top.js's.)
import { h } from "./util.js";

const count = (n, one, many) => (n ? `${n} ${n === 1 ? one : many}` : "");

/** "2 working · 1 needs you · 3 to review", or "nothing waits". */
export function countWords(p) {
  const parts = [count(p.working, "working", "working"), count(p.needs_you, "needs you", "need you"), count(p.review, "to review", "to review")];
  return parts.filter(Boolean).join(" · ") || "nothing waits";
}

/** `core`: the board's frame; `ctx`: {send}; `done()`: the sheet is put away after a switch. Returns {el, load(), render(snapshot, rev)}: `el` is the block of the Projects sheet. */
export function makeProjects(core, ctx, done) {
  const body = h("div", { class: "projects" });
  const el = h("section", { class: "projects-block", "aria-label": "Projects" }, body);
  let list = null;
  let seq = 0;

  function draw() {
    if (!list) { body.replaceChildren(h("p", { class: "muted" }, "Loading…")); return; }
    const others = (list.open || []).filter((p) => p.path !== list.current);
    const here = (list.open || []).find((p) => p.path === list.current) || (core.st.snap?.project ? { name: core.st.snap.project, path: list.current } : null);
    body.replaceChildren(...[here ? h("button", { class: "project-row", type: "button", "aria-current": "true", "data-project": here.name, onclick: () => done() },
      h("b", {}, here.name), h("small", { class: "muted" }, "this one")) : null, others.length ? h("ul", { class: "project-list" }, ...others.map((p) => h("li", {},
      h("button", { class: "project-row", type: "button", "data-project": p.name, onclick: () => use(p) }, h("b", {}, p.name), h("small", { class: "muted" }, countWords(p))))))
      : h("p", { class: "muted" }, "No other project is open. Open a folder at the computer."),
    others.length ? h("p", { class: "muted cap" }, "Open on your computer: a tap switches this phone to one.") : null].filter(Boolean));
  }

  async function load() {
    const mine = ++seq;
    const r = await ctx.send("projects.list");
    if (mine !== seq || !r.ok || r.result?.error) return;
    list = r.result;
    draw();
  }

  async function use(p) {
    if (p.path !== list?.current) {
      const r = await core.call("projects.use", { path: p.path });
      if (!r) return;
      core.close();
      core.reset();                      // the other project's Board replaces this one's
      load();
      await core.refresh();
    }
    done();
  }

  draw();

  return {
    el,
    load,
    render(s, rev) { if (rev !== undefined) load(); },
  };
}
