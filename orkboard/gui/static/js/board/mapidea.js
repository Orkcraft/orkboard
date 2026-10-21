// An idea on the Map (docs/specs/48-map-ideas.md §3, §4): a one-line row, or — at work or waiting for the person — expanded: the
// stage track, the party's lanes with the plan's waves as columns, a task's card in its agent's lane and wave, stacks of several, the
// members' questions in the leader's lane; the idea's card (mapcard.js) on its right. The alert is only on the agent the work stopped
// on (§6): a result waiting is *in Review* in muted ink. A view of `ideas.map`; its actions are the card's.
import { useEffect, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Icon, WhoHead } from "../orkui.js";
import { preview, showIdea, showTask, showResult, act as run } from "../shell/store.js";
import { skippable, spares } from "./idea.js";
import { nodeView, leftToDo } from "./maplayout.js";
import { STAGES, STAGE_WORDS, stageWords, memberWords, taskWords, lanesOf, columnsOf, stackOf, stageTasks } from "./mapstage.js";
import { useLeaving } from "./mapghost.js";
import { IdeaCard } from "./mapcard.js";

/** Who is on an idea now: the agent of its running task, else of its next task, else the goal's leader (it drafts and plans). */
export function stopHead(n, leader) {
  const left = n.tasks.filter(leftToDo);
  const t = left.find((x) => x.state === "running" || x.state === "testing") || left[0];
  return t?.head || leader?.head || null;
}

/** A timed wait (the night, the limits, the reserve) is a clock on the row. */
const timed = (w) => ["night", "limits", "reserve", "week"].includes(w?.kind);

/** "checks 1/2 passed: Reviewer: passed · …": the checks that apply to an idea. */
function checksWords(checks) {
  const on = (checks || []).filter((c) => c.applies);
  if (!on.length) return "";
  const passed = on.filter((c) => c.state === "passed").length;
  return `checks ${passed}/${on.length} passed`;
}

/** An idea in one line: the head of who is on it, its title, *<stage> · <state words>*, a mark. A click expands it (its title opens
 *  the idea's spec from there). */
export function Row({ n, titles, since, goal, onOpen, done = false }) {
  const v = nodeView(n, titles);
  const fresh = !!since && n.updated > since;
  const state = [v.needs && !v.words.includes(v.needs) ? `${v.words} · ${v.needs}` : v.words, v.wait,
    n.by_itself ? "by itself" : "", checksWords(n.checks), fresh ? "new" : ""].filter(Boolean).join(" · ");
  const head = stopHead(n, goal.leader);
  const words = done ? `${n.progress.total ? `${n.progress.done} of ${n.progress.total} tasks in dev · ` : ""}in dev · waits for main` : `${stageWords(n)} · ${state}`;
  return html`<li class=${cls("map-row", { "is-needs": !!v.needs && !done, "is-done": done, "is-wait": !!v.wait })} data-slug=${n.slug} data-stage=${n.stage}>
    <button type="button" class="map-row__btn" aria-expanded="false" title=${`${n.title} · ${words}`} aria-label=${`${n.title}: ${words}`}
      data-state=${n.state} data-needs=${n.needs_you || ""} onClick=${() => (done ? showIdea(n.slug, { via: "map" }) : onOpen(n.slug))}>
      ${done ? html`<span class="map-row__tick" aria-hidden="true"><${Icon} name="check" /></span>` : head ? html`<${WhoHead} head=${head} small />` : html`<span class="trail-chip__nohead" aria-hidden="true"></span>`}
      <b class="map-row__title">${n.short || n.title}</b>
      <span class="map-row__words ok-tone-muted">${words}</span>
      ${v.needs && !done ? html`<span class="trail-chip__mark is-gate" aria-hidden="true"><${Icon} name="warning-diamond" /></span>`
        : v.spin ? html`<span class="shell-spin trail-chip__mark" aria-hidden="true">↻</span>`
          : timed(n.waits) && n.state !== "done" ? html`<span class="trail-chip__mark" aria-hidden="true"><${Icon} name="clock" /></span>` : ""}
    </button></li>`;
}

/** The stage track: Planning — Implementation — Checking, the current one underlined, the past ones ✓. */
function Track({ n }) {
  const at = STAGES.indexOf(n.stage);
  return html`<ol class="map-track" aria-label=${`Stage: ${stageWords(n)}`}>${STAGES.map((s, i) => html`<li key=${s} class=${cls("map-track__stage", { "is-now": i === at, "is-past": i < at })}
    aria-current=${i === at ? "step" : undefined}>${STAGE_WORDS[s]}${i < at ? html`<span aria-hidden="true"> ✓</span><span class="map-sr"> done</span>` : ""}</li>`)}</ol>`;
}

