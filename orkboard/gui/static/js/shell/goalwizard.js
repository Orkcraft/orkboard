// New goal on the desktop in three steps, as on the phone (pwa/shell-goal-new.js): 1. its craft — five tiles, the race's head on
// each (decisions §53), and Mixed —; 2. its party in three bands of seats (ideas.roles `seats`, `parties`, realm/library.py): Leads
// (one: the goal's steps run as it, and it accepts the goal; the Taskmaster when none), Builds (three at most), Checks (two at most);
// the craft's party in them at once, a click takes an agent in or out of its band —; 3. what it is for — the description, the
// priority and the checkers' checks (where each applies or on every idea, and what it adds to an idea) —, Save goal. A task goes to
// the one of the party who does its kind of work; a checker's check adds its line to the spec's Done when and its task to the plan
// (realm/idea_checks.py).
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { track } from "../board/store.js";
import { act, roles, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { Head, Icon, CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "../orkui.js";
import { PRIORITIES } from "./goaldialog.js";

const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"],
  ["product", "lich", "Who it is for, what it moves, what it leaves out"]];
const RACE = Object.fromEntries(CRAFTS);
const BANDS = [["lead", "Leads", "plans the goal's ideas and accepts the goal"], ["build", "Builds", "do the work"],
  ["check", "Checks", "hold each idea to their check"]];
const TASKMASTER = "taskmaster";
const MIXED = "mixed";

export function GoalWizard({ then = "" }) {
  const library = roles.value?.library || [];
  const seats = roles.value?.seats || { lead: 1, build: 3, check: 2 };
  const partyOf = (c) => roles.value?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
  const [step, setStep] = useState(1);
  const [craft, setCraft] = useState("");
  const [leader, setLeader] = useState(TASKMASTER);
  const [team, setTeam] = useState([]);                  // the builders and checkers
  const [every, setEvery] = useState([]);
  const [about, setAbout] = useState("");
  const [priority, setPriority] = useState("normal");
  const [saving, setSaving] = useState(false);

  const agent = (id) => library.find((a) => a.id === id);
  const inBand = (band) => (band === "lead" ? [leader] : team.filter((id) => agent(id)?.band === band));
  const pick = (c) => {
    if (c !== craft) {
      const p = partyOf(c);
      setCraft(c);
      setLeader(p.lead || TASKMASTER);
      setTeam([...p.build, ...p.check]);
    }
    setStep(2);
  };
  /** A click takes an agent in or out of its band (a leader takes the one seat; out, the Taskmaster leads). */
  const toggle = (a) => {
    if (a.band === "lead") { setLeader(leader === a.id ? TASKMASTER : a.id); return; }
    if (team.includes(a.id)) setTeam(team.filter((x) => x !== a.id));
    else if (inBand(a.band).length < seats[a.band]) setTeam([...team, a.id]);
    else toast(`${BANDS.find((b) => b[0] === a.band)[1]} has ${seats[a.band]} seats: take one out first.`);
  };
  const craftOf = () => {
    if (craft !== MIXED) return craft;
    const crafts = [leader, ...team].filter((id) => id !== TASKMASTER).map((id) => agent(id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  };
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const got = await act("ideas.goal_save", { about: about.trim(), craft: craftOf(), leader, team, every: every.filter((id) => team.includes(id)), priority });
    setSaving(false);
    if (!got?.slug) return;
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };

  const on = (a) => (a.band === "lead" ? leader === a.id : team.includes(a.id));
  const row = (a) => html`<button type="button" key=${a.id} class="shell-team-row" aria-pressed=${String(on(a))} data-agent=${a.id}
      aria-label=${`${on(a) ? "Take out" : "Take in"}: ${a.name}`} onClick=${() => toggle(a)}>
    <${Head} race=${RACE[a.craft]} tier=${a.tier} /><b>${a.name}${a.check && html`<span class="shell-check-badge">checks</span>`}</b>
    <small class="ok-tone-muted">${TIER_WORDS[a.tier]} ${RACE_WORDS[RACE[a.craft]]} · ${a.line}</small>
    <span class="shell-team-mark" aria-hidden="true"><${Icon} name=${on(a) ? "check" : "plus"} /></span></button>`;
  /** A band: its seats, then its agents, the goal's craft's first. */
  const band = ([id, words, what]) => {
    const taken = inBand(id);
    const list = library.filter((a) => a.band === id).sort((x, y) => (x.craft === craft ? 0 : 1) - (y.craft === craft ? 0 : 1));
    return html`<section key=${id} class=${`shell-party-band band-${id}`} aria-label=${words}>
      <div class="shell-band-head"><h3>${words}</h3><small class="ok-tone-muted">${taken.length} of ${seats[id]} · ${what}</small></div>
      <div class="shell-team-seats">${Array.from({ length: seats[id] }, (_, i) => {
        const a = agent(taken[i]);
        return html`<span key=${i} class=${`shell-team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}`} title=${a?.name || "A free seat"}>${a && html`<${Head} race=${RACE[a.craft]} tier=${a.tier} />`}</span>`;
      })}</div>
      <div class="shell-team-list">${list.map(row)}</div></section>`;
  };

  /** The team's checks: each checker's, where it applies or on every idea, and what a check adds to an idea, in dollars. */
  function checksBlock() {
    const costs = roles.value?.tier_costs || {};
    const checkers = team.map(agent).filter((a) => a?.check);
    if (!checkers.length) return html`<p class="ok-tone-muted">No checker in the party: an idea is done when its own Done when lines are.</p>`;
    const priced = checkers.every((a) => Number(costs[a.tier]) > 0);       // no price known: no number said
    const usd = (n) => (priced ? ` · ≈ $${Number(n).toFixed(2)}` : "");
    const total = checkers.reduce((sum, a) => sum + Number(costs[a.tier] || 0), 0);
    return html`<div class="shell-checks" role="group" aria-label="Checks"><span class="ok-font-label">Checks</span>
      <p class="ok-tone-muted">How deep each idea is worked: every check adds a line to its Done when and a task to its plan${priced ? `, ≈ $${total.toFixed(2)} an idea they all apply to` : ""}.</p>
      ${checkers.map((a) => html`<div key=${a.id} class="shell-check-row"><${Head} race=${RACE[a.craft]} tier=${a.tier} small=${true} />
        <span><b>${a.name}</b> <small class="ok-tone-muted">${a.check.done} · applies ${a.check.applies}${usd(costs[a.tier])}</small></span>
        <label class="shell-check-every"><input type="checkbox" aria-label=${`Every idea: ${a.name}`} checked=${every.includes(a.id)}
          onChange=${(e) => setEvery(e.target.checked ? [...every, a.id] : every.filter((x) => x !== a.id))} /> Every idea</label></div>`)}</div>`;
  }

  const steps = html`<ol class="shell-steps" aria-label=${`Step ${step} of 3`}>${["Craft", "Team", "What for"].map((w, i) => html`<li key=${w}
    class=${i + 1 === step ? "is-on" : i + 1 < step ? "is-done" : ""}>${w}</li>`)}</ol>`;
  let body, foot;
  if (step === 1) {
    body = html`<p class="ok-tone-muted">What kind of goal is it? Its craft picks the party it starts with.</p>
      <div class="shell-craft-tiles">${CRAFTS.map(([c, race, line]) => html`<button type="button" key=${c} class="shell-craft-tile" data-craft=${c}
          aria-pressed=${String(c === craft)} onClick=${() => pick(c)}><${Head} race=${race} /><b>${CRAFT_WORDS[c]}</b>
          <small class="ok-tone-muted">${RACE_WORDS[race]} · ${line}</small></button>`)}
        <button type="button" class="shell-craft-tile mixed" data-craft=${MIXED} aria-pressed=${String(craft === MIXED)} onClick=${() => pick(MIXED)}>
          <span class="shell-craft-heads">${CRAFTS.map(([c, race]) => html`<${Head} key=${c} race=${race} small=${true} />`)}</span><b>Mixed</b>
          <small class="ok-tone-muted">A party of any crafts: the Taskmaster leads, you pick the rest</small></button></div>`;
    foot = html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>`;
  } else if (step === 2) {
    body = html`<p class="ok-tone-muted">The goal's party: its leader plans and accepts, its builders work, its checkers check. A task goes to the one who does its kind of work; Grunt fills in.</p>
      ${BANDS.map(band)}`;
    foot = html`<button type="button" class="ork-btn" onClick=${() => setStep(1)}>Back</button>
      <button type="button" class="ork-btn primary" onClick=${() => setStep(3)}>Next</button>`;
  } else {
    const lead = agent(leader), names = (b) => inBand(b).map((id) => agent(id)?.name).filter(Boolean).join(", ") || "none";
    body = html`<form id="goal-form" class="shell-form" onSubmit=${save}>
      <p class="ok-tone-muted shell-party-line">${craft === MIXED ? `Mixed, mostly ${CRAFT_WORDS[craftOf()]}` : CRAFT_WORDS[craft]} · led by ${lead?.name || "Taskmaster"} · builds: ${names("build")} · checks: ${names("check")}</p>
      <label class="shell-field"><span class="ok-font-label">Description</span>
        <textarea class="ork-field" rows="5" autofocus value=${about} aria-label="Description" placeholder="A few lines: what you want to reach, and why"
          onInput=${(e) => setAbout(e.target.value)}></textarea></label>
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say(`${lead?.name || "The Taskmaster"} reads the repository and writes the title, the summary, the metrics and the links.`)}</p>
      ${checksBlock()}
    </form>`;
    foot = html`<button type="button" class="ork-btn" onClick=${() => setStep(2)}>Back</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!about.trim() || saving}>Save goal</button>`;
  }
  return html`<${Modal} title="New goal" onClose=${closeDialog} wide=${true} foot=${foot}>${steps}${body}<//>`;
}
