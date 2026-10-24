// Review's answers (docs/specs/33-v1-shell.md §3, §6; spec 48 §5): the results are on their idea in the Map (board/mapcard.js), no column
// of their own. Three answers, on the idea's card and in the result's preview: Merge (only when the tests are green and nothing
// conflicts), Send back / Fix (one line, required), Drop (quiet, apart). And Merge into ▾, the branch results land in.
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { review, preview, act, closePreview } from "./store.js";
import { Modal, openDialog, closeDialog } from "./modals.js";
import { pctOf } from "../spend.js";

export const usd = (n) => (n == null ? "" : pctOf(n) || `$${n < 10 ? n.toFixed(2) : Math.round(n)}`);

export function isRed(r) { return r.tests.failed > 0 || r.tests.green === false; }
export function noTests(r) { return !isRed(r) && r.tests.passed === 0; }

/** The tests, in the person's words: "20 / 20 passed" (the *check* sign), "10 / 20 failed" (the *cross* sign) with the first failing names, or no tests ran; a
 *  command that is not pytest: passed (exit 0) / failed (exit 1). `mark` is the name of orkUI's sign, "" for none. */
export function testsWords(r) {
  const t = r.tests, all = t.passed + t.failed;
  if (t.ran === false) return { mark: "", text: "no tests ran", names: [], tone: "muted" };
  if (t.passed == null && t.failed == null) {          // a command that is not pytest: its exit code speaks
    const failed = isRed(r), code = t.exit ?? (failed ? 1 : 0);
    return failed ? { mark: "cross", text: `failed (exit ${code})`, names: [], tone: "danger" } : { mark: "check", text: `passed (exit ${code})`, names: [], tone: "success" };
  }
  if (isRed(r)) return { mark: "cross", text: t.failed ? `${t.failed} / ${all} failed` : "the tests failed", names: (t.failing || []).slice(0, 2), tone: "danger" };
  if (noTests(r)) return { mark: "", text: "no tests ran", names: [], tone: "muted" };
  return { mark: "check", text: `${t.passed} / ${all} passed`, names: [], tone: "success" };
}
export const changesWords = (d) => `${d.files} file${d.files === 1 ? "" : "s"}, +${d.added} −${d.removed}`;

/** Why Merge is off, or "": red tests, a conflict, or both. */
export function mergeReason(r, into) {
  const why = [];
  if (isRed(r)) why.push("Its tests are red");
  if (r.conflict) why.push(r.conflict);
  return why.length ? `${why.join(" · ")}: send it back to fix ${why.length > 1 ? "them" : r.conflict ? "the conflict" : "them"}` : "";
}

export function fixLine(r, into) {
  if (r.conflict) return `Resolve the conflict with ${into}`;
  if (isRed(r)) return `Fix the failing tests${r.tests.failing?.[0] ? `: ${r.tests.failing[0]}` : ""}`;
  return "";
}

/** What a check found (spec 43 §1.4): *Found 3: 1 fixed, 2 left*; "" for a result that is not a check's or found nothing. */
export function foundWords(findings) {
  const n = findings?.length || 0, fixed = (findings || []).filter((f) => f.fixed).length;
  if (!n) return "";
  return `Found ${n}: ${fixed ? `${fixed} fixed, ` : ""}${n - fixed} left`;
}
export const leftOf = (r) => (r.findings || []).filter((f) => !f.fixed);
const WHY_MAX = 1000;
/** *Fix the findings left:* and one line each (*where: what*), within the one line a send back takes. */
export function fixThemWhy(r) {
  let why = "Fix the findings left:";
  const left = leftOf(r);
  for (const [n, f] of left.entries()) {
    const next = `${why}\n${f.where}: ${f.what}`, more = left.length - n - 1;
    if (next.length + (more ? 24 : 0) > WHY_MAX) return `${why}\nand ${left.length - n} more`;
    why = next;
  }
  return why;
}

/** Merge · Send back / Fix · Drop for one result; `pinned` in a preview's foot. A check with findings left: Fix them · Leave them · Drop. */

export function ResultActions({ r, pinned = false }) {
  const into = review.value?.into || "dev";
  const [line, setLine] = useState(null);       // null: the one-line box is closed
  const [working, setWorking] = useState(false);
  const reason = mergeReason(r, into), fix = isRed(r) || !!r.conflict, check = r.check && leftOf(r).length > 0;
  const key = { slug: r.idea, task: r.task };
  const fixThem = async () => { setWorking(true); const got = await act("ideas.back", { ...key, why: fixThemWhy(r) }); setWorking(false); if (got?.ok) done(); };
  const done = () => { if (preview.value?.task === r.task && preview.value?.slug === r.idea) closePreview(); };
  const merge = async () => { setWorking(true); const got = await act("ideas.merge", r.over ? { ...key, dear: true } : key);   // dear: it cost more than its plan said (only logged)
    setWorking(false); if (got?.ok) done(); };
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
      ${check ? html`<button class="ork-btn primary" disabled=${working} onClick=${fixThem}>Fix them</button>
        <button class="ork-btn" disabled=${!!reason || working} title=${reason || (r.diff.files ? `Merge the fixes into ${into}` : "Nothing is merged")}
          onClick=${merge}>Leave them</button>`
        : html`<button class="ork-btn primary" disabled=${!!reason || working} title=${reason || `Merge into ${into}`}
          onClick=${merge}>Merge into ${into}</button>
        <button class="ork-btn" aria-expanded=${line !== null} onClick=${() => setLine(line === null ? fixLine(r, into) : null)}>${fix ? "Fix" : "Send back"}</button>`}
      <button class="shell-quiet" onClick=${() => openDialog("drop", { r })}>Drop…</button>
    </div>
    ${reason && html`<p class="shell-actions__why ok-tone-error" role="status">${reason}</p>`}
    ${!check && line !== null && html`<form class="shell-actions__line" onSubmit=${back}>
      <input class="ork-field" autofocus value=${line} aria-label=${fix ? "What to fix, in one line" : "Why you send it back, in one line"}
        placeholder="One line: what should change?" onInput=${(e) => setLine(e.target.value)}
        onKeyDown=${(e) => e.key === "Escape" && (e.stopPropagation(), setLine(null))} />
      <button class="ork-btn primary" disabled=${!line.trim() || working}>${fix ? "Fix" : "Send back"}</button></form>`}
  </div>`;
}

/** Under a check's title: *Found 3: 1 fixed, 2 left* and the findings left, each *where · what* (the checker's words, in the text face). */
export function Found({ r }) {
  const left = leftOf(r);
  if (!r.check || !left.length) return null;
  return html`<div class="shell-found"><p class="shell-found__sum">${foundWords(r.findings)}</p>
    <ul class="shell-found__list">${left.map((f, n) => html`<li key=${n}><span class="shell-found__where">${f.where}</span> · ${f.what}</li>`)}</ul></div>`;
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
