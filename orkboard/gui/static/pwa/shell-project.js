// The project's level on the phone (docs/specs/70-orkmaster-and-the-project.md §2.1, §2.4, §3, §4; decisions §85): the Orkmaster is the project's ork; a row at the top of the parties' sheet (shell-where.js) opens
// **The project**, a full sheet: the Orkmaster's head and **New party** (a press deals the library's parties as a strip of tiles, in `ideas.map`'s `project.deal` order, each with its why: a press opens New party
// with that preset picked), a section for each party (its leader's head, its name, *k/n*, **Open <party>**; under it its goals as rows: Planning and At work, Waits for main and Flags folded; a row opens the goal's
// screen) and, pinned at the foot, **New goal** (shell-ideas.js `openProject`: no party yet; **Its party** is asked of the host, `makeItsParty`). A host without `project` has none of it.
// Pure words here too: `whyWords`, `fitWords`, `dealOf`.
import { h, head, sheet } from "./util.js";
import { elem, sign, typeTone } from "./shell-marks.js";
import { RACE_WORDS, raceOf, whoHead } from "./shell-who.js";
import { foot } from "./shell-forms.js";
import { chipsOf, modelOf } from "./shell-arena-words.js";
import { flagTally, goalsOf } from "./shell-goals-words.js";

export const PROJECT = "@project";                   // `ideas.shown`'s party for the project's level
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The project block of `ideas.map` (null for a host older than spec 70). */
export const projectOf = (core) => core.st.map?.project || null;

/** Why the Orkmaster deals a party first (or last): `d` is a `project.deal` entry. */
export function whyWords(d) {
  if (d?.why === "flags_wait") return `${plural(d.n || 0, "flag")} ${d.n === 1 ? "waits" : "wait"} and no party releases ${d.n === 1 ? "it" : "them"}`;
  if (d?.why === "no_pitches") return "No party judges small ideas yet";
  if (d?.why === "have") return "You have one";
  return "";
}

/** The deal as a map: preset id → {i, why, n, words}; empty for a host with no `project`. */
export function dealOf(core) {
  return new Map((projectOf(core)?.deal || []).map((d, i) => [d.id, { i, why: d.why || "", n: d.n || 0, words: whyWords(d) }]));
}

/** How a party fits a goal's type, as `ideas.party_for` says it: *takes it whole* · *needs Artist* · *no one there does it* (a pitch in Ideation, no type). */
export function fitWords(p) {
  if (p.fits === "whole") return "takes it whole";
  if (p.fits === "missing") return `needs ${(p.missing || []).map((m) => m.name || m.agent).join(", ")}`;
  if (p.fits === "none") return "no one there does it";
  if (p.fits === "pitch") return "a pitch there";
  return "";
}

