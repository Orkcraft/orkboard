// The v1 shell's state (docs/specs/33-v1-shell.md §5–§7): what the host last said of the board (js/board/store.js), of
// Review and of Agents, the Map, and the preview's tabs (spec 39 §3; the active one is `preview`). A refresh runs when the town says the ideas changed and
// every 10 s while a model or a task runs; the open task's log is read again every 5 s while it runs.
import { signal, batch } from "@preact/signals";
import { command, toast } from "../link.js";
import { ask, board, opened, page, BUSY } from "../board/store.js";
import { openDialog } from "./modals.js";

export const preview = signal(null);       // the active tab's thing, null when the Map is: {kind: "idea"|"plan"|"task"|"result"|"goal"|"doc"|"file"|"gitdiff", slug?, task?, todo?, path?}
export const review = signal(null);        // ideas.review_list
export const agents = signal(null);        // ideas.agents
export const detail = signal(null);        // the preview's own data: {task} (ideas.task) · {task, diff, spend} (a result; spend: ideas.spend of its idea) · {goal} · {doc}
export const goal = signal(null);          // ideas.goal of the goal in the preview
export const roles = signal(null);         // ideas.roles: the agents, the task types and their agent, the models
export const tab = signal("board");        // the narrow layout's tab (below 1 024 px the shell is the phone's layout)
export const leftTab = signal("board");    // the left column's tab (spec 37 §8, spec 46 §6.3): "board" | "files" (a "needs" kept from before reads "board")
export const editing = signal(null);       // the file open in the editor: {path, dirty, save()}, null when none is

// The preview's tabs (docs/specs/39-map.md §3): the Map first and pinned, every other thing in a tab of its own. A click opens
// a thing in the one passing tab (replacing the one there); a double-click, an edit or Keep keeps it. At most 12 besides the
// Map; each project's tabs are kept per device (the refs only: every tab reads its thing again when shown).
export const MAP = "map";
export const MAX_TABS = 12;
export const tabs = signal([]);            // [{id, p, kept, title}] besides the Map
export const active = signal(MAP);         // MAP or a tab's id
export const mapShown = signal(false);     // below 1 024 px: the Map is on its screen (the Board's Map button)
export const mapData = signal(null);       // ideas.map
export const mapSince = signal("");        // a node updated after this is new (the last time the Map was looked at)
export const mapFolded = signal([]);       // the goals folded on the Map, kept with the tabs
export const mapUi = signal({ tasks: [], done: [], more: [] });   // what is unfolded on the Map: a node's tasks, a goal's Done, its done-when lines
export const mapView = { top: 0 };         // the Map's scroll, kept while another tab is shown

const KINDS = ["idea", "plan", "task", "result", "goal", "doc", "file", "gitdiff"];
const KIND_WORDS = { idea: "Spec", plan: "Plan", task: "Task", result: "Code", goal: "Goal", doc: "Document", file: "File", gitdiff: "Changes" };
export const kindWords = (kind) => KIND_WORDS[kind] || "";
export const tabId = (p) => `${p.kind}:${p.slug || ""}:${p.task || ""}:${p.path || ""}`;
export const narrow = () => typeof matchMedia === "function" && matchMedia("(max-width: 1023px)").matches;

/** SHA-1 as hex, synchronously (the tabs' storage key names the project by it; crypto.subtle is async and needs https). */
function sha1(text) {
  const bytes = new TextEncoder().encode(text), len = bytes.length;
  const n = (((len + 8) >> 6) + 1) * 16, w = new Uint32Array(n), W = new Uint32Array(80);
  for (let i = 0; i < len; i++) w[i >> 2] |= bytes[i] << (24 - (i % 4) * 8);
  w[len >> 2] |= 0x80 << (24 - (len % 4) * 8);
  w[n - 1] = len * 8;
  const rol = (x, s) => (x << s) | (x >>> (32 - s));
  let h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0];
  for (let i = 0; i < n; i += 16) {
    for (let t = 0; t < 16; t++) W[t] = w[i + t];
    for (let t = 16; t < 80; t++) W[t] = rol(W[t - 3] ^ W[t - 8] ^ W[t - 14] ^ W[t - 16], 1);
    let [a, b, c, d, e] = h;
    for (let t = 0; t < 80; t++) {
      const [f, k] = t < 20 ? [(b & c) | (~b & d), 0x5A827999] : t < 40 ? [b ^ c ^ d, 0x6ED9EBA1]
        : t < 60 ? [(b & c) | (b & d) | (c & d), 0x8F1BBCDC] : [b ^ c ^ d, 0xCA62C1D6];
      const tmp = (rol(a, 5) + f + e + k + W[t]) | 0;
      e = d; d = c; c = rol(b, 30); b = a; a = tmp;
    }
    h = [h[0] + a, h[1] + b, h[2] + c, h[3] + d, h[4] + e].map((x) => x | 0);
  }
  return h.map((x) => (x >>> 0).toString(16).padStart(8, "0")).join("");
}

