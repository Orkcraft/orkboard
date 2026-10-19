// New goal on the phone in three steps, one sheet: 1. its craft —
// four tiles, the race's head on each (decisions §53), and Mixed —; 2. its team — the agents of the library that craft suggests, as
// seats, a tap takes one in or out, any craft's from the library (Mixed: the whole library, by craft, none taken); the Taskmaster is in
// every team —; 3. what it is for — the description, the priority, the team's checks (each checker's, where it applies or on every
// idea, and what it adds to an idea), what is left of the AI tools —, Save goal. A task goes to the one of the team who does its kind
// of work, whatever the goal's craft; a Mixed goal's craft is its team's most. The team sets how deep an idea is worked: a checker's
// check adds its line to the spec's Done when and its task to the plan (realm/idea_checks.py).
import { h, sheet, head, icon } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "./shell-who.js";
import { limitsNote } from "./shell-limits.js";

export const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"]];
const RACE = Object.fromEntries(CRAFTS.map(([c, r]) => [c, r]));
const SEATS = 5;                                       // a team's seats, the Taskmaster aside

const MIXED = "mixed";
const library = (core) => core.st.roles?.library || [];     // the agents that come with Orkline (ideas.roles: realm/library.py)
const suggested = (core) => core.st.roles?.suggested ?? 2;  // the library's first ones of the goal's craft come in the team at once

