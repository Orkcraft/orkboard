// A party's members on the desktop (decisions §53; realm/goal_team.py), as New party (goalwizard.js) and Edit the party (goaldialog.js)
// pick them: three bands of seats from the library (ideas.roles `library`, `seats`) — Leads (one: the party's steps run as it; the Taskmaster
// when none), Builds (three at most), Checks (two at most) —; a click takes an agent in or out of its band, a full band says so. Under them what
// the party costs (`ideas.party_price`: about what a goal costs, asked when the picker opens and 300 ms after a seat or *Every goal* changes) and what it
// can take (the goal types it would be offered, docs/specs/63-party-gathered.md), then the checkers' checks: where each applies or on every goal, and what each adds to a goal.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { command, say, toast } from "../link.js";
import { roles } from "./store.js";
import { pctOf, pctRange } from "../spend.js";
import { reducedMotion } from "../arena/motion.js";
import { Head, Icon, Sign, CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "../orkui.js";

export const CRAFTS = [["engineering", "peon", "Code, tests and the build"], ["design", "elf", "Screens, flows and words on them"],
  ["data", "goblin", "Numbers, queries and reports"], ["marketing", "gnome", "Pages, posts and search"],
  ["product", "lich", "Who it is for, what it moves, what it leaves out"]];
export const RACE = Object.fromEntries(CRAFTS);
/** An agent's race: the host's (`library.listed()`: an agent's own, the Release manager is a skeleton), the craft's for an older host that sends none (spec 68 §7.8). */
export const raceOfAgent = (a) => a.race || RACE[a.craft];
const BANDS = [["lead", "Leads", "plans the party's goals"], ["build", "Builds", "do the work"],
  ["check", "Checks", "hold each goal to their check"]];
const PITCH_BANDS = { lead: "decides on each pitch", build: "each reads every pitch, alone", check: "makes the case against" };     // what Ideation's bands do (spec 65 §1)
export const TASKMASTER = "taskmaster";

const library = () => roles.value?.library || [];
/** A line of the library the host sends in the code's words (a check's *applies when the idea changes code*): said in today's (a goal), after `say()`. */
export const libraryWords = (text) => say(String(text || "")).replace(/\bideas\b/g, "goals").replace(/\bidea\b/g, "goal");
export const agentOf = (id) => library().find((a) => a.id === id);
/** Ideation (docs/specs/65-ideation.md §1): a party the Investor leads is always its four views and the Skeptic — no seat changes there, and the six pitch agents
 *  (the library's `pitch`) are never offered to another party. */
export const pitchParty = (leader) => leader === "investor" || !!agentOf(leader)?.pitch;
export const IDEATION_STAYS = "Ideation reads every pitch from all four sides: its views and the Skeptic stay.";
const STAGE_WORDS = { lead: "Planning", build: "Implementation", check: "Checking" };
/** A leader's stages (ideas.roles `stages`, spec 59 §2.3); the default's for a leader not in it, and for an older host that sends none. */
const stagesOf = (leader) => roles.value?.stages?.[leader] || roles.value?.stages?.default || null;
/** The seats of a leader's party: {lead, build, check}. */
export const seatsFor = (leader) => stagesOf(leader)?.seats || roles.value?.seats || { lead: 1, build: 3, check: 2 };
/** The word of a leader's stage in a band: *Concept*, *Build*, *Playtest* with a Game designer; *Planning*, *Implementation*, *Checking* otherwise. */
export const stageWord = (leader, band) => stagesOf(leader)?.[band] || STAGE_WORDS[band];
/** The agents in a band: the leader alone in Leads; the team's builders or checkers. */
export const inBand = (band, leader, team) => (band === "lead" ? [leader] : team.filter((id) => agentOf(id)?.band === band));
/** The party in words: "led by Growth · builds: Copywriter, SEO · checks: Editor". */
export function partyWords(leader, team) {
  const names = (b) => inBand(b, leader, team).map((id) => agentOf(id)?.name).filter(Boolean).join(", ") || "none";
  return `led by ${agentOf(leader)?.name || "Taskmaster"} · builds: ${names("build")} · checks: ${names("check")}`;
}

/** The bands that hold more members than the leader's stage has seats: [{band, extra: [ids past the seats], text}]. A party saved before keeps its
 *  seats, but one picked under another leader has to fit before it is saved (spec 59 §6.2). */
export function overfull(leader, team) {
  const seats = seatsFor(leader), who = agentOf(leader)?.name || "Taskmaster";
  return ["build", "check"].map((band) => {
    const taken = inBand(band, leader, team);
    return { band, extra: taken.slice(seats[band]), text: `${stageWord(leader, band)} has ${seats[band]} seats with ${who}: take one out first.` };
  }).filter((x) => x.extra.length);
}

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
/** *3 parties in 2 projects · 2 met*: said only once a party of the person's has been used (the code's goals). */
export function usedWords(p) {
  return p.goals ? `${plural(p.goals, "party", "parties")} in ${plural(p.projects, "project", "projects")} · ${p.met} met` : "";
}

/** The library's parties New party offers (spec 59 §2.4): the mixed first, the crafts' after them, the Taskmaster alone last. An older host that sends no
 *  `presets` gives the five crafts as `parties` has them. */
export function presetsOf() {
  const sent = roles.value?.presets;
  if (sent?.length) return sent;
  return CRAFTS.map(([c, race, line]) => {
    const p = roles.value?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
    return { id: c, name: CRAFT_WORDS[c], line, craft: c, race, mixed: false, lead: p.lead || TASKMASTER, build: p.build || [], check: p.check || [] };
  });
}

/** The library's parties as tiles: *Mixed* (each its leader's head, its name, its line and its members' small heads), *One craft* (a head and a name),
 *  then the Taskmaster alone. A tile's `data-craft` is the library's id; `picked` is the one pressed (""): none). */
export function LibraryTiles({ picked, onPick }) {
  const all = presetsOf(), mixed = all.filter((p) => p.mixed), crafts = all.filter((p) => !p.mixed && p.craft !== "mixed"), alone = all.filter((p) => !p.mixed && p.craft === "mixed");
  const headOf = (id, fallback) => { const a = agentOf(id); return a ? { race: raceOfAgent(a), tier: a.tier } : fallback; };
  const tile = (p, rich) => {
    const lead = headOf(p.lead, { race: p.race, tier: "elder" });
    return html`<button type="button" key=${p.id} class=${`shell-craft-tile${rich ? " is-mixed" : ""}`} data-craft=${p.id} aria-pressed=${String(p.id === picked)} title=${p.line}
      onClick=${() => onPick(p)}><${Head} race=${lead.race} tier=${lead.tier} small=${true} />
      ${rich ? html`<span class="shell-craft-tile__text"><b>${p.name}</b><small class="ok-tone-muted">${p.line}</small>
        <span class="shell-craft-heads">${[...p.build, ...p.check].map((id, n) => agentOf(id) && html`<${Head} key=${n} race=${raceOfAgent(agentOf(id))} tier=${agentOf(id).tier} small=${true} />`)}</span></span>`
        : html`<b>${p.name}</b>`}</button>`;
  };
  return html`${mixed.length > 0 && html`<section class="shell-library-group" aria-label="Mixed"><h3 class="ok-font-label">Mixed</h3>
      <div class="shell-craft-tiles is-mixed" role="group" aria-label="Mixed">${mixed.map((p) => tile(p, true))}</div></section>`}
    <section class="shell-library-group" aria-label="One craft"><h3 class="ok-font-label">One craft</h3>
      <div class="shell-craft-tiles" role="group" aria-label="One craft">${crafts.map((p) => tile(p, false))}</div></section>
    ${alone.length > 0 && html`<div class="shell-craft-tiles shell-library-alone" role="group" aria-label="Taskmaster alone">${alone.map((p) => tile(p, false))}</div>`}`;
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
        <span class="shell-own-heads">${[p.leader, ...p.team].map((id, n) => agentOf(id) && html`<${Head} key=${n} race=${raceOfAgent(agentOf(id))} tier=${agentOf(id).tier} small=${true} />`)}</span>
        <b>${p.name}</b>${usedWords(p) && html`<small class="ok-tone-muted">${usedWords(p)}</small>`}</button>
      <button type="button" class="shell-own-chip__close" aria-label=${`Remove your party “${p.name}”`} onClick=${() => setAsking(p.id)}><${Icon} name="close" /></button>
      ${asking === p.id && html`<p class="shell-own-ask" role="alert">Remove your party “${p.name}”? Parties that use it keep their agents.
        <button type="button" class="ork-btn danger" onClick=${() => drop(p)}>Remove it</button>
        <button type="button" class="ork-btn" onClick=${() => setAsking("")}>Keep it</button></p>`}</div>`)}</div></section>`;
}

/** In About this party: **Save it to your parties**. It asks a name (*Engineering party*), asks again before it replaces a party of that
 *  name, and says after: *Saved: pick it for a party in any project.* */
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
    toast("Saved: pick it for a party in any project.");
    setName(null);
    setReplace("");
  };
  if (name === null) {
    return html`<button type="button" class="board-link shell-party-save" onClick=${() => setName(`${CRAFT_WORDS[craft] || "Engineering"} party`)}>Save it to your parties</button>`;
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

/** The three bands. `craft`: the party's, its agents listed first in each band. */
export function PartyBands({ craft = "", leader, setLeader, team, setTeam }) {
  const seats = seatsFor(leader), over = overfull(leader, team), fixed = pitchParty(leader);
  const on = (a) => (a.band === "lead" ? leader === a.id : team.includes(a.id));
  const toggle = (a) => {
    if (a.band === "lead") { setLeader(leader === a.id ? TASKMASTER : a.id); return; }
    if (team.includes(a.id)) setTeam(team.filter((x) => x !== a.id));
    else if (inBand(a.band, leader, team).length < seats[a.band]) setTeam([...team, a.id]);
    else toast(`${stageWord(leader, a.band)} has ${seats[a.band]} seats with ${agentOf(leader)?.name || "Taskmaster"}: take one out first.`, "warning");
  };
  const row = (a) => html`<button type="button" key=${a.id} class="shell-team-row" aria-pressed=${String(on(a))} data-agent=${a.id}
      aria-label=${`${on(a) ? "Take out" : "Take in"}: ${a.name}`} onClick=${() => toggle(a)}>
    <${Head} race=${raceOfAgent(a)} tier=${a.tier} /><b>${a.name}${a.check && html`<span class="shell-check-badge">checks</span>`}</b>
    <small class="ok-tone-muted">${TIER_WORDS[a.tier]} ${RACE_WORDS[raceOfAgent(a)]} · ${a.line}</small>
    <span class="shell-team-mark" aria-hidden="true"><${Icon} name=${on(a) ? "check" : "plus"} /></span></button>`;
  const bands = BANDS.map(([id, words, what]) => {
    const taken = inBand(id, leader, team);
    const list = fixed ? [] : library().filter((a) => a.band === id && !a.pitch).sort((x, y) => (x.craft === craft ? 0 : 1) - (y.craft === craft ? 0 : 1));
    const full = over.find((x) => x.band === id);
    return html`<section key=${id} class=${`shell-party-band band-${id}`} aria-label=${words}>
      <div class="shell-band-head"><h3>${stageWord(leader, id)}</h3><small class="ok-tone-muted">${words} · ${taken.length} of ${seats[id]} seats · ${fixed ? PITCH_BANDS[id] : what}</small></div>
      <div class="shell-team-seats">${Array.from({ length: Math.max(seats[id], taken.length) }, (_, i) => {
        const a = agentOf(taken[i]), past = i >= seats[id];
        return html`<span key=${i} class=${`shell-team-seat${a ? "" : " is-empty"}${id === "lead" ? " is-lead" : ""}${past ? " is-over" : ""}`} title=${a?.name || "A free seat"}>${a && html`<${Head} race=${raceOfAgent(a)} tier=${a.tier} />`}</span>`;
      })}</div>
      ${full && html`<p class="shell-band-over" role="alert">${full.text}</p>`}
      ${list.length > 0 && html`<div class="shell-team-list">${list.map(row)}</div>`}</section>`;
  });
  return fixed ? [...bands, html`<p key="fixed" class="ok-tone-muted shell-band-fixed">${IDEATION_STAYS}</p>`] : bands;
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

/** *about $2–6*, for a goal: below $1 (its low end) in cents, *about $0.40–1.20*. */
export function rangeWords(price) {
  const { low, high } = price;
  if (pctRange(low, high)) return `about ${pctRange(low, high)}`;
  if (low < 1) return `about $${low.toFixed(2)}–${high.toFixed(2)}`;
  const a = Math.round(low), b = Math.round(high);
  return a === b ? `about $${a}` : `about $${a}–${b}`;
}

/** Under the bands: *This party: about $2–6 an idea* and, muted, where it comes from; under it the hints (spec 43 §5), muted, one line each:
 *  they never block Save and have no button. */
export function PriceLine({ price }) {
  if (!price) return null;
  return html`<p class="shell-price" role="status">This party: ${rangeWords(price)} ${price.pitch ? "a pitch" : "a goal"}
    <small class="ok-tone-muted"> ${price.learned ? `from this project's last ${price.ideas} ${price.pitch ? "pitches" : "goals"}` : `a first guess: it learns from this project's ${price.pitch ? "pitches" : "goals"}`}</small></p>
    ${(price.hints || []).map((h, n) => html`<p key=${n} class="shell-hint ok-font-status ok-tone-muted">${h}</p>`)}`;
}

/** Under the price: **It can take:** the goal types a party of these seats would be offered (`price.types`: {id, name, sign, missing}, spec 63 §2) — each its sign and name, joined by *·* —, then
 *  **with one more:** the ones that miss someone, *New screen (needs Design system designer)*; none: *nothing of its own yet: add a builder.* Two lines at most: what does not fit ends with *and k more*
 *  (the title lists them all). A type the last answer opened is lit once, as the quiet reward (not at the first answer, none under reduced motion). An older host sends no `types`: no line. */
export function CanTake({ price }) {
  const types = price?.types, root = useRef(), was = useRef(null);
  const ready = (types || []).filter((t) => !t.missing), more = (types || []).filter((t) => t.missing), all = [...ready, ...more];
  const key = all.map((t) => `${t.id}:${t.missing}`).join("|");
  const [fit, setFit] = useState({ key: "", cut: 0 });          // how many types, from the last, the line has had to leave out for its two lines
  const cut = fit.key === key ? fit.cut : 0;
  useLayoutEffect(() => {
    const el = root.current;
    if (el && el.scrollHeight > el.clientHeight + 1 && cut < all.length - 1) setFit({ key, cut: cut + 1 });
  }, [key, cut]);
  useEffect(() => {
    if (!types) return;
    const open = ready.map((t) => t.id), opened = was.current ? open.filter((id) => !was.current.includes(id)) : [];
    was.current = open;
    if (reducedMotion() || document.hidden) return;
    opened.forEach((id) => root.current?.querySelector(`[data-type="${CSS.escape(id)}"]`)?.animate?.([{ background: "var(--ork-ink)", color: "var(--ork-on-ink)" }, { background: "transparent" }], { duration: 600, easing: "steps(4, end)" }));
  }, [types]);
  if (!types || price.pitch) return null;                 // Ideation takes pitches: no goal type (spec 65 §1)
  const said = (t) => `${t.name}${t.missing ? ` (needs ${t.missing})` : ""}`;
  const item = (t, i) => html`<span key=${t.id} class="shell-cantake__item">${i ? " · " : ""}<span class="shell-cantake__one" data-type=${t.id}><${Sign} name=${t.sign} /> ${said(t)}</span></span>`;
  const shown = all.slice(0, all.length - cut), shownReady = shown.slice(0, ready.length), shownMore = shown.slice(ready.length);
  const first = ready.length ? shownReady.map(item) : html`<span class="ok-tone-muted">nothing of its own yet: add a builder${more.length ? "" : "."}</span>`;
  const next = shownMore.length > 0 && html` <span class="ok-tone-muted">with one more:</span> ${shownMore.map(item)}`;
  const rest = cut > 0 && html` <span class="ok-tone-muted">and ${cut} more</span>`;
  return html`<p ref=${root} class="shell-cantake ok-font-status" title=${cut ? all.map(said).join(", ") : undefined}><span class="ok-tone-muted">It can take:</span> ${first}${next}${rest}</p>`;
}

/** *adds about $0.35 to a goal it checks · about half of them* (*· every goal* when it checks every goal). */
export function addsWords(c) {
  const share = c.every ? "every goal" : Math.abs(c.share - 0.5) < 0.03 ? "about half of them" : `about ${Math.round(c.share * 100)} % of them`;
  return `adds about ${pctOf(c.usd) || `$${c.usd.toFixed(2)}`} to a goal it checks · ${share}`;
}

/** The party's checks: each checker's, where it applies or on every goal, and what a check adds to a goal (`price`: `ideas.party_price`). */
export function ChecksBlock({ team, every, setEvery, price = null }) {
  const checkers = team.map(agentOf).filter((a) => a?.check);
  if (!checkers.length) return html`<p class="ok-tone-muted">No checker in the party: a goal is done when its own Done when lines are.</p>`;
  const adds = (a) => { const c = (price?.checks || []).find((x) => x.by === a.id); return c ? ` · ${addsWords(c)}` : ""; };
  return html`<div class="shell-checks" role="group" aria-label="Checks"><span class="ok-font-label">Checks on every goal</span>
    <p class="ok-tone-muted">How deep each goal is worked: every check adds a line to its Done when and a task to its plan.</p>
    ${checkers.map((a) => html`<div key=${a.id} class="shell-check-row"><${Head} race=${raceOfAgent(a)} tier=${a.tier} small=${true} />
      <span><b>${a.name}</b> <small class="ok-tone-muted">${libraryWords(`${a.check.done} · applies ${a.check.applies}`)}${adds(a)}</small></span>
      <label class="shell-check-every"><input type="checkbox" aria-label=${`Every goal: ${a.name}`} checked=${every.includes(a.id)}
        onChange=${(e) => setEvery(e.target.checked ? [...every, a.id] : every.filter((x) => x !== a.id))} /> Every goal</label></div>`)}</div>`;
}
