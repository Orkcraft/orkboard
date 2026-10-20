// Needs you, on the right (spec 46 §6.3), and Review in it (docs/specs/33-v1-shell.md §3, §6): Merge into `dev` ▾ at the top of Review, then the results oldest first,
// one card each — what changed, its tests, its cost. Three answers, on the card and in the result's preview: Merge
// (only when the tests are green and nothing conflicts), Send back / Fix (one line, required), Drop (quiet, apart).
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev } from "../orkui.js";
import { review, preview, act, showResult, closePreview } from "./store.js";
import { Modal, openDialog, closeDialog } from "./modals.js";
import { board } from "../board/store.js";
import { Today, needsCount, needsRows } from "../board/today.js";

const usd = (n) => (n == null ? "" : `$${n < 10 ? n.toFixed(2) : Math.round(n)}`);

export function isRed(r) { return r.tests.failed > 0 || r.tests.green === false; }
export function noTests(r) { return !isRed(r) && r.tests.passed === 0; }

/** The tests, in the person's words: "20 / 20 passed" ✓, "10 / 20 failed" ✗ with the first failing names, or no tests ran; a command that is not pytest: passed (exit 0) / failed (exit 1). */
export function testsWords(r) {
  const t = r.tests, all = t.passed + t.failed;
  if (t.ran === false) return { mark: "", text: "no tests ran", names: [], tone: "muted" };
  if (t.passed == null && t.failed == null) {          // a command that is not pytest: its exit code speaks
    const failed = isRed(r), code = t.exit ?? (failed ? 1 : 0);
    return failed ? { mark: "✗", text: `failed (exit ${code})`, names: [], tone: "danger" } : { mark: "✓", text: `passed (exit ${code})`, names: [], tone: "success" };
  }
  if (isRed(r)) return { mark: "✗", text: t.failed ? `${t.failed} / ${all} failed` : "the tests failed", names: (t.failing || []).slice(0, 2), tone: "danger" };
  if (noTests(r)) return { mark: "", text: "no tests ran", names: [], tone: "muted" };
  return { mark: "✓", text: `${t.passed} / ${all} passed`, names: [], tone: "success" };
}
export const changesWords = (d) => `${d.files} file${d.files === 1 ? "" : "s"}, +${d.added} −${d.removed}`;

/** Why Merge is off, or "": red tests, a conflict, or both. */
export function mergeReason(r, into) {
  const why = [];
  if (isRed(r)) why.push("Its tests are red");
  if (r.conflict) why.push(r.conflict);
  return why.length ? `${why.join(" · ")}: send it back to fix ${why.length > 1 ? "them" : r.conflict ? "the conflict" : "them"}` : "";
}

/** A check's findings left (spec 43 §1.4), and how many it found: "Found 3: 1 fixed, 2 left". */
export const leftOf = (r) => (r.check ? (r.findings || []).filter((f) => !f.fixed) : []);
export function foundWords(r) {
  const all = r.findings || [], left = leftOf(r).length;
  return `Found ${all.length}: ${all.length - left} fixed, ${left} left`;
}

export function fixLine(r, into) {
  if (r.conflict) return `Resolve the conflict with ${into}`;
  if (isRed(r)) return `Fix the failing tests${r.tests.failing?.[0] ? `: ${r.tests.failing[0]}` : ""}`;
  const left = leftOf(r);
  return left.length ? `Fix the findings left: ${left.map((f) => `${f.where}: ${f.what}`).join("; ")}`.slice(0, 1000) : "";
}

/** The findings left of a check's result, in the text face: they are the checker's words. */
function Findings({ r }) {
  const left = leftOf(r);
  if (!left.length) return null;
  return html`<div class="shell-findings"><p class="shell-findings__head">${foundWords(r)}</p>
    <ul class="shell-findings__list">${left.map((f, i) => html`<li key=${i}><span class="shell-findings__where">${f.where}</span> · ${f.what}</li>`)}</ul></div>`;
}

