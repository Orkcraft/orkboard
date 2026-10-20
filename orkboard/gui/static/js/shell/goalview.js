// A goal in the preview (docs/specs/34-v1-round-2.md §7): Description, Summary (the Taskmaster's), Metrics (what is
// measured, the target, how it is counted), Links (a repository path or Wiki page opens in the preview; a web address in
// the browser), the Open questions with a box to answer — the same talk as an idea's, on the goal. Its party's leader speaks in it
// (the Taskmaster when none) and, when its ideas are done, accepts it against its metrics: the Verdict (realm/goal_verdict.py).
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { say, openLink } from "../link.js";
import { goal, act, showDoc, roles, logOpened } from "./store.js";
import { board, ask, layingOutWords } from "../board/store.js";
import { WhoHead } from "../orkui.js";
import { openDialog } from "./modals.js";
import { ErrorLine } from "./errors.js";
import { Questions } from "../board/ask.js";
import { SaveParty } from "./party.js";

export const GOAL_STATE = { reading: "the Taskmaster is reading", asks: "asks you", ready: "ready", raw: "" };
const STATUS_TONE = { met: "ok-tone-ok", "not met": "ok-tone-error", unknown: "ok-tone-muted" };
/** Who leads a goal, as a sentence starts with it: its party's leader by name, else "The Taskmaster". */
const leaderThe = (g) => (g.leader?.slug && g.leader.slug !== "taskmaster" ? g.leader.name : say("The Taskmaster"));
const isUrl = (l) => /^[a-z][a-z0-9+.-]*:\/\//i.test(l);

