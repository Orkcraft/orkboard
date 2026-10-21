// The v1 shell's state (docs/specs/33-v1-shell.md §5–§7): what the host last said of the board (js/board/store.js), of
// Review and of Agents, the Map, the gate and today's events, and the drawer's tabs (spec 39 §3, spec 49 §9; the active one is
// `preview`, and the drawer is out while `drawerOpen`). A refresh runs when the town says the ideas changed and every 10 s while
// a model or a task runs; the open task's log is read again every 5 s while it runs.
import { signal, batch } from "@preact/signals";
import { command, toast } from "../link.js";
import { ask, board, opened, page, BUSY } from "../board/store.js";
import { openDialog } from "./modals.js";

export const preview = signal(null);       // the active tab's thing, null with no tab: {kind: "idea"|"plan"|"task"|"result"|"goal"|"doc"|"file"|"gitdiff"|"gate"|"agents"|"files", slug?, task?, todo?, path?}
export const review = signal(null);        // ideas.review_list
export const agents = signal(null);        // ideas.agents
export const detail = signal(null);        // the preview's own data: {task} (ideas.task) · {task, diff, spend} (a result; spend: ideas.spend of its idea) · {goal} · {doc}
export const goal = signal(null);          // ideas.goal of the goal in the preview
export const roles = signal(null);         // ideas.roles: the agents, the task types and their agent, the models
export const editing = signal(null);       // the file open in the editor: {path, dirty, save()}, null when none is

// The drawer's tabs (docs/specs/39-map.md §3, spec 49 §9): a tab per thing opened, no pinned one. A click opens a thing in the one
// passing tab (replacing the one there); a double-click, an edit or Keep keeps it. At most 12; each project's tabs are kept per
// device (the refs only: every tab reads its thing again when shown). No active tab is the drawer closed; Esc puts the drawer
// away and keeps its tabs (`drawerOpen`), and opening anything brings it back.
export const MAX_TABS = 12;
export const tabs = signal([]);            // [{id, p, kept, title}]
export const active = signal("");          // a tab's id, "" with none
export const drawerOpen = signal(false);   // the drawer is out (its tabs are kept while it is not)
export const mapData = signal(null);       // ideas.map: always read (spec 49 §9)
export const gateData = signal(null);      // ideas.gate: what dev holds that main lacks
export const todayData = signal(null);     // ideas.today: today's events, newest first
export const mapFolded = signal([]);       // the folds kept with the tabs (the Flags fold)

const KINDS = ["idea", "plan", "task", "result", "goal", "doc", "file", "gitdiff", "gate", "agents", "files"];
const KIND_WORDS = { idea: "Spec", plan: "Plan", task: "Task", result: "Code", goal: "Goal", doc: "Document", file: "File", gitdiff: "Changes",
  gate: "Gate", agents: "Agents", files: "Files" };
export const kindWords = (kind) => KIND_WORDS[kind] || "";
export const tabId = (p) => `${p.kind}:${p.slug || ""}:${p.task || ""}:${p.path || ""}`;

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

let storeKey = "", mapLogged = false;
/** This device's last look at the project shown (js/shell/look.js): the storage key, "" with no project; `lookTick` moves when another is shown. */
export const lookKey = () => (storeKey ? storeKey.replace("orkboard.tabs.", "orkboard.look.") : "");
export const lookTick = signal(0);

function persist() {
  if (!storeKey) return;
  try {
    localStorage.setItem(storeKey, JSON.stringify({ tabs: tabs.value.map(({ p, kept, title }) => ({ p, kept, title })), active: active.value,
      open: drawerOpen.value, folded: mapFolded.value }));
  } catch { /* the tabs still work */ }
}

