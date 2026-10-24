// Operations (docs/specs/38-operations.md §10): the person's everyday work by templates, the same in every project. The list
// (at your check · running · failed · done · templates), the New… menu and the rules proposal a template waits with. A click on
// a row opens the check (shell/opcheck.js); the form and the gear are dialogs (shell/opdialog.js). A brief (spec 66 §7) keeps a
// page: its done row opens it read-only; its template's row says what it reads, lists its standing briefs and offers Forget….
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { Icon } from "../orkui.js";
import { openLink } from "../link.js";
import { ops, refreshOps, useOps, hhmm } from "./store.js";
import { act } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";

/** A command of Operations, then Operations and the Board again (Needs you holds its rows). */
export async function run(name, args) {
  const got = await act(name, args);
  await refreshOps();
  return got;
}

const RUNNING = ["preparing", "acting", "held"];
const BUSY_WORDS = { preparing: "preparing", acting: "doing it", held: "preparing" };

/** The value of a follow brief's field (*Before a 1:1 · Alex*): whom its row is about; "" for any other. */
export function aboutOf(r, t) {
  return t?.follow ? String((r.fields || {})[t.follow] || "").trim() : "";
}

/** A run's first draft part, as its row's one line. */
export function firstPart(r, t) {
  const draft = r.draft || {};
  const first = t?.draft?.length ? draft[t.draft[0].name] : Object.values(draft)[0];
  return String(first || "").split("\n").map((l) => l.trim()).find(Boolean) || "";
}

/** What a template that waits with rules is asked: Take them, or No (with a reason, if the person wants to give one). */
export function RulesProposal({ template, title, lines, why = "" }) {
  const [declining, setDeclining] = useState(false);
  const [reason, setReason] = useState("");
  const answer = (take) => run("ops.rules_answer", { template, take, ...(!take && reason.trim() ? { reason: reason.trim() } : {}) });
  return html`<div class="board-op-rules" data-template=${template}>
    ${why && html`<span class="ok-tone-muted">${why}</span>`}
    <ul class="board-op-lines">${lines.map((l, n) => html`<li key=${n}>${l}</li>`)}</ul>
    <div class="board-row">
      <button class="ork-btn primary" aria-label=${`Take the rules: ${title}`} title="The rules are kept for this template, and it goes by itself"
        onClick=${() => answer(true)}>Take</button>
      ${!declining && html`<button class="ork-btn" aria-label=${`No rules: ${title}`} onClick=${() => setDeclining(true)}>No</button>`}</div>
    ${declining && html`<div class="board-row">
      <input class="ork-field" value=${reason} aria-label=${`Why not: ${title}`} placeholder="Why not? (optional, one line)" autofocus
        onInput=${(e) => setReason(e.target.value)} onKeyDown=${(e) => { if (e.key === "Enter") answer(false); }} />
      <button class="ork-btn" aria-label=${`Decline the rules: ${title}`} onClick=${() => answer(false)}>No</button>
      <button class="board-link" onClick=${() => setDeclining(false)}>Cancel</button></div>`}
  </div>`;
}

/** New…: one item per usable template, then a line for each that cannot be used and why. */
export function NewMenu() {
  const [open, setOpen] = useState(false);
  const list = ops.value?.templates || [];
  const usable = list.filter((t) => !t.unusable), off = list.filter((t) => t.unusable);
  const pick = (t) => { setOpen(false); openDialog("opform", { template: t.name }); };
  return html`<div class="board-target board-newmenu">
    <button type="button" class="ork-btn primary" aria-haspopup="menu" aria-expanded=${open} onClick=${() => setOpen(!open)}>New…</button>
    ${open && html`<div class="board-target__menu kit-well" role="menu" aria-label="New operation"
      onKeyDown=${(e) => { if (e.key === "Escape") { e.stopPropagation(); setOpen(false); } }}>
      ${usable.map((t) => html`<button type="button" key=${t.name} role="menuitem" class="board-target__one" data-template=${t.name}
        onClick=${() => pick(t)}><b>${t.title}</b></button>`)}
      ${off.map((t) => html`<div key=${t.name} class="board-target__one board-newmenu__off" data-template=${t.name} data-unusable="true">
        <b>${t.title}</b><span class="ok-tone-muted">${t.unusable}</span></div>`)}
      ${!list.length && html`<span class="ok-tone-muted">No template yet.</span>`}
    </div>`}
  </div>`;
}

