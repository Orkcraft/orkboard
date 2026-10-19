// Needs you (docs/specs/35-goals-window.md §10–§11.2): one list, sorted by the host (what blocks work in progress, then the
// priority, then the oldest; proposals last), an icon per kind, its title and one line. A click opens what it is about:
// the questions as one form, the plan, the to-do's dialog, the goal. A proposal is answered in its row.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { Icon, NEED_ICONS } from "../orkui.js";
import { say } from "../link.js";
import { board, track, PRIORITY_WORDS } from "./store.js";
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

export function Today() {
  const all = board.value.needs_you || [];
  const list = all.filter((n) => isOp(n) || !track.value || n.goal === track.value);
  return html`<section class="board-today" aria-label="Needs you">
    <h3 class="board-sub kit-band">Needs you ${list.length ? html`<span class="board-count kit-well">${list.length}</span>` : ""}</h3>
    ${list.length ? html`<ul class="board-list">${list.map((n) => (n.kind === "proposal" ? html`<${Proposal} key=${"p" + n.idea} n=${n} />`
      : n.kind === "op_rules" ? html`<${OpRules} key=${"r" + n.template} n=${n} />`
      : html`<li key=${n.kind + (n.op || n.idea || n.goal) + (n.todo?.id || "")}>
        <button class="board-need" data-kind=${n.kind} data-priority=${n.priority} onClick=${() => open(n)}>
          <span class="board-need__icon"><${Icon} name=${NEED_ICONS[n.kind] || "flag"} /></span>
          <span class="board-need__text"><b>${n.title}</b><span class="ok-tone-muted board-need__kind">${KIND_WORDS[n.kind]}</span>
            <span class="ok-tone-muted">${isOp(n) ? n.text : say(n.text)}</span></span></button></li>`))}</ul>`
      : html`<p class="ok-tone-muted">Nothing waits for you.</p>`}
  </section>`;
}
