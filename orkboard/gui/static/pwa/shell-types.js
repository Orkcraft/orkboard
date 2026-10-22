// The goal types on the phone (docs/specs/52-goal-types.md §4.1, §4.3, §5.5; decisions §65.4, §65.5): the party's leader deals what kind of goal a new one is. A tap on the create button's deck
// lifts its top card and deals the party's types (the map's `types`, the most used first) as a strip over the scrim, above the button: the line *New goal for <party>*, cards 132 × 185 in a sideways
// strip snapped to a card — the type's sign (28 px) top left, its name (the pixel face), its line (muted, three lines at most) and, when the party misses someone for it, *needs: <agent>* with that
// agent's small head at its foot (muted ink: it is not a stop) —, the blank card last, *Put them back* (44 px). The scrim and Esc gather them; a tap on a card turns it over into the form (shell-fab.js).
// Dealt as a spread (≈ 0.3 s, 35 ms apart, in steps); at once under reduced motion. A type is told by its sign, never by a colour. Also here: the join line of the form, one entry per kind the type
// misses (two at most): a free seat (*<agent> joins the party*), a swap (*Swap: <member> leaves, <agent> joins*, *Who leaves*) or a full band (a muted line), each saying what happens without it.
import { h, icon } from "./util.js";
import { sign } from "./shell-marks.js";
import { whoHead } from "./shell-who.js";
import { motionOn } from "./shell-motion.js";

const DEAL_MS = 300;                                 // each card's trip from the deck
const STEP_MS = 35;                                  // one card after another
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
  return usd > 0 ? `≈$${usd.toFixed(2)} a run` : "";
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

/** A type's card face (132 × 185): its sign, its name, its line, *needs: <agent>* with the agent's small head. `t`: an entry of the map's `types`; null: the blank card. */
export function typeCard(st, t) {
  if (!t) return h("span", { class: "typecard__face is-blank" }, h("span", { class: "typecard__plus" }, icon("plus")), h("b", { class: "typecard__name" }, "A blank goal"));
  const need = (t.missing || [])[0];
  return h("span", { class: "typecard__face" }, h("span", { class: "typecard__sign" }, sign(t.sign, "", { big: true })), h("b", { class: "typecard__name" }, t.name),
    h("span", { class: "typecard__line" }, t.line),
    need ? h("span", { class: "typecard__needs" }, whoHead(agentHead(st, need.agent), true), ` needs: ${need.name}`) : null);
}

/** `core`: the board's frame (st). Returns {open(goal, origin, pick), close(animated), isOpen()}: `pick(type, rect)` runs on a card's tap (`type` null: the blank card). */
export function makeTypes(core) {
  const st = core.st;
  let node = null, from = null;
  const onKey = (e) => { if (e.key === "Escape" && node) { e.preventDefault(); close(); } };
  const trip = (card) => {                           // where a card travels from: the deck's place, to its own
    const r = card.getBoundingClientRect();
    return from ? `translate(${Math.round(from.left + from.width / 2 - (r.left + r.width / 2))}px, ${Math.round(from.top + from.height / 2 - (r.top + r.height / 2))}px) scale(0.3)` : "scale(0.3)";
  };

  function close(animated = true) {
    if (!node) return;
    const gone = node;
    node = null;
    document.removeEventListener("keydown", onKey);
    const cards = [...gone.querySelectorAll(".typecard")];
    if (!animated || !motionOn() || document.visibilityState === "hidden") { gone.remove(); return; }
    gone.classList.add("is-gathering");
    cards.forEach((c, i) => c.animate([{ transform: "none", opacity: 1 }, { transform: trip(c), opacity: 0.4 }],
      { duration: DEAL_MS, delay: (cards.length - 1 - i) * STEP_MS, easing: "steps(6)", fill: "forwards" }));
    setTimeout(() => gone.remove(), DEAL_MS + cards.length * STEP_MS + 20);
  }

  /** Deals `goal`'s types (the map's goal) from `origin` (the deck's rect). */
  function open(goal, origin, pick) {
    close(false);
    from = origin || null;
    const card = (t) => h("button", { class: `typecard${t ? "" : " is-blank"}`, type: "button", "data-type": t ? t.id : "",
      "aria-label": t ? `${t.name}: ${t.line}${t.missing?.length ? `. Needs ${t.missing[0].name}` : ""}` : "A blank goal",
      onclick: (e) => { const r = e.currentTarget.getBoundingClientRect(); close(false); pick(t, r); } }, typeCard(st, t));
    const row = h("div", { class: "typedeal__row" }, ...(goal.types || []).map(card), card(null));
    const party = goal.short || goal.title;
    node = h("div", { class: "typedeal", role: "dialog", "aria-modal": "true", "aria-label": `New goal for ${party}`, onclick: (e) => { if (e.target === node) close(); } },
      h("div", { class: "typedeal__in" }, h("p", { class: "typedeal__cap" }, "New goal for ", h("b", {}, party)), row,
        h("button", { class: "ork-btn", type: "button", "data-act": "put-back", onclick: () => close() }, "Put them back")));
    document.body.append(node);
    document.addEventListener("keydown", onKey);
    if (motionOn() && document.visibilityState !== "hidden") [...row.children].forEach((c, i) => c.animate([{ transform: trip(c), opacity: 0.4 }, { transform: "none", opacity: 1 }],
      { duration: DEAL_MS, delay: i * STEP_MS, easing: "steps(6)", fill: "backwards" }));
    row.firstChild?.focus({ preventScroll: true });
  }

  return { open, close, isOpen: () => Boolean(node) };
}

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