/** `core`: the board's frame. Returns {el, open(after)}; `after(slug)` instead of opening the goal's screen. */
export function makeNewGoal(core) {
  let step = 1, craft = "", team = [], every = [], more = false, then = null;
  const body = h("div", { class: "goal-steps" });
  const sh = sheet("New goal", body);
  const about = h("textarea", { class: "ork-field", rows: "5", "aria-label": "Description", placeholder: "A few lines: what it is for", maxlength: "20000" });
  const priority = prioritySwitch("new-goal-priority");

  const progress = () => h("ol", { class: "steps-bar", "aria-label": `Step ${step} of 3` },
    ...["Craft", "Team", "What for"].map((w, i) => h("li", { class: i + 1 === step ? "is-on" : i + 1 < step ? "is-done" : "" }, w)));
  const back = () => h("button", { class: "ork-btn big", type: "button", onclick: () => { step -= 1; draw(); } }, "Back");

  function stepCraft() {
    return [h("p", { class: "muted" }, "What kind of goal is it? Its craft picks the team it starts with."),
      h("div", { class: "craft-tiles" }, ...CRAFTS.map(([c, race, line]) => h("button", { class: "craft-tile", type: "button", "data-craft": c,
        "aria-pressed": String(c === craft), onclick: () => {
          if (c !== craft) { craft = c; team = library(core).filter((a) => a.craft === c).slice(0, suggested(core)).map((a) => a.id); }
          step = 2; draw();
        } }, head(race, "laborer"), h("b", {}, CRAFT_WORDS[c]), h("small", { class: "muted" }, `${RACE_WORDS[race]} · ${line}`))),
        h("button", { class: "craft-tile mixed", type: "button", "data-craft": MIXED, "aria-pressed": String(craft === MIXED), onclick: () => {
          if (craft !== MIXED) { craft = MIXED; team = []; }
          step = 2; draw();
        } }, h("span", { class: "craft-heads" }, ...CRAFTS.map(([, race]) => head(race, "laborer", { small: true }))), h("b", {}, "Mixed"),
          h("small", { class: "muted" }, "A team of any crafts: you pick each one")))];
  }

  function seat(a) {
    const on = team.includes(a.id);
    return h("button", { class: "team-row", type: "button", "aria-pressed": String(on), "data-agent": a.id,
      "aria-label": `${on ? "Take out" : "Take in"}: ${a.name}`, onclick: () => {
        team = on ? team.filter((x) => x !== a.id) : team.length < SEATS ? [...team, a.id] : team;
        draw();
      } }, head(RACE[a.craft], a.tier), h("b", {}, a.name, a.check ? h("span", { class: "check-badge" }, "checks") : null),
      h("small", { class: "muted" }, `${TIER_WORDS[a.tier]} ${RACE_WORDS[RACE[a.craft]]} · ${a.line}`),
      h("span", { class: "team-mark", "aria-hidden": "true" }, icon(on ? "check" : "plus")));
  }

  function stepTeam() {
    if (craft === MIXED) more = true;                // the whole library, by craft
    const mine = library(core).filter((a) => a.craft === craft), others = library(core).filter((a) => a.craft !== craft);
    const byCraft = (list) => CRAFTS.filter(([c]) => list.some((a) => a.craft === c))
      .flatMap(([c]) => [h("h4", { class: "team-craft" }, CRAFT_WORDS[c]), h("div", { class: "team-list" }, ...list.filter((a) => a.craft === c).map(seat))]);
    const seats = h("div", { class: "team-seats", "aria-label": `The team: ${team.length} of ${SEATS}` },
      h("span", { class: "team-seat is-keeper", title: "Taskmaster" }, head("peon", "elder")),
      ...Array.from({ length: SEATS }, (_, i) => {
        const a = library(core).find((x) => x.id === team[i]);
        return h("span", { class: `team-seat${a ? "" : " is-empty"}`, title: a?.name || "A free seat" }, a ? head(RACE[a.craft], a.tier) : "");
      }));
    return [seats, h("p", { class: "muted" }, `The Taskmaster plans for every team. ${team.length} of ${SEATS} seats taken: a task goes to the one who does its kind of work.`),
      mine.length ? h("h3", {}, `${CRAFT_WORDS[craft]}: suggested`) : null, mine.length ? h("div", { class: "team-list" }, ...mine.map(seat)) : null,
      more ? h("h3", {}, craft === MIXED ? "The library" : "From the library") : null, ...(more ? byCraft(others) : []),
      more ? null : h("button", { class: "linkish", type: "button", onclick: () => { more = true; draw(); } }, "+ From the library: the other crafts' agents"),
      foot(back(), h("button", { class: "ork-btn primary big", type: "button", disabled: !team.length, onclick: () => { step = 3; draw(); } }, "Next"))]
      .filter(Boolean);
  }

  function stepWhat() {
    const save = h("button", { class: "ork-btn primary big", type: "button", disabled: !about.value.trim() }, "Save goal");
    about.oninput = () => { save.disabled = !about.value.trim(); };
    save.addEventListener("click", async () => {
      save.disabled = true;
      const got = await core.call("ideas.goal_save", { about: about.value.trim(), craft: craftOf(), team, every: every.filter((id) => team.includes(id)),
        priority: priority.get() });
      save.disabled = false;
      if (!got?.slug) return;
      const after = then;
      then = null;
      sh.close();
      core.st.track = got.slug;
      await core.refresh();
      if (after) after(got.slug); else core.open({ kind: "goal", slug: got.slug });
    });
    const heads = h("span", { class: "team-heads" }, ...team.map((id) => library(core).find((a) => a.id === id)).filter(Boolean).map((a) => head(RACE[a.craft], a.tier, { small: true, title: a.name })));
    return [h("p", { class: "muted" }, h("span", {}, `${craft === MIXED ? `Mixed, mostly ${CRAFT_WORDS[craftOf()]}` : CRAFT_WORDS[craft]} · `), heads),
      field("Description", about), h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el),
      h("p", { class: "muted hint" }, "The Taskmaster reads it and writes the title, the summary, what counts as done and the links."),
      checksBlock(), limitsNote(core.st.snap), foot(back(), save)].filter(Boolean);
  }

  /** The team's checks: each checker's, where it applies or on every idea, and what a check adds to an idea, in dollars. */
  function checksBlock() {
    const costs = core.st.roles?.tier_costs || {};
    const checkers = team.map((id) => library(core).find((a) => a.id === id)).filter((a) => a?.check);
    if (!checkers.length) return h("p", { class: "muted hint" }, "No checker in the team: an idea is done when its own Done when lines are.");
    const priced = checkers.every((a) => Number(costs[a.tier]) > 0);       // no price known: no number said
    const usd = (n) => (priced ? ` · ≈ $${Number(n).toFixed(2)}` : "");
    const total = checkers.reduce((sum, a) => sum + Number(costs[a.tier] || 0), 0);
    return h("div", { class: "checks-block", role: "group", "aria-label": "Checks" }, h("h3", {}, "Checks"),
      h("p", { class: "muted" }, `How deep each idea is worked: every check adds a line to its Done when and a task to its plan${priced ? `, ≈ $${total.toFixed(2)} an idea they all apply to` : ""}.`),
      ...checkers.map((a) => {
        const box = h("input", { type: "checkbox", "aria-label": `Every idea: ${a.name}`, ...(every.includes(a.id) ? { checked: true } : {}) });
        box.addEventListener("change", () => { every = box.checked ? [...every, a.id] : every.filter((x) => x !== a.id); });
        return h("div", { class: "check-row" }, head(RACE[a.craft], a.tier, { small: true }),
          h("span", { class: "check-text" }, h("b", {}, a.name), h("small", { class: "muted" }, `${a.check.done} · applies ${a.check.applies}${usd(costs[a.tier])}`)),
          h("label", { class: "check-every" }, box, h("span", {}, "Every idea")));
      }));
  }

  /** The goal's craft: the one picked, or a Mixed team's most (the first in the team on a tie). */
  function craftOf() {
    if (craft !== MIXED) return craft;
    const crafts = team.map((id) => library(core).find((a) => a.id === id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  }

  function draw() {
    body.replaceChildren(progress(), ...(step === 1 ? stepCraft() : step === 2 ? stepTeam() : stepWhat()));
    if (step === 3) about.focus();
  }

  return {
    el: sh.el,
    open(after = null) {
      step = 1; craft = ""; team = []; every = []; more = false; then = after;
      about.value = "";
      priority.set("normal");
      draw();
      sh.open();
    },
  };
}
