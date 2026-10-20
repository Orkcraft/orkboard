// A goal's party on the desktop (decisions §53; realm/goal_team.py), as New goal (goalwizard.js) and Edit goal (goaldialog.js)
// pick it: three bands of seats from the library (ideas.roles `library`, `seats`) — Leads (one: the goal's steps run as it, and
// it accepts the goal; the Taskmaster when none), Builds (three at most), Checks (two at most) —; a click takes an agent in or out of
// its band, a full band says so. Under the bands, about what an idea costs with the party (ideas.party_price: spec 43 C, asked when
// the picker opens and 300 ms after a seat or Every idea changes), and its hints (spec 43 E: at most two plain lines). Then the checkers' checks: where each applies or on every idea,
// and what a check adds to an idea. Above the bands, Your parties (spec 43 F): the parties the person saved from a goal, each a chip
// that fills the seats, with a mark to remove it; on a goal's screen, Save this party (`SaveParty`).
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { toast } from "../link.js";
import { ask } from "../board/store.js";
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
/** The agents in a band: the leader alone in Leads; the team's builders or checkers (an agent of the person's own, not the library's, builds). */
export const inBand = (band, leader, team) => (band === "lead" ? [leader] : team.filter((id) => (agentOf(id)?.band || "build") === band));
/** An agent's name: the library's, else the project's own role's, else its slug said as a name (a party's agent this project has not yet). */
const nameOf = (id) => agentOf(id)?.name || (roles.value?.roles || []).find((r) => r.slug === id)?.name || id.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());
/** An agent of the person's own in the team: the library does not know it; drawn as a builder's row. */
const ownAgent = (id) => {
  const r = (roles.value?.roles || []).find((x) => x.slug === id);
  return { id, name: nameOf(id), band: "build", craft: r?.craft || r?.head?.craft || "engineering", tier: r?.head?.tier || "laborer", line: "one of your own agents" };
};
/** The party in words: "led by Growth · builds: Copywriter, SEO · checks: Editor". */
export function partyWords(leader, team) {
  const names = (b) => inBand(b, leader, team).map(nameOf).join(", ") || "none";
  return `led by ${nameOf(leader)} · builds: ${names("build")} · checks: ${names("check")}`;
}

export const PRICE_MS = 300;
/** About what an idea costs with the party (spec 43 §3): asked when the picker opens (`on`), then 300 ms after a change. */
export function usePartyPrice(on, leader, team, every, craft = "") {
  const [price, setPrice] = useState(null);
  const asked = useRef(false);
  const mine = every.filter((id) => team.includes(id));
  const key = JSON.stringify([leader, team, mine, craft]);
  useEffect(() => {
    if (!on) { asked.current = false; return undefined; }
    let live = true, timer = 0;
    const run = () => ask("ideas.party_price", { leader, team, every: mine, craft }).then((got) => { if (live && got && !got.error) setPrice(got); });
    if (asked.current) timer = setTimeout(run, PRICE_MS);
    else { asked.current = true; run(); }
    return () => { live = false; clearTimeout(timer); };
  }, [on, key]);
  return price;
}
/** *This party: about $2–6 an idea* (below $1: *about $0.40–1.20*). */
export function priceWords(p) {
  const f = (n) => (p.low < 1 ? Number(n).toFixed(2) : String(Math.round(n)));
  return `This party: about $${f(p.low)}–${f(p.high)} an idea`;
}
const shareWords = (share) => (share === 0.5 ? "about half of them" : share <= 0 ? "none of them so far" : `about ${Math.round(share * 100)}% of them`);
/** What a check adds, as its line ends: *adds about $0.35 to an idea it checks · about half of them* (*· every idea*). */
export function addsWords(c) {
  return `adds about $${Number(c.usd).toFixed(2)} to an idea it checks · ${c.every ? "every idea" : shareWords(c.share)}`;
}
/** The price in one line under the bands, and after it, muted, where it comes from; under it the party's hints (spec 43 E), muted,
 *  one line each. A hint never blocks Save and has no button. */
