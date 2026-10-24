// About this party (docs/specs/50-parties-and-goals.md §3.7), a party in the drawer — the code's goal: *What it is for* (its brief and Summary), *The party* (the
// leader, each member with what it does and costs), *Checks on every goal*, *What it costs* (so far, today, the price a goal), *Its flags* (⚑ the goal · date ·
// ≈$ · k of n first time; the newest ten, then All n) and, only for a party with a verdict of before, *Before: <its old flag>*; at the foot *Edit the party* and
// *Save it to your parties*. No Metrics, no Verdict, no *Ask … to accept*: a party has no end, only a count and its goals' flags. A question the party's leader asked is
// still answered here, in the same talk as a goal's.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { goal, act, aboutAt, agents, mapData, roles, logOpened, showIdea } from "./store.js";
import { ask } from "../board/store.js";
import { Sign, WhoHead } from "../orkui.js";
import { openDialog } from "./modals.js";
import { ErrorLine } from "./errors.js";
import { Questions } from "../board/ask.js";
import { SaveParty, libraryWords, rangeWords, usePartyPrice } from "./party.js";
import { flagDate } from "../board/maplayout.js";
import { soFarWords, todayWords } from "../board/mapstage.js";
import { flagRow, waitsMain } from "../arena/goalwords.js";
import { money } from "../arena/arenawords.js";
import { pctOf } from "../spend.js";

export const GOAL_STATE = { reading: "the Taskmaster is reading", asks: "asks you", ready: "ready", raw: "" };
/** Who leads a party, as a sentence starts with it: its leader by name, else "The Taskmaster". */
const leaderThe = (g) => (g.leader?.slug && g.leader.slug !== "taskmaster" ? g.leader.name : say("The Taskmaster"));

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const usdWords = (usd) => `≈${pctOf(usd) || `$${usd.toFixed(2)}`}`;
const SHOWN = 10;

/** What a party did (spec 43 §2.3), a line each, in the text face: the leader's steps, each member's tasks, each checker's checks. */
export function partyLines(w) {
  if (!w.ideas) return ["No work yet"];
  const lead = w.leader;
  const lines = [`${lead.name} (leads)${lead.usd != null ? `: ${usdWords(lead.usd)} for the party, the drafts and the plans` : ""}`];
  for (const m of w.members) {
    lines.push(`${m.name}: ${plural(m.tasks, "task", "tasks")}, ${m.first_time ? `${m.first_time} merged the first time` : "none merged the first time"}${m.usd != null ? ` · ${usdWords(m.usd)}` : ""}`);
  }
  for (const c of w.checks) {
    lines.push(`${c.name}: checked ${plural(c.applied, "goal", "goals")}: ${c.clean} clean, caught ${c.caught}${c.left ? ` (${c.left} left)` : ""}`
      + `${c.usd != null ? ` · ${usdWords(c.usd)}` : ""}${c.skipped ? ` · skipped ${c.skipped}` : ""}${c.before ? ` · ${c.before} ended without findings` : ""}`);
  }
  return lines;
}

/** *What the party did*: a fold, closed at first, that reads `ideas.party` when it is opened and says it once (`opened` `party`). */
export function PartyWork({ goal: slug }) {
  const [work, setWork] = useState(null);
  const toggle = async (e) => {
    if (!e.currentTarget.open) return;
    logOpened("party", slug);
    const got = await ask("ideas.party", { goal: slug });
    if (got) setWork(got);
  };
  return html`<details class="shell-party" onToggle=${toggle}><summary>What the party did</summary>
    ${work ? html`<ul class="shell-party__lines">${partyLines(work).map((l, n) => html`<li key=${n}>${l}</li>`)}</ul>` : html`<p class="ok-tone-muted">Reading…</p>`}</details>`;
}