/** `core`: the board's frame; `act`: {openParty(slug)}. Returns {el, open(), draw(), isOpen()}. */
export function makeProject(core, act) {
  const st = core.st;
  const body = h("div", { class: "project" });
  const newGoal = h("button", { class: "ork-btn primary big", type: "button", "data-act": "project-new-goal", onclick: () => { sh.close(); core.newIdea("", PROJECT); } }, "New goal");
  const sh = sheet("The project", body, foot(newGoal));
  sh.el.classList.add("full", "project-sheet");
  let dealt = false;                                 // the deal's strip is out
  const folded = new Set();                          // the folds opened: `<party>:waits`, `<party>:flags`

  /** A goal's row: its element, its type's sign and title, its state's words, its mark; a tap opens the goal's screen. */
  const row = (r) => h("button", { class: "pj-row", type: "button", "data-idea": r.slug, title: `${r.title} · ${r.line}`, onclick: () => { sh.close(); core.open(r.open, "map"); } },
    elem(r.element, { dim: r.raw }) || h("span", { class: "pj-row__none" }),
    h("span", { class: "pj-row__body" }, h("span", { class: "pj-row__title" }, r.type ? h("span", { class: `dk__type ${typeTone(r.element, r.raw)}`, "data-type": r.type.id }, sign(r.type.sign, r.type.name)) : null, r.title),
      h("span", { class: "pj-row__line" }, r.line)),
    r.mark ? h("span", { class: "dk__mark" }, sign(r.mark, r.markTip)) : null, h("i", { class: "ork-chev right", "aria-hidden": "true" }));
  const flagRow = (f) => row({ slug: f.slug, title: f.short, element: f.element, raw: false, type: null, line: flagTally(f), mark: "flag", markTip: "flag", open: { kind: "idea", slug: f.slug } });

  /** A fold shut by default: a 44 px button, its count, then its rows. */
  function fold(c, key, words, rows, count = true) {
    if (!rows.length) return null;
    const id = `${c.slug}:${key}`, on = folded.has(id);
    return h("div", { class: `pj-fold${on ? " is-open" : ""}`, "data-fold": key },
      h("button", { class: "pj-fold__head", type: "button", "aria-expanded": String(on), onclick: () => { if (on) folded.delete(id); else folded.add(id); draw(); } },
        h("span", {}, words), count ? h("small", { class: "muted" }, String(rows.length)) : null, h("i", { class: `ork-chev${on ? " up" : ""}`, "aria-hidden": "true" })),
      on ? h("div", { class: "pj-rows" }, ...rows) : null);
  }

  /** A party's section: its leader's head, name and *k/n*, **Open <party>**, then its goals. */
  function section(c) {
    const m = modelOf(st, c.slug);
    const list = m ? goalsOf(st, m) : { atWork: [], planning: [], waits: [], flags: [] };
    const g = (st.map?.goals || []).find((x) => x.slug === c.slug);
    const empty = !list.atWork.length && !list.planning.length && !list.waits.length && !list.flags.length;
    const group = (words, rows) => (rows.length ? [h("h4", { class: "pj-group" }, words), h("div", { class: "pj-rows" }, ...rows.map(row))] : []);
    return h("section", { class: "pj-party", "data-goal": c.slug, "aria-label": c.title },
      h("div", { class: "pj-party__head" },
        c.head ? whoHead(c.head, false) : h("span", { class: "where-row__head" }),
        h("span", { class: "pj-party__name", title: c.title }, h("b", {}, c.short), h("small", { class: "muted" }, g?.ideation ? `${g.ideas ?? 0}` : `${g?.done ?? 0}/${g?.ideas ?? 0}`)),
        h("button", { class: "ork-btn quiet pj-party__open", type: "button", "data-act": "open-party", "aria-label": `Open ${c.short}`, onclick: () => { sh.close(); act.openParty(c.slug); } }, `Open ${c.short}`)),
      empty ? h("p", { class: "cap pj-empty" }, `Nothing in ${c.short} yet`) : null,
      ...group("Planning", list.planning), ...group("At work", list.atWork),
      fold(c, "waits", "Waits for main", list.waits.map(row)),
      fold(c, "flags", `Flags (${list.flags.length})`, list.flags.map(flagRow), false));
  }

  /** The library's parties dealt as a strip of tiles, in the deal's order, each with its why; a press opens New party with that preset picked. */
  function strip() {
    const deal = dealOf(core), lib = core.st.roles?.library || [];
    const tiles = (core.st.roles?.presets || []).filter((p) => deal.has(p.id)).sort((a, b) => deal.get(a.id).i - deal.get(b.id).i).map((p) => {
      const heads = [p.lead, ...(p.build || []), ...(p.check || [])].map((id) => lib.find((a) => a.id === id)).filter((a) => a?.craft)
        .map((a) => head(raceOf(a), a.tier || "warrior", { small: true }));
      const why = deal.get(p.id);
      return h("button", { class: `pj-tile${why.why === "have" ? " is-have" : ""}`, type: "button", "data-preset": p.id, "data-why": why.why, onclick: () => { sh.close(); core.newParty(p.id); } },
        h("span", { class: "pj-tile__heads" }, ...heads), h("b", {}, p.name), h("small", { class: "muted" }, p.line), why.words ? h("small", { class: "pj-tile__why" }, why.words) : null);
    });
    return h("div", { class: "pj-deal", role: "group", "aria-label": "New party" }, ...tiles);
  }

  function draw() {
    const project = projectOf(core);
    if (!project) { body.replaceChildren(); return; }
    const o = project.orkmaster || { race: "peon", tier: "elder", name: "Orkmaster" };
    const parties = chipsOf(st).filter((c) => c.slug !== "general");
    body.replaceChildren(
      h("div", { class: "pj-top" }, head(o.race, o.tier, { title: `Orkmaster · ${(o.tier === "elder" ? "Veteran" : o.tier === "warrior" ? "Seasoned" : "Novice")} ${RACE_WORDS[o.race] || ""}`.trim() }),
        h("span", { class: "pj-top__name" }, h("b", {}, "Orkmaster"), h("small", { class: "muted" }, "The parties, their goals")),
        h("button", { class: "ork-btn", type: "button", "data-act": "project-new-party", "aria-expanded": String(dealt), onclick: () => { dealt = !dealt; draw(); } }, "New party")),
      ...[dealt ? strip() : null, ...parties.map(section), parties.length ? null : h("p", { class: "muted" }, "No parties yet.")].filter(Boolean));
  }

  return {
    el: sh.el,
    isOpen: () => sh.el.open,
    open() { dealt = false; draw(); sh.open(); },
    /** The sheet drawn again with the Board while it is open. */
    draw() { if (sh.el.open) draw(); },
  };
}