function CheckRow({ r, t }) {
  const part = firstPart(r, t), about = aboutOf(r, t);
  return html`<li><button class="board-need" data-kind="op" data-op=${r.id} onClick=${() => openDialog("opcheck", { op: r.id })}>
    <span class="board-need__icon" aria-hidden="true">☑</span>
    <span class="board-need__text"><b>${r.title}${about && ` · ${about}`}</b>
      <span class="ok-tone-muted board-need__kind">${r.why || "at your check"} · ${hhmm(r.at)}</span>
      ${part && html`<span class="ok-tone-muted">${part}</span>`}</span></button></li>`;
}

function RunningRow({ r }) {
  const held = r.state === "held" || r.held_until;
  return html`<li class="board-op" data-op=${r.id} data-state=${r.state}>
    <span class="board-op__title"><b>${r.title}</b>
      <span class="board-state" data-state="working">${!held && html`<span class="shell-spin" aria-hidden="true">↻</span> `}${held
        ? r.why || `waits for limits · after ${hhmm(r.held_until)}` : BUSY_WORDS[r.state]}</span></span>
    <span class="board-card__acts"><button class="ork-btn danger" aria-label=${`Stop: ${r.title}`} onClick=${() => run("ops.stop", { id: r.id })}>Stop</button></span></li>`;
}

function FailedRow({ r }) {
  return html`<li class="board-op" data-op=${r.id} data-state="failed">
    <span class="board-op__title"><b>${r.title}</b><span class="board-state" data-state="failed">${r.why || "It failed"}</span></span>
    <span class="board-card__acts">
      ${r.acted === false && html`<button class="ork-btn" aria-label=${`Try again: ${r.title}`} onClick=${() => run("ops.retry", { id: r.id })}>Try again</button>`}
      <button class="ork-btn" aria-label=${`Add again: ${r.title}`} title="Adds a new operation with the same form" onClick=${() => run("ops.again", { id: r.id })}>Add again</button>
      <button class="ork-btn" aria-label=${`Drop: ${r.title}`} onClick=${() => run("ops.drop", { id: r.id })}>Drop</button></span></li>`;
}

