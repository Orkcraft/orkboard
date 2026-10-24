// New party on the phone, on one sheet (docs/specs/41-phone-round-3.md §6, spec 50 §0, §6.7), top to bottom: what it is for — the description (focused) and the
// priority —, its craft — one row of six heads, the five crafts and Mixed, the picked one's word and line under it (decisions §53) —, its
// party folded to one line (Leads · Builds · Checks) with Change, its checks folded to one line, what is left of the AI tools, and Save party
// pinned at the foot. The team is three folds, one open at a time, each closed by Done: Leads (one seat: a pick folds it and opens Builds),
// Builds (three at most), Checks (two at most); the craft's party is in them at once. A task goes to the one of the party who does its kind of
// work (Grunt fills in); a checker's check adds its line to the spec's Done when and its task to the plan (realm/idea_checks.py). A Mixed
// goal starts with the Taskmaster alone, its craft its party's most. `makeParty` is the team and the checks alone: a goal's own screen
// changes its team with the same two (§7). Under the price, *It can take:* the goal types the seats would be offered (spec 63 §2); a party saved here gathers its heads into the party's deck (§4).
// Ideation (spec 65 §1) is the library's like any: its six agents are offered to no other party, and its seats are not changed (no Change; its price is a pitch's, it takes no goal type).
import { h, sheet, head, icon } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "./shell-who.js";
import { limitsNote } from "./shell-limits.js";
import { say } from "./shell-words.js";
import { sign } from "./shell-marks.js";
import { motionOn, pulse, gather } from "./shell-motion.js";

export const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"],
  ["product", "lich", "Who it is for, what it moves, what it leaves out"]];
const RACE = Object.fromEntries(CRAFTS.map(([c, r]) => [c, r]));
const BANDS = [["lead", "Leads", "reads and plans each goal"], ["build", "Builds", "do the work"],
  ["check", "Checks", "hold each goal to their check"]];
const presetsOf = (core) => core.st.roles?.presets || [];       // the library's parties, the mixed first (spec 59 §2.4); none from an older host
const TASKMASTER = "taskmaster";
const MIXED = "mixed";
const library = (core) => core.st.roles?.library || [];     // the agents that come with Orkline (ideas.roles: realm/library.py)
const DEFAULT_SEATS = { lead: 1, build: 3, check: 2 };
/** The seats of a leader's party (spec 59 §2.3: `ideas.roles` `stages`), the default's for an older host or a leader the host does not name. */
const stagesOf = (core, leader) => core.st.roles?.stages?.[leader] || core.st.roles?.stages?.default || { lead: "Planning", build: "Implementation", check: "Checking", seats: core.st.roles?.seats || DEFAULT_SEATS };
const seatsOf = (core, leader) => stagesOf(core, leader).seats || DEFAULT_SEATS;
const partyOf = (core, c) => core.st.roles?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const lcfirst = (t) => t.charAt(0).toLowerCase() + t.slice(1);
const TAKES_LINES = 3;                                         // *It can take* runs to three lines at most, then *and k more* (spec 63 §2.1)
const GATHER_HEADS = 6;                                        // the heads that gather into the deck, the leader's first (spec 63 §4.1)
/** Ideation is always its four views and the skeptic (spec 65 §1, realm/goal_team.py `IDEATION_WHOLE`): its seats are not changed, and its agents sit in no other party. */
export const IDEATION_WHOLE = "Ideation reads every pitch from all four sides: its views and the skeptic stay.";
/** A head of the sheet that stands for an agent: the gather finds where the sheet shows it by this. */
const tag = (img, id) => { img.dataset.agent = id; return img; };

/** A goal's team and its checks: {team, checks, set({leader, team, every}), get() → {leader, team, every}, preset(craft)}. `team` is the line
 *  with Change and the three folds; `checks` the checks' line with Change and its list. */
