// Orkboard on a phone (docs/specs/37-board-and-line.md §4): the v1 shell alone (board.js, shell-*.js), always in
// Office's calm look, with no camp file loaded or cached. The phone listener serves it as the app's page script when its
// host is Orkboard (gui/pwa.py `serve`); Orkline's phone keeps app.js, which draws the same shell in focus. It speaks the
// phone's protocol (gui/phones.py): the snapshot (`state`), a command and its `reply`, and `news` while it is open; it
// may send what a phone may in Orkboard (gui/board_host.py `BoardPhone`): the Board's commands and Stop all.

import { h, store, kept, outbox, clock, guessName } from "./util.js";
import { makeBoard } from "./board.js";

const PROTOCOL = "orkcraft.v1";
const API = 1;
const IOS = "standalone" in navigator;  // only iOS Safari has navigator.standalone
const STANDALONE = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

const app = document.getElementById("app");
const show = (...kids) => app.replaceChildren(...kids);
document.documentElement.dataset.look = "office";
document.documentElement.classList.add("focus-board");

// -- what the address brings: a pairing code, a token for an iOS Home Screen app --------------------------

const hash = new URLSearchParams(location.hash.slice(1));
let device = store.get();
if (hash.get("k") && !device) {                  // an iOS Home Screen app's first start (gui/pwa.py manifest)
  device = { id: "", token: hash.get("k"), name: guessName() };
  store.set(device);
}
const code = hash.get("pair");
// Nothing of it stays in the address: a code is once, a token is this phone's own.
if (location.hash || location.search) history.replaceState(null, "", location.pathname);

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js?app=board").catch(() => {});

// -- pairing ----------------------------------------------------------------------------------------

function unpaired(note = "") {
  ui = null;
  show(h("section", { class: "card" },
    h("h1", {}, "Orkline"),
    note && h("p", { class: "warn" }, note),
    h("p", {}, "This phone is not paired with the board yet."),
    h("p", { class: "muted" }, "On the computer: the gear → Phones → Pair a phone, then scan the second QR code, "
      + "“Open in the phone’s browser”, with this phone’s camera. Both need Tailscale, logged in, with HTTPS certificates on.")));
}

// Opened from the desktop's QR code: it pairs at once, by the phone's kind as its name.
function pairing(pairCode) {
  const msg = h("p", { class: "muted" }, "Pairing…");
  const again = h("button", { class: "ork-btn", hidden: true, onclick: () => pair(pairCode, guessName(), msg, again) }, "Try again");
  show(h("section", { class: "card" },
    h("h1", {}, "Pairing this phone"),
    h("p", {}, "It will see the board: goals and ideas, what needs you, the agents at work and the results to review. "
      + "It may answer, start, merge or send back, and stop all. It never types into a terminal."),
    msg, again));
  pair(pairCode, guessName(), msg, again);
}

async function pair(pairCode, name, msg, button) {
  button.hidden = true;
  msg.textContent = "Pairing…";
  msg.className = "muted";
  try {
    const v = await fetch("/api/version", { headers: { Authorization: `Bearer ${pairCode}` } });
    if (!v.ok) throw new Error("The code was not taken: show a new one on the computer and scan it again.");
    const version = await v.json();
    if (version.api !== API) throw new Error(`This app speaks api ${API}, the board ${version.api}: update Orkline.`);
    const r = await fetch("/api/pair", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pairCode, name }) });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `Not paired (${r.status})`);
    device = { id: body.id, token: body.token, name: body.name };
    store.set(device);
    if (IOS && !STANDALONE) homeScreen();
    else connect();
  } catch (e) {
    msg.textContent = e.message || String(e);
    msg.className = "warn";
    button.hidden = false;
  }
}

// iOS keeps a Home Screen app's storage apart from Safari's: the app the person adds opens with the token
// in its start_url once (gui/pwa.py `manifest`), and keeps it from then on.
function handOff() {
  if (!IOS || STANDALONE || !device?.token) return;
  document.getElementById("manifest").href = `manifest.webmanifest?k=${encodeURIComponent(device.token)}`;
  history.replaceState(null, "", `${location.pathname}#k=${encodeURIComponent(device.token)}`);
}

function homeScreen() {
  handOff();
  show(h("section", { class: "card" },
    h("h1", {}, `Paired: ${device.name}`),
    h("p", {}, "Now add it to the Home Screen: Share → Add to Home Screen, then open Orkline from there."),
    h("p", { class: "muted" }, "Until then this page’s address holds the phone’s key: do not share it."),
    h("button", { class: "ork-btn", onclick: () => connect() }, "Use it in Safari for now")));
}

// -- the socket ---------------------------------------------------------------------------------------

let ws = null;
let opened = false;
let retry = 1;
let retryTimer = 0;
let nextId = 1;
const waiting = new Map();
let board = null;          // the last snapshot
let ui = null;
let seenAt = 0;

