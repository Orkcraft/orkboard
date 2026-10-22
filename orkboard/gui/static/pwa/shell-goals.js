// The goals bar and the Goals sheet (docs/specs/50-parties-and-goals.md §3.5, §6.2, §6.4; spec 52 §5.2, §5.8). Under the top bar, one quiet line of 44 px that says the party: at its left
// *⌄ Tech · 3 of 12 goals done* (while the filter is on, the party, the picked goals' elements, *1 of 7 goals* and *Show all*), at its right the gate (shell-party.js). A tap on the left opens the Goals sheet from the bottom: *About Tech ›* (the party's sheet), a line that says
// what a tap does, **At work**, **Planning**, **Waits for main · n** (✓) and **Flags · n** (⚑); a goal's row (52 px) is its pile (a back with its element and one to three edges behind for its open tasks),
// its type's sign (muted) before its title, its title, its line, its mark (no alert edge, no alert words: the mark is the stop's one sign) and ✓ when picked, and › (44 px) that opens it. A tap picks or unpicks: only the picked goals' cards stay on the field, only their results and stops stay along the bottom (the filter, kept per party for the session in `st.picks`).
import { h, icon, sheet } from "./util.js";
import { elem, sign } from "./shell-marks.js";
import { barName, barWords, filterWords, flagTally, goalsOf } from "./shell-goals-words.js";

const LIT_MS = 700;                                  // a flag lit once in the sheet

