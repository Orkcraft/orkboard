// New goal on the phone, on one sheet (docs/specs/41-phone-round-3.md §6), top to bottom: what it is for — the description (focused) and the
// priority —, its craft — one row of six heads, the five crafts and Mixed, the picked one's word and line under it (decisions §53) —, its
// team folded to one line (Leads · Builds · Checks) with Change, its checks folded to one line, what is left of the AI tools, and Save goal
// pinned at the foot. The team is three folds, one open at a time, each closed by Done: Leads (one seat: a pick folds it and opens Builds),
// Builds (three at most), Checks (two at most); the craft's party is in them at once. A task goes to the one of the party who does its kind of
// work (Grunt fills in); a checker's check adds its line to the spec's Done when and its task to the plan (realm/idea_checks.py). A Mixed
// goal starts with the Taskmaster alone, its craft its party's most. `makeParty` is the team and the checks alone: a goal's own screen
// changes its team with the same two (§7). Under the team, one line says about what an idea costs with the party (ideas.party_price:
// spec 43 C), asked when the picker opens and 300 ms after a seat or Every idea changes; each check says what it adds, and under the
// price come the party's hints (E: at most two plain lines, muted). Above the team, Your parties (F): the parties the person saved, each a
// chip with its members' small heads, its name and its record; a tap fills the leader, the builders, the checkers and Every idea (and, in
// New goal, the craft), a seat changed afterwards drops the party's id, and a mark removes it after asking.
import { h, sheet, head, icon } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "./shell-who.js";
import { limitsNote } from "./shell-limits.js";

export const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"],
  ["product", "lich", "Who it is for, what it moves, what it leaves out"]];
const RACE = Object.fromEntries(CRAFTS.map(([c, r]) => [c, r]));
const BANDS = [["lead", "Leads", "plans the goal's ideas and accepts the goal"], ["build", "Builds", "do the work"],
  ["check", "Checks", "hold each idea to their check"]];
const TASKMASTER = "taskmaster";
const MIXED = "mixed";
const library = (core) => core.st.roles?.library || [];     // the agents that come with Orkline (ideas.roles: realm/library.py)
const seatsOf = (core) => core.st.roles?.seats || { lead: 1, build: 3, check: 2 };
const partyOf = (core, c) => core.st.roles?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
const PRICE_MS = 300;
/** *This party: about $2–6 an idea* (below $1: *about $0.40–1.20*). */
const priceWords = (p) => { const f = (n) => (p.low < 1 ? Number(n).toFixed(2) : String(Math.round(n))); return `This party: about $${f(p.low)}–${f(p.high)} an idea`; };
const shareWords = (share) => (share === 0.5 ? "about half of them" : share <= 0 ? "none of them so far" : `about ${Math.round(share * 100)}% of them`);
/** What a check adds, as its line ends: *adds about $0.35 to an idea it checks · about half of them* (*· every idea*). */
const addsWords = (c) => `adds about $${Number(c.usd).toFixed(2)} to an idea it checks · ${c.every ? "every idea" : shareWords(c.share)}`;
const lcfirst = (t) => t.charAt(0).toLowerCase() + t.slice(1);

/** A goal's team and its checks: {team, price, checks, set({leader, team, every}), get() → {leader, team, every}, preset(craft), open()}.
 *  `team` is the line with Change and the three folds; `price` the party's price in one line; `checks` the checks' line with Change and
 *  its list. `open()`: the picker is shown, the price is asked at once. */
