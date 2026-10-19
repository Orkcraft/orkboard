// Needs you (docs/specs/35-goals-window.md §10–§11.2), a tab of its own beside the Board's, as on the phone (pwa/shell-needs.js):
// one list of every goal's rows, sorted by the host (what blocks work in progress, then the priority, then the oldest; proposals
// last), an icon per kind, its title, its kind and goal, and one line. Questions are answered in their row: each question's likely
// answers (the keeper ends a question with them, "(one / other)") as buttons, one Send, and More for the form with a box per
// question. A click on another row opens what it is about: the plan, the to-do's dialog, the goal. A proposal is answered in its
// row. Later puts a row away on this computer for a few hours; nothing is sent.
import { useState } from "preact/hooks";
import { signal } from "@preact/signals";
import { html } from "../html.js";
import { Icon, NEED_ICONS } from "../orkui.js";
import { say, toast } from "../link.js";
import { board, PRIORITY_WORDS } from "./store.js";
import { RulesProposal } from "./ops.js";
import { act as run, showGoal, showIdea, showPlan } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";

const KIND_WORDS = { goal: "A goal asks", asks: "A spec asks", plan: "A plan waits for you", todo: "A to-do", failed: "Failed", proposal: "A proposal", op: "At your check", op_failed: "Failed", op_rules: "Rules to take" };

