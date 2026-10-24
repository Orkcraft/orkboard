// An opened idea (29a §7), as the v1 shell's preview shows it (docs/specs/33-v1-shell.md §6): its sections as blocks (each
// its own colour role and icon, the thesis bold, the text folded), the question box, the talk, and the actions by state —
// Take it to work · Start · task states with Stop · Start again. `PlanView` is the same idea's plan, scrolled to a to-do. The talk names the party's leader, and a spec whose plan-making
// sections changed since the plan says so (docs/specs/62-spec-after-start.md §5, §6): `ChangedLine` under the sections, **The change** over the plan while the leader's plan change waits.
// The goal's route (spec 68 §7.1, arena/route.js) stands at the top of its screen.
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Who, Icon } from "../orkui.js";
import { toast } from "../link.js";
import { stateWords, board, PRIORITY_WORDS, holdWords } from "./store.js";
import { Stages } from "./stages.js";
import { act as run, showTask, showIdea, closePreview, roles, mapData } from "../shell/store.js";
import { missingWords } from "../arena/types.js";
import { changeGem, changeToast } from "../arena/arenawords.js";
import { ErrorLine } from "../shell/errors.js";
import { pctOf, pctRange } from "../spend.js";
import { PointedAt } from "../shell/lens.js";
import { RouteLine } from "../arena/route.js";

// Section → [colour role, line icon, kit icon]. The role is a design-system token in board.css (`[data-sec]`); the line
// icon (16px) is Office's, the kit's pixel icon (tools/ui_kit.py) Camp's.
const SECTIONS = {
  Gist: ["info", "M3 2.5h7l3 3v8H3zM5.5 8h5M5.5 10.5h5", "gist"],
  "Done when": ["ok", "M3 8.5l3.2 3.2L13 4.8", "in"],
  "Depends on": ["muted", "M2 8h5M9 8h5M7 5.5 9.5 8 7 10.5", "stages"],
  Why: ["accent", "M8 1.5a4.5 4.5 0 0 0-2 8.5v1.5h4V10A4.5 4.5 0 0 0 8 1.5zM6.5 14h3", "why"],
  In: ["ok", "M3 8.5l3.2 3.2L13 4.8", "in"],
  Out: ["muted", "M4 4l8 8M12 4l-8 8", "out"],
  Risks: ["fire", "M8 2 14.5 13.5h-13zM8 6.5v3.5M8 11.8v.4", "risk"],
  "Open questions": ["wait", "M6 6a2 2 0 1 1 2.8 1.8c-.5.3-.8.7-.8 1.2M8 11.8v.4", "ask"],
  Estimate: ["accent", "M8 14a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM8 4.5V8l2.5 1.5", "estimate"],
  Stages: ["info", "M2 4h4v3H2zM10 9h4v3h-4zM6 5.5h2.5V10.5H10", "stages"],
  Decisions: ["ok", "M3 2v12M3 3h9l-2 2.5L12 8H3", "decide"],
};
const KIT_ICONS = "/ds/sprites/v4/ui/icons/";
const camp = () => document.documentElement.dataset.look === "camp";    // the kit's icon only there: Office asks for no sprite

const usd = (n) => (n < 10 ? n.toFixed(2).replace(/0$/, "") : String(Math.round(n)));
export const price = (e) => (e ? `~${pctRange(e.usd_low, e.usd_high) || `$${usd(e.usd_low)}–${usd(e.usd_high)}`}` : "");

