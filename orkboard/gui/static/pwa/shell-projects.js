// The Projects sheet on the phone (docs/specs/37-board-and-line.md §8, spec 50 §6.1): from the top bar's project name, a sheet from the top with the projects open at the computer as rows — the name, *this
// one*, what waits (what is working, what needs you, what waits in Review) — and a line that says where projects are opened; a tap switches this phone to one (`projects.use`). A project is opened and
// closed at the computer, never from the phone. Read again when the snapshot's `rev` moves. (The menu — Stop all, Spend, Agents and the settings — is shell-top.js's.)
import { h, sheet } from "./util.js";

const count = (n, one, many) => (n ? `${n} ${n === 1 ? one : many}` : "");

/** "2 working · 1 needs you · 3 to review", or "nothing waits". */
export function countWords(p) {
  const parts = [count(p.working, "working", "working"), count(p.needs_you, "needs you", "need you"), count(p.review, "to review", "to review")];
  return parts.filter(Boolean).join(" · ") || "nothing waits";
}

/** `core`: the board's frame; `ctx`: {send}. Returns {open(), sheet, sheets, render(snapshot, rev)}. */
export function makeProjects(core, ctx) {
  const body = h("div", { class: "projects" });
  const sh = sheet("Projects", h("p", { class: "muted" }, "Open on your computer: a tap switches this phone to one."), body);
  sh.el.classList.add("top");
  let list = null;
  let seq = 0;

  function draw() {
    if (!list) { body.replaceChildren(h("p", { class: "muted" }, "Loading…")); return; }
    const open = list.open || [];
    body.replaceChildren(open.length ? h("ul", { class: "project-list" }, ...open.map((p) => h("li", {},
      h("button", { class: "project-row", type: "button", "aria-current": p.path === list.current ? "true" : null, "data-project": p.name, onclick: () => use(p) },
        h("b", {}, p.name), h("small", { class: "muted" }, [p.path === list.current ? "this one" : "", countWords(p)].filter(Boolean).join(" · "))))))
      : h("p", { class: "muted" }, "No project is open. Open a folder at the computer."));
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
    sh.close();
  }

  draw();

  return {
    open() { sh.open(); load(); },
    sheet: sh,
    sheets: [sh.el],
    render(s, rev) { if (rev !== undefined) load(); },
  };
}