/** A member of the party and what it does and costs: *Backend · builds · ≈$0.40 a result*, *Reviewer · checks · ≈$0.25 a goal*. */
function memberLine(slug) {
  const a = (roles.value?.library || []).find((x) => x.id === slug), r = (agents.value?.roles || []).find((x) => x.role === slug);
  const band = a?.band === "check" ? "checks" : "builds", price = r?.usd_task != null ? ` · ≈${money(r.usd_task)} ${a?.band === "check" ? "a goal" : "a result"}` : "";
  return { name: r?.name || a?.name || slug, head: r?.head || null, text: `${band}${price}` };
}

/** *Reviewer checks code · caught 2/6 lately*: a check that holds every goal. */
function checkLine(slug) {
  const a = (roles.value?.library || []).find((x) => x.id === slug), r = (agents.value?.roles || []).find((x) => x.role === slug), w = r?.check_week;
  return { name: r?.name || a?.name || slug, text: `${a?.check?.applies ? libraryWords(`checks ${a.check.applies}`) : "checks every goal"}${w?.checks ? ` · caught ${w.caught}/${w.checks} lately` : ""}` };
}

export function GoalView() {
  const g = goal.value, root = useRef();
  const m = mapData.value?.goals.find((x) => x.slug === g?.slug), nodes = (mapData.value?.nodes || []).filter((n) => n.goal === g?.slug);
  const seats = g?.team || [], price = usePartyPrice(!!g, g?.leader?.slug || "taskmaster", seats, (g?.every || []).filter((s) => seats.includes(s)), g?.craft || "");
  const all = useState(false);
  useEffect(() => {                                       // opened from the flag line: at Its flags
    if (aboutAt.value === "flags" && g && root.current) {
      root.current.querySelector("[data-sec=flags]")?.scrollIntoView({ block: "start" });
      aboutAt.value = "";
    }
  }, [g?.slug, !!g, !!mapData.value]);
  if (!g) return html`<p class="ok-tone-muted">Opening…</p>`;
  const lead = leaderThe(g), named = g.leader?.slug && g.leader.slug !== "taskmaster";
  const words = g.state === "reading" && named ? `${lead} is reading` : GOAL_STATE[g.state];
  const brief = m?.brief || "", summary = g.summary || "", flagged = nodes.filter((n) => n.flag).sort((a, b) => String(b.flag.at).localeCompare(String(a.flag.at)));
  const shown = all[0] ? flagged : flagged.slice(0, SHOWN), atWork = nodes.filter((n) => n.stage === "implementation" || n.stage === "checking").length;
  const old = g.verdict && (g.verdict.by || g.verdict.met !== undefined) ? g.verdict : null;
  const cost = [m ? soFarWords(m.usd) : "", m ? todayWords(m.today) : ""].filter(Boolean).join(" · ");
  return html`<div class="shell-result" ref=${root}><div class="shell-result__body shell-goal" data-state=${g.state}>
    <div class="board-bar"><span class="shell-ptab__kind">Party</span><span class="board-state" data-state=${g.state}>${say(words || "")}</span>
      <span class="board-size kit-well">${({ high: "High", normal: "Normal", low: "Low" })[g.priority]}</span></div>
    <div class="shell-goal__head"><h2>${g.title}</h2><span class="ok-tone-muted">led by ${lead} · ${plural(seats.length, "member", "members")}</span></div>
    ${g.state_error && g.state === "raw" && html`<${ErrorLine} text=${g.state_error} />`}
    <section class="shell-goal__sec" aria-label="What it is for" data-sec="for"><h3 class="board-sub">What it is for</h3>
      <p class="shell-brief">${brief || g.description || html`<span class="ok-tone-muted">${g.state === "reading" ? `${lead} is reading the party…` : "No description yet."}</span>`}</p>
      ${summary && summary !== brief && html`<p class="shell-brief ok-tone-muted">${summary}</p>`}</section>
    <section class="shell-goal__sec" aria-label="The party" data-sec="party"><h3 class="board-sub">The party</h3>
      <ul class="shell-goal__team"><li key="lead">${g.leader?.head && html`<${WhoHead} head=${g.leader.head} small />`} <b>${g.leader?.name || "Taskmaster"}</b> <span class="ok-tone-muted">leads</span></li>
        ${seats.map((s) => { const l = memberLine(s); return html`<li key=${s}>${l.head && html`<${WhoHead} head=${l.head} small />`} <b>${l.name}</b> <span class="ok-tone-muted">· ${l.text}</span></li>`; })}</ul>
      <${PartyWork} goal=${g.slug} /></section>
    <section class="shell-goal__sec" aria-label="Checks on every goal" data-sec="checks"><h3 class="board-sub">Checks on every goal</h3>
      ${(g.every || []).length ? html`<ul class="shell-goal__team">${g.every.map((s) => { const c = checkLine(s); return html`<li key=${s}><b>${c.name}</b> <span class="ok-tone-muted">${c.text}</span></li>`; })}</ul>`
        : html`<p class="ok-tone-muted">None: a check holds a goal where it applies.</p>`}</section>
    <section class="shell-goal__sec" aria-label="What it costs" data-sec="costs"><h3 class="board-sub">What it costs</h3>
      ${cost && html`<p>${cost}</p>`}
      ${price && html`<p class="ok-tone-muted">${rangeWords(price)} a goal with this party</p>`}
      ${!cost && !price && html`<p class="ok-tone-muted">Nothing yet.</p>`}</section>
    <section class="shell-goal__sec" aria-label="Its flags" data-sec="flags"><h3 class="board-sub">Its flags</h3>
      ${flagged.length ? html`<ul class="shell-goal__flags">${shown.map((n) => { const f = flagRow(n); return html`<li key=${f.slug}><button type="button" class="board-link shell-goal__flag" onClick=${() => showIdea(f.slug, { via: "flags" })}>
          <span class="shell-goal__flagmark"><${Sign} name="flag" /></span> ${f.short}</button> <span class="ok-tone-muted">· ${f.words}</span></li>`; })}</ul>
        ${!all[0] && flagged.length > SHOWN && html`<button type="button" class="board-link" onClick=${() => all[1](true)}>All ${flagged.length}</button>`}`
        : html`<p class="ok-tone-muted">No flag yet: a goal raises its flag when the gate takes it into main.</p>`}
      <p class="ok-tone-muted">${[atWork ? plural(atWork, "goal", "goals") + " at work" : "", m ? `${waitsMain(m, nodes)} wait for main` : ""].filter(Boolean).join(", ")}</p></section>
    ${old && html`<section class="shell-goal__sec" aria-label="Before" data-sec="before"><p class="ok-tone-muted">Before: ${old.met ? "met" : "not met yet"}, says ${old.by || "its leader"}${old.at ? ` · ${flagDate(old.at)}` : ""}</p></section>`}
    ${g.questions?.length > 0 && html`<section class="shell-goal__sec" aria-label="Open questions"><h3 class="board-sub">Open questions</h3>
      <ul class="shell-links">${g.questions.map((q) => html`<li key=${q}>${q}</li>`)}</ul>
      <${Questions} key=${g.questions.join("|")} questions=${g.questions} busy=${g.busy}
        onSend=${(answers) => act("ideas.answer", { slug: g.slug, answers, goal: true })} /></section>`}
    ${g.talk?.length > 0 && html`<ol class="board-talk" aria-label="The talk">${g.talk.slice(-8).map((t, n) => html`<li key=${n} data-who=${t.who}>
      <span class="board-talk__who">${t.who === "you" ? "You" : lead}</span><span>${t.text}</span></li>`)}</ol>`}
  </div>
  <footer class="shell-result__foot shell-goal__acts"><button type="button" class="ork-btn" onClick=${() => openDialog("goal", { slug: g.slug })}>Edit the party</button>
    <${SaveParty} goal=${g.slug} craft=${g.craft} /></footer></div>`;
}
