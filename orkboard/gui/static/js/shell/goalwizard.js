// New goal on the desktop in three steps, as on the phone (pwa/shell-goal-new.js): 1. its craft — four tiles, the race's head on
// each (decisions §53), and Mixed —; 2. its team — the library's agents (ideas.roles `library`, realm/library.py), the craft's first
// ones in it at once; a click takes one in or out, any craft's from the library; the Taskmaster plans for every team —; 3. what it is
// for — the description and the priority —, Save goal. A task goes to the one of the team who does its kind of work.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { track } from "../board/store.js";
import { act, roles, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { Head, Icon, CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "../orkui.js";
import { PRIORITIES } from "./goaldialog.js";

const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"]];
const RACE = Object.fromEntries(CRAFTS);
const MIXED = "mixed";
const SEATS = 5;

export function GoalWizard({ then = "" }) {
  const library = roles.value?.library || [];
  const suggested = roles.value?.suggested ?? 2;
  const [step, setStep] = useState(1);
  const [craft, setCraft] = useState("");
  const [team, setTeam] = useState([]);
  const [more, setMore] = useState(false);
  const [about, setAbout] = useState("");
  const [priority, setPriority] = useState("normal");
  const [saving, setSaving] = useState(false);

  const pick = (c) => {
    if (c !== craft) { setCraft(c); setTeam(c === MIXED ? [] : library.filter((a) => a.craft === c).slice(0, suggested).map((a) => a.id)); }
    setMore(c === MIXED);
    setStep(2);
  };
  const toggle = (id) => setTeam(team.includes(id) ? team.filter((x) => x !== id) : team.length < SEATS ? [...team, id] : team);
  const craftOf = () => {
    if (craft !== MIXED) return craft;
    const crafts = team.map((id) => library.find((a) => a.id === id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  };
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const got = await act("ideas.goal_save", { about: about.trim(), craft: craftOf(), team, priority });
    setSaving(false);
    if (!got?.slug) return;
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };

  const row = (a) => html`<button type="button" key=${a.id} class="shell-team-row" aria-pressed=${String(team.includes(a.id))}
      aria-label=${`${team.includes(a.id) ? "Take out" : "Take in"}: ${a.name}`} onClick=${() => toggle(a.id)}>
    <${Head} race=${RACE[a.craft]} tier=${a.tier} /><b>${a.name}</b>
    <small class="ok-tone-muted">${TIER_WORDS[a.tier]} ${RACE_WORDS[RACE[a.craft]]} · ${a.line}</small>
    <span class="shell-team-mark" aria-hidden="true"><${Icon} name=${team.includes(a.id) ? "check" : "plus"} /></span></button>`;
  const byCraft = (list) => CRAFTS.filter(([c]) => list.some((a) => a.craft === c)).map(([c]) => html`<div key=${c}>
    <h4 class="shell-team-craft">${CRAFT_WORDS[c]}</h4>${list.filter((a) => a.craft === c).map(row)}</div>`);

  const steps = html`<ol class="shell-steps" aria-label=${`Step ${step} of 3`}>${["Craft", "Team", "What for"].map((w, i) => html`<li key=${w}
    class=${i + 1 === step ? "is-on" : i + 1 < step ? "is-done" : ""}>${w}</li>`)}</ol>`;
  let body, foot;
  if (step === 1) {
    body = html`<p class="ok-tone-muted">What kind of goal is it? Its craft picks the team it starts with.</p>
      <div class="shell-craft-tiles">${CRAFTS.map(([c, race, line]) => html`<button type="button" key=${c} class="shell-craft-tile" data-craft=${c}
          aria-pressed=${String(c === craft)} onClick=${() => pick(c)}><${Head} race=${race} /><b>${CRAFT_WORDS[c]}</b>
          <small class="ok-tone-muted">${RACE_WORDS[race]} · ${line}</small></button>`)}
        <button type="button" class="shell-craft-tile mixed" data-craft=${MIXED} aria-pressed=${String(craft === MIXED)} onClick=${() => pick(MIXED)}>
          <span class="shell-craft-heads">${CRAFTS.map(([c, race]) => html`<${Head} key=${c} race=${race} small=${true} />`)}</span><b>Mixed</b>
          <small class="ok-tone-muted">A team of any crafts: you pick each one</small></button></div>`;
    foot = html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>`;
  } else if (step === 2) {
    const mine = library.filter((a) => a.craft === craft), others = library.filter((a) => a.craft !== craft);
    body = html`<div class="shell-team-seats" aria-label=${`The team: ${team.length} of ${SEATS}`}>
        <span class="shell-team-seat is-keeper" title="Taskmaster"><${Head} race="peon" tier="elder" /></span>
        ${Array.from({ length: SEATS }, (_, i) => {
          const a = library.find((x) => x.id === team[i]);
          return html`<span key=${i} class=${`shell-team-seat${a ? "" : " is-empty"}`} title=${a?.name || "A free seat"}>${a && html`<${Head} race=${RACE[a.craft]} tier=${a.tier} />`}</span>`;
        })}</div>
      <p class="ok-tone-muted">The Taskmaster plans for every team. ${team.length} of ${SEATS} seats taken: a task goes to the one who does its kind of work.</p>
      ${mine.length > 0 && html`<h3>${CRAFT_WORDS[craft]}: suggested</h3>${mine.map(row)}`}
      ${more ? html`<h3>${craft === MIXED ? "The library" : "From the library"}</h3>${byCraft(others)}`
        : html`<button type="button" class="ork-btn quiet" onClick=${() => setMore(true)}>+ From the library: the other crafts' agents</button>`}`;
    foot = html`<button type="button" class="ork-btn" onClick=${() => setStep(1)}>Back</button>
      <button type="button" class="ork-btn primary" disabled=${!team.length} onClick=${() => setStep(3)}>Next</button>`;
  } else {
    body = html`<form id="goal-form" class="shell-form" onSubmit=${save}>
      <p class="ok-tone-muted">${craft === MIXED ? `Mixed, mostly ${CRAFT_WORDS[craftOf()]}` : CRAFT_WORDS[craft]} · ${team.map((id) => library.find((a) => a.id === id)?.name).filter(Boolean).join(", ")}</p>
      <label class="shell-field"><span class="ok-font-label">Description</span>
        <textarea class="ork-field" rows="5" autofocus value=${about} aria-label="Description" placeholder="A few lines: what you want to reach, and why"
          onInput=${(e) => setAbout(e.target.value)}></textarea></label>
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say("The Taskmaster reads the repository and writes the title, the summary, the metrics and the links.")}</p>
    </form>`;
    foot = html`<button type="button" class="ork-btn" onClick=${() => setStep(2)}>Back</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!about.trim() || saving}>Save goal</button>`;
  }
  return html`<${Modal} title="New goal" onClose=${closeDialog} wide=${true} foot=${foot}>${steps}${body}<//>`;
}
