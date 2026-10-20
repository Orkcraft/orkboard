// A goal's party on the desktop (decisions §53; realm/goal_team.py), as New goal (goalwizard.js) and Edit goal (goaldialog.js)
// pick it: three bands of seats from the library (ideas.roles `library`, `seats`) — Leads (one: the goal's steps run as it, and
// it accepts the goal; the Taskmaster when none), Builds (three at most), Checks (two at most) —; a click takes an agent in or out of
// its band, a full band says so. Under them what the party costs (`ideas.party_price`: about what an idea costs, asked when the picker
// opens and 300 ms after a seat or *Every idea* changes), then the checkers' checks: where each applies or on every idea, and what each
// adds to an idea.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { command, toast } from "../link.js";
import { roles } from "./store.js";
import { Head, Icon, RACE_WORDS, TIER_WORDS } from "../orkui.js";

export const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"],
  ["product", "lich", "Who it is for, what it moves, what it leaves out"]];
export const RACE = Object.fromEntries(CRAFTS);
const BANDS = [["lead", "Leads", "plans the goal's ideas and accepts the goal"], ["build", "Builds", "do the work"],
  ["check", "Checks", "hold each idea to their check"]];
export const TASKMASTER = "taskmaster";

const library = () => roles.value?.library || [];
const seatsOf = () => roles.value?.seats || { lead: 1, build: 3, check: 2 };
export const agentOf = (id) => library().find((a) => a.id === id);
/** The agents in a band: the leader alone in Leads; the team's builders or checkers. */
export const inBand = (band, leader, team) => (band === "lead" ? [leader] : team.filter((id) => agentOf(id)?.band === band));
/** The party in words: "led by Growth · builds: Copywriter, SEO · checks: Editor". */
export function partyWords(leader, team) {
  const names = (b) => inBand(b, leader, team).map((id) => agentOf(id)?.name).filter(Boolean).join(", ") || "none";
  return `led by ${agentOf(leader)?.name || "Taskmaster"} · builds: ${names("build")} · checks: ${names("check")}`;
}

/** The three bands. `craft`: the goal's, its agents listed first in each band. */
export function PartyBands({ craft = "", leader, setLeader, team, setTeam }) {
  const seats = seatsOf();
  const on = (a) => (a.band === "lead" ? leader === a.id : team.includes(a.id));
  const toggle = (a) => {
    if (a.band === "lead") { setLeader(leader === a.id ? TASKMASTER : a.id); return; }
    if (team.includes(a.id)) setTeam(team.filter((x) => x !== a.id));
    else if (inBand(a.band, leader, team).length < seats[a.band]) setTeam([...team, a.id]);
    else toast(`${BANDS.find((b) => b[0] === a.band)[1]} has ${seats[a.band]} seats: take one out first.`, "warning");
  };
  const row = (a) => html`<button type="button" key=${a.id} class="shell-team-row" aria-pressed=${String(on(a))} data-agent=${a.id}
      aria-label=${`${on(a) ? "Take out" : "Take in"}: ${a.name}`} onClick=${() => toggle(a)}>
    <${Head} race=${RACE[a.craft]} tier=${a.tier} /><b>${a.name}${a.check && html`<span class="shell-check-badge">checks</span>`}</b>
    <small class="ok-tone-muted">${TIER_WORDS[a.tier]} ${RACE_WORDS[RACE[a.craft]]} · ${a.line}</small>
    <span class="shell-team-mark" aria-hidden="true"><${Icon} name=${on(a) ? "check" : "plus"} /></span></button>`;
  return BANDS.map(([id, words, what]) => {
    const taken = inBand(id, leader, team);
    const list = library().filter((a) => a.band === id).sort((x, y) => (x.craft === craft ? 0 : 1) - (y.craft === craft ? 0 : 1));
    return html`<section key=${id} class=${`shell-party-band band-${id}`} aria-label=${words}>
      <div class="shell-band-head"><h3>${words}</h3><small class="ok-tone-muted">${taken.length} of ${seats[id]} · ${what}</small></div>
      <div class="shell-team-seats">${Array.from({ length: seats[id] }, (_, i) => {
        const a = agentOf(taken[i]);
        return html`<span key=${i} class=${`shell-team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}`} title=${a?.name || "A free seat"}>${a && html`<${Head} race=${RACE[a.craft]} tier=${a.tier} />`}</span>`;
      })}</div>
      <div class="shell-team-list">${list.map(row)}</div></section>`;
  });
}

