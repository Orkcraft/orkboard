// New goal on the phone in three steps, one sheet (a mock of the team's flow: the host does not keep the team yet): 1. its craft —
// four tiles, the race's head on each (decisions §53), and Mixed —; 2. its team — the agents of the library that craft suggests, as
// seats, a tap takes one in or out, any craft's from the library (Mixed: the whole library, by craft, none taken); the Taskmaster is in
// every team —; 3. what it is for — the description, the priority, what is left of the AI tools —, Save goal. A task goes to the one
// of the team who does its kind of work, whatever the goal's craft; a Mixed goal's craft is its team's most.
import { h, sheet, head, icon } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "./shell-who.js";
import { limitsNote } from "./shell-limits.js";

export const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"]];
const RACE = Object.fromEntries(CRAFTS.map(([c, r]) => [c, r]));
const SEATS = 5;                                       // a team's seats, the Taskmaster aside

// The library: agents that come with Orkline, each with what it does (a mock: the host's roles take their place).
export const LIBRARY = [
  { id: "grunt", name: "Grunt", craft: "engineering", tier: "warrior", line: "Writes the code a task asks for, with its tests" },
  { id: "architect", name: "Architect", craft: "engineering", tier: "elder", line: "Splits a wide change into steps and keeps the modules apart" },
  { id: "tester", name: "Tester", craft: "engineering", tier: "laborer", line: "Writes the tests a change lacks and finds the cases that break it" },
  { id: "reviewer", name: "Reviewer", craft: "engineering", tier: "elder", line: "Reads a change before it merges and says what breaks" },
  { id: "product-designer", name: "Product designer", craft: "design", tier: "elder", line: "Turns a goal into flows and screens people get through" },
  { id: "design-system-designer", name: "Design system designer", craft: "design", tier: "warrior", line: "Keeps the components and tokens one: adds what is missing in orkUI" },
  { id: "accessibility-reviewer", name: "Accessibility reviewer", craft: "design", tier: "warrior", line: "Checks contrast, tap sizes, labels and the keyboard" },
  { id: "artist", name: "Artist", craft: "design", tier: "laborer", line: "Draws the pixel art: icons, heads and pictures" },
  { id: "analyst", name: "Analyst", craft: "data", tier: "warrior", line: "Turns the event log into the goal's metrics" },
  { id: "data-engineer", name: "Data engineer", craft: "data", tier: "elder", line: "Builds the pipelines and tables the numbers come from" },
  { id: "experimenter", name: "Experimenter", craft: "data", tier: "warrior", line: "Sets up an A/B test and says when it is decided" },
  { id: "sql", name: "SQL", craft: "data", tier: "laborer", line: "Writes and checks the queries a report needs" },
  { id: "copywriter", name: "Copywriter", craft: "marketing", tier: "warrior", line: "Writes the pages and posts, in the product's voice" },
  { id: "growth", name: "Growth", craft: "marketing", tier: "elder", line: "Plans the launch and the channels, and counts what they bring" },
  { id: "seo", name: "SEO", craft: "marketing", tier: "laborer", line: "Finds the words people search for and where they go" },
  { id: "community", name: "Community", craft: "marketing", tier: "laborer", line: "Answers in the forums and channels and brings back what people ask" },
];
const SUGGESTED = 2;
const MIXED = "mixed";                                   // the library's first ones of the goal's craft come in the team at once

/** `core`: the board's frame. Returns {el, open(after)}; `after(slug)` instead of opening the goal's screen. */
export function makeNewGoal(core) {
  let step = 1, craft = "", team = [], more = false, then = null;
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
          if (c !== craft) { craft = c; team = LIBRARY.filter((a) => a.craft === c).slice(0, SUGGESTED).map((a) => a.id); }
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
      } }, head(RACE[a.craft], a.tier), h("b", {}, a.name), h("small", { class: "muted" }, `${TIER_WORDS[a.tier]} ${RACE_WORDS[RACE[a.craft]]} · ${a.line}`),
      h("span", { class: "team-mark", "aria-hidden": "true" }, icon(on ? "check" : "plus")));
  }

  function stepTeam() {
    if (craft === MIXED) more = true;                // the whole library, by craft
    const mine = LIBRARY.filter((a) => a.craft === craft), others = LIBRARY.filter((a) => a.craft !== craft);
    const byCraft = (list) => CRAFTS.filter(([c]) => list.some((a) => a.craft === c))
      .flatMap(([c]) => [h("h4", { class: "team-craft" }, CRAFT_WORDS[c]), h("div", { class: "team-list" }, ...list.filter((a) => a.craft === c).map(seat))]);
    const seats = h("div", { class: "team-seats", "aria-label": `The team: ${team.length} of ${SEATS}` },
      h("span", { class: "team-seat is-keeper", title: "Taskmaster" }, head("peon", "elder")),
      ...Array.from({ length: SEATS }, (_, i) => {
        const a = LIBRARY.find((x) => x.id === team[i]);
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
      const got = await core.call("ideas.goal_save", { about: about.value.trim(), craft: craftOf(), team, priority: priority.get() });
      save.disabled = false;
      if (!got?.slug) return;
      const after = then;
      then = null;
      sh.close();
      core.st.track = got.slug;
      await core.refresh();
      if (after) after(got.slug); else core.open({ kind: "goal", slug: got.slug });
    });
    const heads = h("span", { class: "team-heads" }, ...team.map((id) => LIBRARY.find((a) => a.id === id)).filter(Boolean).map((a) => head(RACE[a.craft], a.tier, { small: true, title: a.name })));
    return [h("p", { class: "muted" }, h("span", {}, `${craft === MIXED ? `Mixed, mostly ${CRAFT_WORDS[craftOf()]}` : CRAFT_WORDS[craft]} · `), heads),
      field("Description", about), h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el),
      h("p", { class: "muted hint" }, "The Taskmaster reads it and writes the title, the summary, what counts as done and the links."),
      limitsNote(core.st.snap), foot(back(), save)].filter(Boolean);
  }

  /** The goal's craft: the one picked, or a Mixed team's most (the first in the team on a tie). */
  function craftOf() {
    if (craft !== MIXED) return craft;
    const crafts = team.map((id) => LIBRARY.find((a) => a.id === id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  }

  function draw() {
    body.replaceChildren(progress(), ...(step === 1 ? stepCraft() : step === 2 ? stepTeam() : stepWhat()));
    if (step === 3) about.focus();
  }

  return {
    el: sh.el,
    open(after = null) {
      step = 1; craft = ""; team = []; more = false; then = after;
      about.value = "";
      priority.set("normal");
      draw();
      sh.open();
    },
  };
}