/** Merge · Send back / Fix · Drop for one result; `pinned` in a preview's foot. */
export function ResultActions({ r, pinned = false }) {
  const into = review.value?.into || "dev";
  const [line, setLine] = useState(null);       // null: the one-line box is closed
  const [working, setWorking] = useState(false);
  const reason = mergeReason(r, into), fix = isRed(r) || !!r.conflict, found = leftOf(r).length > 0;
  const key = { slug: r.idea, task: r.task };
  const done = () => { if (preview.value?.task === r.task && preview.value?.slug === r.idea) closePreview(); };
  const merge = async () => { setWorking(true); const got = await act("ideas.merge", key); setWorking(false); if (got?.ok) done(); };
  const back = async (e) => {
    e.preventDefault();
    if (!line.trim()) return;
    setWorking(true);
    const got = await act("ideas.back", { ...key, why: line.trim() });
    setWorking(false);
    if (got?.ok) { setLine(null); done(); }
  };
  return html`<div class=${cls("shell-actions", { "is-pinned": pinned })} onClick=${(e) => e.stopPropagation()}>
    <div class="shell-actions__main">
      <button class="ork-btn primary" disabled=${!!reason || working} title=${reason || (found ? "Leave the findings as they are: nothing is changed" : `Merge into ${into}`)}
        onClick=${merge}>${found ? "Leave them" : `Merge into ${into}`}</button>
      <button class="ork-btn" aria-expanded=${line !== null} onClick=${() => setLine(line === null ? fixLine(r, into) : null)}>${found ? "Fix them" : fix ? "Fix" : "Send back"}</button>
      <button class="shell-quiet" onClick=${() => openDialog("drop", { r })}>Drop…</button>
    </div>
    ${reason && html`<p class="shell-actions__why ok-tone-error" role="status">${reason}</p>`}
    ${line !== null && html`<form class="shell-actions__line" onSubmit=${back}>
      <input class="ork-field" autofocus value=${line} aria-label=${fix || found ? "What to fix, in one line" : "Why you send it back, in one line"}
        placeholder="One line: what should change?" onInput=${(e) => setLine(e.target.value)}
        onKeyDown=${(e) => e.key === "Escape" && (e.stopPropagation(), setLine(null))} />
      <button class="ork-btn primary" disabled=${!line.trim() || working}>${found ? "Fix them" : fix ? "Fix" : "Send back"}</button></form>`}
  </div>`;
}

function Card({ r, selected }) {
  const t = testsWords(r);
  return html`<article class=${cls("shell-card", { "is-on": selected })} tabindex="0" role="listitem" aria-label=${r.title}
      data-task=${r.task} data-idea=${r.idea} aria-current=${selected} onClick=${() => showResult(r.idea, r.task, { via: "review" })}
      onKeyDown=${(e) => { if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); showResult(r.idea, r.task, { via: "review" }); } }}>
    <div class="shell-card__head"><b>${r.title}</b>
      <span class="ok-tone-muted">${r.idea_title}${r.round > 1 ? html` · <span class="shell-round">round ${r.round}</span>` : ""}</span></div>
    <dl class="shell-facts">
      <dt>Tests</dt><dd class=${`is-${t.tone}`}>${t.mark} ${t.text}${t.names.length ? html` <span class="ok-tone-muted">${t.names.join(", ")}</span>` : ""}</dd>
      <dt>Changes</dt><dd>${changesWords(r.diff)}</dd>
      ${r.cost != null && html`<dt>Cost</dt><dd>${usd(r.cost)}</dd>`}
    </dl>
    <${Findings} r=${r} />
    ${r.conflict && html`<p class="ok-tone-error shell-conflict">⚠ ${r.conflict}</p>`}
    <${ResultActions} r=${r} />
  </article>`;
}

function Into() {
  const rv = review.value;
  if (!rv) return null;
  return html`<div class="shell-into">
    <button class="ork-btn" aria-haspopup="dialog" onClick=${() => openDialog("into")}>Merge into <b>${rv.into}</b><${Chev} /></button>
  </div>`;
}