function DoneRow({ r, t }) {
  const [asking, setAsking] = useState(false);
  const [why, setWhy] = useState("");
  const send = async () => { setAsking(false); await run("ops.not_right", { id: r.id, ...(why.trim() ? { why: why.trim() } : {}) }); };
  const part = firstPart(r, t), about = aboutOf(r, t);
  return html`<li class="board-op" data-op=${r.id} data-state="done" data-brief=${r.brief ? "true" : null}>
    <span class="board-op__title"><b>${r.title}${about && ` · ${about}`}</b>
      ${r.alone && html`<span class="board-chip" data-by-itself="true">by itself</span>`}
      <span class="ok-tone-muted">${r.brief ? `kept ${dayWords(r.done_at || r.at)} ${hhmm(r.done_at || r.at)}` : hhmm(r.done_at || r.at)}</span>
      ${part && html`<span class="ok-tone-muted">${part}</span>`}
      ${r.link && html`<button class="board-link" title="Opens it in your browser" onClick=${() => openLink(r.link)}>${r.link.replace(/^https?:\/\//, "")}</button>`}</span>
    ${(r.brief || (r.alone && !asking)) && html`<span class="board-card__acts">
      ${r.brief && html`<button class="ork-btn" aria-label=${`Open: ${r.title}${about && ` · ${about}`}`} title="Opens the kept brief, to read and copy"
        onClick=${() => openDialog("opcheck", { op: r.id })}>Open</button>`}
      ${r.alone && !asking && html`<button class="ork-btn" aria-label=${`Not right: ${r.title}`}
        title="The template learns from this and checks with you again" onClick=${() => setAsking(true)}>Not right</button>`}</span>`}
    ${asking && html`<span class="board-row">
      <input class="ork-field" value=${why} aria-label=${`What was not right: ${r.title}`} placeholder="What was not right? (optional, one line)" autofocus
        onInput=${(e) => setWhy(e.target.value)} onKeyDown=${(e) => { if (e.key === "Enter") send(); }} />
      <button class="ork-btn" aria-label=${`Teach it: ${r.title}`} onClick=${send}>Teach it</button>
      <button class="board-link" onClick=${() => setAsking(false)}>Cancel</button></span>`}
  </li>`;
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** *18 October* of an ISO time: the day a brief was kept. */
export function dayWords(iso) {
  const [y, m, d] = String(iso || "").slice(0, 10).split("-").map(Number);
  return y ? `${d} ${MONTHS[m - 1]}` : "";
}

/** *since 18 October · 12 done* (spec 42 §5): *since today* the day it went by itself; nothing after it while none is done. */
export function sinceWords(t) {
  const [y, m, d] = String(t.alone_since || "").split("-").map(Number);
  if (!y) return "";
  const day = new Date(y, m - 1, d), now = new Date();
  const when = day.toDateString() === now.toDateString() ? "today" : `${d} ${MONTHS[m - 1]}`;
  return `since ${when}${t.done_alone > 0 ? ` · ${t.done_alone} done` : ""}`;
}

/** *Checks with you: 2 of 3 clean checks, then it goes by itself*, with a pip for each check it asks for (spec 42 §5). */
export function waysWords(t) {
  const need = Math.max(1, t.trust_after || 1), clean = Math.min(t.clean || 0, need);
  return need === 1 ? "Checks with you: one clean check and it goes by itself" : `Checks with you: ${clean} of ${need} clean checks, then it goes by itself`;
}

/** What a template about people reads (spec 66 §2), with the nudge to say so to the team: on its form and in its row. */
export function ReadsLine({ reads }) {
  return html`<span class="shell-reads" role="note" aria-label="What it reads" data-reads>
    <span><span class="ok-font-label">Reads</span> ${reads}</span>
    <span class="ok-font-status ok-tone-muted" data-tell>Tell your team what it reads.</span></span>`;
}

/** A standing brief under its template's row (spec 66 §3): *Before the daily: weekdays 09:30*, Change, Stop. */
function StandingRow({ s }) {
  return html`<li class="board-op__standing" data-standing=${s.id}>
    <span class="board-op__title"><span>${s.words}</span>${s.skipped && html`<span class="ok-tone-muted" data-skipped>${s.skipped}</span>`}</span>
    <span class="board-card__acts">
      <button class="ork-btn" aria-label=${`Change: ${s.words}`} title="Changes its form, its days or its time" onClick=${() => openDialog("opform", { template: s.template, standing: s.id })}>Change</button>
      <button class="ork-btn" aria-label=${`Stop: ${s.words}`} title="It is no longer prepared on its own; what was kept stays"
        onClick=${() => run("ops.standing_stop", { id: s.id })}>Stop</button></span></li>`;
}

function TemplateRow({ t, standing = [] }) {
  const need = Math.max(1, t.trust_after || 1), clean = Math.min(t.clean || 0, need);
  return html`<li class="board-op board-op--template" data-template=${t.name} data-state=${t.state} data-brief=${t.brief ? "true" : null}>
    <span class="board-op__title"><b>${t.title}</b>
      <span class="board-state" data-template-state=${t.state}>${t.unusable || t.state_words}</span>
      ${t.does && html`<span class="ok-tone-muted" data-does>${t.does}</span>`}
      ${t.state === "checks" && !t.unusable && html`<span class="board-op__way ok-tone-muted" data-way="checks">
        <span class="ork-pips" aria-hidden="true">${Array.from({ length: need }, (_, i) => html`<i key=${i} class=${i < clean ? "d" : ""}></i>`)}</span> ${waysWords(t)}</span>`}
      ${t.state === "alone" && html`<span class="ok-tone-muted">${t.brief ? "goes by itself: prepared and kept without asking you"
        : `goes by itself: ${String(t.act_label || "").toLowerCase()} without asking you`}</span>
        ${t.alone_since && html`<span class="ok-tone-muted" data-since>${sinceWords(t)}</span>`}`}</span>
    ${t.people && t.reads && html`<${ReadsLine} reads=${t.reads} />`}
    <span class="board-card__acts">
      ${t.state === "alone" && html`<button class="ork-btn" aria-label=${`Check again: ${t.title}`}
        title="It checks with you again until you pass it" onClick=${() => run("ops.trust_reset", { template: t.name })}>Check again</button>`}
      <button class="ork-btn" aria-label=${`Rules: ${t.title}`} onClick=${() => openDialog("oprules", { template: t.name })}>Rules</button>
      ${t.forget && html`<button class="ork-btn danger" aria-label=${`Forget: ${t.title}`} aria-haspopup="dialog"
        title="Removes everything kept about one of them, by the name you give: it asks first" onClick=${() => openDialog("opforget", { template: t.name })}>Forget…</button>`}</span>
    ${standing.length > 0 && html`<ul class="board-op__standings" aria-label=${`Standing: ${t.title}`}>${standing.map((s) => html`<${StandingRow} key=${s.id} s=${s} />`)}</ul>`}
    ${t.proposal && html`<${RulesProposal} template=${t.name} title=${t.title} lines=${t.proposal.lines || []} why=${t.proposal.why || ""} />`}
  </li>`;
}

export function Operations({ withNew = false }) {
  const o = useOps();
  if (!o) return html`<p class="ok-tone-muted">Opening Operations…</p>`;
  const by = Object.fromEntries(o.templates.map((t) => [t.name, t]));
  const runs = o.runs;
  const check = runs.filter((r) => r.state === "check"), going = runs.filter((r) => RUNNING.includes(r.state)),
    failed = runs.filter((r) => r.state === "failed"), done = runs.filter((r) => r.state === "done").reverse();
  return html`<div class="board-ops" aria-label="Operations">
    <h3 class="board-sub kit-band">Operations ${withNew && html`<${NewMenu} />`}
      <button class="ork-btn board-ops__gear" aria-label="Operations settings" aria-haspopup="dialog" onClick=${() => openDialog("opsettings")}><${Icon} name="sliders" /></button></h3>
    <section class="board-ops__sec" aria-label="At your check">
      <h4 class="board-sub">At your check ${check.length > 0 && html`<span class="board-count kit-well">${check.length}</span>`}</h4>
      ${check.length ? html`<ul class="board-list">${check.map((r) => html`<${CheckRow} key=${r.id} r=${r} t=${by[r.template]} />`)}</ul>`
        : html`<p class="ok-tone-muted">Nothing waits at your check.</p>`}</section>
    ${going.length > 0 && html`<section class="board-ops__sec" aria-label="Running"><h4 class="board-sub">Running</h4>
      <ul class="board-list">${going.map((r) => html`<${RunningRow} key=${r.id} r=${r} />`)}</ul></section>`}
    ${failed.length > 0 && html`<section class="board-ops__sec" aria-label="Failed"><h4 class="board-sub">Failed</h4>
      <ul class="board-list">${failed.map((r) => html`<${FailedRow} key=${r.id} r=${r} />`)}</ul></section>`}
    <details class="board-done" aria-label="Done"><summary>Done (${done.length})</summary>
      ${done.length ? html`<ul class="board-list">${done.map((r) => html`<${DoneRow} key=${r.id} r=${r} t=${by[r.template]} />`)}</ul>`
        : html`<p class="ok-tone-muted">Nothing done yet.</p>`}</details>
    <details class="board-done" aria-label="Templates"><summary>Templates (${o.templates.length})</summary>
      <ul class="board-list">${o.templates.map((t) => html`<${TemplateRow} key=${t.name} t=${t} standing=${(o.standing || []).filter((s) => s.template === t.name)} />`)}</ul></details>
  </div>`;
}