/** One task's card in its lane and wave. A check not run yet can be skipped from it (× spares its run). */
function TaskCard({ n, t, leaving = false }) {
  const said = `${t.title} · ${t.tag ? `${t.tag} · ` : ""}${taskWords(t)}`;
  const check = (n.checks || []).find((c) => c.task === t.id);
  const open = () => (t.state === "review" ? showResult(n.slug, t.id, { via: "map" }) : showTask(n.slug, t.id, { via: "map" }));
  return html`<span class=${cls("map-taskcard-pair", { "map-leaving": leaving })} aria-hidden=${leaving ? "true" : undefined}>
    <button type="button" class=${cls("map-taskcard", { "is-wait": t.state === "waiting" || t.state === "held" || t.state === "ready", "is-failed": t.state === "failed", "is-review": t.state === "review" })}
      data-task=${t.id} data-state=${t.state} data-wave=${t.wave} title=${said} aria-label=${said} tabindex=${leaving ? -1 : undefined} onClick=${open}>
      <b class="map-taskcard__title">${t.short || t.title}</b>
      <span class="map-taskcard__words">${leaving ? "in dev" : taskWords(t)}</span></button>
    ${!leaving && check && skippable(check) && html`<button type="button" class="map-task__skip" aria-label=${`Skip the check: ${check.name}`}
      title=${`Skip the check: its run is spared${spares(check)}`} onClick=${() => run("ideas.check_skip", { slug: n.slug, by: check.by })}><${Icon} name="close" /></button>`}
  </span>`;
}

/** Several tasks of one agent in one wave: one card, the next one's edge behind it, a count; hover, focus or click opens them as a list. */
function Stack({ n, tasks }) {
  const [open, setOpen] = useState(false);
  const top = tasks[0];
  useEffect(() => {                                           // Esc closes the list, and only the list, wherever the focus is
    if (!open) return undefined;
    const esc = (e) => { if (e.key === "Escape") { e.stopPropagation(); setOpen(false); } };
    document.addEventListener("keydown", esc, true);
    return () => document.removeEventListener("keydown", esc, true);
  }, [open]);
  const shut = (e) => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); };
  return html`<span class="map-stack" data-count=${tasks.length} onMouseEnter=${() => setOpen(true)} onMouseLeave=${() => setOpen(false)}
      onFocusIn=${() => setOpen(true)} onFocusOut=${shut}>
    <span class="map-stack__edge" aria-hidden="true"></span>
    <button type="button" class=${cls("map-taskcard", { "is-failed": tasks.some((t) => t.state === "failed") })} aria-haspopup="true" aria-expanded=${open}
      title=${`${tasks.length} tasks: ${tasks.map((t) => `${t.title}, ${taskWords(t)}`).join("; ")}`} aria-label=${`${tasks.length} tasks of ${top.by.name} in wave ${top.wave}`}
      onClick=${() => setOpen(!open)}>
      <b class="map-taskcard__title">${top.short || top.title}</b>
      <span class="map-taskcard__words">${taskWords(top)}</span></button>
    <span class="map-stack__count" aria-hidden="true">${tasks.length}</span>
    ${open && html`<ul class="map-stack__list" aria-label=${`${top.by.name} · wave ${top.wave} · ${tasks.length}`}>${tasks.map((t) => html`<li key=${t.id}>
      <button type="button" class="map-stack__item" data-task=${t.id} data-state=${t.state}
        onClick=${() => (t.state === "review" ? showResult(n.slug, t.id, { via: "map" }) : showTask(n.slug, t.id, { via: "map" }))}>
        <b>${t.short || t.title}</b><span class="ok-tone-muted">${taskWords(t)}</span></button></li>`)}</ul>`}
  </span>`;
}

/** A lane's head: the member's head, name and state in words; the alert only when the work stopped on it. */
function LaneHead({ lane }) {
  return html`<div class=${cls("map-lane__head", { "is-needs": lane.state === "needs" })} role="rowheader" data-agent=${lane.slug} data-state=${lane.state}>
    <${WhoHead} head=${lane.head} small /><b>${lane.name}</b>
    <span class="map-lane__state">${memberWords(lane)}${lane.state === "work" ? " ↻" : ""}</span>
    ${lane.state === "needs" && html`<span class="trail-chip__mark is-gate" aria-hidden="true"><${Icon} name="warning-diamond" /></span>`}</div>`;
}

/** Planning: one column, *Plan*: the plan's card and the members' questions, each wearing the head of who asks. */
function PlanningLane({ n, lane }) {
  const tasks = n.tasks, checks = tasks.filter((t) => t.band === "check").length, builds = tasks.length - checks;
  const plan = tasks.length ? `${builds} task${builds === 1 ? "" : "s"}${checks ? `, ${checks} check${checks === 1 ? "" : "s"}` : ""}` : "";
  return html`<div class="map-lane" role="row" aria-label=${lane.name}><${LaneHead} lane=${lane} />
    <div class="map-lane__cells" role="cell">
      ${(n.asked || []).map((q, i) => html`<button type="button" key=${i} class="map-taskcard is-needs map-ask" data-ask=${i} title=${q.ask}
        aria-label=${`${q.by?.name || lane.name} asks: ${q.ask}`} onClick=${() => showIdea(n.slug, { via: "map" })}>
        ${q.by?.head && html`<${WhoHead} head=${q.by.head} small />`}<span class="map-taskcard__title">${q.ask}</span><span class="map-taskcard__words">asks you</span></button>`)}
      ${plan && html`<button type="button" class=${cls("map-taskcard map-plan", { "is-needs": n.needs_you === "plan" })} aria-label=${`The plan of ${n.title}: ${plan}`}
        onClick=${() => showIdea(n.slug, { via: "map" })}><b class="map-taskcard__title">${plan}</b>
        <span class="map-taskcard__words">${n.needs_you === "plan" ? "plan ready" : "planned"}</span></button>`}
      ${!plan && !(n.asked || []).length && html`<span class="ok-tone-muted map-lane__empty">${memberWords(lane) || "free"}</span>`}</div></div>`;
}

