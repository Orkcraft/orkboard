// The lens a new idea is written with, on the phone (realm/idea_lens.py; decisions §53): beside the text — always there, and
// enough alone —, what to point at in the way of the goal's party. A row of lenses, the ones the party has: Text; Code (an
// engineer's: the repository's parts, what each uses and what uses it, and a note of what to change); Screen (a designer's:
// shell-lens-screen.js); Pain (a product manager's: whom it is for and what hurts them, the project's own kept a tap away).
// The leader's lens is open first. What each lens holds goes with the idea; switching lenses loses nothing.
import { h } from "./util.js";
import { makeScreenLens } from "./shell-lens-screen.js";

const WORDS = { text: "Text", code: "Code", screen: "Screen", pain: "Pain" };
const SHOWN = 6;                       // the kept segments and pains offered as chips

/** `core`: the board's frame (its `call`); `ctx`: {flash}. Returns {el, track(slug), value(), reset()}. */
export function makeLens(core, ctx) {
  let lenses = [{ id: "text" }];
  let on = "text";
  let of = "";
  let segments = [];
  const bar = h("div", { class: "lens-bar", role: "radiogroup", "aria-label": "Lens", hidden: true });

  // -- Pain: whom it is for, what hurts them ----------------------------------------------------------------------------
  const segment = h("input", { class: "ork-field", type: "text", maxlength: "120", "aria-label": "For whom", placeholder: "Shop owners, new users…" });
  const pain = h("input", { class: "ork-field", type: "text", maxlength: "300", "aria-label": "What hurts them", placeholder: "What goes wrong for them" });
  const segChips = h("div", { class: "answers lens-chips", role: "group", "aria-label": "Kept segments" });
  const painChips = h("div", { class: "answers lens-chips", role: "group", "aria-label": "Their pains" });
  const chip = (text, input, then) => h("button", { class: "ork-btn answer", type: "button", "aria-pressed": String(input.value === text),
    onclick: () => { input.value = text; then(); } }, text);
  function drawPain() {
    segChips.replaceChildren(...segments.slice(0, SHOWN).map((s) => chip(s.segment, segment, () => { pain.value = ""; drawPain(); })));
    const mine = segments.find((s) => s.segment.toLowerCase() === segment.value.trim().toLowerCase());
    painChips.replaceChildren(...(mine?.pains || []).slice(0, SHOWN).map((p) => chip(p, pain, drawPain)));
  }
  segment.addEventListener("input", drawPain);
  const painPane = h("div", { class: "lens-pane", "data-lens": "pain" },
    h("label", { class: "field" }, h("span", { class: "field-label" }, "For whom"), segment), segChips,
    h("label", { class: "field" }, h("span", { class: "field-label" }, "What hurts them"), pain), painChips);

  // -- Code: the repository's parts, what each uses and what uses it --------------------------------------------------------
  let parts = null;                    // ideas.lens_code, read once the lens is opened
  let picked = [];
  const filter = h("input", { class: "ork-field", type: "search", "aria-label": "Find a part", placeholder: "Find a part: a folder" });
  const partList = h("ul", { class: "lens-parts", "aria-label": "The repository's parts" });
  const note = h("textarea", { class: "ork-field", rows: "2", maxlength: "1000", "aria-label": "What to change there", placeholder: "What to change there" });
  const chosen = h("p", { class: "muted lens-picked" });
  function drawParts() {
    chosen.textContent = picked.length ? `Picked: ${picked.join(", ")}` : "Pick the parts the idea changes.";
    if (!parts) { partList.replaceChildren(h("li", { class: "muted" }, "Reading the repository…")); return; }
    const near = new Set(parts.filter((p) => picked.includes(p.path)).flatMap((p) => [...p.uses, ...p.used_by]));
    const q = filter.value.trim().toLowerCase();
    const shown = parts.filter((p) => !q || p.path.toLowerCase().includes(q) || picked.includes(p.path))
      .sort((a, b) => (picked.includes(b.path) - picked.includes(a.path)) || (near.has(b.path) - near.has(a.path)));
    partList.replaceChildren(...shown.slice(0, 60).map((p) => {
      const isOn = picked.includes(p.path);
      return h("li", {}, h("button", { class: `lens-part${near.has(p.path) && !isOn ? " is-near" : ""}`, type: "button", "aria-pressed": String(isOn),
        "aria-label": `${isOn ? "Leave out" : "Pick"}: ${p.path}`,
        onclick: () => { picked = isOn ? picked.filter((x) => x !== p.path) : [...picked, p.path].slice(0, 12); drawParts(); } },
        h("b", {}, p.path === "." ? "The top folder" : p.path), h("small", { class: "muted" }, `${p.count} file${p.count === 1 ? "" : "s"}`
          + (p.uses.length ? ` · uses ${p.uses.slice(0, 3).join(", ")}${p.uses.length > 3 ? "…" : ""}` : "")
          + (p.used_by.length ? ` · used by ${p.used_by.length}` : ""))));
    }));
  }
  filter.addEventListener("input", drawParts);
  const codePane = h("div", { class: "lens-pane", "data-lens": "code" }, filter, chosen, partList,
    h("label", { class: "field" }, h("span", { class: "field-label" }, "What to change there"), note));

  // -- Screen ------------------------------------------------------------------------------------------------------------
  const screen = makeScreenLens(core, ctx);
  const screenPane = h("div", { class: "lens-pane", "data-lens": "screen" }, screen.el);
  const textPane = h("p", { class: "muted lens-hint lens-pane", "data-lens": "text" }, "The text alone is enough: the party reads it.");
  const panes = { text: textPane, code: codePane, screen: screenPane, pain: painPane };

  async function show(id) {
    on = id;
    for (const b of bar.children) b.setAttribute("aria-checked", String(b.dataset.lens === id));
    for (const [k, p] of Object.entries(panes)) p.hidden = k !== id;
    if (id === "code" && !parts) {
      drawParts();
      const got = await core.call("ideas.lens_code", {});
      parts = got?.parts || [];
      drawParts();
    }
  }
  function drawBar() {
    bar.hidden = lenses.length < 2;
    head.hidden = bar.hidden;
    bar.replaceChildren(...lenses.map((l) => h("button", { class: "ork-btn lens-chip", type: "button", role: "radio", "data-lens": l.id,
      "aria-checked": String(l.id === on), "aria-label": l.by ? `${WORDS[l.id]} · ${l.by}` : WORDS[l.id], onclick: () => show(l.id) },
      h("b", {}, WORDS[l.id]), h("small", {}, l.by || "only words"))));
  }

  const head = h("span", { class: "field-label" }, "Lens");
  const el = h("div", { class: "lens" }, head, bar, textPane, codePane, screenPane, painPane);
  for (const [k, p] of Object.entries(panes)) p.hidden = k !== "text";
  return {
    el,
    /** The goal's lenses: read once per goal while the sheet is open; its leader's lens is shown. */
    async track(slug) {
      if (!slug || slug === of) return;
      of = slug;
      const got = await core.call("ideas.lens", { track: slug });
      if (!got || of !== slug) return;
      lenses = got.lenses;
      segments = got.segments || [];
      screen.load(got.screens);
      drawBar();
      drawPain();
      await show(lenses.some((l) => l.id === on) && on !== "text" ? on : got.default);
    },
    /** What `ideas.add` takes in `lens`: each lens's own, of the lenses the goal's party has. */
    value() {
      const has = new Set(lenses.map((l) => l.id));
      const out = [];
      if (has.has("pain") && (segment.value.trim() || pain.value.trim())) out.push({ kind: "pain", segment: segment.value.trim(), pain: pain.value.trim() });
      if (has.has("code") && picked.length) out.push({ kind: "code", paths: picked, note: note.value.trim() });
      if (has.has("screen")) out.push(...screen.value());
      return out;
    },
    reset() {
      of = ""; on = "text"; picked = []; segment.value = ""; pain.value = ""; note.value = ""; filter.value = "";
      screen.reset();
      for (const [k, p] of Object.entries(panes)) p.hidden = k !== "text";
    },
  };
}

/** What an idea's lens pointed at, for its spec: one line each (null with nothing). */
export function pointedAt(lens) {
  if (!(lens || []).length) return null;
  const line = (a) => (a.kind === "pain" ? [`Pain · ${a.segment || "whom: not said"}`, a.pain]
    : a.kind === "code" ? [`Code · ${a.paths.join(", ")}`, a.note]
      : [`Screen · ${a.name || "a screen"}`, (a.marks || []).map((m, i) => `${i + 1}) ${m.note || "marked"}`).join(" · ") || a.note]);
  return h("div", { class: "pointed", role: "list", "aria-label": "Pointed at" }, h("span", { class: "field-label" }, "Pointed at"),
    ...lens.map((a) => { const [head, more] = line(a); return h("p", { role: "listitem", "data-kind": a.kind }, h("b", {}, head), more ? h("small", { class: "muted" }, ` ${more}`) : null); }));
}