let storeKey = "", seen = "";
/** This device's last look at the project shown (js/shell/look.js): the storage key, "" with no project; `lookTick` moves when another is shown. */
export const lookKey = () => (storeKey ? storeKey.replace("orkboard.tabs.", "orkboard.look.") : "");
export const lookTick = signal(0);
const pad = (n) => String(n).padStart(2, "0");
const nowIso = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };

function persist() {
  if (!storeKey) return;
  try {
    localStorage.setItem(storeKey, JSON.stringify({ tabs: tabs.value.map(({ p, kept, title }) => ({ p, kept, title })), active: active.value,
      seen, folded: mapFolded.value }));
  } catch { /* the tabs still work */ }
}

function readTabs(key) {
  try {
    const got = JSON.parse(localStorage.getItem(key) || "null");
    if (!got || typeof got !== "object") return null;
    const list = (Array.isArray(got.tabs) ? got.tabs : []).filter((t) => t && t.p && KINDS.includes(t.p.kind))
      .slice(0, MAX_TABS).map((t) => ({ id: tabId(t.p), p: t.p, kept: t.kept === true, title: typeof t.title === "string" ? t.title : "" }));
    return { tabs: list, active: typeof got.active === "string" ? got.active : MAP, seen: typeof got.seen === "string" ? got.seen : "",
      folded: Array.isArray(got.folded) ? got.folded.filter((x) => typeof x === "string") : [] };
  } catch { return null; }
}

/** What a tab whose thing is gone says (§3.7), "" while it is there or the Board is not read yet. */
export function goneWords(p, bd = board.value) {
  if (!p || !bd) return "";
  if (p.kind === "goal") return (bd.tracks || []).some((t) => t.slug === p.slug) ? "" : "This goal is gone";
  if (["idea", "plan", "task", "result", "doc"].includes(p.kind) && p.slug) return (bd.ideas || []).some((i) => i.slug === p.slug) ? "" : "This idea is gone";
  return "";
}

/** The Map is shown now: what moved since the last time it was looked at is new, and the use is logged. */
function mapNowShown() {
  if (!storeKey) return;
  mapSince.value = seen || nowIso();
  logOpened("map", "");
}
/** The Map is left (or the page is): that is when it was last looked at. */
function mapLeft() {
  if (!storeKey) return;
  seen = nowIso();
  persist();
}
if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => { if (active.value === MAP) mapLeft(); });
}

const LIVE = ["running", "testing"];

/** What the open preview reads besides the idea's page: a task, a result's task and its code, a goal, a linked document. */
async function detailFor(p) {
  if (p?.kind === "goal") return { goal: await ask("ideas.goal", { slug: p.slug }) };
  if (p?.kind === "doc") return { doc: await ask("ideas.doc", { path: p.path }) };
  if (!p || (p.kind !== "task" && p.kind !== "result")) return null;
  const [task, diff, spend] = await Promise.all([ask("ideas.task", { slug: p.slug, task: p.task }),
    p.kind === "result" ? ask("ideas.diff", { slug: p.slug, task: p.task }) : null,
    p.kind === "result" ? ask("ideas.spend", { idea: p.slug }) : null]);
  return { task, diff, spend };
}