/** `core`: the board's frame (st, draw, open); `about(slug)`: opens About this party. Returns {sheets, bar(model, gate), sync(model), clear()}. */
export function makeGoals(core, about) {
  const st = core.st;
  const body = h("div", { class: "goals" });
  const sh = sheet("Goals", body);
  const count = h("span", { class: "ork-count" });
  const all = h("button", { class: "ork-btn quiet", type: "button", "data-act": "show-all", onclick: () => clear() }, "Show all");
  sh.bar.insertBefore(count, sh.shut);
  sh.bar.insertBefore(h("span", { class: "spacer" }), sh.shut);
  sh.bar.insertBefore(all, sh.shut);
  let shown = null;                                  // the party and its goals as they were drawn last

  const picked = (m) => m.picks;                       // the picks that are still among the party's open goals
  function setPicks(party, list) { st.picks = { ...(st.picks || {}), [party]: list }; core.draw(); }
  function toggle(slug) {
    const party = shown.m.goal.slug, now = picked(shown.m);
    setPicks(party, now.includes(slug) ? now.filter((s) => s !== slug) : [...now, slug]);
  }
  function clear() { if (shown) setPicks(shown.m.goal.slug, []); }

  // -- one goal's row ---------------------------------------------------------------------------------------------------------------------------------
  function row(r, on) {
    const pile = h("span", { class: "pile", "aria-hidden": "true" }, ...Array.from({ length: r.edges }, (_, i) => h("i", { class: `pile__edge e${r.edges - i}` })),
      h("span", { class: "pile__back" }, elem(r.element, { dim: r.raw })));
    return h("div", { class: `dk${on ? " is-on" : ""}`, "data-idea": r.slug },
      h("button", { class: "dk__main", type: "button", "aria-pressed": String(on), "data-idea": r.slug, title: `${r.title} · ${r.line}`, onclick: () => toggle(r.slug) }, pile,
        h("span", { class: "dk__body" }, h("span", { class: "dk__title" }, r.type ? h("span", { class: "dk__type", "data-type": r.type.id }, sign(r.type.sign, r.type.name)) : null, r.title),
          h("span", { class: "dk__line" }, r.line)),
        r.mark ? h("span", { class: "dk__mark" }, sign(r.mark, r.markTip)) : null, on ? h("span", { class: "dk__check" }, sign("check", "picked")) : null),
      h("button", { class: "dk__open", type: "button", "aria-label": `Open ${r.title}`, onclick: () => { sh.close(); core.open(r.open, "map"); } }, h("i", { class: "ork-chev right", "aria-hidden": "true" })));
  }

  function drawSheet() {
    const { m, list } = shown;
    const on = new Set(picked(m));
    const lit = new Set(st.lit || []);
    const lines = (rows, mark) => rows.map((r) => h("p", { class: "cap goals__line" }, sign(mark), ` ${r.title} · ${r.line}`));
    count.textContent = String(list.n);
    all.hidden = !on.size;
    body.replaceChildren(
      h("button", { class: "goals__about", type: "button", "data-act": "about", "aria-haspopup": "dialog", title: "About this party: what it is for, its checks, its price and its flags",
        onclick: () => { sh.close(); about(m.goal.slug); } }, h("span", {}, `About ${m.goal.short || m.goal.title}`), h("i", { class: "ork-chev right", "aria-hidden": "true" })),
      h("p", { class: "cap goals__how" }, "A tap shows only that goal’s tasks; tap more to add them. ", h("i", { class: "ork-chev right", "aria-hidden": "true" }), " opens one."),
      h("h3", {}, "At work"), ...(list.atWork.length ? list.atWork.map((r) => row(r, on.has(r.slug))) : [h("p", { class: "cap" }, "Nothing at work.")]),
      h("h3", {}, "Planning"), ...(list.planning.length ? list.planning.map((r) => row(r, on.has(r.slug))) : [h("p", { class: "cap" }, "Nothing in Planning.")]),
      list.waits.length ? h("h3", {}, `Waits for main · ${list.waits.length}`) : null, ...lines(list.waits, "check"),
      h("h3", {}, `Flags · ${list.flags.length}`), ...(list.flags.length ? list.flags.map((f) => h("p", { class: `cap goals__line goals__flag${lit.has(f.slug) ? " is-reward" : ""}`, "data-idea": f.slug },
        sign("flag"), " ", h("span", { class: "goals__ink" }, f.short), ` · ${flagTally(f)}`)) : [h("p", { class: "cap" }, "None yet.")]));
    if (lit.size && sh.el.open) { st.lit = new Set(); setTimeout(() => body.querySelectorAll(".is-reward").forEach((e) => e.classList.remove("is-reward")), LIT_MS + 50); }
  }

  // -- the bar ------------------------------------------------------------------------------------------------------------------------------------------
  /** The bar: *⌄ Tech · 3 of 12 goals done* (the filter on: the party, the picked goals' elements, *1 of 7 goals*, *Show all*) and at its right the gate (`gate`: a node or null). */
  function bar(m, gate) {
    const list = goalsOf(st, m);
    const on = picked(m);
    shown = { m, list };
    const head = on.length
      ? h("button", { class: "gbar__head", type: "button", "aria-haspopup": "dialog", "data-act": "goals", "aria-label": `${filterWords(on, list)}: only their tasks are shown. Goals`, onclick: () => open() },
        h("i", { class: "ork-chev", "aria-hidden": "true" }), h("span", { class: "gbar__lbl" }, barName(m.goal)), h("span", { class: "gbar__els" }, ...on.map((s) => elem(m.nodes.find((n) => n.slug === s)?.element, { dim: false }))),
        h("span", { class: "gbar__words" }, filterWords(on, list)))
      : h("button", { class: "gbar__head", type: "button", "aria-haspopup": "dialog", "data-act": "goals", title: "The goals: a tap on one shows only its tasks",
        onclick: () => open() },
        h("i", { class: "ork-chev", "aria-hidden": "true" }), h("span", { class: "gbar__lbl" }, barName(m.goal)), " ", h("span", { class: "gbar__quiet" }, `· ${barWords(m.goal)}`));
    return h("div", { class: `gbar${on.length ? " is-on" : ""}` }, head, on.length ? h("button", { class: "ork-btn quiet gbar__all", type: "button", "data-act": "show-all", onclick: () => clear() }, "Show all") : null, gate || null);
  }

  function open() { sh.open(); drawSheet(); }                   // open first: what is lit once is lit as it opens

  return {
    sheets: [sh.el],
    bar,
    /** The field was drawn again: an open sheet shows what it drew. */
    sync() { if (sh.el.open && shown) drawSheet(); },
    clear,
  };
}