/** The lanes and columns of the stage. */
function Field({ n, lanes }) {
  const tasks = stageTasks(n);
  const gone = useLeaving(tasks, (t) => t.id, (t) => n.tasks.find((x) => x.id === t.id)?.state === "merged");     // seen in the field, merged now
  const ghosts = gone.filter((t) => !tasks.some((x) => x.id === t.id));
  const waves = columnsOf([...tasks, ...ghosts]);
  return html`<div class="map-field" role="table" aria-label=${`${stageWords(n)}: who does what`}>
    <div class="map-field__cols" role="row"><span class="map-field__corner" role="columnheader">${n.stage === "checking" ? "Checkers" : "Builders"}</span>
      ${waves.map((w) => html`<span key=${w} class="map-field__col" role="columnheader">Wave ${w}</span>`)}</div>
    ${lanes.map((lane) => html`<div key=${lane.slug} class="map-lane" role="row" aria-label=${lane.name}><${LaneHead} lane=${lane} />
      ${waves.map((w) => {
        const mine = stackOf(lane, w), leaving = ghosts.filter((t) => t.by.slug === lane.slug && t.wave === w);
        return html`<div key=${w} class="map-lane__cell" role="cell" data-wave=${w}>
          ${mine.length > 1 ? html`<${Stack} n=${n} tasks=${mine} />` : mine.map((t) => html`<${TaskCard} key=${t.id} n=${n} t=${t} />`)}
          ${leaving.map((t) => html`<${TaskCard} key=${"gone" + t.id} n=${n} t=${t} leaving />`)}</div>`;
      })}</div>`)}
  </div>`;
}

/** An idea not planned yet: the checks its plan will hold, each with × to leave it out (its run spared) and + to take it again. */
function Checks({ n, team }) {
  if (n.tasks.length || n.state === "done") return null;
  const mine = (n.checks || []).filter((c) => c.applies && !c.task);
  if (!mine.length) return null;
  const head = (c) => (team || []).find((t) => t.slug === c.by)?.head;
  return html`<div class="map-checks" role="list" aria-label=${`Checks of ${n.title}`}>${mine.map((c) => html`<span key=${c.by} role="listitem"
      class=${cls("map-task-pair is-check", { "is-skipped": c.skipped })}>
    <span class="map-task" title=${c.skipped ? `${c.name}: skipped by you` : `${c.name}: in the plan to come${spares(c)}`}>${head(c) && html`<${WhoHead} head=${head(c)} small />`}<span class="map-task__title">${c.name}</span></span>
    ${c.skipped ? html`<button type="button" class="map-task__skip" aria-label=${`Take the check again: ${c.name}`} title="Take it again: the plan holds it"
        onClick=${() => run("ideas.check_skip", { slug: n.slug, by: c.by, skip: false })}><${Icon} name="plus" /></button>`
      : html`<button type="button" class="map-task__skip" aria-label=${`Skip the check: ${c.name}`} title=${`Leave it out of the plan: its run is spared${spares(c)}`}
        onClick=${() => run("ideas.check_skip", { slug: n.slug, by: c.by })}><${Icon} name="close" /></button>`}</span>`)}</div>`;
}

/** An expanded idea: its stage track and lanes on the left, its card on the right; a click on the title folds it. */
export function Expanded({ n, goal, titles, onFold }) {
  const lanes = lanesOf(n, goal);
  return html`<li class=${cls("map-idea", { "is-on": preview.value?.kind === "idea" && preview.value.slug === n.slug })} data-slug=${n.slug} data-stage=${n.stage}>
    <section aria-label=${n.title} class="map-idea__body">
      <header class="map-idea__head"><button type="button" class="map-idea__fold" aria-expanded="true" onClick=${onFold}>${n.title}</button>
        <button type="button" class="board-link" onClick=${() => showIdea(n.slug, { via: "map" })}>Open</button></header>
      <${Track} n=${n} />
      ${n.stage === "planning" ? html`<div class="map-field map-field--plan" role="table" aria-label="Planning: who does what">
          <div class="map-field__cols" role="row"><span class="map-field__corner" role="columnheader">Leader</span><span class="map-field__col" role="columnheader">Plan</span></div>
          ${lanes.map((lane) => html`<${PlanningLane} key=${lane.slug} n=${n} lane=${lane} />`)}</div>
          <${Checks} n=${n} team=${goal.team} />`
        : html`<${Field} n=${n} lanes=${lanes} />`}
    </section>
    <${IdeaCard} n=${n} titles=${titles} />
  </li>`;
}