let loading = false, again = false;
export async function refreshShell() {
  if (loading) { again = true; return; }
  loading = true;
  try {
    const p = preview.value;
    const wantMap = active.value === MAP && (!narrow() || mapShown.value);
    const there = (bd) => !!p && !goneWords(p, bd);
    const side = (bd) => (there(bd) ? Promise.all([detailFor(p), p.kind === "idea" || p.kind === "plan" ? ask("ideas.page", { slug: p.slug }) : null])
      : Promise.resolve([null, null]));
    const rest = Promise.all([ask("ideas.board"), ask("ideas.review_list"), ask("ideas.agents"), ask("ideas.roles"), wantMap ? ask("ideas.map") : null]);
    let b, r, a, ro, mp, d, pg;
    if (board.value) [[b, r, a, ro, mp], [d, pg]] = await Promise.all([rest, side(board.value)]);
    else { [b, r, a, ro, mp] = await rest; [d, pg] = await side(b); }   // a restored tab: its thing is looked for only if the Board has it
    batch(() => {
      if (b) board.value = b;
      if (r) review.value = r;
      if (a) agents.value = a;
      if (ro) roles.value = ro;
      if (mp && Array.isArray(mp.goals)) mapData.value = mp;
      if (preview.value === p) { if (p) detail.value = d; if (pg) page.value = pg; if (p?.kind === "goal" && d?.goal) goal.value = d.goal; }
    });
  } finally {
    loading = false;
    if (again) { again = false; refreshShell(); }
  }
}

/** A command, then everything again. */
export async function act(name, args) {
  const got = await ask(name, args);
  await refreshShell();
  return got;
}

/** What the person opened, for the day's analysis (docs/specs/33-v1-shell.md §9): the host's one loggable event. */
export function logOpened(what, ref, via = "") {
  command("ideas.log", { event: "opened", what, ref: String(ref || ""), device: "desktop", ...(via ? { via } : {}) }).catch(() => {});
}

/** Runs `then` now, or after the person says what to do with the unsaved changes of the file in the editor. */
export function leaving(then) {
  if (editing.value?.dirty) openDialog("leave", { then });
  else then();
}

/** Another project is shown: nothing of the last one stays on the page but the Map, and the tabs are that project's own. */
export function resetForProject(project = "") {
  storeKey = project ? `orkboard.tabs.${sha1(project).slice(0, 12)}` : "";
  let got = null;
  if (storeKey) got = readTabs(storeKey);
  const list = got ? got.tabs : [];
  const now = got && list.find((t) => t.id === got.active);
  batch(() => {
    editing.value = null;
    detail.value = null; page.value = null; goal.value = null;
    board.value = null; review.value = null; agents.value = null; roles.value = null;
    leftTab.value = "board";
    mapData.value = null; mapUi.value = { tasks: [], done: [], more: [] }; mapView.top = 0; mapShown.value = false;
    mapFolded.value = got ? got.folded : [];
    seen = got ? got.seen : "";
    tabs.value = list;
    active.value = now ? now.id : MAP;
    preview.value = now ? now.p : null;
    opened.value = now && (now.p.kind === "idea" || now.p.kind === "plan") ? now.p.slug : "";
  });
  lookTick.value += 1;
  if (!now) mapNowShown();
}

/** Needs you, from a card: the right column (the phone's layout: its tab, off the Map's screen), scrolled to its top and given the focus. */
export function showNeeds() {
  batch(() => { tab.value = "needs"; mapShown.value = false; });
  requestAnimationFrame(() => {
    const col = document.querySelector(".shell-review");
    const body = col?.querySelector(".shell-pane__body");
    if (body) body.scrollTop = 0;
    col?.focus({ preventScroll: true });
  });
}

function setActive(id) {
  const t = tabs.value.find((x) => x.id === id);
  const was = active.value;
  editing.value = null;
  batch(() => {
    active.value = t ? id : MAP;
    preview.value = t ? t.p : null;
    detail.value = null; page.value = null; goal.value = null;
    opened.value = t && (t.p.kind === "idea" || t.p.kind === "plan") ? t.p.slug : "";
  });
  if (was === MAP && t) mapLeft();
  if (!t && was !== MAP) mapNowShown();
  persist();
  refreshShell();
}

/** Show a tab (or the Map); unsaved changes in the file being edited are asked about first. */
export function activate(id) {
  if (id === active.value) return;
  leaving(() => setActive(id));
}

/** Below 1 024 px: the Board's Map button puts the Map on its own screen. */
export function openMap() {
  leaving(() => {
    mapShown.value = true;
    if (active.value !== MAP) setActive(MAP);
    else { mapNowShown(); refreshShell(); }
  });
}

export function keepTab(id) {
  const t = tabs.value.find((x) => x.id === id);
  if (!t || t.kept) return;
  tabs.value = tabs.value.map((x) => (x.id === id ? { ...x, kept: true } : x));
  persist();
}

export function setTabTitle(id, title) {
  const t = tabs.value.find((x) => x.id === id);
  if (!t || t.title === title) return;
  tabs.value = tabs.value.map((x) => (x.id === id ? { ...x, title } : x));
  persist();
}