export function PriceLine({ price }) {
  if (!price) return null;
  return html`<p class="shell-party-price" aria-live="polite"><b>${priceWords(price)}</b> <small class="ok-tone-muted">${price.learned
    ? `from this project's last ${price.ideas} ideas` : "a first guess: it learns from this project's ideas"}</small></p>
    ${(price.hints || []).map((t) => html`<p key=${t} class="shell-party-hint ok-tone-muted">${t}</p>`)}`;
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
    const list = [...library().filter((a) => a.band === id), ...(id === "build" ? team.filter((x) => !agentOf(x)).map(ownAgent) : [])]
      .sort((x, y) => (x.craft === craft ? 0 : 1) - (y.craft === craft ? 0 : 1));
    return html`<section key=${id} class=${`shell-party-band band-${id}`} aria-label=${words}>
      <div class="shell-band-head"><h3>${words}</h3><small class="ok-tone-muted">${taken.length} of ${seats[id]} · ${what}</small></div>
      <div class="shell-team-seats">${Array.from({ length: seats[id] }, (_, i) => {
        const a = agentOf(taken[i]) || (taken[i] ? ownAgent(taken[i]) : null);
        return html`<span key=${i} class=${`shell-team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}`} title=${a?.name || "A free seat"}>${a && html`<${Head} race=${RACE[a.craft]} tier=${a.tier} />`}</span>`;
      })}</div>
      <div class="shell-team-list">${list.map(row)}</div></section>`;
  });
}

/** The party's checks: each checker's, where it applies or on every idea, and what a check adds to an idea, in dollars (`price`:
 *  ideas.party_price). */
export function ChecksBlock({ team, every, setEvery, price = null }) {
  const checkers = team.map(agentOf).filter((a) => a?.check);
  if (!checkers.length) return html`<p class="ok-tone-muted">No checker in the party: an idea is done when its own Done when lines are.</p>`;
  const adds = (a) => { const c = price?.checks?.find((x) => x.by === a.id); return c ? ` · ${addsWords(c)}` : ""; };
  return html`<div class="shell-checks" role="group" aria-label="Checks"><span class="ok-font-label">Checks</span>
    <p class="ok-tone-muted">How deep each idea is worked: every check adds a line to its Done when and a task to its plan.</p>
    ${checkers.map((a) => html`<div key=${a.id} class="shell-check-row"><${Head} race=${RACE[a.craft]} tier=${a.tier} small=${true} />
      <span><b>${a.name}</b> <small class="ok-tone-muted">${a.check.done} · applies ${a.check.applies}${adds(a)}</small></span>
      <label class="shell-check-every"><input type="checkbox" aria-label=${`Every idea: ${a.name}`} checked=${every.includes(a.id)}
        onChange=${(e) => setEvery(e.target.checked ? [...every, a.id] : every.filter((x) => x !== a.id))} /> Every idea</label></div>`)}</div>`;
}

/** The person's parties (ideas.parties), read when `on` (the picker is shown); `reload()` reads them again. */
export function useOwnParties(on) {
  const [parties, setParties] = useState([]);
  const load = () => ask("ideas.parties", {}).then((got) => { if (got) setParties(got.parties || []); });
  useEffect(() => { if (on) load(); }, [on]);
  return [parties, load];
}
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
/** *3 goals in 2 projects · 2 met*; nothing for a party not used yet. */
export const recordWords = (p) => (p.goals ? `${plural(p.goals, "goal", "goals")} in ${plural(p.projects, "project", "projects")}${p.met ? ` · ${p.met} met` : ""}` : "");

/** *Your parties*, above the bands (spec 43 §6.3): each a chip with its members' small heads, its name and its record; a tap fills the seats
 *  (`onPick(party)`), the mark removes it after asking. Nothing when the person has none. */
export function OwnParties({ parties, picked = "", onPick, reload }) {
  if (!parties.length) return null;
  const headOf = (id, p) => { const a = agentOf(id); return { race: RACE[a?.craft || p.craft], tier: a?.tier || "laborer" }; };
  const remove = async (p) => {
    if (!confirm(`Remove your party “${p.name}”? Goals that use it keep their agents.`)) return;
    if (await ask("ideas.party_drop", { id: p.id })) reload();
  };
  return html`<section class="shell-own" aria-label="Your parties"><h3 class="shell-own__title">Your parties</h3>
    <div class="shell-own__list">${parties.map((p) => html`<div key=${p.id} class="shell-own__chip" data-party=${p.id}>
      <button type="button" class="shell-own__pick" aria-pressed=${String(p.id === picked)} aria-label=${`Pick your party “${p.name}”`} onClick=${() => onPick(p)}>
        <span class="shell-own__heads">${[p.leader, ...p.team].filter((id) => id !== TASKMASTER).map((id) => html`<${Head} key=${id} ...${headOf(id, p)} small=${true} />`)}</span>
        <b>${p.name}</b>${recordWords(p) && html` <small class="ok-tone-muted">${recordWords(p)}</small>`}</button>
      <button type="button" class="ork-btn quiet shell-own__x" aria-label=${`Remove your party “${p.name}”`} onClick=${() => remove(p)}><${Icon} name="close" /></button></div>`)}</div></section>`;
}

/** *Save this party*, quiet, under a goal's Team (spec 43 §6.3): asks a name (filled with *Engineering party*), saves the goal's party among the
 *  person's, and says where to pick it. A taken name asks *Replace your party “…”?* first. */
export function SaveParty({ goal }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const show = () => { setName(`${CRAFT_WORDS[goal.craft] || "Your"} party`); setOpen(true); };
  const save = async (e) => {
    e.preventDefault();
    const typed = name.trim().replace(/\s+/g, " ");
    if (!typed || busy) return;
    setBusy(true);
    const mine = (await ask("ideas.parties", {}))?.parties || [];
    const taken = mine.find((p) => p.name.toLowerCase() === typed.toLowerCase());
    const go = !taken || confirm(`Replace your party “${taken.name}”?`);
    const got = go ? await ask("ideas.party_save", { goal: goal.slug, name: typed, ...(taken ? { replace: true } : {}) }) : null;
    setBusy(false);
    if (!got) return;
    setOpen(false);
    toast("Saved: pick it for a goal in any project.");
  };
  if (!open) return html`<button type="button" class="ork-btn quiet shell-party-save" onClick=${show}>Save this party</button>`;
  return html`<form class="shell-party-save-form" aria-label="Save this party" onSubmit=${save}>
    <input class="ork-field" aria-label="Name of your party" value=${name} maxlength="40" autofocus onInput=${(e) => setName(e.target.value)} />
    <button type="submit" class="ork-btn primary" disabled=${!name.trim() || busy}>Save</button>
    <button type="button" class="ork-btn" onClick=${() => setOpen(false)}>Cancel</button></form>`;
}