export function makeParty(core, { onPick = () => {} } = {}) {
  let leader = TASKMASTER, team = [], every = [];          // team: the builders and checkers
  let partyId = "", mine = [];                              // the person's party the seats were filled from (a seat changed drops it); the person's parties
  let editing = false, fold = "", checking = false;
  let craftNow = () => "";                                   // the goal's craft: its agents sort first, and the hints read it (set by the sheet)
  const teamEl = h("div", { class: "party" });
  const checksEl = h("div", { class: "party-checks" });
  const priceEl = h("p", { class: "party-price", "aria-live": "polite", hidden: true });
  const hintsEl = h("div", { class: "party-hints", "aria-live": "polite", hidden: true });   // spec 43 E: at most two lines, muted
  const priceBox = h("div", { class: "party-priced" }, priceEl, hintsEl);
  let price = null, timer = 0, asking = 0;

  /** The price of the party now (the leader, the team, the checkers on every idea), drawn when it comes. */
  async function askPrice() {
    clearTimeout(timer);
    const mine = ++asking, p = party();
    const got = await core.call("ideas.party_price", { leader: p.leader, team: p.team, every: p.every, craft: craftNow() });
    if (mine !== asking || !got) return;
    price = got;
    drawPrice();
  }
  /** After a change: 300 ms of quiet, then one call. */
  const changed = () => { clearTimeout(timer); timer = setTimeout(askPrice, PRICE_MS); };
  function drawPrice() {
    priceEl.hidden = !price;
    if (price) priceEl.replaceChildren(h("b", {}, priceWords(price)), " ", h("small", { class: "muted" },
      price.learned ? `from this project's last ${price.ideas} ideas` : "a first guess: it learns from this project's ideas"));
    const hints = price?.hints || [];
    hintsEl.hidden = !hints.length;
    hintsEl.replaceChildren(...hints.map((t) => h("p", { class: "muted" }, t)));
    for (const el of checksEl.querySelectorAll("[data-adds]")) {           // a check's line, in place (the box in hand keeps its focus)
      const c = price?.checks?.find((x) => x.by === el.dataset.adds);
      el.textContent = `${el.dataset.base}${c ? ` · ${addsWords(c)}` : ""}`;
    }
  }
  const party = () => ({ leader, team: [...team], every: every.filter((id) => team.includes(id)), party: partyId });
  const ownEl = h("section", { class: "own-parties", "aria-label": "Your parties", hidden: true });
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const recordWords = (p) => (p.goals ? `${plural(p.goals, "goal", "goals")} in ${plural(p.projects, "project", "projects")}${p.met ? ` · ${p.met} met` : ""}` : "");
  function drawOwn() {
    ownEl.hidden = !mine.length;
    ownEl.replaceChildren(h("h3", {}, "Your parties"), h("div", { class: "own-list" }, ...mine.map((p) => {
      const heads = [p.leader, ...p.team].filter((id) => id !== TASKMASTER).map((id) => {
        const a = library(core).find((x) => x.id === id);
        return head(RACE[a?.craft || p.craft] || "peon", a?.tier || "laborer", { small: true });
      });
      return h("div", { class: "own-chip", "data-party": p.id },
        h("button", { class: "own-pick", type: "button", "aria-pressed": String(p.id === partyId), "aria-label": `Pick your party “${p.name}”`, onclick: () => {
          leader = p.leader || TASKMASTER; team = [...p.team]; every = [...p.every]; partyId = p.id;
          editing = false; fold = ""; checking = false;
          onPick(p);
          draw(); drawOwn();
          changed();
        } }, h("span", { class: "own-heads" }, ...heads), h("b", {}, p.name), recordWords(p) ? h("small", { class: "muted" }, recordWords(p)) : ""),
        h("button", { class: "ork-btn quiet own-x", type: "button", "aria-label": `Remove your party “${p.name}”`, onclick: async () => {
          if (!confirm(`Remove your party “${p.name}”? Goals that use it keep their agents.`)) return;
          if (await core.call("ideas.party_drop", { id: p.id })) loadOwn();
        } }, icon("close")));
    })));
  }
  async function loadOwn() {
    const got = await core.call("ideas.parties", {});
    mine = got?.parties || [];
    drawOwn();
  }

  const agent = (id) => library(core).find((a) => a.id === id) || (core.st.roles?.roles || []).find((r) => r.slug === id && { id: r.slug, name: r.name });
  const nameOf = (id) => agent(id)?.name || id.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());     // a party's own agent this project has not yet: its slug as a name
  /** The band an agent sits in: the library says; an agent of the person's own builds. */
  const bandOf = (id) => library(core).find((a) => a.id === id)?.band || "build";
  const inBand = (band) => (band === "lead" ? [leader] : team.filter((id) => bandOf(id) === band));
  const names = (band) => inBand(band).map(nameOf).join(", ") || "none";
  const draw = () => { drawTeam(); drawChecks(); };
  async function loadOwns() {
    const got = await core.call("ideas.parties");
    if (got) { owns = got.parties || []; draw(); }
  }
  /** *3 goals in 2 projects · 2 met*: said only once a party has been used. */
  const usedWords = (p) => (p.goals ? `${p.goals} ${p.goals === 1 ? "goal" : "goals"} in ${p.projects} ${p.projects === 1 ? "project" : "projects"} · ${p.met} met` : "");
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
          h("span", { class: "own-heads" }, ...[p.leader, ...p.team].map(agent).filter((a) => a?.craft).map((a) => head(RACE[a.craft] || "peon", a.tier || "warrior", { small: true }))),
          h("b", {}, p.name), usedWords(p) ? h("small", { class: "muted" }, usedWords(p)) : null),
        h("button", { class: "own-close", type: "button", "aria-label": `Remove your party “${p.name}”`, onclick: () => { asking = p.id; draw(); } }, icon("close")),
        asking === p.id ? h("p", { class: "own-ask", role: "alert" }, `Remove your party “${p.name}”? Goals that use it keep their agents.`,
          h("button", { class: "ork-btn danger", type: "button", onclick: () => drop(p) }, "Remove it"),
          h("button", { class: "ork-btn", type: "button", onclick: () => { asking = ""; draw(); } }, "Keep it")) : null))));
  }
  function pickOwn(p) {
    leader = p.leader || TASKMASTER;
    team = [...p.team];
    every = [...p.every];
    partyId = p.id;
    if (p.craft && opts.onCraft) opts.onCraft(p.craft);
    draw();
    askPrice();
  }
  const current = () => ({ leader, team: [...team], every: every.filter((id) => team.includes(id)) });
  function askPrice(now = false) {
    clearTimeout(priceTimer);
    const go = async () => {
      const got = await core.call("ideas.party_price", { ...current(), ...(craftNow() ? { craft: craftNow() } : {}) });
      if (got) { price = got; draw(); }
    };
    if (now) go(); else priceTimer = setTimeout(go, 300);
  }
  /** *This party: about $2–6 an idea* (below $1, in cents) and, muted, where it comes from. */
  function priceLine() {
    if (!price) return null;
    const { low, high } = price, a = Math.round(low), b = Math.round(high);
    const range = low < 1 ? `$${low.toFixed(2)}–${high.toFixed(2)}` : a === b ? `$${a}` : `$${a}–${b}`;
    return h("div", { class: "party-price-box" },
      h("p", { class: "party-price", role: "status" }, `This party: about ${range} an idea`,
        h("small", { class: "muted" }, ` ${price.learned ? `from this project's last ${price.ideas} ideas` : "a first guess: it learns from this project's ideas"}`)),
      ...(price.hints || []).map((t) => h("p", { class: "muted party-hint" }, t)));    // spec 43 §5: quiet lines, never a block, no button
  }
  /** *adds about $0.35 to an idea it checks · about half of them* (*· every idea* when it checks every idea). */
  function addsWords(id) {
    const c = (price?.checks || []).find((x) => x.by === id);
    if (!c) return "";
    const share = c.every ? "every idea" : Math.abs(c.share - 0.5) < 0.03 ? "about half of them" : `about ${Math.round(c.share * 100)} % of them`;
    return ` · adds about $${c.usd.toFixed(2)} to an idea it checks · ${share}`;
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
        else if (inBand(band).length < seatsOf(core)[band]) team = [...team, id];
        else { core.flash(`${BANDS.find((b) => b[0] === band)[1]} has ${seatsOf(core)[band]} seats: take one out first.`); return; }
        partyId = "";
        draw(); drawOwn();
        changed();
      } }, head(kind, a.tier || "warrior"), h("b", {}, a.name, a.check ? h("span", { class: "check-badge" }, "checks") : null),
      h("small", { class: "muted" }, `${TIER_WORDS[a.tier] || ""} ${RACE_WORDS[kind]}${a.line ? ` · ${a.line}` : ""}`.trim()),
      h("span", { class: "team-mark", "aria-hidden": "true" }, icon(on ? "check" : "plus")));
  }

  function band([id, words, what]) {
    const n = seatsOf(core)[id], taken = inBand(id), on = fold === id;
    const own = (core.st.roles?.roles || []).filter((r) => team.includes(r.slug) && bandOf(r.slug) === id && !library(core).some((a) => a.id === r.slug));
    const bare = id === "build" ? team.filter((x) => !agent(x)).map((x) => ({ id: x, name: nameOf(x), band: id, craft: "engineering", tier: "laborer" })) : [];   // a party's own agent this project has not yet
    const list = [...library(core).filter((a) => a.band === id), ...own.map((r) => ({ ...r, id: r.slug, band: id })), ...bare]
      .sort((x, y) => (x.craft === craftNow() ? 0 : 1) - (y.craft === craftNow() ? 0 : 1));        // the goal's craft's first
    return h("section", { class: `party-fold band-${id}${on ? " is-open" : ""}`, "aria-label": words },
      h("button", { class: "fold-head", type: "button", "aria-expanded": String(on), onclick: () => { fold = on ? "" : id; draw(); } },
        h("b", {}, words), h("small", { class: "muted" }, taken.length ? names(id) : "none"), h("span", { class: "fold-mark", "aria-hidden": "true" }, icon(on ? "close" : "plus"))),
      on ? h("div", { class: "fold-body" },
        h("small", { class: "muted" }, `${taken.length} of ${n} · ${what}`),
        h("div", { class: "team-seats" }, ...Array.from({ length: n }, (_, i) => {
          const a = agent(taken[i]);
          return h("span", { class: `team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}`, title: a ? nameOf(taken[i]) : "A free seat" },
            a ? head(RACE[a.craft] || "peon", a.tier || "warrior") : "");
        })),
        h("div", { class: "team-list" }, ...list.map(seat)),
        h("button", { class: "ork-btn", type: "button", "data-done": id, onclick: () => { fold = ""; draw(); } }, "Done")) : null);
  }

  function drawTeam() {
    const line = h("p", { class: "party-line" }, h("b", {}, "Leads: "), names("lead"), " · ", h("b", {}, "Builds: "), names("build"), " · ", h("b", {}, "Checks: "), names("check"));
    if (!editing) {
      teamEl.replaceChildren(h("h3", {}, "Team"), ownRow(), line, priceLine(),
        h("button", { class: "ork-btn", type: "button", "data-change": "team", onclick: () => { editing = true; fold = "lead"; draw(); } }, "Change"));
      return;
    }
    if (!fold) { editing = false; drawTeam(); return; }            // every fold closed by Done: back to the line
    teamEl.replaceChildren(h("h3", {}, "Team"), ownRow(), ...BANDS.map(band), priceLine());
  }

  // -- the team's checks: each checker's, where it applies or on every idea, and what a check adds to an idea, in dollars ----------
  function drawChecks() {
    const checkers = team.map(agent).filter((a) => a?.check);
    const mine = every.filter((id) => team.includes(id));
    const said = !checkers.length ? "No check" : `${checkers.length} ${checkers.length === 1 ? "check" : "checks"}, ${mine.length ? `${mine.length} on every idea` : "where each applies"}`;
    if (!checking || !checkers.length) {
      checksEl.replaceChildren(h("h3", {}, "Checks"), h("p", { class: "party-line" }, checkers.length ? said : "No checker in the party: an idea is done when its own Done when lines are."),
        checkers.length ? h("button", { class: "ork-btn", type: "button", "data-change": "checks", onclick: () => { checking = true; drawChecks(); } }, "Change") : null);
      return;
    }
    checksEl.replaceChildren(h("h3", {}, "Checks"), h("div", { class: "checks-block", role: "group", "aria-label": "Checks" },
      h("p", { class: "muted" }, `How deep each idea is worked: every check adds a line to its Done when and a task to its plan.`),
      ...checkers.map((a) => {
        const box = h("input", { type: "checkbox", "aria-label": `Every idea: ${a.name}`, ...(every.includes(a.id) ? { checked: true } : {}) });
        box.addEventListener("change", () => { every = box.checked ? [...every, a.id] : every.filter((x) => x !== a.id); partyId = ""; drawOwn(); changed(); });
        const base = `${a.check.done} · applies ${a.check.applies}`, c = price?.checks?.find((x) => x.by === a.id);
        return h("div", { class: "check-row" }, head(RACE[a.craft], a.tier, { small: true }),
          h("span", { class: "check-text" }, h("b", {}, a.name), h("small", { class: "muted", "data-adds": a.id, "data-base": base }, `${base}${c ? ` · ${addsWords(c)}` : ""}`)),
          h("label", { class: "check-every" }, box, h("span", {}, "Every idea")));
      }),
      h("button", { class: "ork-btn", type: "button", "data-done": "checks", onclick: () => { checking = false; drawChecks(); } }, "Done")));
  }

  return {
    own: ownEl,
    team: teamEl,
    price: priceBox,
    checks: checksEl,
    /** The party a goal has (or starts with); `craft`: whose agents sort first. */
    set(party, craft = () => "") {
      leader = party.leader || TASKMASTER;
      team = [...(party.team || [])];
      every = [...(party.every || [])];
      editing = false; fold = ""; checking = false; price = null; asking = "";
      partyId = party.party || "";
      craftNow = craft;
      price = null; asking++;
      partyId = "";
      draw();
      drawOwn();
      drawPrice();
    },
    /** The picker is shown: the price now, and the person's parties. */
    open() { askPrice(); loadOwn(); },
    /** A craft's party in the seats at once. */
    preset(craft) {
      const p = partyOf(core, craft);
      leader = p.lead || TASKMASTER;
      team = [...p.build, ...p.check];
      every = [];
      partyId = "";
      draw(); drawOwn();
      changed();
    },
    get: party,
    /** The crafts of the party's agents, for a Mixed goal's own craft. */
    crafts: () => [leader, ...team].filter((id) => id !== TASKMASTER).map((id) => agent(id)?.craft).filter(Boolean),
    names,
    draw,
  };
}