function removeTab(id, toBoard = false) {
  const list = tabs.value, i = list.findIndex((t) => t.id === id);
  if (i < 0) return;
  tabs.value = list.filter((t) => t.id !== id);
  if (active.value === id) {
    const to = narrow() ? MAP : list[i - 1]?.id || MAP;     // the tab to its left, the Map at the end (the phone's layout: the Board)
    setActive(to);
    if (toBoard) mapShown.value = false;
  } else persist();
}

/** Closes a tab; the active one with unsaved changes asks first (`leaving`). */
export function closeTab(id) {
  if (id === active.value) leaving(() => removeTab(id));
  else removeTab(id);
}

/** Closes the active tab, so every caller that closes the preview after an action goes on working; the Map has no ×, and on the
 *  phone's layout Back from it leaves its screen. `toBoard`: the layout's own tabs were used, so nothing of the preview stays. */
export function closePreview({ toBoard = false } = {}) {
  if (active.value === MAP) { mapShown.value = false; return; }
  leaving(() => removeTab(active.value, toBoard));
}

export function show(p, opts = {}) {
  if (!p) { closePreview(); return; }
  leaving(() => showNow(p, opts));
}

function showNow(p, { keep = false, via = "" } = {}) {
  if (!["doc", "file", "gitdiff"].includes(p.kind)) logOpened(p.kind === "goal" ? "idea" : p.kind === "plan" && p.todo ? "todo" : p.kind,
    p.kind === "goal" ? `goal:${p.slug}` : p.task ? `${p.slug}/${p.task}` : p.todo ? `${p.slug}/${p.todo}` : p.slug, via);
  const id = tabId(p);
  const list = tabs.value;
  if (list.some((t) => t.id === id)) {                      // what already has a tab shows that tab (a plan scrolls to the to-do asked)
    tabs.value = list.map((t) => (t.id === id ? { ...t, p, kept: t.kept || keep } : t));
  } else {
    const fresh = { id, p, kept: keep, title: "" };
    const at = keep ? -1 : list.findIndex((t) => !t.kept);       // the passing tab is replaced where it stands
    let next = at < 0 ? [...list, fresh] : list.map((t, i) => (i === at ? fresh : t));
    if (next.length > MAX_TABS) {
      const old = next.find((t) => t.kept && t.id !== id);
      if (old) {
        next = next.filter((t) => t !== old);
        toast(`closed the oldest tab: ${old.title || kindWords(old.p.kind)}`, "information");
      }
    }
    tabs.value = next;
  }
  setActive(id);
}
export const showIdea = (slug, o) => show({ kind: "idea", slug }, o);
export const showPlan = (slug, todo = "", o) => show({ kind: "plan", slug, todo }, o);
export const showTask = (slug, task, o) => show({ kind: "task", slug, task }, o);
export const showGoal = (slug, o) => show({ kind: "goal", slug }, o);
export const showDoc = (slug, path, o) => show({ kind: "doc", slug, path }, o);
export const showFile = (path, o) => show({ kind: "file", path }, o);
export const showGitDiff = (path, o) => show({ kind: "gitdiff", path }, o);
export const showResult = (slug, task, o) => show({ kind: "result", slug, task }, o);

/** Something a model or a task does now: the shell looks again every 10 s. */
export function busy() {
  const b = board.value, a = agents.value;
  return !!(b && (b.ideas.some((i) => BUSY.includes(i.state)) || b.tracks.some((t) => t.state === "reading"))) || !!(a && a.roles.some((r) => (r.chips || []).some((c) => LIVE.includes(c.state) || (c.goal && c.state === "reading"))));
}

// The Agents pane's size and whether it is hidden are kept per machine; the layout works without storage.
const KEY = "orkline.shell.agents";
export function readLayout() {
  try {
    const got = JSON.parse(localStorage.getItem(KEY) || "{}");
    return { h: Number.isFinite(got.h) ? got.h : 0, hidden: got.hidden === true };
  } catch { return { h: 0, hidden: false }; }
}
export function writeLayout(layout) {
  try { localStorage.setItem(KEY, JSON.stringify(layout)); } catch { /* the layout still works */ }
}
export const agentsLayout = signal(readLayout());   // {h: px, 0 = a third of the centre, hidden}
export function setLayout(change) {
  agentsLayout.value = { ...agentsLayout.value, ...change };
  writeLayout(agentsLayout.value);
}