/** The leader of the party a goal belongs to (`track`: its slug in the Map), by name; "" when the Taskmaster leads or the Map does not know it (yet). `say()` does not swap a name. */
const leaderOf = (track) => {
  const lead = (mapData.value?.goals || []).find((g) => g.slug === track)?.leader;
  return lead?.name && lead.slug !== "taskmaster" ? lead.name : "";
};
const inText = (lead) => lead || "the Taskmaster";                    // in a sentence …
const atStart = (lead) => lead || "The Taskmaster";                  // … and at a sentence's start
/** *Gist, Done when and Out*. */
const andList = (names) => (names.length < 2 ? names.join("") : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`);

function Block({ s, onAsk, asked, slug, plan }) {
  const [role, d, icon] = SECTIONS[s.name] || ["muted", "M3 8h10", "gist"];
  const [editing, setEditing] = useState(null);
  const save = async () => { await run("ideas.edit", { slug, section: s.name, text: editing }); setEditing(null); };
  return html`<details class=${cls("board-sec kit-well", { "is-asked": asked })} data-sec=${role} data-name=${s.name} open=${s.name === "Gist"}>
    <summary><svg class="board-sec__icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d=${d} /></svg>
      ${camp() && html`<span class="board-sec__mark" aria-hidden="true"><img alt="" width="24" height="24" src=${`${KIT_ICONS}${icon}.png`}
        srcset=${`${KIT_ICONS}${icon}.png 1x, ${KIT_ICONS}${icon}@2x.png 2x`} /></span>`}
      <span class="board-sec__name">${s.name}</span>
      <b class="board-sec__thesis">${s.thesis}</b></summary>
    ${editing === null ? html`<div class="board-sec__body">${s.name === "Stages" ? html`<${Stages} text=${s.text} plan=${plan} slug=${slug} />` : html`<p class="board-sec__text">${s.text}</p>`}
        <div class="board-row"><button class="ork-btn" onClick=${() => onAsk(s.name)}>Ask about ${s.name}</button>
          <button class="ork-btn" onClick=${() => setEditing(s.text)}>Edit</button></div></div>`
      : html`<div class="board-sec__body"><textarea class="ork-field" rows="6" value=${editing} aria-label=${`Text of ${s.name}`}
          onInput=${(e) => setEditing(e.target.value)}></textarea>
        <div class="board-row"><button class="ork-btn primary" onClick=${save}>Keep it</button>
          <button class="ork-btn" onClick=${() => setEditing(null)}>Cancel</button></div></div>`}
  </details>`;
}

function Say({ p, section, setSection, lead }) {
  const [text, setText] = useState("");
  const send = async () => {
    const t = text.trim();
    if (!t) return;
    setText("");
    await run("ideas.say", { slug: p.slug, text: t, ...(section ? { section } : {}) });
  };
  return html`<div class="board-say">
    ${section && html`<span class="board-chip">About ${section} <button class="board-link" aria-label="Ask about the whole goal"
      onClick=${() => setSection("")}>×</button></span>`}
    <textarea class="ork-field" rows="2" value=${text} aria-label=${`Ask or answer ${inText(lead)}`}
      placeholder=${section ? `About ${section}…` : `Ask or answer ${inText(lead)}…`} onInput=${(e) => setText(e.target.value)}
      onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } }}></textarea>
    <div class="board-row"><button class="ork-btn" disabled=${!text.trim() || p.busy} onClick=${send}>Ask</button>
      ${p.busy && html`<span class="ok-tone-wait">${atStart(lead)} is answering…</span>`}</div>
  </div>`;
}

function Talk({ turns, lead }) {
  if (!turns.length) return "";
  return html`<ol class="board-talk" aria-label="The talk">${turns.slice(-8).map((t, n) => html`<li key=${n} data-who=${t.who}>
    <span class="board-talk__who">${t.who === "you" ? "You" : atStart(lead)}${t.section ? ` · ${t.section}` : ""}</span>
    <span>${t.text}</span></li>`)}</ol>`;
}

const TASK_WORDS = { waiting: "waiting", ready: "ready", running: "working", testing: "testing", review: "at Review", merged: "merged",
  failed: "failed", held: "held" };

function Tasks({ plan, working }) {
  return html`<ul class="board-tasks">${plan.tasks.map((k) => html`<li key=${k.id} data-state=${k.state}>
    <span class="board-task__state" data-state=${k.state}>${TASK_WORDS[k.state] || k.state}</span>
    <button class="board-link board-task__title" onClick=${() => showTask(plan.idea, k.id)}><b>${k.title}</b></button>
    ${k.tag && html`<span class="board-chip board-task__tag">${k.tag}</span>`}
    ${k.head ? html`<${Who} head=${k.head} small />` : html`<span class="board-chip">${k.tier}</span>`}
    ${k.after?.length ? html`<span class="ok-tone-muted">after ${k.after.join(", ")}</span>` : ""}
    ${k.commit && html`<code class="board-commit" title=${k.branch}>${k.commit.slice(0, 8)}</code>`}
    ${plan.passed_by === "auto" && !["waiting", "ready"].includes(k.state) && html`<span class="ok-tone-muted">by itself</span>`}
    ${k.state === "held" && k.note && html`<span class="ok-tone-wait">${holdWords(k.note, k.waits_title || board.value?.ideas.find((i) => k.note.endsWith(` · ${i.slug}`))?.title)}</span>`}
    ${k.error && html`<span class="ok-tone-error">${k.error}</span>`}
    ${working && k.cost != null && html`<span class="ok-tone-muted">${pctOf(k.cost) || `$${usd(k.cost)}`}</span>`}
  </li>`)}</ul>`;
}

/** "tasks k2 and k3 wait for it": the tasks a to-do holds back. */
const CHECK_STATE = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", review: "at Review", held: "held", failed: "failed" };

/** A check the person may still skip: it applies, it has not run (no task yet, or its task waits). */
export const skippable = (c) => c.applies && !c.skipped && (!c.state || ["waiting", "ready", "held"].includes(c.state));
/** What skipping a check spares, in words ("" when its tier has no price yet). */
export const spares = (c) => { const usd = Number(roles.value?.tier_costs?.[c.tier]); return usd > 0 ? ` · spares ≈ ${pctOf(usd) || `$${usd.toFixed(2)}`}` : ""; };

/** The checks the goal's team holds this idea to (realm/idea_checks.py): passed, its task's state, why it does not apply, or
 *  skipped by the person; Skip spares a check that has not run (its task taken out of the plan), Take again before a plan. */
function Checks({ checks, slug, planned }) {
  if (!(checks || []).length) return null;
  const found = (c) => (c.found === 0 ? "clean" : `found ${c.found}: ${[c.fixed && `${c.fixed} fixed`, c.left && `${c.left} left`].filter(Boolean).join(", ")}`);
  const words = (c) => (c.skipped ? "skipped by you" : !c.applies ? `not needed: ${c.why}` : c.found != null ? found(c) : c.state === "passed" ? "passed" : CHECK_STATE[c.state] || c.state || "in the plan to come");
  return html`<div class="board-checks" role="list" aria-label="Checks"><span class="ok-font-label">Checks</span>
    ${checks.map((c) => html`<span key=${c.by} role="listitem" class=${cls("board-check", { "is-off": !c.applies || c.skipped, "is-passed": c.state === "passed" })}>
      <b>${c.state === "passed" && html`<${Icon} name="check" />`}${c.name}</b><small>${words(c)}</small>
      ${skippable(c) && html`<button class="board-link board-check__skip" aria-label=${`Skip the check: ${c.name}`} title=${`Skip it: its run is spared${spares(c)}`}
        onClick=${() => run("ideas.check_skip", { slug, by: c.by })}>Skip${spares(c)}</button>`}
      ${c.skipped && !planned && html`<button class="board-link board-check__skip" aria-label=${`Take the check again: ${c.name}`}
        onClick=${() => run("ideas.check_skip", { slug, by: c.by, skip: false })}>Take again</button>`}</span>`)}</div>`;
}

export function unblocks(todo) {
  const ids = todo.for || [];
  if (!ids.length) return "";
  const list = ids.length === 1 ? ids[0] : `${ids.slice(0, -1).join(", ")} and ${ids[ids.length - 1]}`;
  return `${ids.length === 1 ? "task" : "tasks"} ${list} ${ids.length === 1 ? "waits" : "wait"} for it`;
}

function Plan({ plan, todo = "" }) {
  const e = plan.estimate;
  return html`<div class="board-plan kit-well"><h3 class="board-sub kit-legend">The plan ${e ? html`<span class="ok-tone-muted">${e.tasks} tasks · ${price(e)}</span>` : ""}</h3>
    <${Tasks} plan=${plan} />
    ${plan.todos?.length ? html`<h3 class="board-sub kit-legend">To-dos before it starts</h3><ul class="board-tasks">${plan.todos.map((t) =>
      html`<li key=${t.id} data-todo=${t.id} class=${cls("board-plan__todo", { "is-target": t.id === todo })}
        ref=${(el) => { if (el && t.id === todo) el.scrollIntoView({ block: "center" }); }}>
        <b>${t.title}</b><span class="board-chip kit-well">${t.kind}</span><span class="ok-tone-muted">${t.why}</span>
        ${t.id === todo && unblocks(t) && html`<span class="board-plan__line">${unblocks(t)}</span>`}</li>`)}</ul>` : ""}
  </div>`;
}

function Actions({ p, lead }) {
  const s = p.state, plan = p.plan, slug = p.slug;
  const e = plan?.estimate;
  if (s === "reading" || s === "planning") return html`<div class="board-row"><p class="ok-tone-wait" role="status">${atStart(lead)} is ${s === "reading" ? "drafting" : "planning"}…</p>
    <button class="ork-btn danger" onClick=${() => run("ideas.read_stop", { slug })}>Stop</button></div>`;
  if (s === "raw") return html`<div class="board-row">${!p.state_error && html`<p class="ok-tone-muted">New: ${inText(lead)} drafts it tonight, or when you press Process now.</p>`}
    <button class="ork-btn" onClick=${() => run("ideas.queue", { slug, queue: "now" })}>${p.state_error ? "Try again" : "Process now"}</button></div>`;
  return html`<div class="board-actions">
    ${(s === "ready" || s === "asks") && html`<button class="ork-btn primary" onClick=${() => run("ideas.plan", { slug })}>Take it to work</button>`}
    ${plan && html`<${Plan} plan=${plan} />`}
    ${s === "plan" && e && html`<button class="ork-btn primary" onClick=${() => run("ideas.start", { slug })}>Start · ${e.tasks} tasks · ${price(e)}</button>`}
    ${s === "working" && html`<button class="ork-btn danger" onClick=${() => run("ideas.stop", { slug })}>Stop</button>`}
    ${s === "failed" && html`<${ErrorLine} text=${plan?.tasks.find((k) => k.error)?.error || "It stopped and needs you."} />
      <button class="ork-btn primary" onClick=${() => run("ideas.start", { slug })}>Start again</button>`}
  </div>`;
}

/** The plan-making sections written since the plan (spec 62 §6.1), under the sections, with the press that makes the plan again: **Re-plan** before the start, **Re-plan what is left** after it (the
 *  leader then proposes a plan change, which waits in the hand; the press says *again* while one waits). A model call each press, so never by itself. Nothing for a goal that is done. */
function ChangedLine({ p, lead }) {
  const names = p.changed || [];
  if (!names.length || p.state === "done") return null;
  const after = !!p.passed, working = after && !!p.revising, waits = after && !!p.change, list = andList(names);
  const words = !after ? `${list} changed since the plan.` : working ? `${atStart(lead)} re-plans what is left…`
    : waits ? `${atStart(lead)} proposed a plan change: it waits for you below.` : `${list} changed since the work started: the tasks not started may change.`;
  return html`<div class="board-row board-changed" data-passed=${String(after)}>
    <p class=${working ? "ok-tone-wait" : "ok-tone-muted"} role="status">${words}</p>
    <button class="ork-btn" disabled=${!!p.busy || working} onClick=${() => run(after ? "ideas.revise" : "ideas.plan", { slug: p.slug })}>${!after ? "Re-plan" : waits ? "Re-plan what is left again" : "Re-plan what is left"}</button>
  </div>`;
}

const CHANGE_ROWS = { add: ["+", "added"], change: ["~", "changed"], drop: ["−", "dropped"] };

/** **The change** (spec 62 §6.4), over the plan while the leader's plan change waits: why, its price, the tasks it adds, changes and drops (a dropped one muted and struck) and the two presses. */
function Change({ p }) {
  const c = p.change, [busy, setBusy] = useState(false);
  if (!c) return null;
  const answer = async (take) => {
    setBusy(true);
    const got = await run("ideas.revise_answer", { slug: p.slug, take });
    setBusy(false);
    if (got) toast(changeToast(got));
  };
  const gem = changeGem(c);
  return html`<div class="board-plan shell-change kit-well" role="group" aria-label="The change">
    <h3 class="board-sub kit-legend">The change ${gem && html`<span class="ok-tone-muted" title="At API prices, not your bill">${gem}</span>`}</h3>
    ${c.why && html`<p class="shell-change__why">${c.why}</p>`}
    ${c.rows.length > 0 && html`<ul class="board-tasks shell-change__rows">${c.rows.map((r, i) => html`<li key=${i} data-op=${r.op}>
      <span class="shell-change__op" role="img" aria-label=${CHANGE_ROWS[r.op][1]}>${CHANGE_ROWS[r.op][0]}</span><span class="shell-change__title">${r.title}</span></li>`)}</ul>`}
    <div class="board-row"><button class="ork-btn primary" disabled=${busy} onClick=${() => answer(true)}>Take the new plan</button>
      <button class="ork-btn" disabled=${busy} onClick=${() => answer(false)}>Keep the plan</button></div>
  </div>`;
}

/** The goal's plan with the to-do it was opened from highlighted and said what it unblocks; Start stays here. A plan that gives work to no one of the party says
 *  so under it (docs/specs/52-goal-types.md §4.4). A plan change that waits is over it. */
export function PlanView({ p, todo }) {
  const plan = p.plan, e = plan?.estimate;
  if (!plan) return html`<p class="ok-tone-muted">This goal has no plan yet.</p>`;
  return html`<div class="board-actions">
    <${Change} p=${p} />
    <${Plan} plan=${plan} todo=${todo} />
    ${(plan.missing || []).length > 0 && html`<p class="ok-font-status ok-tone-muted board-missing">${missingWords(plan.missing)}</p>`}
    ${p.state === "plan" && e && html`<button class="ork-btn primary" onClick=${() => run("ideas.start", { slug: p.slug })}>Start · ${e.tasks} tasks · ${price(e)}</button>`}
    <button class="board-link" onClick=${() => showIdea(p.slug)}>Open the spec</button>
  </div>`;
}

export function IdeaView({ p }) {
  const [section, setSection] = useState("");
  const [sure, setSure] = useState(false);
  const row = board.value?.ideas.find((i) => i.slug === p.slug), lead = leaderOf(p.track);
  const drop = async () => { await run("ideas.drop", { slug: p.slug }); closePreview(); };
  return html`<div class="board-ideaview">
    <${RouteLine} steps=${p.route} goal=${p.slug} />
    <div class="board-bar">
      <span class="board-state" data-state=${p.state}>${stateWords({ state: p.state, progress: planProgress(p.plan) })}</span>
      ${p.size && html`<span class="board-size kit-well">${p.size}</span>`}
      ${row?.risk && html`<span class="board-chip" title=${(row.risk_triggers || []).join(", ")}>Risk: ${row.risk[0].toUpperCase() + row.risk.slice(1)}</span>`}
      ${row?.priority && html`<label class="board-inline"><span class="ok-font-status ok-tone-muted">Priority</span>
        <select class="ork-field" aria-label="Priority of this goal" value=${row.priority}
          onChange=${(e) => run("ideas.edit", { slug: p.slug, priority: e.target.value })}>
          ${Object.entries(PRIORITY_WORDS).map(([id, name]) => html`<option key=${id} value=${id}>${name}</option>`)}</select></label>`}</div>
    ${p.state_error && !["reading", "planning", "failed"].includes(p.state) && html`<${ErrorLine} text=${p.state_error} />`}
    <${PointedAt} lens=${p.lens} />
    <${Checks} checks=${p.checks} slug=${p.slug} planned=${!!p.plan} />
    <${Actions} p=${p} lead=${lead} />
    <div class="board-secs">${p.sections.map((s) => html`<${Block} key=${s.name} s=${s} slug=${p.slug} plan=${p.plan} asked=${section === s.name} onAsk=${setSection} />`)}</div>
    <${ChangedLine} p=${p} lead=${lead} />
    <${Say} p=${p} section=${section} setSection=${setSection} lead=${lead} />
    <${Talk} turns=${p.talk || []} lead=${lead} />
    <div class="board-row">${sure ? html`<span>Drop this goal and its page?</span>
        <button class="ork-btn danger" onClick=${drop}>Delete it</button><button class="ork-btn" onClick=${() => setSure(false)}>Keep it</button>`
      : html`<button class="ork-btn danger" onClick=${() => setSure(true)}>Delete goal</button>`}</div>
  </div>`;
}

export function planProgress(plan) {
  return plan ? { done: plan.tasks.filter((k) => k.state === "merged").length, total: plan.tasks.length } : { done: 0, total: 0 };
}