const PRICE_MS = 300;
/** What the party costs (spec 43 §3): `ideas.party_price` once the picker is open (`active`), again 300 ms after a seat or *Every idea* changes. null until answered. */
export function usePartyPrice(active, leader, team, every) {
  const [price, setPrice] = useState(null);
  const asked = useRef(false);
  const key = JSON.stringify([leader, team, every.filter((id) => team.includes(id))]);
  useEffect(() => {
    if (!active) { asked.current = false; return undefined; }
    let live = true;
    const run = () => command("ideas.party_price", { leader, team, every: every.filter((id) => team.includes(id)) })
      .then((got) => { if (live && got && !got.error) setPrice(got); }).catch(() => {});
    const first = !asked.current;
    asked.current = true;
    const timer = first ? 0 : setTimeout(run, PRICE_MS);
    if (first) run();
    return () => { live = false; clearTimeout(timer); };
  }, [active, key]);
  return price;
}

/** *about $2–6 an idea*; below $1 (its low end) in cents, *about $0.40–1.20*. */
export function rangeWords(price) {
  const { low, high } = price;
  if (low < 1) return `about $${low.toFixed(2)}–${high.toFixed(2)}`;
  const a = Math.round(low), b = Math.round(high);
  return a === b ? `about $${a}` : `about $${a}–${b}`;
}

/** Under the bands: *This party: about $2–6 an idea* and, muted, where it comes from. */
export function PriceLine({ price }) {
  if (!price) return null;
  return html`<p class="shell-price" role="status">This party: ${rangeWords(price)} an idea
    <small class="ok-tone-muted"> ${price.learned ? `from this project's last ${price.ideas} ideas` : "a first guess: it learns from this project's ideas"}</small></p>`;
}

/** *adds about $0.35 to an idea it checks · about half of them* (*· every idea* when it checks every idea). */
export function addsWords(c) {
  const share = c.every ? "every idea" : Math.abs(c.share - 0.5) < 0.03 ? "about half of them" : `about ${Math.round(c.share * 100)} % of them`;
  return `adds about $${c.usd.toFixed(2)} to an idea it checks · ${share}`;
}

/** The party's checks: each checker's, where it applies or on every idea, and what a check adds to an idea (`price`: `ideas.party_price`). */
export function ChecksBlock({ team, every, setEvery, price = null }) {
  const checkers = team.map(agentOf).filter((a) => a?.check);
  if (!checkers.length) return html`<p class="ok-tone-muted">No checker in the party: an idea is done when its own Done when lines are.</p>`;
  const adds = (a) => { const c = (price?.checks || []).find((x) => x.by === a.id); return c ? ` · ${addsWords(c)}` : ""; };
  return html`<div class="shell-checks" role="group" aria-label="Checks"><span class="ok-font-label">Checks</span>
    <p class="ok-tone-muted">How deep each idea is worked: every check adds a line to its Done when and a task to its plan.</p>
    ${checkers.map((a) => html`<div key=${a.id} class="shell-check-row"><${Head} race=${RACE[a.craft]} tier=${a.tier} small=${true} />
      <span><b>${a.name}</b> <small class="ok-tone-muted">${a.check.done} · applies ${a.check.applies}${adds(a)}</small></span>
      <label class="shell-check-every"><input type="checkbox" aria-label=${`Every idea: ${a.name}`} checked=${every.includes(a.id)}
        onChange=${(e) => setEvery(e.target.checked ? [...every, a.id] : every.filter((x) => x !== a.id))} /> Every idea</label></div>`)}</div>`;
}
