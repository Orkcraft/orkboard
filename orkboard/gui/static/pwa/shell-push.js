// Notifications on this phone (docs/specs/42-coming-back.md §3.4): a row in the drawer's *This phone* that says its state in words
// and has at most one button. The computer sends a push (gui/phone_push.py) to the subscription this phone's browser gave it: for an
// answer that waits, and once in the morning, never in the quiet hours. The tap that turns it on asks the browser for permission
// from the tap itself, then the computer for its key, then the browser to subscribe, then tells the computer the subscription.
import { h } from "./util.js";

const IOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
const STANDALONE = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
const WAYS = "When an answer waits, and once in the morning. Never in the quiet hours.";
const unb64 = (text) => Uint8Array.from(atob(text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4)), (c) => c.charCodeAt(0));

let quiet = "";                                         // the computer's quiet hours as it last said them: "23:00-09:00"

/** Why this phone cannot be notified, in words; "" when it can ask. */
export function unsupported() {
  if ("serviceWorker" in navigator && "PushManager" in window && "Notification" in window) return "";
  return IOS && !STANDALONE() ? "Add Orkline to the Home Screen to get notifications here" : "This browser cannot show notifications from Orkline";
}

async function subscription() {
  try { return await (await navigator.serviceWorker.ready).pushManager.getSubscription(); } catch { return null; }
}

/** The subscription as the computer takes it. */
function wire(sub) {
  const j = sub.toJSON ? sub.toJSON() : sub;
  return { endpoint: j.endpoint, p256dh: j.keys?.p256dh, auth: j.keys?.auth };
}

/** On every connect while on, the page sends its subscription again (an endpoint the browser renewed reaches the computer this way). */
export async function renewPush(send) {
  if (unsupported() || Notification.permission !== "granted") return;
  const sub = await subscription();
  if (!sub) return;
  const r = await send("mobile.push_on", wire(sub));
  if (r.ok && r.result?.quiet) quiet = r.result.quiet;
}

/** Unpairing unsubscribes first. */
export async function dropPush() {
  try { await (await subscription())?.unsubscribe(); } catch { /* the pairing goes all the same */ }
}

/** `ctx`: {send}. Returns {el, draw()}. */
export function makePush(ctx) {
  const el = h("div", { class: "field push-row", "aria-label": "Notifications" });
  let error = "";
  let busy = false;

  async function turnOn() {
    if (busy) return;
    busy = true;
    error = "";
    try {
      const asked = await Notification.requestPermission();                       // from the tap itself
      if (asked !== "granted") return;
      const k = await ctx.send("mobile.push_key");
      if (!k.ok) { error = k.error; return; }
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: unb64(k.result.key) });
      const r = await ctx.send("mobile.push_on", wire(sub));
      if (!r.ok) { error = r.error; await sub.unsubscribe().catch(() => {}); return; }
      quiet = r.result?.quiet || k.result.quiet || "";
    } catch (e) {
      error = e?.message || String(e);
    } finally { busy = false; draw(); }
  }

  async function turnOff() {
    await dropPush();
    await ctx.send("mobile.push_off");
    draw();
  }

  async function setQuiet(from, to) {
    if (!from.value || !to.value) return;
    const r = await ctx.send("mobile.push_quiet", { quiet: `${from.value}-${to.value}` });
    if (r.ok) { quiet = `${from.value}-${to.value}`; draw(); } else { error = r.error; draw(); }
  }

  async function draw() {
    const label = h("span", { class: "field-label" }, "Notifications");
    const no = unsupported();
    if (no) { el.replaceChildren(label, h("small", { class: "muted" }, no)); return; }
    if (Notification.permission === "denied") {
      el.replaceChildren(label, h("small", { class: "muted" }, "Notifications are off for Orkline in this phone’s settings"));
      return;
    }
    const on = Notification.permission === "granted" && Boolean(await subscription());
    const note = error ? h("small", { class: "warn" }, error) : null;
    if (!on) {
      el.replaceChildren(...[label, h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: turnOn }, "Notify this phone")),
        h("small", { class: "muted" }, WAYS), note].filter(Boolean));
      return;
    }
    const [a, b] = (quiet || "").split("-");
    const from = h("input", { class: "ork-field", type: "time", "aria-label": "Quiet from", value: a || "" });
    const to = h("input", { class: "ork-field", type: "time", "aria-label": "Quiet to", value: b || "" });
    for (const input of [from, to]) input.addEventListener("change", () => setQuiet(from, to));
    el.replaceChildren(label, h("small", { class: "muted push-state" }, quiet ? `On · quiet ${a}–${b}` : "On"),
      h("div", { class: "row night-row" }, from, h("span", {}, "to"), to),
      h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: turnOff }, "Turn off")), ...(note ? [note] : []));
  }

  draw();
  return { el, draw };
}
