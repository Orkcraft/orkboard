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
import { Head, Icon, CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "../orkui.js";

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

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
/** *3 goals in 2 projects · 2 met*: said only once a party has been used. */
export function usedWords(p) {
  return p.goals ? `${plural(p.goals, "goal", "goals")} in ${plural(p.projects, "project", "projects")} · ${p.met} met` : "";
}

/** The person's own parties (spec 43 §6): asked when the picker opens (`active`); [parties, ask again]. */
export function useOwnParties(active) {
  const [parties, setParties] = useState([]);
  const load = () => command("ideas.parties", {}).then((got) => { if (got && !got.error) setParties(got.parties || []); }).catch(() => {});
  useEffect(() => { if (active) load(); }, [active]);
  return [parties, load];
}

/** **Your parties**, above the bands when there is one: each a chip with its members' small heads, its name and, muted, where it was used; a tap
 *  fills the seats (`onPick`), its `close` mark removes it after asking. */
export function OwnParties({ parties, onPick, reload, picked = "" }) {
  const [asking, setAsking] = useState("");
  if (!parties.length) return null;
  const drop = async (p) => {
    const got = await command("ideas.party_drop", { id: p.id }).catch(() => null);
    if (got?.error) toast(got.error, "error");
    setAsking("");
    reload();
  };
  return html`<section class="shell-own-parties" aria-label="Your parties"><h3 class="ok-font-label">Your parties</h3>
    <div class="shell-own-chips">${parties.map((p) => html`<div key=${p.id} class=${`shell-own-chip${picked === p.id ? " is-on" : ""}`} data-party=${p.id}>
      <button type="button" class="shell-own-chip__pick" aria-pressed=${String(picked === p.id)} aria-label=${`Pick your party “${p.name}”`} onClick=${() => onPick(p)}>
        <span class="shell-own-heads">${[p.leader, ...p.team].map((id, n) => agentOf(id) && html`<${Head} key=${n} race=${RACE[agentOf(id).craft]} tier=${agentOf(id).tier} small=${true} />`)}</span>
        <b>${p.name}</b>${usedWords(p) && html`<small class="ok-tone-muted">${usedWords(p)}</small>`}</button>
      <button type="button" class="shell-own-chip__close" aria-label=${`Remove your party “${p.name}”`} onClick=${() => setAsking(p.id)}><${Icon} name="close" /></button>
      ${asking === p.id && html`<p class="shell-own-ask" role="alert">Remove your party “${p.name}”? Goals that use it keep their agents.
        <button type="button" class="ork-btn danger" onClick=${() => drop(p)}>Remove it</button>
        <button type="button" class="ork-btn" onClick=${() => setAsking("")}>Keep it</button></p>`}</div>`)}</div></section>`;
}

/** On a goal's screen, under its Team: **Save this party**. It asks a name (*Engineering party*), asks again before it replaces a party of that
 *  name, and says after: *Saved: pick it for a goal in any project.* */
export function SaveParty({ goal, craft }) {
  const [name, setName] = useState(null);                       // null: the button; a string: the name being typed
  const [replace, setReplace] = useState("");                   // the name of the party the save would replace
  const [busy, setBusy] = useState(false);
  const send = async (replacing) => {
    setBusy(true);
    const got = await command("ideas.party_save", { goal, name: name.trim(), ...(replacing ? { replace: true } : {}) }).catch((e) => ({ error: String(e) }));
    setBusy(false);
    if (got?.error) {
      const taken = /^You have a party named “(.+)”$/.exec(got.error);
      if (taken && !replacing) { setReplace(taken[1]); return; }
      toast(got.error, "error");
      return;
    }
    toast("Saved: pick it for a goal in any project.");
    setName(null);
    setReplace("");
  };
  if (name === null) {
    return html`<button type="button" class="board-link shell-party-save" onClick=${() => setName(`${CRAFT_WORDS[craft] || "Engineering"} party`)}>Save this party</button>`;
  }
  if (replace) {
    return html`<p class="shell-party-save-ask" role="alert">Replace your party “${replace}”?
      <button type="button" class="ork-btn primary" disabled=${busy} onClick=${() => send(true)}>Replace it</button>
      <button type="button" class="ork-btn" onClick=${() => setReplace("")}>Cancel</button></p>`;
  }
  return html`<form class="shell-party-save-form" onSubmit=${(e) => { e.preventDefault(); if (name.trim() && !busy) send(false); }}>
    <input class="ork-field" autofocus value=${name} aria-label="Name of your party" maxlength="40" onInput=${(e) => setName(e.target.value)} />
    <button class="ork-btn primary" disabled=${!name.trim() || busy}>Save</button>
    <button type="button" class="ork-btn" onClick=${() => setName(null)}>Cancel</button></form>`;
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
export function usePartyPrice(active, leader, team, every, craft = "") {
  const [price, setPrice] = useState(null);
  const asked = useRef(false);
  const key = JSON.stringify([leader, team, every.filter((id) => team.includes(id)), craft]);
  useEffect(() => {
    if (!active) { asked.current = false; return undefined; }
    let live = true;
    const run = () => command("ideas.party_price", { leader, team, every: every.filter((id) => team.includes(id)), ...(craft ? { craft } : {}) })
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

/** Under the bands: *This party: about $2–6 an idea* and, muted, where it comes from; under it the hints (spec 43 §5), muted, one line each:
 *  they never block Save and have no button. */
export function PriceLine({ price }) {
  if (!price) return null;
  return html`<p class="shell-price" role="status">This party: ${rangeWords(price)} an idea
    <small class="ok-tone-muted"> ${price.learned ? `from this project's last ${price.ideas} ideas` : "a first guess: it learns from this project's ideas"}</small></p>
    ${(price.hints || []).map((h, n) => html`<p key=${n} class="shell-hint ok-font-status ok-tone-muted">${h}</p>`)}`;
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
