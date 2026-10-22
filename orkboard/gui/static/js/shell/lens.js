// The lens of New idea on the desktop, as the phone's (pwa/shell-lens.js; realm/idea_lens.py, decisions §53): beside the text —
// always there, and enough alone —, what to point at in the way of the goal's party. A row of the lenses the party has: Text;
// Code (an engineer's: the repository's parts, what each uses and what uses it, and a note of what to change); Screen (a
// designer's: lensscreen.js); Pain (a product manager's: whom it is for and what hurts them, the project's own a click away).
// A goal type's lens is open first, else the leader's (lensFirst); switching lenses loses nothing, and what each holds goes with the idea.
import { useEffect, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { ask } from "../board/store.js";
import { ScreenLens, noScreen, screenValue } from "./lensscreen.js";

const WORDS = { text: "Text", code: "Code", screen: "Screen", pain: "Pain" };
const SHOWN = 6;

export const noLens = { on: "", segment: "", pain: "", picked: [], note: "", screen: noScreen };
/** The lens state New goal starts with: a goal type's lens open first (docs/specs/52-goal-types.md §4.2) when the party offers it, else the leader's. */
export const lensFirst = (type) => ({ ...noLens, on: type?.lens || "" });

/** The goal's lenses (ideas.lens), read again when the goal changes: {lenses, default, segments, screens}. */
export function useLenses(goal) {
  const [got, setGot] = useState(null);
  useEffect(() => {
    let live = true;
    setGot(null);
    if (goal) ask("ideas.lens", { track: goal }).then((r) => { if (live) setGot(r); });
    return () => { live = false; };
  }, [goal]);
  return got;
}

/** What `ideas.add` takes in `lens`: each lens's own, of the lenses the goal's party has. */
export function lensValue(info, s) {
  const has = new Set((info?.lenses || []).map((l) => l.id));
  const out = [];
  if (has.has("pain") && (s.segment.trim() || s.pain.trim())) out.push({ kind: "pain", segment: s.segment.trim(), pain: s.pain.trim() });
  if (has.has("code") && s.picked.length) out.push({ kind: "code", paths: s.picked, note: s.note.trim() });
  if (has.has("screen")) out.push(...screenValue(s.screen));
  return out;
}

function CodeLens({ s, set }) {
  const [parts, setParts] = useState(null);
  const [q, setQ] = useState("");
  useEffect(() => { ask("ideas.lens_code").then((r) => setParts(r?.parts || [])); }, []);
  const near = new Set((parts || []).filter((p) => s.picked.includes(p.path)).flatMap((p) => [...p.uses, ...p.used_by]));
  const shown = (parts || []).filter((p) => !q || p.path.toLowerCase().includes(q.toLowerCase()) || s.picked.includes(p.path))
    .sort((a, b) => (s.picked.includes(b.path) - s.picked.includes(a.path)) || (near.has(b.path) - near.has(a.path)));
  const flip = (path) => set({ ...s, picked: s.picked.includes(path) ? s.picked.filter((x) => x !== path) : [...s.picked, path].slice(0, 12) });
  return html`<div class="shell-lens-pane">
    <input class="ork-field" type="search" value=${q} aria-label="Find a part" placeholder="Find a part: a folder" onInput=${(e) => setQ(e.target.value)} />
    <p class="ok-font-status ok-tone-muted">${s.picked.length ? `Picked: ${s.picked.join(", ")}` : "Pick the parts the idea changes."}</p>
    ${parts === null ? html`<p class="ok-tone-muted">Reading the repository…</p>` : html`<ul class="shell-lens-parts" aria-label="The repository's parts">
      ${shown.slice(0, 80).map((p) => {
        const on = s.picked.includes(p.path);
        return html`<li key=${p.path}><button type="button" class=${cls("shell-lens-part", { "is-near": near.has(p.path) && !on })} aria-pressed=${String(on)}
          aria-label=${`${on ? "Leave out" : "Pick"}: ${p.path}`} onClick=${() => flip(p.path)}>
          <b>${p.path === "." ? "The top folder" : p.path}</b>
          <small class="ok-tone-muted">${p.count} file${p.count === 1 ? "" : "s"}${p.uses.length ? ` · uses ${p.uses.join(", ")}` : ""}${p.used_by.length ? ` · used by ${p.used_by.join(", ")}` : ""}</small></button></li>`;
      })}</ul>`}
    <label class="shell-field"><span class="ok-font-label">What to change there</span>
      <textarea class="ork-field" rows="2" maxlength="1000" value=${s.note} aria-label="What to change there" placeholder="What to change there"
        onInput=${(e) => set({ ...s, note: e.target.value })}></textarea></label></div>`;
}

function PainLens({ info, s, set }) {
  const segs = info.segments || [];
  const mine = segs.find((x) => x.segment.toLowerCase() === s.segment.trim().toLowerCase());
  return html`<div class="shell-lens-pane">
    <label class="shell-field"><span class="ok-font-label">For whom</span>
      <input class="ork-field" maxlength="120" value=${s.segment} aria-label="For whom" placeholder="Shop owners, new users…"
        onInput=${(e) => set({ ...s, segment: e.target.value })} /></label>
    ${segs.length > 0 && html`<div class="shell-lens-chips" role="group" aria-label="Kept segments">${segs.slice(0, SHOWN).map((x) => html`<button key=${x.segment}
      type="button" class="ork-btn" aria-pressed=${String(x.segment === s.segment)} onClick=${() => set({ ...s, segment: x.segment, pain: "" })}>${x.segment}</button>`)}</div>`}
    <label class="shell-field"><span class="ok-font-label">What hurts them</span>
      <input class="ork-field" maxlength="300" value=${s.pain} aria-label="What hurts them" placeholder="What goes wrong for them"
        onInput=${(e) => set({ ...s, pain: e.target.value })} /></label>
    ${(mine?.pains || []).length > 0 && html`<div class="shell-lens-chips" role="group" aria-label="Their pains">${mine.pains.slice(0, SHOWN).map((p) => html`<button key=${p}
      type="button" class="ork-btn" aria-pressed=${String(p === s.pain)} onClick=${() => set({ ...s, pain: p })}>${p}</button>`)}</div>`}</div>`;
}

/** The lens row and the open lens's pane. `info`: useLenses; `s`, `set`: the dialog's lens state. */
export function Lens({ info, s, set }) {
  if (!info || (info.lenses || []).length < 2) return null;
  const on = s.on && info.lenses.some((l) => l.id === s.on) ? s.on : info.default;
  return html`<div class="shell-lens">
    <span class="ok-font-label">Lens</span>
    <div class="shell-lens-bar" role="radiogroup" aria-label="Lens">${info.lenses.map((l) => html`<button key=${l.id} type="button" role="radio"
      class="ork-btn shell-lens-chip" aria-checked=${String(l.id === on)} aria-label=${l.by ? `${WORDS[l.id]} · ${l.by}` : WORDS[l.id]}
      onClick=${() => set({ ...s, on: l.id })}><b>${WORDS[l.id]}</b><small>${l.by || "only words"}</small></button>`)}</div>
    ${on === "text" && html`<p class="ok-font-status ok-tone-muted">The text alone is enough: the party reads it.</p>`}
    ${on === "code" && html`<${CodeLens} s=${s} set=${set} />`}
    ${on === "screen" && html`<${ScreenLens} kept=${info.screens || []} value=${s.screen} set=${(v) => set((cur) => ({ ...cur, screen: v }))} />`}
    ${on === "pain" && html`<${PainLens} info=${info} s=${s} set=${set} />`}
  </div>`;
}

/** What an idea's lens pointed at, for its spec: one line each. */
export function PointedAt({ lens }) {
  if (!(lens || []).length) return null;
  const line = (a) => (a.kind === "pain" ? [`Pain · ${a.segment || "whom: not said"}`, a.pain]
    : a.kind === "code" ? [`Code · ${a.paths.join(", ")}`, a.note]
      : [`Screen · ${a.name || "a screen"}`, (a.marks || []).map((m, i) => `${i + 1}) ${m.note || "marked"}`).join(" · ") || a.note]);
  return html`<div class="shell-pointed" role="list" aria-label="Pointed at"><span class="ok-font-label">Pointed at</span>
    ${lens.map((a, i) => { const [head, more] = line(a); return html`<p key=${i} role="listitem" data-kind=${a.kind}><b>${head}</b>${more && html` <small class="ok-tone-muted">${more}</small>`}</p>`; })}</div>`;
}