export function makeParty(core, opts = {}) {
  let leader = TASKMASTER, team = [], every = [];          // team: the builders and checkers
  let owns = [], partyId = "", asking = "";                // your parties (spec 43 §6); `partyId`: the one whose seats these are, until a seat changes
  let editing = false, fold = "", checking = false;
  let presetId = "";                                       // the library's party the seats are, until a seat changes
  let price = null, priceTimer = 0;                        // `ideas.party_price`: asked when the picker opens, 300 ms after a seat or *Every idea* changes
  let seen = null, opened = new Set();                     // the goal types of the answer before (none at the first), and those the last change opened: lit once (spec 63 §2.2)
  let takes = null;                                        // the *It can take* line drawn last, cut to its lines once it is in the page
  const teamEl = h("div", { class: "party" });
  const checksEl = h("div", { class: "party-checks" });

  const agent = (id) => library(core).find((a) => a.id === id) || (core.st.roles?.roles || []).find((r) => r.slug === id && { id: r.slug, name: r.name });
  const nameOf = (id) => agent(id)?.name || agent(id)?.id || id;
  /** The band an agent sits in: the library says; an agent of the person's own builds. */
  const bandOf = (id) => library(core).find((a) => a.id === id)?.band || "build";
  const inBand = (band) => (band === "lead" ? [leader] : team.filter((id) => bandOf(id) === band));
  const names = (band) => inBand(band).map(nameOf).join(", ") || "none";
  const draw = () => { drawTeam(); drawChecks(); opts.onChange?.(); };
  /** The party is Ideation: its leader judges pitches (the library's `pitch`). */
  const ideation = () => agent(leader)?.pitch === true;
  const seats = (band) => seatsOf(core, leader)[band];
  /** The refusal for a stage that has fewer seats with this leader than the party has members (spec 59 §6.2): "" when the party fits. */
  const overWords = () => {
    const band = ["build", "check"].find((b) => inBand(b).length > seats(b));
    return band ? `${stagesOf(core, leader)[band]} has ${seats(band)} ${seats(band) === 1 ? "seat" : "seats"} with ${nameOf(leader)}: take one out first.` : "";
  };
  async function loadOwns() {
    const got = await core.call("ideas.parties");
    if (got) { owns = got.parties || []; draw(); }
  }
  /** *3 parties in 2 projects · 2 met*: said only once a party has been used. */
  const usedWords = (p) => (p.goals ? `${p.goals} ${p.goals === 1 ? "party" : "parties"} in ${p.projects} ${p.projects === 1 ? "project" : "projects"} · ${p.met} met` : "");
  /** **Your parties**, above the team when there is one: a chip each with its members' small heads, its name and where it was used. A tap fills the seats
   *  (and the craft in New goal); its `close` mark removes it after asking. */
  function ownRow() {
    if (!owns.length) return null;
    const drop = async (p) => {
      const got = await core.call("ideas.party_drop", { id: p.id });
      asking = "";
      if (got) loadOwns(); else draw();
    };
    return h("section", { class: "own-parties", "aria-label": "Your parties" }, h("h3", {}, "Your parties"),
      h("div", { class: "own-chips" }, ...owns.map((p) => h("div", { class: `own-chip${partyId === p.id ? " is-on" : ""}`, "data-party": p.id },
        h("button", { class: "own-pick", type: "button", "aria-pressed": String(partyId === p.id), "aria-label": `Pick your party “${p.name}”`, onclick: () => pickOwn(p) },
          h("span", { class: "own-heads" }, ...[p.leader, ...p.team].map(agent).filter((a) => a?.craft).map((a) => tag(head(RACE[a.craft] || "peon", a.tier || "warrior", { small: true }), a.id || a.slug))),
          h("b", {}, p.name), usedWords(p) ? h("small", { class: "muted" }, usedWords(p)) : null),
        h("button", { class: "own-close", type: "button", "aria-label": `Remove your party “${p.name}”`, onclick: () => { asking = p.id; draw(); } }, icon("close")),
        asking === p.id ? h("p", { class: "own-ask", role: "alert" }, `Remove your party “${p.name}”? Parties that use it keep their agents.`,
          h("button", { class: "ork-btn danger", type: "button", onclick: () => drop(p) }, "Remove it"),
          h("button", { class: "ork-btn", type: "button", onclick: () => { asking = ""; draw(); } }, "Keep it")) : null))));
  }
  function pickOwn(p) {
    leader = p.leader || TASKMASTER;
    team = [...p.team];
    every = [...p.every];
    partyId = p.id; presetId = "";
    if (p.craft && opts.onCraft) opts.onCraft(p.craft);
    draw();
    askPrice();
  }
  const current = () => ({ leader, team: [...team], every: every.filter((id) => team.includes(id)) });
  /** `lights`: whether the types this answer newly offers are lit (a seat the person changed); the answers to the picker's opening are the baseline and light nothing (spec 63 §2.2). */
  function askPrice(now = false, lights = true) {
    clearTimeout(priceTimer);
    const go = async () => {
      const got = await core.call("ideas.party_price", { ...current(), ...(craftNow() ? { craft: craftNow() } : {}) });
      if (!got) return;
      const ids = Array.isArray(got.types) ? got.types.map((t) => t.id) : null;           // an older host sends none: no line
      opened = new Set(lights && seen && ids ? ids.filter((id) => !seen.has(id)) : []);
      seen = ids && new Set(ids);
      price = got;
      draw();
    };
    if (now) go(); else priceTimer = setTimeout(go, 300);
  }
  /** *This party: about $2–6 a goal* (below $1, in cents) and, muted, where it comes from. */
  function priceLine() {
    if (!price) return null;
    const { low, high } = price, a = Math.round(low), b = Math.round(high);
    const range = low < 1 ? `$${low.toFixed(2)}–${high.toFixed(2)}` : a === b ? `$${a}` : `$${a}–${b}`;
    const [one, many] = price.pitch ? ["pitch", "pitches"] : ["goal", "goals"];            // Ideation's price is a pitch's (spec 65 §3)
    return h("div", { class: "party-price-box" },
      h("p", { class: "party-price", role: "status" }, `This party: about ${range} a ${one}`,
        h("small", { class: "muted" }, ` ${price.learned ? `from this project's last ${price.ideas} ${many}` : `a first guess: it learns from this project's ${many}`}`)),
      ...(price.hints || []).map((t) => h("p", { class: "muted party-hint" }, t)));    // spec 43 §5: quiet lines, never a block, no button
  }
  /** *It can take:* the goal types a party of these seats would be offered (spec 63 §2): `ideas.party_price`'s `types`, each its sign and name, joined by ·; then *with one more:* the types that
   *  miss someone (*New screen (needs Design system designer)*); none at all, *nothing of its own yet: add a builder*. Three lines at most (`fitTakes`); a type the last change opened is
   *  lit once. Null for an older host (no `types`). */
  function takesLine() {
    takes = null;
    if (!Array.isArray(price?.types) || price.pitch) return null;                        // a pitch has no goal type: its decision names the one it will have
    const lit = motionOn() ? opened : new Set();
    opened = new Set();
    const have = price.types.filter((t) => !t.missing), all = [...have, ...price.types.filter((t) => t.missing)];
    const words = (t) => (t.missing ? `${t.name} (needs ${t.missing})` : t.name);
    const item = (t) => h("span", { class: `take${t.missing ? " is-missing" : ""}`, "data-type": t.id }, sign(t.sign), words(t));
    const el = h("p", { class: "party-takes" });
    /** The first `n` types; the rest are said as *and k more*, their names in its title. */
    const paint = (n) => {
      const nodes = all.slice(0, n).map(item), kids = [h("b", {}, "It can take:"), " "];
      if (!have.length) kids.push("nothing of its own yet: add a builder", nodes.length ? ", " : ".");
      nodes.forEach((node, i) => {
        if (i === have.length) kids.push(i ? ", " : "", h("span", { class: "take-with" }, "with one more:"), " ");
        else if (i) kids.push("\u00a0· ");
        kids.push(node);
      });
      if (n < all.length) kids.push(" ", h("span", { class: "take-more", title: all.map(words).join(", ") }, `and ${all.length - n} more`));
      el.replaceChildren(...kids);
      nodes.forEach((node, i) => lit.has(all[i].id) && pulse(node));
    };
    paint(all.length);
    takes = { el, count: all.length, paint };
    return el;
  }
  /** The line cut to its lines once it is in the page (its sheet open): types come off its end until it fits. */
  function fitTakes() {
    if (!takes?.el.getClientRects().length) return;
    const { el, count, paint } = takes, style = getComputedStyle(el);
    const line = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.4;
    for (let n = count; n > 1 && el.getBoundingClientRect().height > line * TAKES_LINES + 1; n--) paint(n - 1);
  }
  /** *adds about $0.35 to a goal it checks · about half of them* (*· every goal* when it checks every goal). */
  function addsWords(id) {
    const c = (price?.checks || []).find((x) => x.by === id);
    if (!c) return "";
    const share = c.every ? "every goal" : Math.abs(c.share - 0.5) < 0.03 ? "about half of them" : `about ${Math.round(c.share * 100)} % of them`;
    return ` · adds about $${c.usd.toFixed(2)} to a goal it checks · ${share}`;
  }

  /** An agent's row in its fold: a tap takes it in or out (a leader takes the one seat; out, the Taskmaster leads). */
  function seat(a) {
    const id = a.id || a.slug, band = a.band || bandOf(id);
    const on = band === "lead" ? leader === id : team.includes(id);
    const kind = RACE[a.craft] || "peon";
    return h("button", { class: "team-row", type: "button", "aria-pressed": String(on), "data-agent": id,
      "aria-label": `${on ? "Take out" : "Take in"}: ${a.name}`, onclick: () => {
        if (band === "lead") { leader = on ? TASKMASTER : id; fold = on ? "lead" : "build"; }      // a pick folds Leads and opens Builds
        else if (on) team = team.filter((x) => x !== id);
        else if (inBand(band).length < seats(band)) team = [...team, id];
        else { core.flash(core.st.roles?.stages ? `${stagesOf(core, leader)[band]} has ${seats(band)} seats with ${nameOf(leader)}: take one out first.`
          : `${BANDS.find((b) => b[0] === band)[1]} has ${seats(band)} seats: take one out first.`); return; }       // an older host has no stages: today's words
        partyId = ""; presetId = "";                             // a seat changed: the party is then the person's own picking
        draw();
        askPrice();
      } }, head(kind, a.tier || "warrior"), h("b", {}, a.name, a.check ? h("span", { class: "check-badge" }, "checks") : null),
      h("small", { class: "muted" }, say(`${TIER_WORDS[a.tier] || ""} ${RACE_WORDS[kind]}${a.line ? ` · ${a.line}` : ""}`.trim())),
      h("span", { class: "team-mark", "aria-hidden": "true" }, icon(on ? "check" : "plus")));
  }

  function band([id, words, what]) {
    const n = Math.max(seats(id), inBand(id).length), taken = inBand(id), on = fold === id, word = stagesOf(core, leader)[id];
    const own = (core.st.roles?.roles || []).filter((r) => team.includes(r.slug) && bandOf(r.slug) === id && !library(core).some((a) => a.id === r.slug));
    const list = [...library(core).filter((a) => a.band === id && !a.pitch), ...own.map((r) => ({ ...r, id: r.slug, band: id }))]       // the pitch agents are Ideation's only
      .sort((x, y) => (x.craft === craftNow() ? 0 : 1) - (y.craft === craftNow() ? 0 : 1));        // the goal's craft's first
    const over = taken.length > seats(id);
    return h("section", { class: `party-fold band-${id}${on ? " is-open" : ""}`, "aria-label": words, "data-stage": word },
      h("button", { class: "fold-head", type: "button", "aria-expanded": String(on), onclick: () => { fold = on ? "" : id; draw(); } },
        h("b", {}, words), h("small", { class: "muted" }, taken.length ? names(id) : "none"), h("small", { class: "muted fold-stage" }, id === "lead" ? word : `${word} · ${plural(seats(id), "seat")}`), h("span", { class: "fold-mark", "aria-hidden": "true" }, icon(on ? "close" : "plus"))),
      on ? h("div", { class: "fold-body" },
        h("small", { class: "muted" }, `${taken.length} of ${seats(id)} · ${what}`),
        over ? h("p", { class: "party-over", role: "alert" }, overWords()) : null,
        h("div", { class: "team-seats" }, ...Array.from({ length: n }, (_, i) => {
          const a = agent(taken[i]);
          return h("span", { class: `team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}${i >= seats(id) ? " is-over" : ""}`, title: a ? nameOf(taken[i]) : "A free seat" },
            a ? tag(head(RACE[a.craft] || "peon", a.tier || "warrior"), taken[i]) : "");
        })),
        h("div", { class: "team-list" }, ...list.map(seat)),
        h("button", { class: "ork-btn", type: "button", "data-done": id, onclick: () => { fold = ""; draw(); } }, "Done")) : null);
  }

  function drawTeam() {
    const line = h("p", { class: "party-line" }, h("b", {}, "Leads: "), names("lead"), " · ", h("b", {}, "Builds: "), names("build"), " · ", h("b", {}, "Checks: "), names("check"));
    if (ideation()) editing = false;                              // Ideation's seats stay: no Change
    if (!editing) {
      teamEl.replaceChildren(...[h("h3", {}, "The party"), ownRow(), line, overWords() ? h("p", { class: "party-over", role: "alert" }, overWords()) : null, priceLine(), takesLine(),
        ideation() ? h("p", { class: "muted party-whole", "data-sec": "ideation" }, IDEATION_WHOLE)
          : h("button", { class: "ork-btn", type: "button", "data-change": "team", onclick: () => { editing = true; fold = "lead"; draw(); } }, "Change")].filter(Boolean));
      fitTakes();
      return;
    }
    if (!fold) { editing = false; drawTeam(); return; }            // every fold closed by Done: back to the line
    teamEl.replaceChildren(...[h("h3", {}, "The party"), ownRow(), ...BANDS.map(band), priceLine(), takesLine()].filter(Boolean));
    fitTakes();
  }

  /** The craft the party was started from (the goal's craft sorts its agents first); set by the sheet. */
  let craftNow = () => "";

  // -- the party's checks: each checker's, where it applies or on every goal, and what a check adds to a goal, in dollars ----------
  function drawChecks() {
    const checkers = team.map(agent).filter((a) => a?.check);
    const mine = every.filter((id) => team.includes(id));
    const said = !checkers.length ? "No check" : `${checkers.length} ${checkers.length === 1 ? "check" : "checks"}, ${mine.length ? `${mine.length} on every goal` : "where each applies"}`;
    if (ideation()) {                                               // the Skeptic makes the case against every pitch: no check to set
      checksEl.replaceChildren(h("h3", {}, "Checks on every goal"), h("p", { class: "party-line" }, `${names("check")} makes the case against every pitch; ${nameOf(leader)} decides.`));
      return;
    }
    if (!checking || !checkers.length) {
      checksEl.replaceChildren(...[h("h3", {}, "Checks on every goal"), h("p", { class: "party-line" }, checkers.length ? said : "No checker in the party: a goal is done when its own Done when lines are."),
        checkers.length ? h("button", { class: "ork-btn", type: "button", "data-change": "checks", onclick: () => { checking = true; drawChecks(); } }, "Change") : null].filter(Boolean));
      return;
    }
    checksEl.replaceChildren(h("h3", {}, "Checks on every goal"), h("div", { class: "checks-block", role: "group", "aria-label": "Checks" },
      h("p", { class: "muted" }, `How deep each goal is worked: every check adds a line to its Done when and a task to its plan.`),
      ...checkers.map((a) => {
        const box = h("input", { type: "checkbox", "aria-label": `Every goal: ${a.name}`, ...(every.includes(a.id) ? { checked: true } : {}) });
        box.addEventListener("change", () => { every = box.checked ? [...every, a.id] : every.filter((x) => x !== a.id); partyId = ""; presetId = ""; askPrice(); });
        return h("div", { class: "check-row" }, head(RACE[a.craft], a.tier, { small: true }),
          h("span", { class: "check-text" }, h("b", {}, a.name), h("small", { class: "muted" }, say(`${a.check.done} · applies ${a.check.applies}`) + addsWords(a.id))),
          h("label", { class: "check-every" }, box, h("span", {}, "Every goal")));
      }),
      h("button", { class: "ork-btn", type: "button", "data-done": "checks", onclick: () => { checking = false; drawChecks(); } }, "Done")));
  }

  return {
    team: teamEl,
    checks: checksEl,
    /** The party a goal has (or starts with); `craft`: whose agents sort first. */
    set(party, craft = () => "") {
      leader = party.leader || TASKMASTER;
      team = [...(party.team || [])];
      every = [...(party.every || [])];
      editing = false; fold = ""; checking = false; price = null; seen = null; opened = new Set(); asking = "";
      partyId = party.party || ""; presetId = "";
      craftNow = craft;
      draw();
      askPrice(true, false);                               // the picker opens: its answers light nothing
      loadOwns();
    },
    /** A craft's party in the seats at once (`lights`: false when the sheet opens with it, which lights nothing). */
    preset(craft, lights = true) {
      const p = partyOf(core, craft);
      leader = p.lead || TASKMASTER;
      team = [...p.build, ...p.check];
      every = [];
      partyId = ""; presetId = "";
      draw();
      askPrice(false, lights);
    },
    /** A library party in the seats at once (`preset(id)` keeps its id for `ideas.goal_save`, cleared when a seat changes, as `party` is). */
    library(p) {
      leader = p.lead || TASKMASTER;
      team = [...p.build, ...p.check];
      every = [];
      partyId = "";
      presetId = p.id;
      draw();
      askPrice();
    },
    fits: () => !overWords(),
    get: () => ({ ...current(), party: partyId, preset: partyId ? "" : presetId }),
    /** The crafts of the party's agents, for a Mixed goal's own craft. */
    crafts: () => [leader, ...team].filter((id) => id !== TASKMASTER).map((id) => agent(id)?.craft).filter(Boolean),
    /** The party's heads as the seats draw them, the leader first: [{id, race, tier}]. */
    heads: () => [leader, ...team].filter((id) => agent(id)).map((id) => ({ id, race: RACE[agent(id).craft] || "peon", tier: agent(id).tier || "warrior" })),
    names,
    draw,
  };
}