export function GoalView() {
  const g = goal.value;
  if (!g) return html`<p class="ok-tone-muted">Opening…</p>`;
  const lead = leaderThe(g), named = g.leader?.slug && g.leader.slug !== "taskmaster";
  const laying = layingOutWords(g);
  const words = laying || (g.state === "reading" && named ? `${lead} is reading` : GOAL_STATE[g.state]);
  return html`<div class="board-ideaview shell-goal" data-state=${g.state}>
    <div class="board-bar"><span class="board-state" data-state=${g.state}>${say(words || "not read yet")}</span>
      <span class="board-size kit-well">${({ high: "High", normal: "Normal", low: "Low" })[g.priority]}</span>
      ${g.deadline && html`<span class="ok-tone-muted">by ${g.deadline}</span>`}
      ${g.state === "ready" && !g.trail?.waiting && html`<button class="ork-btn" disabled=${!!g.trail?.busy} onClick=${() => act("ideas.trail", { goal: g.slug })}>Lay out ideas</button>`}
      <button class="ork-btn" onClick=${() => openDialog("goal", { slug: g.slug })}>Edit</button></div>
    ${g.state_error && g.state === "raw" && html`<${ErrorLine} text=${g.state_error} />`}
    <section class="shell-goal__sec" aria-label="Description"><h3 class="board-sub">Description</h3>
      <p class="shell-brief">${g.description || html`<span class="ok-tone-muted">No description yet.</span>`}</p></section>
    <${Verdict} g=${g} lead=${named ? lead : "the Taskmaster"} />
    ${((g.team || []).length > 0 || named) && html`<section class="shell-goal__sec" aria-label="Team"><h3 class="board-sub">Team</h3>
      <ul class="shell-goal__team">${named && html`<li key="lead">${g.leader.head && html`<${WhoHead} head=${g.leader.head} small />`} <b>${g.leader.name}</b>
        <span class="ok-tone-muted"> · leads: plans its ideas and accepts the goal</span></li>`}${(g.team || []).map((s) => {
        const r = (roles.value?.roles || []).find((x) => x.slug === s);
        const check = (roles.value?.library || []).find((a) => a.id === s)?.check;
        return html`<li key=${s}>${r?.head && html`<${WhoHead} head=${r.head} small />`} <b>${r?.name || s}</b>
          ${check && html` <span class="ok-tone-muted">· checks ${(g.every || []).includes(s) ? "every idea" : check.applies}</span>`}</li>`;
      })}</ul><${SaveParty} goal=${g} /></section>`}
    <section class="shell-goal__sec" aria-label="What the party did"><${PartyFold} slug=${g.slug} /></section>
    <section class="shell-goal__sec" aria-label="Summary"><h3 class="board-sub">Summary ${g.title_by === "keeper" && html`<span class="ok-tone-muted">· title by the Taskmaster</span>`}</h3>
      <p class="shell-brief">${g.summary || html`<span class="ok-tone-muted">${g.state === "reading" ? `${lead} is reading the goal…` : layingOutWords(g) || "Not written yet."}</span>`}</p></section>
    <section class="shell-goal__sec" aria-label="Metrics"><h3 class="board-sub">Metrics ${g.metrics_by === "keeper" && html`<span class="ok-tone-muted">· by the Taskmaster</span>`}</h3>
      ${g.metrics.length ? html`<table class="shell-metrics"><thead><tr><th>What is measured</th><th>Target</th><th>How it is counted</th></tr></thead>
        <tbody>${g.metrics.map((m) => html`<tr key=${m.name}><td>${m.name}</td><td>${m.target || "—"}</td><td>${m.how || html`<span class="ok-tone-muted">—</span>`}</td></tr>`)}</tbody></table>`
        : html`<p class="ok-tone-muted">No metric yet.</p>`}</section>
    <section class="shell-goal__sec" aria-label="Links"><h3 class="board-sub">Links</h3>
      ${g.links.length ? html`<ul class="shell-links">${g.links.map((l) => html`<li key=${l}>${isUrl(l)
        ? html`<a class="gui-link" href=${l} target="_blank" rel="noopener noreferrer" onClick=${(e) => { e.preventDefault(); openLink(l); }}>${l}</a>`
        : html`<button class="board-link" onClick=${() => showDoc(g.slug, l)}>${l}</button>`}</li>`)}</ul>`
        : html`<p class="ok-tone-muted">No link.</p>`}</section>
    <section class="shell-goal__sec" aria-label="Open questions"><h3 class="board-sub">Open questions</h3>
      ${g.questions.length ? html`<ul class="shell-links">${g.questions.map((q) => html`<li key=${q}>${q}</li>`)}</ul>`
        : html`<p class="ok-tone-muted">${g.state === "ready" ? `${lead} has no question.` : "No question yet."}</p>`}
      ${g.questions.length > 0 && html`<${Questions} key=${g.questions.join("|")} questions=${g.questions} busy=${g.busy}
        onSend=${(answers) => act("ideas.answer", { slug: g.slug, answers, goal: true })} />`}</section>
    ${g.talk?.length > 0 && html`<ol class="board-talk" aria-label="The talk">${g.talk.slice(-8).map((t, n) => html`<li key=${n} data-who=${t.who}>
      <span class="board-talk__who">${t.who === "you" ? "You" : lead}</span><span>${t.text}</span></li>`)}</ol>`}
  </div>`;
}

/** The goal's verdict: met or not, each metric's status and why, the next ideas (each added with a click); and the button
 * that asks the leader to accept the goal — once its ideas are all done, or again after a verdict. */
