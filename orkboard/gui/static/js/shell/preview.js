// The drawer's body (docs/specs/33-v1-shell.md §6, spec 39 §3, spec 49 §9): tabs, one per thing opened: an idea's spec (29a's
// sections view), an idea's plan (scrolled to a to-do, said what it unblocks), a task (its brief, state and log), a result's code
// (commits, then the files changed, each patch folded), a goal, a pick (its variants large, a note: shell/pickview.js), a document, a file, a diff,
// the gate's screen, Agents, Files. A result's actions stay pinned at its foot. A goal of Ideation is a pitch: its page's `pitch` shows its own screen (pitchview.js).
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Sign, Who } from "../orkui.js";
import { ErrorLine } from "./errors.js";
import { board, page } from "../board/store.js";
import { IdeaView, PlanView } from "../board/idea.js";
import { TASK_STATE } from "../board/maplayout.js";
import { preview, detail, review, goal, editing, active, goneWords, keepTab, setTabTitle, act, closePreview, showIdea, showResult, showGoal, refreshShell } from "./store.js";
import { TabStrip } from "./tabs.js";
import { ResultActions, Found, testsWords, changesWords, isRed } from "./review.js";
import { GoalView } from "./goalview.js";
import { File } from "./diffview.js";
import { FileView, FilesPane } from "./files.js";
import { GitDiffView } from "./gitpane.js";
import { AgentsPane } from "./agents.js";
import { GateView } from "../arena/gate.js";
import { rowOf } from "../arena/pickwords.js";
import { PickView } from "./pickview.js";
import { PitchView } from "./pitchview.js";
import { pctOf, pctShort } from "../spend.js";

/** A failed task's way on: run its idea's tasks again, or drop it (asked first). */
function FailedActions({ t }) {
  const [sure, setSure] = useState(false);
  const drop = async () => { const got = await act("ideas.drop_task", { slug: t.idea, task: t.id }); if (got?.ok) closePreview(); };
  return html`<div class="board-row">
    <button class="ork-btn primary" title="Its goal's tasks that are not merged or at Review run again" onClick=${() => act("ideas.start", { slug: t.idea })}>Start again</button>
    ${sure ? html`<span>Drop this task? Its worktree goes; its branch stays.</span>
      <button class="ork-btn danger" onClick=${drop}>Drop it</button><button class="ork-btn" onClick=${() => setSure(false)}>Keep it</button>`
      : html`<button class="shell-quiet" onClick=${() => setSure(true)}>Drop…</button>`}</div>`;
}

function Task({ d }) {
  const t = d?.task;
  const ref = useRef();
  const live = t && (t.state === "running" || t.state === "testing");
  useEffect(() => {                        // the log's tail is read again every 5 s while the task runs
    if (!live) return undefined;
    const id = setInterval(refreshShell, 5000);
    return () => clearInterval(id);
  }, [live]);
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [t?.log]);
  if (!t) return html`<p class="ok-tone-muted">Opening…</p>`;
  return html`<div class="shell-task">
    <dl class="shell-facts">
      <dt>State</dt><dd data-state=${t.state}>${TASK_STATE[t.state] || t.state}${t.note ? html` <span class="ok-tone-muted">${t.note}</span>` : ""}</dd>
      <dt>Goal</dt><dd><button class="board-link" onClick=${() => showIdea(t.idea)}>${t.idea_title}</button></dd>
      <dt>Tier</dt><dd>${t.head ? html`<${Who} head=${t.head} small />` : t.tier}</dd>
      <dt>Branch</dt><dd><code>${t.branch || "—"}</code></dd>
      <dt>Round</dt><dd>${t.round || 1}</dd>
      <dt>Spend</dt><dd>${t.cost != null ? (pctOf(t.cost) ? `≈${pctOf(t.cost)}` : `$${t.cost.toFixed(2)}`) : "—"}</dd>
    </dl>
    ${t.error && html`<${ErrorLine} text=${t.error} />`}
    ${t.state === "failed" && html`<${FailedActions} t=${t} />`}
    <h3 class="board-sub">Brief</h3><p class="shell-brief">${t.brief}</p>
    ${t.state === "review" && html`<p><button class="ork-btn primary" onClick=${() => showResult(t.idea, t.id)}>Open the result</button></p>`}
    ${live && html`<p><button class="ork-btn danger" onClick=${() => act("ideas.stop_task", { slug: t.idea, task: t.id })}>Stop</button></p>`}
    <h3 class="board-sub">Log</h3>
    <pre class="shell-log" ref=${ref} aria-label="Log">${t.log || "Nothing logged yet."}</pre>
  </div>`;
}

const STAGE_WORDS = [["goal", "party"], ["spec", "spec"], ["plan", "plan"], ["work", "work"], ["rework", "rework"], ["dropped", "dropped"]];

/** The idea's money so far, by stage (spec 36 §5): stages at 0 left out, — when nothing is priced. */
export function spendWords(s) {
  if (!s || !s.stages) return "";
  if (s.usd == null) return "This goal so far: —";
  const parts = STAGE_WORDS.map(([k, w]) => [w, s.stages[k]?.usd]).filter(([, v]) => v).map(([w, v]) => `${w} ${pctShort(v) || v.toFixed(2)}`);
  const total = `≈${pctOf(s.usd) || `$${s.usd < 10 ? s.usd.toFixed(2) : Math.round(s.usd)}`}`;
  return `This goal so far: ${total}${parts.length ? ` — ${parts.join(" · ")}` : ""}`;
}