/** Merge into ▾ : the branch the results land in, from the local branches, or a new one. */
export function IntoDialog() {
  const rv = review.value;
  const [making, setMaking] = useState(null);
  if (!rv) return null;
  const pick = async (branch) => { if (branch !== rv.into) await act("ideas.into", { branch }); closeDialog(); };
  return html`<${Modal} title="Merge into" onClose=${closeDialog}>
    <div class="shell-menu__list" role="menu" aria-label="Merge into">
      ${(rv.branches || [rv.into]).map((b) => html`<button key=${b} class="shell-menu__item" role="menuitemradio"
        aria-checked=${b === rv.into} onClick=${() => pick(b)}>${b === rv.into ? "✓" : ""} ${b}</button>`)}
      ${making === null ? html`<button class="shell-menu__item" role="menuitem" onClick=${() => setMaking("")}>New branch…</button>`
        : html`<form class="shell-menu__new" onSubmit=${(e) => { e.preventDefault(); if (making.trim()) pick(making.trim()); }}>
          <input class="ork-field" autofocus value=${making} aria-label="Name of the new branch" placeholder="Name of the new branch"
            onInput=${(e) => setMaking(e.target.value)} /><button class="ork-btn primary" disabled=${!making.trim()}>Make it</button></form>`}
    </div>
  <//>`;
}

/** Drop's confirm: the result's task fails ("dropped by you"), its branch stays. */
export function DropDialog({ r }) {
  const drop = async () => {
    const got = await act("ideas.drop_task", { slug: r.idea, task: r.task });
    if (got?.ok) { if (preview.value?.task === r.task && preview.value?.slug === r.idea) closePreview(); closeDialog(); }
  };
  return html`<${Modal} title="Drop this result?" onClose=${closeDialog}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Keep it</button>
      <button type="button" class="ork-btn danger" onClick=${drop}>Drop it</button>`}>
    <p class="shell-modal__text"><b>${r.title}</b> will not be merged. Its worktree goes; its branch stays.</p>
  <//>`;
}

/** The right column (spec 46 §6.3): *Needs you* — its head with the signal (`.ork-count.warning` while an answer waits), the rows that wait for an
 *  answer (board/today.js) — then **Review**, a section of its own: its count, Merge into ▾ and its cards. Nothing in either: *Nothing waits for you.* */
export function NeedsPane() {
  const rv = review.value, p = preview.value, b = board.value;
  const results = rv?.results || [];
  const asks = b ? needsCount() : 0;
  const rows = b ? needsRows().length : 0;
  // ↑ ↓ move through the cards and open each one's code; no shortcut merges
  const move = (e) => {
    if ((e.key !== "ArrowDown" && e.key !== "ArrowUp") || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || !results.length || !e.target.closest?.(".shell-reviewing")) return;
    e.preventDefault();
    const at = results.findIndex((r) => r.task === (e.target.closest?.(".shell-card")?.dataset.task ?? p?.task) && r.idea === (e.target.closest?.(".shell-card")?.dataset.idea ?? p?.slug));
    const next = results[Math.max(0, Math.min(results.length - 1, at + (e.key === "ArrowDown" ? 1 : -1)))];
    showResult(next.idea, next.task);
    requestAnimationFrame(() => document.querySelector(`.shell-card[data-task="${next.task}"][data-idea="${next.idea}"]`)?.focus());
  };
  const nothing = !!rv && !!b && !rows && !results.length;
  return html`<aside class="shell-pane shell-review shell-needs" aria-label="Needs you" tabindex="-1" onKeyDown=${move}>
    <header class="shell-pane__head"><h2>Needs you ${asks > 0 && html`<span class="shell-count ork-count warning">${asks}</span>`}</h2></header>
    <div class="shell-pane__body">
      ${!b || !rv ? html`<p class="ok-tone-muted">Opening…</p>` : html`
        <${Today} empty=${nothing} />
        <section class="shell-reviewing" aria-label="Review">
          <h3 class="shell-reviewing__head">Review ${results.length > 0 && html`<span class="shell-count">${results.length}</span>`}</h3>
          <${Into} />
          ${results.length ? html`<div role="list" class="shell-cards">${results.map((r) => html`<${Card} key=${r.idea + r.task} r=${r}
              selected=${p?.kind === "result" && p.task === r.task && p.slug === r.idea} />`)}</div>`
            : !nothing && html`<p class="ok-tone-muted">Nothing waits at Review. A result lands here when a Grunt's work has been tested.</p>`}
        </section>`}
    </div>
  </aside>`;
}
