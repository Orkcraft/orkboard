// New party (docs/specs/50-parties-and-goals.md §3.7), one screen: its name, *What it is for* (one line), the party — *one of yours, or from the library*: the
// leader, builders and checkers in three bands of seats (ideas.roles `seats`, `parties`, realm/library.py), a click takes an agent in or out of its band,
// with what the party costs a goal (spec 43 §3) —, the checks on every goal and its priority (*goes first when the window is short*). No metrics, no deadline,
// no links: a party has no end. It sends `ideas.goal_save` with `title`, `about`, `team`, `every`, `leader`, `party` (a party of the person's that was picked), `preset` (the library's party the seats still are) and
// `priority`. A task goes to the one of the party who does its kind of work; a checker's check adds its line to a goal's Done when and its task to the plan
// (realm/idea_checks.py). The code's goal is a party. At the press of *Save party* the boxes of the seats' heads are kept: once the party is saved and shown, the heads gather into its deck
// (docs/specs/63-party-gathered.md §3, arena/goaltabs.js).
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { track } from "../board/store.js";
import { act, mapData, roles, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { PRIORITIES } from "./goaldialog.js";
import { ReleasesFrom, useReleasesFrom } from "./release.js";
import { gatherWaits } from "../arena/arenastate.js";
import { reducedMotion } from "../arena/motion.js";
import { TASKMASTER, raceOfAgent, PartyBands, PriceLine, CanTake, ChecksBlock, OwnParties, LibraryTiles, agentOf, inBand, partyWords, overfull, pitchParty, presetsOf, usePartyPrice, useOwnParties } from "./party.js";

export const FOR_HINT = "goes first when the window is short";

const boxOf = (r) => ({ left: r.left, top: r.top, width: r.width, height: r.height });
/** The heads of the seats as the dialog draws them now (spec 63 §3.1): [{race, tier, box}], the leader's first, then the builders', then the checkers' (six at most). A head whose seat is not on
 *  screen (scrolled out of the dialog) starts from *Save party*'s box: its own size, at that box's centre. */
function seatHeads(leader, team) {
  const heads = [leader, ...inBand("build", leader, team), ...inBand("check", leader, team)].map(agentOf).filter(Boolean).slice(0, 6);
  const seats = [...document.querySelectorAll("#goal-form .shell-team-seat .ork-race__head")].map((x) => x.getBoundingClientRect());
  const view = document.querySelector(".shell-modal__body")?.getBoundingClientRect(), save = document.querySelector(".shell-modal__foot button[type=submit]")?.getBoundingClientRect();
  const seen = (r) => !view || (r.bottom > Math.max(view.top, 0) && r.top < Math.min(view.bottom, innerHeight) && r.right > view.left && r.left < view.right);
  const atSave = (r) => (save ? { left: save.left + (save.width - r.width) / 2, top: save.top + (save.height - r.height) / 2, width: r.width, height: r.height } : r);
  return heads.map((a, i) => seats[i] && { race: raceOfAgent(a), tier: a.tier, box: boxOf(seen(seats[i]) ? seats[i] : atSave(seats[i])) }).filter(Boolean);
}

export function GoalWizard({ then = "", preset: first = "" }) {
  const from = first ? presetsOf().find((p) => p.id === first) : null;    // opened with a party of the library (a pitch sent to one the project lacks, spec 65 §5)
  const start = from ? { lead: from.lead, build: from.build, check: from.check } : roles.value?.parties?.engineering || { lead: TASKMASTER, build: [], check: [] };
  const [title, setTitle] = useState(from?.name || "");
  const [about, setAbout] = useState("");
  const [priority, setPriority] = useState("normal");
  const [craft, setCraft] = useState(from ? (from.craft === "mixed" ? "" : from.craft) : "engineering");     // the library's party's craft the seats started from: its agents are listed first in each band
  const [preset, setPreset] = useState(from?.id || "");       // the library's party picked (its id), sent with the party until a seat changes; none for the party it opens with
  const [lit, setLit] = useState(from?.id || "engineering");   // the tile pressed: the party it opens with, then the one picked
  const [leader, setLeader] = useState(start.lead || TASKMASTER);
  const [team, setTeam] = useState([...(start.build || []), ...(start.check || [])]);
  const [every, setEvery] = useState([]);
  const [saving, setSaving] = useState(false);
  const [partyId, setPartyId] = useState("");              // the saved party of the person's whose seats these are, until a seat changes
  const [owns, loadOwns] = useOwnParties(true);
  const seat = (set) => (v) => { set(v); setPartyId(""); setPreset(""); setLit(""); };      // a seat changed afterwards: the party is then the person's own picking
  const pickOwn = (p) => {
    if (p.craft) setCraft(p.craft);
    setLeader(p.leader || TASKMASTER);
    setTeam([...p.team]);
    setEvery([...p.every]);
    setPartyId(p.id);
    setPreset("");
    setLit("");
  };
  const fromLibrary = (p) => { setCraft(p.craft === "mixed" ? "" : p.craft); setPreset(p.id); setLit(p.id); setPartyId(""); setLeader(p.lead || TASKMASTER); setTeam([...(p.build || []), ...(p.check || [])]); setEvery([]); };
  const rf = useReleasesFrom({ leads: leader === "release-manager" });             // the Release party takes its goals from the others (spec 68 §7.6): every party but Ideation, ticked
  const price = usePartyPrice(true, leader, team, every, craft);
  const fits = overfull(leader, team).length === 0;      // a leader with fewer seats than the party fills: it is saved once it fits (spec 59 §6.2)
  const ready = (title.trim() || about.trim()) && !saving && fits;
  const save = async (e) => {
    e?.preventDefault();
    if (!ready) return;
    const heads = then === "idea" || reducedMotion() || document.hidden ? [] : seatHeads(leader, team);       // the heads' boxes at the press: the dialog is gone when they travel
    setSaving(true);
    const got = await act("ideas.goal_save", { ...(title.trim() ? { title: title.trim() } : {}), about: about.trim(), leader, team, every: every.filter((id) => team.includes(id)), priority,
      ...(partyId ? { party: partyId } : {}), ...(preset && !partyId ? { preset } : {}), ...(rf.value() ? { releases_from: rf.value() } : {}) });
    setSaving(false);
    if (!got?.slug) return;
    for (const note of got.notes || []) toast(note);       // an agent of the project's own that the party carries stays as it was
    if (heads.length) gatherWaits(got.slug, heads);        // the heads gather into the party's deck once it is shown (arena/goaltabs.js)
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };
  return html`<${Modal} title="New party" onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!ready}>Save party</button>`}>
    <form id="goal-form" class="shell-form" onSubmit=${save}>
      <label class="shell-field"><span class="ok-font-label">Name</span>
        <input class="ork-field" autofocus value=${title} aria-label="Name" placeholder="Its name, in a few words" maxlength="120" onInput=${(e) => setTitle(e.target.value)} /></label>
      <label class="shell-field"><span class="ok-font-label">What it is for</span>
        <input class="ork-field" value=${about} aria-label="What it is for" placeholder="One line: what this party is for" onInput=${(e) => setAbout(e.target.value)} /></label>
      <div class="shell-field" role="group" aria-label="The party"><span class="ok-font-label">The party</span>
        <p class="ok-tone-muted">One of yours, or from the library: its leader plans, its builders work, its checkers check. A task goes to the one who does its kind of work; Grunt fills in.</p>
        <${LibraryTiles} picked=${partyId ? "" : lit} onPick=${fromLibrary} deal=${mapData.value?.project?.deal} />
        <${OwnParties} parties=${owns} onPick=${pickOwn} reload=${loadOwns} picked=${partyId} />
        <${PartyBands} craft=${craft} leader=${leader} setLeader=${seat(setLeader)} team=${team} setTeam=${seat(setTeam)} />
        <${PriceLine} price=${price} />
        <${CanTake} price=${price} />
        <p class="ok-tone-muted shell-party-line">${partyWords(leader, team)}</p></div>
      <${ReleasesFrom} rf=${rf} />
      ${!pitchParty(leader) && html`<${ChecksBlock} team=${team} every=${every} setEvery=${seat(setEvery)} price=${price} />`}
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span><small class="ok-tone-muted">${FOR_HINT}</small>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say(`${agentOf(leader)?.name || "The Taskmaster"} reads the repository and writes the summary.`)}</p>
    </form>
  <//>`;
}
