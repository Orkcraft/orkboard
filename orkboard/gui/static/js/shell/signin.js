// A tool's own sign-in, opened at once (docs/specs/45-sign-in.md §5, §8; decisions §58). The snapshot's `sign_in` holds the tools
// that are not signed in: this page
// - opens the sign-in of a tool `needed` with `auto: true` (once per episode: the server takes the first page's ask), when the
//   person is at the page — visible and focused —, at once if so, else on its next focus, press or key; one tool at a time;
// - says what is going on in a toast: while the sign-in is open (in the browser, or in a terminal's own window) it stays; then
//   *signed in* with how much goes on by itself, or *did not finish*;
// - gives every line of a failure that a sign-in helps its **Sign in** (`SignInButton`, `entryFor`).
// The phone shows the wait and opens nothing (pwa/shell-needs.js): this file is the desktop's.
import { useEffect } from "preact/hooks";
import { html } from "../html.js";
import { town, toast, toasts, dismiss, command, copyText } from "../link.js";

const entries = () => town.value?.sign_in || [];
const atPage = () => document.visibilityState === "visible" && document.hasFocus();

// -- what a tool's session wants typed, when it is not in the snapshot ------------------------------------------------------
const TYPED = { pi: "/login" };

const WHY = {
  timeout: "it took too long.",
  cancelled: "it was cancelled.",
  refused: "the tool did not take the sign-in.",
  no_browser: "the browser did not open.",
};
const whyWords = (e) => (e.why ? WHY[e.why] || e.why : "");

// -- opening at once ----------------------------------------------------------------------------------------------------
const tried = new Set();                                      // `harness:since` of an episode this page asked for
let inflight = false;

/** Asks the host to open the first tool that needs a sign-in, when the person is at the page and no other is open. */
export function openAuto() {
  const list = entries();
  if (inflight || !atPage() || list.some((e) => e.state === "open")) return;
  const e = list.find((x) => x.state === "needed" && x.auto && !tried.has(`${x.harness}:${x.since}`));
  if (!e) return;
  tried.add(`${e.harness}:${e.since}`);
  inflight = true;
  command("tools.sign_in", { harness: e.harness, auto: true }).catch(() => {}).finally(() => { inflight = false; });
}

/** The person asks: *Sign in* (`by`: "terminal" for a browser that did not open). */
export const signIn = (harness, by = "") => command("tools.sign_in", { harness, ...(by ? { by } : {}) }).catch(() => {});

/** The entry of a tool whose failure line this is (`LINES`' words: *Claude Code is not signed in, …*), else null. */
export function entryFor(text) {
  const t = String(text || "");
  return t ? entries().find((e) => e.tool && t.includes(`${e.tool} is not signed in`)) || null : null;
}

/** **Sign in** beside a failure that a sign-in helps; nothing while that sign-in is open. */
export function SignInButton({ harness, tool, label = "Sign in" }) {
  const e = entries().find((x) => x.harness === harness);
  const open = e?.state === "open";
  return html`<button type="button" class="ork-btn quiet" data-sign-in=${harness} disabled=${open}
    aria-label=${`${label} ${tool ? `to ${tool}` : ""}`.trim()} onClick=${() => signIn(harness)}>${open ? "Signing in…" : label}</button>`;
}

// -- the toasts ---------------------------------------------------------------------------------------------------------
const shown = new Map();                                      // harness → {sig, id}
const last = new Map();                                       // harness → the entry as last seen
let first = true;

const sigOf = (e) => [e.state, e.by, e.why, e.command].join("|");