function Result({ d, p }) {
  const r = (review.value?.results || []).find((x) => x.idea === p.slug && x.task === p.task);
  const diff = d?.diff;
  const t = r && testsWords(r);
  return html`<div class="shell-result">
    <div class="shell-result__body">
      ${d?.spend && html`<p class="shell-spend ok-font-status ok-tone-muted" title="At API prices, not your bill">${spendWords(d.spend)}</p>`}
      ${r ? html`<dl class="shell-facts">
        <dt>Tests</dt><dd class=${`is-${t.tone}`}>${t.mark && html`<${Sign} name=${t.mark} /> `}${t.text}${t.names.length ? html` <span class="ok-tone-muted">${t.names.join(", ")}</span>` : ""}</dd>
        <dt>Changes</dt><dd>${changesWords(r.diff)}</dd>${r.round > 1 ? html`<dt>Round</dt><dd>${r.round}</dd>` : ""}</dl>
        ${r.conflict && html`<p class="ok-tone-error">⚠ ${r.conflict}</p>`}
        <${Found} r=${r} />
        ${isRed(r) && r.tests.tail && html`<details class="shell-file"><summary>What the tests said</summary><pre class="shell-log">${r.tests.tail}</pre></details>`}`
        : html`<p class="ok-tone-muted">This result is no longer waiting at Review.</p>`}
      ${!diff ? html`<p class="ok-tone-muted">Reading the code…</p>` : html`
        <h3 class="board-sub">Commits</h3>
        <ol class="shell-commits">${diff.commits.map((c) => html`<li key=${c.sha}><code>${c.sha}</code> ${c.subject}</li>`)}</ol>
        <h3 class="board-sub">Files changed (${diff.files.length})</h3>
        ${diff.files.map((f) => html`<${File} key=${f.path} f=${f} />`)}
        ${diff.truncated && html`<p class="ok-tone-muted">Some files are too large to show.</p>`}`}
    </div>
    ${r && html`<footer class="shell-result__foot"><${ResultActions} r=${r} pinned=${true} /></footer>`}
  </div>`;
}

function Doc({ d, p }) {
  return html`<div class="shell-doc"><p><button class="board-link" onClick=${() => showGoal(p.slug)}>← Back to the party</button></p>
    ${!d ? html`<p class="ok-tone-muted">Opening…</p>`
      : d.doc?.html ? html`<div class="shell-md" aria-label=${p.path} dangerouslySetInnerHTML=${{ __html: d.doc.html }}></div>${d.doc.truncated ? html`<p class="ok-tone-muted">Cut here: the document is longer.</p>` : ""}`
      : d.doc ? html`<pre class="shell-log shell-doc__text" aria-label=${p.path}>${d.doc.text}</pre>${d.doc.truncated ? html`<p class="ok-tone-muted">Cut here: the document is longer.</p>` : ""}`
      : html`<p class="ok-tone-muted">That document cannot be shown.</p>`}</div>`;
}

/** What a tab shows as its title, "" until its thing is read. */
function titleOf(p, d, pg) {
  if (p.kind === "task" || p.kind === "result") return d?.task?.title || "";
  if (p.kind === "goal") return goal.value?.title || "";
  if (p.kind === "pick") return rowOf(board.value?.needs_you, p.slug, p.task)?.title || "";
  if (p.kind === "doc" || p.kind === "file" || p.kind === "gitdiff") return p.path;
  if (p.kind === "gate") return "dev → main";
  if (p.kind === "agents") return "Agents";
  if (p.kind === "files") return "Files";
  return pg?.title || "";
}

/** The drawer's body for the active tab (the strip is above it). */
export function Preview() {
  const p = preview.value, pg = page.value, d = detail.value, id = active.value;
  const gone = p ? goneWords(p) : "";
  const title = p ? titleOf(p, d, pg) : "";
  const dirty = !!editing.value?.dirty;
  useEffect(() => { if (p && title && !gone) setTabTitle(id, title); }, [id, title, gone]);     // the strip names an inactive tab by the last title read
  useEffect(() => { if (p && dirty) keepTab(id); }, [id, dirty]);                                 // an edit in the passing tab keeps it
  return html`<section class="shell-preview" aria-label="Preview">
    <${TabStrip} />
    <div class=${cls("shell-preview__body", { "is-pane": p?.kind === "agents" })}>
      ${!p ? ""
        : gone ? html`<div class="shell-empty"><p>${gone}</p><p><button class="ork-btn" onClick=${() => closePreview()}>Close</button></p></div>`
        : p.kind === "idea" ? (pg ? (pg.pitch ? html`<${PitchView} pg=${pg} />` : html`<${IdeaView} p=${pg} />`) : html`<p class="ok-tone-muted">Opening…</p>`)
        : p.kind === "plan" ? (pg ? html`<${PlanView} p=${pg} todo=${p.todo} />` : html`<p class="ok-tone-muted">Opening…</p>`)
        : p.kind === "goal" ? html`<${GoalView} />`
        : p.kind === "pick" ? html`<${PickView} p=${p} />`
        : p.kind === "doc" ? html`<${Doc} d=${d} p=${p} />`
        : p.kind === "file" ? html`<${FileView} path=${p.path} />`
        : p.kind === "gitdiff" ? html`<${GitDiffView} path=${p.path} />`
        : p.kind === "gate" ? html`<${GateView} />`
        : p.kind === "agents" ? html`<${AgentsPane} />`
        : p.kind === "files" ? html`<${FilesPane} />`
        : p.kind === "task" ? html`<${Task} d=${d} />` : html`<${Result} d=${d} p=${p} />`}
    </div>
  </section>`;
}