/** **Its party** in New goal from the project (shell-ideas.js): the parties as `ideas.party_for` answers them, the suggested one picked, a line *Orkmaster suggests Website · takes it whole*, the others as chips
 *  with their fit; without a type *Any party*. `pick(slug)` is told the party picked (and the suggestion, at first). Returns {el, ask(type), reset()}. */
export function makeItsParty(core, pick) {
  let list = [], suggested = "", picked = "", type = "", seq = 0;
  const line = h("p", { class: "itsparty__line", role: "status" });
  const chips = h("div", { class: "itsparty__chips", role: "radiogroup", "aria-label": "Its party" });
  const el = h("div", { class: "field itsparty", hidden: true }, h("span", { class: "field-label" }, "Its party"), line, chips);
  const nameOf = (slug) => list.find((p) => p.party === slug)?.name || slug;
  function draw() {
    const sug = list.find((p) => p.party === suggested);
    line.replaceChildren(...(type && sug ? [h("b", {}, `Orkmaster suggests ${sug.name}`), fitWords(sug) ? ` · ${fitWords(sug)}` : ""] : [h("b", {}, "Any party")]));
    chips.replaceChildren(...list.map((p) => h("button", { class: "itsparty__chip", type: "button", role: "radio", "aria-checked": String(p.party === picked), "data-goal": p.party, "data-fits": p.fits || "",
      onclick: () => { if (p.party === picked) return; picked = p.party; draw(); pick(picked); } },
    h("b", {}, p.name), fitWords(p) ? h("small", { class: "muted" }, fitWords(p)) : null, p.party === picked ? sign("check", "Picked") : null)));
  }
  return {
    el,
    nameOf,
    picked: () => picked,
    /** Asks the host for the parties of a goal of this type ("" none) and picks the one it suggests. */
    async ask(t = "") {
      const n = ++seq;
      type = t;
      const got = await core.call("ideas.party_for", t ? { type: t } : {});
      if (n !== seq || !got) return;
      list = got.parties || [];
      suggested = got.suggested || list[0]?.party || "";
      picked = suggested;
      draw();
      if (picked) pick(picked);
    },
  };
}
