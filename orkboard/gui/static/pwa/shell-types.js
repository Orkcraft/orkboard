// The goal types on the phone (docs/specs/52-goal-types.md §4.3, spec 53 §2; decisions §65.4, §65.5): what the party's leader deals for a new goal is the types' row of the New goal form
// (shell-ideas.js), not a strip over a deck (spec 53 drops spec 52 §5.5's strip). Here: the agents' heads and prices the join line speaks with, and the join line of the form, one entry per kind
// the type misses (two at most): a free seat (*<agent> joins the party*), a swap (*Swap: <member> leaves, <agent> joins*, *Who leaves*) or a full band (a muted line), each saying what happens without it.
import { h } from "./util.js";
import { pctOf } from "./shell-spend.js";
import { whoHead } from "./shell-who.js";

const JOINS = 2;                                     // the join line's entries at most
const BANDS = { build: "builders", check: "checkers" };
const HINT = "at API prices, not your bill";

/** A library agent's head ({race, tier, craft}) from `ideas.roles`' library (null when not known). */
export function agentHead(st, slug) {
  const a = (st.roles?.library || []).find((x) => x.id === slug);
  return a ? { race: a.race, tier: a.tier, craft: a.craft } : null;
}

/** *≈$0.40 a run*: the agent's tier's price a task (`ideas.roles`' `tier_costs`), "" when not known. */
export function runPrice(st, slug) {
  const a = (st.roles?.library || []).find((x) => x.id === slug);
  const usd = Number(st.roles?.tier_costs?.[a?.tier]);
  return usd > 0 ? `≈${pctOf(usd) || `$${usd.toFixed(2)}`} a run` : "";
}

/** What the join line says for one entry of a type's `missing` (spec 52 §4.3): {shape: "free"|"swap"|"full", line, without, out}. */
export function joinWords(m) {
  const without = `Without ${m.name}, its ${m.words} goes to the Grunt.`;
  if (m.free) return { shape: "free", line: `${m.name} joins the party`, without, out: [] };
  const out = m.out || [];
  if (out.length) return { shape: "swap", line: `Swap: ${out[0].name} leaves, ${m.name} joins`, without, out };
  return { shape: "full", line: `The party’s ${BANDS[m.band] || "builders"} all have work open: ${m.name} can join from Edit the party when one is done. Till then its ${m.words} goes to the Grunt.`,
    without, out: [] };
}

/** *<name> · <n> runs this week*: a member who could leave, as the select says it. */
export const leaverWords = (o) => `${o.name} · ${o.runs} run${o.runs === 1 ? "" : "s"} this week`;

/** The join line of New goal by its type. `core`: the board's frame (st). Returns {el, set(missing), value(), reset()}: `value()` is `ideas.add`'s `join` — the first entry ticked — or null. */
export function makeJoin(core) {
  const st = core.st;
  const el = h("div", { class: "joins", hidden: true });
  let entries = [];

  function entry(m) {
    const w = joinWords(m);
    if (w.shape === "full") return { m, w, node: h("p", { class: "muted joinline is-full", "data-agent": m.agent }, w.line), on: () => false };
    const box = h("input", { type: "checkbox", checked: true, "data-agent": m.agent });
    const text = h("span", { class: "joinline__words" }, w.line);
    const without = h("p", { class: "muted joinline__without", hidden: true }, w.without);
    const price = runPrice(st, m.agent);
    const who = w.shape === "swap" ? h("select", { class: "ork-field joinline__out", "aria-label": "Who leaves" }, ...w.out.map((o) => h("option", { value: o.slug }, leaverWords(o)))) : null;
    who?.addEventListener("change", () => { text.textContent = `Swap: ${w.out.find((o) => o.slug === who.value)?.name || ""} leaves, ${m.name} joins`; });
    box.addEventListener("change", () => { without.hidden = box.checked; if (who) who.disabled = !box.checked; });
    const node = h("div", { class: `joinline is-${w.shape}`, "data-agent": m.agent },
      h("label", { class: "joinline__tick" }, box, text, whoHead(agentHead(st, m.agent), true), price ? h("span", { class: "muted joinline__price", title: HINT }, price) : null),
      who ? h("label", { class: "field joinline__who" }, h("span", { class: "field-label" }, "Who leaves"), who) : null, without);
    return { m, w, node, on: () => box.checked, out: () => who?.value || "" };
  }

  return {
    el,
    set(missing) {
      entries = (missing || []).slice(0, JOINS).map(entry);
      el.replaceChildren(...entries.map((e) => e.node));
      el.hidden = !entries.length;
    },
    value() {
      const e = entries.find((x) => x.on());
      if (!e) return null;
      return { add: e.m.agent, ...(e.w.shape === "swap" && e.out() ? { out: e.out() } : {}), name: e.m.name };
    },
    reset() { entries = []; el.replaceChildren(); el.hidden = true; },
  };
}