/** `core`: the board's frame. Returns {el, open(after)}; `after(slug)` instead of opening the goal's screen. */
export function makeNewGoal(core) {
  let craft = "engineering", then = null;
  const party = makeParty(core, { onPick: (p) => { craft = p.craft; drawCraft(); } });          // Your parties: a party brings its craft
  const about = h("textarea", { class: "ork-field", rows: "4", "aria-label": "Description", placeholder: "A few lines: what it is for", maxlength: "20000" });
  const priority = prioritySwitch("new-goal-priority");
  const row = h("div", { class: "craft-row", role: "group", "aria-label": "Craft" });
  const craftLine = h("p", { class: "muted craft-line", "aria-live": "polite" });
  const left = h("div", {});
  const save = h("button", { class: "ork-btn primary big", type: "button", disabled: true }, "Save goal");
  const body = h("div", { class: "goal-steps one-sheet" });
  const sh = sheet("New goal", body, foot(save));
  about.addEventListener("input", () => { save.disabled = !about.value.trim(); });

  /** The goal's craft: the one picked, or a Mixed team's most (the first in the team on a tie). */
  function craftOf() {
    if (craft !== MIXED) return craft;
    const crafts = party.crafts();
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  }

  function pick(c) {
    craft = c;
    party.preset(c);
    drawCraft();
  }
  function drawCraft() {
    row.replaceChildren(...CRAFTS.map(([c, race]) => h("button", { class: "craft-tile", type: "button", "data-craft": c, "aria-label": CRAFT_WORDS[c],
      "aria-pressed": String(c === craft), title: CRAFT_WORDS[c], onclick: () => pick(c) }, head(race, "laborer"))),
      h("button", { class: "craft-tile mixed", type: "button", "data-craft": MIXED, "aria-label": "Mixed", "aria-pressed": String(craft === MIXED), title: "Mixed",
        onclick: () => pick(MIXED) }, h("span", { class: "craft-heads" }, ...CRAFTS.slice(0, 2).map(([, race]) => head(race, "laborer", { small: true })))));
    const line = craft === MIXED ? "A party of any crafts: the Taskmaster leads, you pick the rest" : CRAFTS.find((x) => x[0] === craft)?.[2] || "";
    craftLine.replaceChildren(h("b", {}, craft === MIXED ? "Mixed" : CRAFT_WORDS[craft]), `: ${craft === MIXED ? line : lcfirst(line)}`);
  }

  save.addEventListener("click", async () => {
    if (!about.value.trim()) return;
    save.disabled = true;
    const p = party.get();
    const got = await core.call("ideas.goal_save", { about: about.value.trim(), craft: craftOf(), leader: p.leader, team: p.team, every: p.every, priority: priority.get(), ...(p.party ? { party: p.party } : {}) });
    save.disabled = !about.value.trim();
    if (!got?.slug) return;
    (got.notes || []).forEach((n) => core.flash(n));       // an agent of the party's the project has already: kept as it is
    const after = then;
    then = null;
    sh.close();
    core.st.track = got.slug;
    await core.refresh();
    if (after) after(got.slug); else core.open({ kind: "goal", slug: got.slug });
  });
  sh.el.addEventListener("close", () => { then = null; });

  return {
    el: sh.el,
    open(after = null) {
      then = after;
      craft = "engineering";
      about.value = "";
      save.disabled = true;
      priority.set("normal");
      party.set({ leader: TASKMASTER, team: [], every: [] }, () => craftOf());
      party.preset(craft);
      drawCraft();
      left.replaceChildren(limitsNote(core.st.snap) || "");
      body.replaceChildren(
        h("section", { class: "new-goal-for", "aria-label": "What for" }, field("What for", about), h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el)),
        h("section", { class: "new-goal-craft", "aria-label": "Craft" }, h("h3", {}, "Craft"), row, craftLine),
        party.own, party.team, party.price, party.checks,
        h("p", { class: "muted hint" }, "The leader reads the goal and writes the title, the summary, what counts as done and the links."), left);
      sh.open();
      party.open();
      about.focus();
    },
  };
}
