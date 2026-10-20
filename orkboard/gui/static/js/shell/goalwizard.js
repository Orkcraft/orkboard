// New goal on the desktop on one sheet, as the phone's (pwa/shell-goal-new.js; docs/specs/41-phone-round-3.md §6, spec 46 §6.2), top to
// bottom: what it is for — the description (focused) and the priority —, its craft — one row of six heads, the five crafts and Mixed, the
// picked one's word and line under it (decisions §53); a pick sets the team to the craft's party —, its team folded to one line (Leads ·
// Builds · Checks) with Change (three folds, one open at a time, each closed by Done: party.js `PartyBands` with `setOpen`), its checks
// folded to one line, and Save goal in the foot, enabled once the description has words. *Engineering* is picked at the start (spec 41
// §12). A task goes to the one of the party who does its kind of work; a checker's check adds its line to the spec's Done when and its
// task to the plan (realm/idea_checks.py). Above the team, Your parties (party.js): a tap fills the craft and the seats and keeps the
// party's id for the save. The command is `ideas.goal_save` with `craft`, `team`, `every`, `leader`. Edit goal is goaldialog.js.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { track } from "../board/store.js";
import { act, roles, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { Head, CRAFT_WORDS } from "../orkui.js";
import { PRIORITIES } from "./goaldialog.js";
import { CRAFTS, TASKMASTER, PartyBands, ChecksFold, PriceLine, OwnParties, agentOf, teamLine, usePartyPrice, useOwnParties } from "./party.js";

const MIXED = "mixed";
const START = "engineering";
const lcfirst = (t) => t.charAt(0).toLowerCase() + t.slice(1);

export function GoalWizard({ then = "" }) {
  const partyOf = (c) => roles.value?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
  const first = partyOf(START);
  const [craft, setCraft] = useState(START);
  const [leader, setLeader] = useState(first.lead || TASKMASTER);
  const [team, setTeam] = useState(() => [...first.build, ...first.check]);   // the builders and checkers
  const [every, setEvery] = useState([]);
  const [about, setAbout] = useState("");
  const [priority, setPriority] = useState("normal");
  const [saving, setSaving] = useState(false);
  const [party, setParty] = useState("");                // the id of the person's own party the seats were filled from; a seat changed drops it
  const [changing, setChanging] = useState(false);       // the Team fold is opened
  const [fold, setFold] = useState("");                  // the band open in it: "lead" | "build" | "check" | ""
  const touched = useRef(false);                         // the person changed the craft or a seat: the library arriving later does not reset them
  const [mine, reload] = useOwnParties(true);
  const seats = (set) => (v) => { touched.current = true; setParty(""); set(v); };

  useEffect(() => {                                      // the library not read yet when the sheet opened: the first craft's party fills the seats when it comes
    if (touched.current || !roles.value?.parties) return;
    const p = partyOf(craft);
    setLeader(p.lead || TASKMASTER);
    setTeam([...p.build, ...p.check]);
  }, [roles.value]);

  const takeParty = (p) => {                             // Your parties: its craft, its seats and its id
    touched.current = true;
    setCraft(p.craft);
    setLeader(p.leader || TASKMASTER);
    setTeam([...p.team]);
    setEvery([...p.every]);
    setParty(p.id);
    setChanging(false);
    setFold("");
  };
  const pick = (c) => {
    touched.current = true;
    if (c === craft) return;
    const p = partyOf(c);
    setParty("");
    setCraft(c);
    setLeader(p.lead || TASKMASTER);
    setTeam([...p.build, ...p.check]);
    setEvery([]);
    setChanging(false);
    setFold("");
  };
  const craftOf = () => {
    if (craft !== MIXED) return craft;
    const crafts = [leader, ...team].filter((id) => id !== TASKMASTER).map((id) => agentOf(id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  };
  const price = usePartyPrice(true, leader, team, every, craftOf());   // what an idea costs with this party and its hints (spec 43 C, E)
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const got = await act("ideas.goal_save", { about: about.trim(), craft: craftOf(), leader, team, every: every.filter((id) => team.includes(id)), priority, ...(party ? { party } : {}) });
    setSaving(false);
    if (!got?.slug) return;
    (got.notes || []).forEach((n) => toast(n));          // an agent of the party's the project has already: kept as it is
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };
  const folding = (v) => { setFold(v); if (!v) setChanging(false); };
  const line = craft === MIXED ? "A party of any crafts: the Taskmaster leads, you pick the rest" : CRAFTS.find((x) => x[0] === craft)?.[2] || "";
  const lead = agentOf(leader);

  const foot = html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
    <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!about.trim() || saving}>Save goal</button>`;
  return html`<${Modal} title="New goal" onClose=${closeDialog} wide=${true} foot=${foot}>
    <form id="goal-form" class="shell-form" onSubmit=${save}>
      <section class="shell-newgoal__for" aria-label="What for">
        <label class="shell-field"><span class="ok-font-label">What for</span>
          <textarea class="ork-field" rows="4" autofocus value=${about} aria-label="Description" placeholder="A few lines: what you want to reach, and why"
            onInput=${(e) => setAbout(e.target.value)}></textarea></label>
        <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span>
          <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
            <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      </section>
      <section class="shell-newgoal__craft" aria-label="Craft"><h3 class="shell-fold-title">Craft</h3>
        <div class="shell-craft-row" role="group" aria-label="Craft">${CRAFTS.map(([c, race]) => html`<button type="button" key=${c} class="shell-craft-tile" data-craft=${c}
            aria-label=${CRAFT_WORDS[c]} title=${CRAFT_WORDS[c]} aria-pressed=${String(c === craft)} onClick=${() => pick(c)}><${Head} race=${race} /></button>`)}
          <button type="button" class="shell-craft-tile mixed" data-craft=${MIXED} aria-label="Mixed" title="Mixed" aria-pressed=${String(craft === MIXED)} onClick=${() => pick(MIXED)}>
            <span class="shell-craft-heads">${CRAFTS.slice(0, 2).map(([c, race]) => html`<${Head} key=${c} race=${race} small=${true} />`)}</span></button></div>
        <p class="ok-tone-muted shell-craft-line" aria-live="polite"><b>${craft === MIXED ? "Mixed" : CRAFT_WORDS[craft]}</b>: ${craft === MIXED ? line : lcfirst(line)}</p>
      </section>
      <${OwnParties} parties=${mine} picked=${party} onPick=${takeParty} reload=${reload} />
      ${changing ? html`<section class="shell-newgoal__team" aria-label="Team"><h3 class="shell-fold-title">Team</h3>
          <${PartyBands} craft=${craft} leader=${leader} setLeader=${seats(setLeader)} team=${team} setTeam=${seats(setTeam)} open=${fold} setOpen=${folding} /></section>`
        : html`<section class="shell-newgoal__team" aria-label="Team"><h3 class="shell-fold-title">Team</h3>
          <p class="shell-party-line">${teamLine(leader, team)}</p>
          <button type="button" class="ork-btn" data-change="team" onClick=${() => { setChanging(true); setFold("lead"); }}>Change</button></section>`}
      <${PriceLine} price=${price} />
      <${ChecksFold} team=${team} every=${every} setEvery=${seats(setEvery)} price=${price} />
      <p class="ok-font-status ok-tone-muted">${say(`${lead?.name || "The Taskmaster"} reads the repository and writes the title, the summary, the metrics and the links.`)}</p>
    </form>
  <//>`;
}