function Proposal({ n }) {
  const g = board.value.tracks.find((t) => t.slug === n.goal);
  const [priority, setPriority] = useState(g?.priority || "normal");
  const [reason, setReason] = useState("");
  const [declining, setDeclining] = useState(false);
  return html`<li class="board-need board-proposal" data-kind="proposal">
    <span class="board-need__icon"><${Icon} name=${NEED_ICONS.proposal} /></span>
    <div class="board-need__text"><b>${n.title}</b><span class="ok-tone-muted">${n.text}</span>
      <div class="board-row">
        <label class="board-inline">
          <select class="ork-field" aria-label=${`Priority of ${n.title}`} title="Priority" value=${priority} onChange=${(e) => setPriority(e.target.value)}>
            ${Object.entries(PRIORITY_WORDS).map(([id, name]) => html`<option key=${id} value=${id}>${name}</option>`)}</select></label>
        <button class="ork-btn primary" aria-label=${`Take: ${n.title}`} onClick=${() => run("ideas.proposal", { slug: n.idea, take: true, priority })}>Take</button>
        ${!declining && html`<button class="ork-btn" aria-label=${`No: ${n.title}`} onClick=${() => setDeclining(true)}>No</button>`}</div>
      ${declining && html`<div class="board-row">
        <input class="ork-field" value=${reason} aria-label=${`Why not: ${n.title}`} placeholder="Why not? (optional, one line)" autofocus
          onInput=${(e) => setReason(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter") run("ideas.proposal", { slug: n.idea, take: false, ...(reason.trim() ? { reason: reason.trim() } : {}) }); }} />
        <button class="ork-btn" aria-label=${`Decline: ${n.title}`}
          onClick=${() => run("ideas.proposal", { slug: n.idea, take: false, ...(reason.trim() ? { reason: reason.trim() } : {}) })}>No</button>
        <button class="board-link" onClick=${() => setDeclining(false)}>Cancel</button></div>`}
    </div></li>`;
}

/** Operations' rows (spec 38 §8) belong to no goal and no project: they show whichever goal is chosen. */
const isOp = (n) => n.kind === "op" || n.kind === "op_failed" || n.kind === "op_rules";

function OpRules({ n }) {
  return html`<li class="board-need board-proposal" data-kind="op_rules" data-template=${n.template}>
    <span class="board-need__icon"><${Icon} name=${NEED_ICONS.op_rules} /></span>
    <div class="board-need__text"><b>${n.title}</b><span class="ok-tone-muted board-need__kind">${KIND_WORDS.op_rules}</span>
      <${RulesProposal} template=${n.template} title=${n.title} lines=${n.lines || [n.text]} /></div></li>`;
}

function open(n) {
  if (n.kind === "op" || n.kind === "op_failed") openDialog("opcheck", { op: n.op });
  else if (n.kind === "goal") openDialog("ask", { slug: n.goal, goal: true, title: n.title });
  else if (n.kind === "asks") openDialog("ask", { slug: n.idea, title: n.title });
  else if (n.kind === "todo") openDialog("todo", { idea: n.idea, todo: n.todo });
  else if (n.kind === "plan") showPlan(n.idea, "", { via: "needs" });
  else showIdea(n.idea, { via: "needs" });
}

// -- Later: a row put away on this computer for a few hours (as the phone's, its own) ---------------------------------
const LATER = "orkboard.later";                       // {row key: until}
const LATER_MS = 4 * 3600 * 1000;
const keyOf = (n) => `${n.kind}:${n.idea || n.goal || n.op || n.template || ""}:${n.text || ""}`;
const laterRev = signal(0);                           // a row put away: drawn again
const laterAll = () => { try { return JSON.parse(localStorage.getItem(LATER)) || {}; } catch { return {}; } };
const isLater = (n) => (laterAll()[keyOf(n)] || 0) > Date.now();
function putAway(n) {
  const now = Date.now(), all = Object.fromEntries(Object.entries(laterAll()).filter(([, t]) => t > now));
  all[keyOf(n)] = now + LATER_MS;
  try { localStorage.setItem(LATER, JSON.stringify(all)); } catch { /* this run only */ }
  laterRev.value += 1;
  toast("Put away for a few hours, on this computer.");
}

/** A question and its likely answers: "Which store first? (App Store / Google Play)" → {ask: "Which store first?", choices: [...]}. */
export function choicesOf(q) {
  const m = String(q || "").match(/^(.*?)\s*\(([^()]*\/[^()]*)\)\s*([?.!]?)\s*$/);
  const choices = m ? m[2].split("/").map((c) => c.trim()).filter(Boolean) : [];
  if (!m || choices.length < 2 || choices.length > 4 || choices.some((c) => c.length > 40)) return { ask: String(q || ""), choices: [] };
  return { ask: `${m[1].trim()}${m[3] && !/[?.!]$/.test(m[1].trim()) ? m[3] : ""}`, choices };
}

const goalTitle = (slug) => (board.value?.tracks || []).find((t) => t.slug === slug)?.title || "";
const kindLine = (n) => [KIND_WORDS[n.kind], !isOp(n) && n.goal && n.goal !== "general" ? goalTitle(n.goal) : ""].filter(Boolean).join(" · ");

/** Questions answered in their row: a likely answer each, one Send; More for the whole form; Later. */
function Quick({ n }) {
  const qs = (n.questions?.length ? n.questions : [n.text]).filter(Boolean).slice(0, 3);
  const [picked, setPicked] = useState(qs.map(() => ""));
  const [sending, setSending] = useState(false);
  const isGoal = n.kind === "goal";
  const send = async () => {
    setSending(true);
    const got = await run("ideas.answer", { slug: isGoal ? n.goal : n.idea, answers: picked, ...(isGoal ? { goal: true } : {}) });
    setSending(false);
    if (got) toast(say("Sent: the Taskmaster answers in a moment."));
  };
  return html`<li class="board-need board-quick" data-kind=${n.kind} data-priority=${n.priority} data-idea=${n.idea || undefined} data-goal=${n.goal || undefined}>
    <span class="board-need__icon"><${Icon} name=${NEED_ICONS[n.kind] || "flag"} /></span>
    <div class="board-need__text"><b>${n.title}</b><span class="ok-tone-muted board-need__kind">${kindLine(n)}</span>
      ${qs.map((q, i) => {
        const { ask, choices } = choicesOf(q);
        return html`<div key=${i} class="board-quick__q"><span>${say(ask)}</span>${choices.length > 0 && html`<div class="board-row board-quick__answers">
          ${choices.map((c) => html`<button key=${c} type="button" class="ork-btn board-quick__answer" aria-pressed=${String(picked[i] === c)}
            onClick=${() => setPicked(picked.map((x, j) => (j === i ? (x === c ? "" : c) : x)))}>${c}</button>`)}</div>`}</div>`;
      })}
      ${qs.length > 1 && html`<span class="ok-tone-muted board-need__kind">${say("A question left without an answer: the Taskmaster decides.")}</span>`}
      <div class="board-row"><button type="button" class="ork-btn primary" disabled=${sending || !picked.some(Boolean)} aria-label=${`Send: ${n.title}`} onClick=${send}>Send</button>
        <button type="button" class="ork-btn" aria-label=${`More: ${n.title}`} onClick=${() => open(n)}>More</button>
        <button type="button" class="ork-btn" aria-label=${`Later: ${n.title}`} onClick=${() => putAway(n)}>Later</button></div></div></li>`;
}

function Row({ n }) {
  if (n.kind === "proposal") return html`<${Proposal} n=${n} />`;
  if (n.kind === "op_rules") return html`<${OpRules} n=${n} />`;
  if (n.kind === "goal" || n.kind === "asks") return html`<${Quick} n=${n} />`;
  return html`<li class="board-need-row">
    <button class="board-need" data-kind=${n.kind} data-priority=${n.priority} onClick=${() => open(n)}>
      <span class="board-need__icon"><${Icon} name=${NEED_ICONS[n.kind] || "flag"} /></span>
      <span class="board-need__text"><b>${n.title}</b><span class="ok-tone-muted board-need__kind">${kindLine(n)}</span>
        <span class="ok-tone-muted">${isOp(n) ? n.text : say(n.text)}</span></span></button>
    <button class="ork-btn board-need__later" aria-label=${`Later: ${n.title}`} onClick=${() => putAway(n)}>Later</button></li>`;
}

const rowKey = (n) => n.kind + (n.op || n.idea || n.goal || n.template || "") + (n.todo?.id || "");

/** How many rows wait on the person now (proposals, and the ones put away Later, aside): the Needs you tab says it. */
export function needsCount() {
  void laterRev.value;
  return (board.value?.needs_you || []).filter((n) => n.kind !== "proposal" && n.kind !== "op_rules" && !isLater(n)).length;
}

export function Today() {
  void laterRev.value;
  const [showLater, setShowLater] = useState(false);
  const all = board.value.needs_you || [];
  const list = all.filter((n) => !isLater(n)), away = all.filter(isLater);
  return html`<section class="board-today" aria-label="Needs you">
    ${list.length ? html`<ul class="board-list">${list.map((n) => html`<${Row} key=${rowKey(n)} n=${n} />`)}</ul>`
      : html`<p class="ok-tone-muted">Nothing waits for you.</p>`}
    ${away.length > 0 && html`<button class="board-link" onClick=${() => setShowLater(!showLater)}>${showLater ? `Hide the ${away.length} put away` : `Put away for later (${away.length}): show`}</button>
      ${showLater && html`<ul class="board-list is-later">${away.map((n) => html`<${Row} key=${rowKey(n)} n=${n} />`)}</ul>`}`}
  </section>`;
}