function readTabs(key) {
  try {
    const got = JSON.parse(localStorage.getItem(key) || "null");
    if (!got || typeof got !== "object") return null;
    const list = (Array.isArray(got.tabs) ? got.tabs : []).filter((t) => t && t.p && KINDS.includes(t.p.kind))
      .slice(0, MAX_TABS).map((t) => ({ id: tabId(t.p), p: t.p, kept: t.kept === true, title: typeof t.title === "string" ? t.title : "" }));
    const now = typeof got.active === "string" && list.some((t) => t.id === got.active) ? got.active : "";
    return { tabs: list, active: now, open: !!now && got.open !== false,
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
    const p = drawerOpen.value ? preview.value : null;
    const there = (bd) => !!p && !goneWords(p, bd);
    const side = (bd) => (there(bd) ? Promise.all([detailFor(p), p.kind === "idea" || p.kind === "plan" ? ask("ideas.page", { slug: p.slug }) : null])
      : Promise.resolve([null, null]));
    const rest = Promise.all([ask("ideas.board"), ask("ideas.review_list"), ask("ideas.agents"), ask("ideas.roles"), ask("ideas.map"), ask("ideas.gate"), ask("ideas.today")]);
    let b, r, a, ro, mp, gt, td, d, pg;
    if (board.value) [[b, r, a, ro, mp, gt, td], [d, pg]] = await Promise.all([rest, side(board.value)]);
    else { [b, r, a, ro, mp, gt, td] = await rest; [d, pg] = await side(b); }   // a restored tab: its thing is looked for only if the Board has it
    batch(() => {
      if (b) board.value = b;
      if (r) review.value = r;
      if (a) agents.value = a;
      if (ro) roles.value = ro;
      if (mp && Array.isArray(mp.goals)) mapData.value = mp;
      if (gt && typeof gt.same === "boolean") gateData.value = gt;
      if (td && Array.isArray(td.events)) todayData.value = td;
      if (p && drawerOpen.value && preview.value === p) { detail.value = d; if (pg) page.value = pg; if (p.kind === "goal" && d?.goal) goal.value = d.goal; }
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

/** Another project is shown: nothing of the last one stays on the page, and the tabs are that project's own. */
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
    mapData.value = null; gateData.value = null; todayData.value = null;
    mapFolded.value = got ? got.folded : [];
    tabs.value = list;
    active.value = now ? now.id : "";
    preview.value = now ? now.p : null;
    drawerOpen.value = !!now && got.open;
    opened.value = now && (now.p.kind === "idea" || now.p.kind === "plan") ? now.p.slug : "";
  });
  lookTick.value += 1;
  if (storeKey && !mapLogged) { mapLogged = true; logOpened("map", ""); }       // the window is shown: once a page load
}

/** The stops along the bottom, from a card (While you were away): the goal of the first one is shown and the first is in focus. */
export const needsFocus = signal(0);
export function showNeeds() {
  needsFocus.value += 1;
}

function setActive(id) {
  const t = tabs.value.find((x) => x.id === id);
  editing.value = null;
  batch(() => {
    active.value = t ? id : "";
    preview.value = t ? t.p : null;
    drawerOpen.value = !!t;
    detail.value = null; page.value = null; goal.value = null;
    opened.value = t && (t.p.kind === "idea" || t.p.kind === "plan") ? t.p.slug : "";
  });
  persist();
  refreshShell();
}

/** Show a tab; unsaved changes in the file being edited are asked about first. */
export function activate(id) {
  if (id === active.value && drawerOpen.value) return;
  leaving(() => setActive(id));
}

/** Esc, or the drawer's ×: the drawer goes away and keeps its tabs; opening anything brings it back. */
export function hideDrawer() {
  if (!drawerOpen.value) return;
  leaving(() => { drawerOpen.value = false; persist(); });
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

function removeTab(id) {
  const list = tabs.value, i = list.findIndex((t) => t.id === id);
  if (i < 0) return;
  tabs.value = list.filter((t) => t.id !== id);
  if (active.value === id) setActive(list[i - 1]?.id || list[i + 1]?.id || "");      // the tab to its left, else to its right; none: the drawer goes
  else persist();
}

/** Closes a tab; the active one with unsaved changes asks first (`leaving`). */
export function closeTab(id) {
  if (id === active.value) leaving(() => removeTab(id));
  else removeTab(id);
}

/** Closes the active tab, so every caller that closes the preview after an action goes on working. */
export function closePreview() {
  if (!active.value) { if (drawerOpen.value) hideDrawer(); return; }
  leaving(() => removeTab(active.value));
}

export function show(p, opts = {}) {
  if (!p) { closePreview(); return; }
  leaving(() => showNow(p, opts));
}

function showNow(p, { keep = false, via = "" } = {}) {
  if (p.kind === "agents" || p.kind === "files") logOpened("tab", p.kind, via);
  else if (p.kind === "gate") logOpened("gate", "", via);
  else if (!["doc", "file", "gitdiff"].includes(p.kind)) logOpened(p.kind === "goal" ? "idea" : p.kind === "plan" && p.todo ? "todo" : p.kind,
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
export const showGate = (o) => show({ kind: "gate" }, o);
export const showAgents = (o) => show({ kind: "agents" }, { keep: true, ...o });      // the panes are kept: a file or a task opened from them is a tab of its own
export const showFiles = (o) => show({ kind: "files" }, { keep: true, ...o });

/** Something a model or a task does now: the shell looks again every 10 s. */
export function busy() {
  const b = board.value, a = agents.value;
  return !!(b && (b.ideas.some((i) => BUSY.includes(i.state)) || b.tracks.some((t) => t.state === "reading"))) || !!(a && a.roles.some((r) => (r.chips || []).some((c) => LIVE.includes(c.state) || (c.goal && c.state === "reading"))));
}