function Verdict({ g, lead }) {
  const mine = (board.value?.ideas || []).filter((i) => i.track === g.slug);
  const done = mine.length > 0 && mine.every((i) => i.state === "done");
  const v = g.verdict;
  if (!v && !done) return null;
  const Lead = lead.charAt(0).toUpperCase() + lead.slice(1);
  const accepting = g.busy && g.state !== "reading";
  const ask = html`<button type="button" class=${`ork-btn${v ? "" : " primary"}`} disabled=${accepting}
    onClick=${() => act("ideas.goal_accept", { slug: g.slug })}>${v ? `Ask ${lead} again` : `Ask ${lead} to accept`}</button>`;
  if (!v) {
    return html`<section class="shell-goal__sec" aria-label="Verdict"><h3 class="board-sub">Verdict</h3>
      <p class="ok-tone-muted">${accepting ? `${Lead} is accepting the goal against its metrics…` : `Its ideas are done: ${lead} accepts the goal against its metrics, not against the work done.`}</p>
      <div class="shell-goal__acts">${ask}</div></section>`;
  }
  return html`<section class="shell-goal__sec" aria-label="Verdict"><h3 class="board-sub">Verdict</h3>
    <p><b class=${v.met ? "ok-tone-ok" : "ok-tone-error"}>${v.met ? "Goal met" : "Not met yet"}</b> <span class="ok-tone-muted">· by ${v.by || Lead}</span></p>
    ${v.verdict && html`<p class="shell-brief">${v.verdict}</p>`}
    ${v.metrics?.length > 0 && html`<table class="shell-metrics"><thead><tr><th>Metric</th><th>Status</th><th>Why</th></tr></thead>
      <tbody>${v.metrics.map((m) => html`<tr key=${m.name}><td>${m.name}</td><td class=${STATUS_TONE[m.status] || ""}>${m.status}</td><td>${m.why || "—"}</td></tr>`)}</tbody></table>`}
    ${v.next?.length > 0 && html`<div class="shell-goal__next" role="group" aria-label="Next ideas"><span class="ok-font-label">Next ideas</span>
      ${v.next.map((x) => html`<div key=${x} class="shell-goal__next-row"><span>${x}</span>
        <button type="button" class="ork-btn" aria-label=${`Add as idea: ${x}`} onClick=${() => act("ideas.add", { text: x, track: g.slug, priority: "normal" })}>Add as idea</button></div>`)}</div>`}
    <div class="shell-goal__acts">${ask}</div></section>`;
}

const usdWords = (usd) => (usd == null ? "" : ` · ≈$${usd.toFixed(2)}`);
const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** The lines of *What the party did* (spec 43 §2.3) from `ideas.party`'s object: the leader, each member, each check. */
export function partyLines(w) {
  if (!w.ideas) return [{ key: "none", text: "No work yet" }];
  const lead = w.leader;
  return [
    { key: `lead:${lead.slug}`, head: lead.head, text: `${lead.name} (leads): ${lead.usd != null ? `≈$${lead.usd.toFixed(2)} for the goal, the drafts and the plans` : "the goal, the drafts and the plans"}` },
    ...w.members.map((m) => ({ key: `m:${m.slug}`, head: m.head,
      text: `${m.name}: ${count(m.tasks, "task", "tasks")}, ${m.first_time} merged the first time${usdWords(m.usd)}` })),
    ...w.checks.map((c) => ({ key: `c:${c.by}`, head: c.head,
      text: `${c.name}: ${c.applied || c.clean || c.caught
        ? `checked ${count(c.applied, "idea", "ideas")}: ${c.clean} clean, caught ${c.caught}${c.left ? ` (${c.left} left)` : ""}` : "no idea checked yet"}`
        + `${usdWords(c.usd)}${c.skipped ? ` · skipped ${c.skipped}` : ""}${c.before ? ` · ${c.before} before findings were kept` : ""}` })),
  ];
}

/** *What the party did*: a fold, closed at first; what a goal's party did is read when it is opened (spec 43 §2.3), and logged. */
export function PartyFold({ slug }) {
  const [open, setOpen] = useState(false);
  const [work, setWork] = useState(null);
  useEffect(() => {
    if (!open) return undefined;
    let on = true;
    ask("ideas.party", { goal: slug }).then((got) => { if (on && got) setWork(got); });
    return () => { on = false; };
  }, [open, slug]);
  const toggle = () => { if (!open) logOpened("party", slug); setOpen(!open); };
  return html`<div class="party-work">
    <button type="button" class="board-link party-work__btn" aria-expanded=${open} onClick=${toggle}>What the party did</button>
    ${open && (work ? html`<ul class="party-work__list" aria-label="What the party did">${partyLines(work).map((l) => html`<li key=${l.key}>
      ${l.head && html`<${WhoHead} head=${l.head} small />`} <span>${l.text}</span></li>`)}</ul>`
      : html`<p class="ok-tone-muted">Reading…</p>`)}
  </div>`;
}