/** `core`: the board's frame. Returns {el, open(after)}; `after(slug)` instead of opening the party's screen. */
export function makeNewGoal(core) {
  let craft = "engineering", then = null;
  let preset = "";                                   // the library's party picked (its id), "" for the old row of crafts
  const party = makeParty(core, { onCraft: (c) => { craft = c; preset = ""; drawCraft(); }, onChange: () => sync() });
  const about = h("textarea", { class: "ork-field", rows: "4", "aria-label": "What it is for", placeholder: "A few lines: what it is for", maxlength: "20000" });
  const priority = prioritySwitch("new-goal-priority");
  const row = h("div", { class: "craft-row", role: "group", "aria-label": "Craft" });
  const craftLine = h("p", { class: "muted craft-line", "aria-live": "polite" });
  const left = h("div", {});
  const save = h("button", { class: "ork-btn primary big", type: "button", disabled: true }, "Save party");
  const body = h("div", { class: "goal-steps one-sheet" });
  const sh = sheet("New party", body, foot(save));
  const sync = () => { save.disabled = !about.value.trim() || !party.fits(); };       // a leader with fewer seats than the party has keeps Save off
  about.addEventListener("input", sync);

  /** The goal's craft: the one picked, or a Mixed team's most (the first in the team on a tie). */
  function craftOf() {
    if (craft !== MIXED) return craft;
    const crafts = party.crafts();
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  }

  function pick(c) {
    craft = c;
    preset = "";
    party.preset(c);
    drawCraft();
  }
  function pickPreset(p) {
    craft = p.craft;
    preset = p.id;
    party.library(p);
    drawCraft();
  }
  /** The library's parties in one column (spec 59 §7.1): *Mixed* first, then *One craft*, then the Taskmaster alone. */
  function drawLibrary(presets) {
    const tile = (p) => {
      const ids = [p.lead, ...p.build, ...p.check];
      const heads = ids.map((id) => library(core).find((a) => a.id === id)).filter((a) => a?.craft).map((a) => tag(head(RACE[a.craft] || "peon", a.tier || "warrior", { small: true }), a.id));
      const alone = p.craft === MIXED;
      return h("button", { class: `craft-tile preset-tile${p.mixed ? " is-mixed" : ""}`, type: "button", "data-preset": p.id, ...(p.mixed ? {} : { "data-craft": p.craft }),
        "aria-label": p.name, "aria-pressed": String(preset ? preset === p.id : !p.mixed && p.craft === craft), onclick: () => (alone ? pick(MIXED) : pickPreset(p)) },
      alone ? h("span", { class: "craft-heads" }, ...CRAFTS.slice(0, 2).map(([, race]) => head(race, "laborer", { small: true }))) : h("span", { class: "preset-heads" }, ...heads),
      h("span", { class: "preset-text" }, h("b", {}, p.name), h("small", { class: "muted" }, p.line)));
    };
    const group = (name, list) => (list.length ? h("div", { class: "preset-group", role: "group", "aria-label": name }, h("h4", {}, name), ...list.map(tile)) : null);
    row.replaceChildren(...[group("Mixed", presets.filter((p) => p.mixed)), group("One craft", presets.filter((p) => !p.mixed && p.craft !== MIXED)),
      group("Taskmaster alone", presets.filter((p) => p.craft === MIXED))].filter(Boolean));
    const one = presets.find((p) => (preset ? p.id === preset : !p.mixed && p.craft === craft));
    craftLine.replaceChildren(...(one ? [h("b", {}, one.name), `: ${lcfirst(one.line)}`] : []));
  }
  function drawCraft() {
    if (presetsOf(core).length) { row.className = "preset-list"; drawLibrary(presetsOf(core)); sync(); return; }
    row.className = "craft-row";
    row.replaceChildren(...CRAFTS.map(([c, race]) => h("button", { class: "craft-tile", type: "button", "data-craft": c, "aria-label": CRAFT_WORDS[c],
      "aria-pressed": String(c === craft), title: CRAFT_WORDS[c], onclick: () => pick(c) }, head(race, "laborer"))),
      h("button", { class: "craft-tile mixed", type: "button", "data-craft": MIXED, "aria-label": "Mixed", "aria-pressed": String(craft === MIXED), title: "Mixed",
        onclick: () => pick(MIXED) }, h("span", { class: "craft-heads" }, ...CRAFTS.slice(0, 2).map(([, race]) => head(race, "laborer", { small: true })))));
    const line = craft === MIXED ? "A party of any crafts: the Taskmaster leads, you pick the rest" : CRAFTS.find((x) => x[0] === craft)?.[2] || "";
    craftLine.replaceChildren(h("b", {}, craft === MIXED ? "Mixed" : CRAFT_WORDS[craft]), `: ${craft === MIXED ? line : lcfirst(line)}`);
    sync();
  }

  /** Where the sheet shows the party's heads at the press (spec 63 §4.1), the leader's first, six at most: [{race, tier, box}]. A head is where its seat is drawn in the open fold, else in the tile or the
   *  chip of the party picked; one that is not on screen (scrolled away, or never drawn) starts from Save party. */
  function gatherFrom() {
    const view = sh.el.getBoundingClientRect(), floor = save.parentElement.getBoundingClientRect().top, mine = save.getBoundingClientRect();
    const shown = (b) => b.width > 0 && b.top >= view.top && b.bottom <= floor && b.left >= 0 && b.right <= innerWidth;
    const from = { left: mine.left + mine.width / 2 - 12, top: mine.top + mine.height / 2 - 11, width: 24, height: 22 };
    return party.heads().slice(0, GATHER_HEADS).map(({ id, race, tier }) => {
      const where = [".party-fold.is-open .team-seat", '.preset-tile[aria-pressed="true"]', ".own-chip.is-on"]
        .map((s) => sh.el.querySelector(`${s} img[data-agent="${CSS.escape(id)}"]`)?.getBoundingClientRect()).find((b) => b && shown(b));
      const b = where || from;
      return { race, tier, box: { left: b.left, top: b.top, width: b.width, height: b.height } };
    });
  }

  save.addEventListener("click", async () => {
    if (!about.value.trim() || !party.fits()) return;
    save.disabled = true;
    const p = party.get();
    const heads = motionOn() ? gatherFrom() : [];                // read at the press, before the sheet closes
    const got = await core.call("ideas.goal_save", { about: about.value.trim(), craft: craftOf(), leader: p.leader, team: p.team, every: p.every, priority: priority.get(),
      ...(p.party ? { party: p.party } : {}), ...(p.preset ? { preset: p.preset } : {}) });
    sync();
    if (!got?.slug) { gather.drop(); return; }
    for (const note of got.notes || []) core.flash(note);       // an agent of the project's own that the party carries stays as it was
    const after = then;
    then = null;
    if (!after) gather.wait(got.slug, heads);                   // New goal opening right after is what the person looks at: the heads gather only into a party they are shown
    sh.close();
    core.st.track = got.slug;
    await core.refresh();
    if (after) after(got.slug);
    else if (heads.length) setTimeout(() => core.open({ kind: "goal", slug: got.slug }), gather.ms(heads.length));     // the party's screen covers the deck: it opens once the heads have gathered and the deck is lit
    else core.open({ kind: "goal", slug: got.slug });
  });
  sh.el.addEventListener("close", () => { then = null; });

  return {
    el: sh.el,
    /** `presetId`: a party of the library picked at once (a pitch sent to a party the project lacks, spec 65 §5). */
    open(after = null, presetId = "") {
      then = after;
      craft = "engineering";
      preset = "";
      about.value = "";
      save.disabled = true;
      priority.set("normal");
      party.set({ leader: TASKMASTER, team: [], every: [] }, () => craftOf());
      party.preset(craft, false);
      const picked = presetId && presetsOf(core).find((p) => p.id === presetId);
      if (picked) pickPreset(picked);
      drawCraft();
      left.replaceChildren(limitsNote(core.st.snap) || "");
      body.replaceChildren(
        h("section", { class: "new-goal-for", "aria-label": "About the party" }, field("What it is for", about), h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el)),
        h("section", { class: "new-goal-craft", "aria-label": "Craft" }, h("h3", {}, "Craft"), row, craftLine),
        party.team, party.checks,
        h("p", { class: "muted hint" }, "The leader reads it and writes the title and the summary."), left);
      sh.open();
      about.focus();
    },
  };
}