function view(e) {
  const t = e.tool;
  const again = { label: "Sign in again", run: () => signIn(e.harness) };
  if (e.state === "open" && e.by === "terminal") {
    const typed = TYPED[e.harness] || "";
    return { title: `Sign in to ${t}`, severity: "warning", seconds: 600,
      message: `${t} signs in in its own window: a terminal opened with ${t}.${typed ? ` Type ${typed} there.` : ""}`,
      acts: [{ label: "Copy", run: () => { copyText(typed || e.command || t); keep(e); } },
        { label: "Done", run: () => command("tools.sign_in_done", { harness: e.harness }).catch(() => {}) },
        { label: "Cancel", run: () => command("tools.sign_in_cancel", { harness: e.harness }).catch(() => {}) }] };
  }
  if (e.state === "open") {
    return { title: `Sign in to ${t}`, severity: "warning", seconds: 600,
      message: "Its sign-in opened in your browser. Sign in there: the work that waits for it goes on by itself.",
      acts: [{ label: "Cancel", run: () => command("tools.sign_in_cancel", { harness: e.harness }).catch(() => {}) }] };
  }
  if (e.state === "none") {
    return { title: `Sign in to ${t}`, severity: "warning", seconds: 60,
      message: `No terminal was found. Open one and run: ${e.command || t}`,
      acts: [{ label: "Copy", run: () => { copyText(e.command || t); keep(e); } }] };
  }
  if (e.state === "failed" && e.why === "cancelled") return null;      // the person did it: nothing to say
  if (e.state === "failed" && e.why === "no_browser") {
    return { title: "", severity: "warning", seconds: 60, message: "The browser did not open.",
      acts: [{ label: "Sign in in a terminal", run: () => signIn(e.harness, "terminal") }] };
  }
  if (e.state === "failed") {
    const why = whyWords(e);
    return { title: "", severity: "warning", seconds: 30, message: `${t}'s sign-in did not finish.`,
      acts: [again, { label: "Details", run: () => toast(why ? `${t}: ${why}` : `${t}'s sign-in did not finish.`, "information", "Sign-in", 12) }] };
  }
  return null;
}

/** Shows the toast again after a button that dismisses it (Copy keeps it up). */
function keep(e) {
  const v = view(e);
  if (v) put(e.harness, e, v);
}

function put(harness, e, v) {
  toast(v.message, v.severity, v.title, v.seconds, null, v.acts);
  const id = toasts.value[toasts.value.length - 1]?.id;
  shown.set(harness, { sig: sigOf(e), id });
}

function done(e) {
  const n = e.waiting || 0;
  toast(`${e.tool} is signed in.${n > 0 ? ` ${n} ${n === 1 ? "task goes" : "tasks go"} on.` : ""}`, "information", "", 8);
}

/** The toasts for the snapshot's `sign_in`: one per tool, changed only when its state does; a tool gone is signed in. */
export function sync(list) {
  const now = new Set(list.map((e) => e.harness));
  for (const [harness, e] of [...last]) {
    if (now.has(harness)) continue;
    const s = shown.get(harness);
    if (s) dismiss(s.id);
    shown.delete(harness);
    last.delete(harness);
    if (e.state !== "needed" || e.waiting > 0) done(e);
  }
  for (const e of list) {
    const prev = last.get(e.harness);
    last.set(e.harness, e);
    const s = shown.get(e.harness);
    if (s && s.sig === sigOf(e)) continue;
    if (s) { dismiss(s.id); shown.delete(e.harness); }
    if (first && e.state === "failed") continue;                   // a page opened on an old failure says nothing
    const v = view(e);
    if (v && (prev || e.state !== "needed")) put(e.harness, e, v);
  }
  first = false;
}

/** Mounted by the shell and by the first screen: the page that opens a sign-in at once and says how it goes. */
export function SignIn() {
  const list = town.value?.sign_in;
  useEffect(() => { sync(list || []); openAuto(); }, [list]);
  useEffect(() => {
    const on = () => openAuto();
    const events = ["focus", "pointerdown", "keydown"];
    for (const ev of events) window.addEventListener(ev, on);
    document.addEventListener("visibilitychange", on);
    return () => { for (const ev of events) window.removeEventListener(ev, on); document.removeEventListener("visibilitychange", on); };
  }, []);
  return null;
}
