// New goal on the phone in three steps, one sheet: 1. its craft — five tiles, the race's head on each (decisions §53), and Mixed —;
// 2. its party, three bands of seats: Leads (one: the goal's steps — its reading, its ideas' drafts and plans, accepting the goal — run
// as it; the Taskmaster when none), Builds (three at most) and Checks (two at most); the craft's party in them at once, a tap takes
// an agent in or out of its band; 3. what it is for — the description, the priority, the checkers' checks (where each applies or on
// every idea, and what it adds to an idea), what is left of the AI tools —, Save goal. A task goes to the one of the party who does
// its kind of work (Grunt fills in); a checker's check adds its line to the spec's Done when and its task to the plan
// (realm/idea_checks.py). A Mixed goal starts with the Taskmaster alone, its craft its party's most.
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

/** `core`: the board's frame. Returns {el, open(after)}; `after(slug)` instead of opening the goal's screen. */
export function makeNewGoal(core) {
  let step = 1, craft = "", leader = TASKMASTER, team = [], every = [], then = null;   // team: the builders and checkers
  const body = h("div", { class: "goal-steps" });
  const sh = sheet("New goal", body);
  const about = h("textarea", { class: "ork-field", rows: "5", "aria-label": "Description", placeholder: "A few lines: what it is for", maxlength: "20000" });
  const priority = prioritySwitch("new-goal-priority");

  const progress = () => h("ol", { class: "steps-bar", "aria-label": `Step ${step} of 3` },
    ...["Craft", "Team", "What for"].map((w, i) => h("li", { class: i + 1 === step ? "is-on" : i + 1 < step ? "is-done" : "" }, w)));
  const back = () => h("button", { class: "ork-btn big", type: "button", onclick: () => { step -= 1; draw(); } }, "Back");

  function pickCraft(c) {
    if (c !== craft) {
      craft = c;
      const p = partyOf(core, c);
      leader = p.lead || TASKMASTER;
      team = [...p.build, ...p.check];
    }
    step = 2;
    draw();
  }

  function stepCraft() {
    return [h("p", { class: "muted" }, "What kind of goal is it? Its craft picks the party it starts with."),
      h("div", { class: "craft-tiles" }, ...CRAFTS.map(([c, race, line]) => h("button", { class: "craft-tile", type: "button", "data-craft": c,
        "aria-pressed": String(c === craft), onclick: () => pickCraft(c) },
        head(race, "laborer"), h("b", {}, CRAFT_WORDS[c]), h("small", { class: "muted" }, `${RACE_WORDS[race]} · ${line}`))),
        h("button", { class: "craft-tile mixed", type: "button", "data-craft": MIXED, "aria-pressed": String(craft === MIXED), onclick: () => pickCraft(MIXED) },
          h("span", { class: "craft-heads" }, ...CRAFTS.map(([, race]) => head(race, "laborer", { small: true }))), h("b", {}, "Mixed"),
          h("small", { class: "muted" }, "A party of any crafts: the Taskmaster leads, you pick the rest")))];
  }

  const agent = (id) => library(core).find((a) => a.id === id);
  const inBand = (band) => (band === "lead" ? [leader] : team.filter((id) => agent(id)?.band === band));

  /** An agent's row in its band: a tap takes it in or out (a leader takes the one seat; out, the Taskmaster leads). */
  function seat(a) {
    const on = a.band === "lead" ? leader === a.id : team.includes(a.id);
    return h("button", { class: "team-row", type: "button", "aria-pressed": String(on), "data-agent": a.id,
      "aria-label": `${on ? "Take out" : "Take in"}: ${a.name}`, onclick: () => {
        if (a.band === "lead") leader = on ? TASKMASTER : a.id;
        else if (on) team = team.filter((x) => x !== a.id);
        else if (inBand(a.band).length < seatsOf(core)[a.band]) team = [...team, a.id];
        else { core.flash(`${BANDS.find((b) => b[0] === a.band)[1]} has ${seatsOf(core)[a.band]} seats: take one out first.`); return; }
        draw();
      } }, head(RACE[a.craft], a.tier), h("b", {}, a.name),
      h("small", { class: "muted" }, `${TIER_WORDS[a.tier]} ${RACE_WORDS[RACE[a.craft]]} · ${a.line}`),
      h("span", { class: "team-mark", "aria-hidden": "true" }, icon(on ? "check" : "plus")));
  }

  function band([id, words, what]) {
    const n = seatsOf(core)[id], taken = inBand(id);
    const list = library(core).filter((a) => a.band === id)
      .sort((x, y) => (x.craft === craft ? 0 : 1) - (y.craft === craft ? 0 : 1));        // the goal's craft's first
    return h("section", { class: `party-band band-${id}`, "aria-label": words },
      h("div", { class: "band-head" }, h("h3", {}, words), h("small", { class: "muted" }, `${taken.length} of ${n} · ${what}`)),
      h("div", { class: "team-seats" }, ...Array.from({ length: n }, (_, i) => {
        const a = agent(taken[i]);
        return h("span", { class: `team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}`, title: a?.name || "A free seat" },
          a ? head(RACE[a.craft], a.tier) : "");
      })),
      h("div", { class: "team-list" }, ...list.map(seat)));
  }

  function stepTeam() {
    return [h("p", { class: "muted" }, "The goal's party: its leader plans and accepts, its builders work, its checkers check. "
      + "A task goes to the one who does its kind of work; Grunt fills in."),
      ...BANDS.map(band),
      foot(back(), h("button", { class: "ork-btn primary big", type: "button", onclick: () => { step = 3; draw(); } }, "Next"))];
  }

  function stepWhat() {
    const save = h("button", { class: "ork-btn primary big", type: "button", disabled: !about.value.trim() }, "Save goal");
    about.oninput = () => { save.disabled = !about.value.trim(); };
    save.addEventListener("click", async () => {
      save.disabled = true;
      const got = await core.call("ideas.goal_save", { about: about.value.trim(), craft: craftOf(), leader, team,
        every: every.filter((id) => team.includes(id)), priority: priority.get() });
      save.disabled = false;
      if (!got?.slug) return;
      const after = then;
      then = null;
      sh.close();
      core.st.track = got.slug;
      await core.refresh();
      if (after) after(got.slug); else core.open({ kind: "goal", slug: got.slug });
    });
    const lead = agent(leader), names = (band) => inBand(band).map((id) => agent(id)?.name).filter(Boolean).join(", ") || "none";
    return [h("p", { class: "muted party-line" }, `${craft === MIXED ? `Mixed, mostly ${CRAFT_WORDS[craftOf()]}` : CRAFT_WORDS[craft]} · led by ${lead?.name || "Taskmaster"} · `
      + `builds: ${names("build")} · checks: ${names("check")}`),
      field("Description", about), h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el),
      h("p", { class: "muted hint" }, `${lead?.name || "The Taskmaster"} reads it and writes the title, the summary, what counts as done and the links.`),
      checksBlock(), limitsNote(core.st.snap), foot(back(), save)].filter(Boolean);
  }

  /** The team's checks: each checker's, where it applies or on every idea, and what a check adds to an idea, in dollars. */
  function checksBlock() {
    const costs = core.st.roles?.tier_costs || {};
    const checkers = team.map(agent).filter((a) => a?.check);
    if (!checkers.length) return h("p", { class: "muted hint" }, "No checker in the party: an idea is done when its own Done when lines are.");
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
    const crafts = [leader, ...team].filter((id) => id !== TASKMASTER).map((id) => agent(id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  }

  function draw() {
    body.replaceChildren(progress(), ...(step === 1 ? stepCraft() : step === 2 ? stepTeam() : stepWhat()));
    if (step === 3) about.focus();
  }

  return {
    el: sh.el,
    open(after = null) {
      step = 1; craft = ""; leader = TASKMASTER; team = []; every = []; then = after;
      about.value = "";
      priority.set("normal");
      draw();
      sh.open();
    },
  };
}