function connect() {
  clearTimeout(retryTimer);
  if (!device?.token) { unpaired(); return; }
  if (ws && ws.readyState <= 1) return;
  ui = ui || layout();
  status("Connecting…");
  if (!board) {                                  // the board as it was last seen, greyed, until it answers
    const last = kept.get();
    if (last?.state) { render(last.state, last.at); offline(last.at, "Connecting…"); }
  }
  opened = false;
  ws = new WebSocket(`wss://${location.host}/ws`, [PROTOCOL, `bearer.${device.token}`]);
  ws.onopen = () => { opened = true; retry = 1; status(""); flush(); };
  ws.onmessage = (e) => {
    let msg;
    try { msg = JSON.parse(e.data); } catch { return; }
    if (msg.t === "state") { render(msg.state); online(); }
    else if (msg.t === "reply") { const w = waiting.get(msg.id); waiting.delete(msg.id); w?.(msg); }
    else if (msg.t === "news") news(msg.news || []);
  };
  ws.onclose = (e) => {
    for (const w of waiting.values()) w({ ok: false, error: "The town went away" });
    waiting.clear();
    if (e.code === 1008) {                       // forgotten on the computer: the token is dead
      store.clear();
      device = null;
      unpaired("The board forgot this phone. Pair it again to use it.");
      return;
    }
    offline(seenAt, opened ? "The board went away: trying again…" : "Cannot reach the board: is it running, and Tailscale on?");
    retryTimer = setTimeout(connect, retry * 1000);
    retry = Math.min(retry * 2, 30);
  };
}

// Away from the computer the phone shows what it last saw, greyed and said "as of", and acts on none of it; an
// answer or an idea given with no signal is kept and sent when it returns (`deliver`).
function offline(at, why) {
  if (!ui) return;
  document.documentElement.classList.toggle("offline", Boolean(board));
  for (const el of ui.content()) el.inert = Boolean(board);
  status(board && at ? `As of ${clock(at)}. ${why}` : why);
}

function online() {
  document.documentElement.classList.remove("offline");
  for (const el of ui?.content() || []) el.inert = false;
}

/** Send now, or with no signal keep it on the phone (`outbox`) and send it when the board answers again. */
async function deliver(name, args, label) {
  if (ws && ws.readyState === 1) {
    const r = await send(name, args);
    if (r.ok || r.error !== "The town went away") return r;
  }
  if (outbox.add({ name, args, label, at: Date.now() })) return { ok: true, kept: true };
  if (args?.photos) {                             // no room for the photos on this phone: the words are kept all the same
    const { photos: _left, ...rest } = args;
    if (outbox.add({ name, args: rest, label, at: Date.now() })) return { ok: true, kept: true, unphotographed: true };
  }
  return { ok: true, kept: true };
}

let flushing = false;
async function flush() {
  if (flushing) return;
  flushing = true;
  try {
    for (const item of outbox.all()) {
      if (!ws || ws.readyState !== 1) break;
      if (!outbox.claim(item.key)) continue;          // taken by another page of the app: never sent twice
      const r = await send(item.name, item.args);
      if (!r.ok && (r.error === "Not connected to the town" || r.error === "The town went away")) { outbox.restore(item); break; }
      flash(r.ok ? `Sent: ${item.label}` : `Not sent: ${item.label}. ${r.error}`);
    }
  } finally {
    flushing = false;
  }
}

function send(name, args = {}) {
  return new Promise((resolve) => {
    if (!ws || ws.readyState !== 1) { resolve({ ok: false, error: "Not connected to the town" }); return; }
    const id = nextId++;
    waiting.set(id, resolve);
    ws.send(JSON.stringify({ t: "cmd", id, name, args }));
  });
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && device?.token && (!ws || ws.readyState > 1)) connect();
});

// -- the board ----------------------------------------------------------------------------------------

function layout() {
  const parts = {
    status: h("p", { class: "status", role: "status" }),
    news: h("div", { class: "news", "aria-live": "polite" }),
  };
  parts.board = makeBoard({ send, deliver, flash, unpair: unpairHere });
  parts.content = () => parts.board.content();
  show(parts.status, parts.news, parts.board.el, ...parts.board.sheets);
  return parts;
}

function status(text) {
  if (!ui) return;
  ui.status.textContent = text;
  ui.status.hidden = !text;
}

function flash(text) {
  if (!ui || !text) return;
  const line = h("p", { class: "flash" }, text);
  ui.news.prepend(line);
  setTimeout(() => line.remove(), 6000);
}


// `keptAt`: the board comes from this phone's storage (seen then), not from the socket.
function render(s, keptAt = 0) {
  board = s;
  seenAt = keptAt || Date.now();
  if (!keptAt) kept.set(s);
  document.title = s.needs_you ? `(${s.needs_you}) Orkline` : "Orkline";
  ui.board.render(s);
}

function news(items) {
  for (const item of items) {
    flash(item.line);
    if (document.visibilityState === "hidden" && "Notification" in window && Notification.permission === "granted") {
      navigator.serviceWorker?.ready.then((reg) => reg.showNotification("Orkline", { body: item.line, tag: item.id || item.kind, icon: "icon-192.png" }));
    }
  }
  if (items.length && navigator.vibrate) navigator.vibrate(80);
}

function unpairHere() {
  if (!confirm("Unpair this phone here? Forget it on the computer too: the gear → Phones.")) return;
  store.clear();
  device = null;
  ws?.close(1000);
  unpaired();
}

// -- start ----------------------------------------------------------------------------------------------

if (code) pairing(code);
else if (device?.token) connect();
else unpaired();
