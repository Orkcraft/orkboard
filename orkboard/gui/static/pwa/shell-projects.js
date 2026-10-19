// The project switcher on the phone (docs/specs/37-board-and-line.md §8): a drawer from the left, the projects open at the computer,
// each with what is working, what needs you and what waits in Review; a tap shows that one. A project is opened and closed at the
// computer, never from the phone: the recent ones are only named. Under them, the documents the goal shown links (read only, §8).
// Read again when the snapshot's `rev` moves.
import { h, sheet, icon } from "./util.js";
import { foot } from "./shell-forms.js";

const count = (n, one, many) => (n ? `${n} ${n === 1 ? one : many}` : "");

/** "2 working · 1 needs you · 3 to review", or "Nothing waiting". */
export function countWords(p) {
  const parts = [count(p.working, "working", "working"), count(p.needs_you, "needs you", "need you"), count(p.review, "to review", "to review")];
  return parts.filter(Boolean).join(" · ") || "Nothing waiting";
}

/** `core`: the board's frame (board.js). Returns {chip, sheets, render(snapshot)}. */
export function makeProjects(core, ctx) {
  const chip = h("button", { class: "project-chip", type: "button", "aria-haspopup": "dialog" });
  const body = h("div", { class: "projects" });
  const docs = h("div", { class: "project-docs" });
  const sh = sheet("Projects", body, docs, foot(h("button", { class: "ork-btn primary big", type: "button", onclick: () => sh.close() }, "Done")));
  sh.el.classList.add("drawer");
  /** The goal's links that are files of the project: each opens read only on its screen. */
  function drawDocs() {
    const g = (core.st.board?.tracks || []).find((t) => t.slug === core.st.track);
    const paths = (g?.links || []).filter((l) => !/^[a-z][a-z0-9+.-]*:\/\//i.test(l));
    docs.replaceChildren(...(g ? [h("h3", {}, `${g.title}: its documents`), paths.length
      ? h("ul", { class: "project-list" }, ...paths.map((p) => h("li", {}, h("button", { class: "project-row", type: "button",
        onclick: () => { sh.close(); core.open({ kind: "doc", slug: g.slug, path: p }); } }, h("b", {}, p)))))
      : h("p", { class: "muted" }, "The goal links no file yet: the Taskmaster adds the ones it finds.")] : []));
  }
  let list = null;
  let name = "";
  let seq = 0;

  function draw() {
    if (!list) { body.replaceChildren(h("p", { class: "muted" }, "Loading…")); return; }
    const open = list.open || [];
    const recent = list.recent || [];
    body.replaceChildren(...[
      open.length ? h("ul", { class: "project-list" }, ...open.map((p) => h("li", {},
        h("button", { class: "project-row", type: "button", "aria-current": p.path === list.current ? "true" : null, onclick: () => use(p) },
          h("b", {}, p.name), h("small", { class: "muted" }, countWords(p)), p.path === list.current ? h("small", { class: "muted" }, "Shown now") : null))))
        : h("p", { class: "muted" }, "No project is open. Open a folder at the computer."),
      recent.length ? h("h3", {}, "Recent, not open") : null,
      recent.length ? h("ul", { class: "project-list" }, ...recent.map((p) => h("li", { class: "project-recent" }, h("b", {}, p.name)))) : null,
      h("p", { class: "muted" }, "A project is opened and closed at the computer. From the phone you choose which open one to show.")]
      .filter(Boolean));                                  // no recent ones: nothing, not "null"
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

  chip.addEventListener("click", () => { drawDocs(); sh.open(); load(); });
  draw();

  return {
    chip,
    sheets: [sh.el],
    render(s, rev) {
      name = s.project || "";
      chip.replaceChildren(icon("folder"));                // the top bar says the project's name over the goal
      chip.setAttribute("aria-label", name ? `Project ${name}: choose another` : "No project open");
      if (rev !== undefined) load();
    },
  };
}
