// What the goal's window keeps of the Map (docs/specs/39-map.md, spec 42 §2, spec 49 §10): how far a goal is, why a node does not move in
// words, the flag a met goal raises once (on this phone, when its mark is on screen: not under reduced motion) and the Flags list (the goals
// met, a sheet from the menu). The trails, the idea cards and the party line were the Map's own and went with it: the goal's window is
// shell-arena.js. A flag is raised from the goal's mark in its header; its tally is the header's line.
import { h, icon, sheet } from "./util.js";
import { partyFold } from "./shell-goal.js";
import { hhmm } from "./shell-words.js";
import { NEEDS } from "./shell-map-idea.js";

/** "18:00" from a bare "HH:MM" or an ISO time. */
const until = (u) => (/^\d{1,2}:\d{2}$/.test(String(u || "")) ? u : hhmm(u));

/** Why a node that is not done does not move, in words (the Map's own words: §4.3's, as the Agents' chips). "" when it moves. */
export function waitsWords(node) {
  const w = node.waits;
  if (!w || node.state === "done") return "";
  const at = until(w.until);
  if (w.kind === "you") return NEEDS[node.needs_you] || "needs you";
  if (w.kind === "idea") return `waits for ${w.title || w.ref}`;
  if (w.kind === "files") return `same files as ${w.title || w.ref}`;
  if (w.kind === "limits") return at ? `waits for limits · after ${at}` : "waits for limits";
  if (w.kind === "reserve") return at ? `keeps your reserve · after ${at}` : "keeps your reserve";
  if (w.kind === "night") return "tonight";
  if (w.kind === "stopped") return "stopped";
  if (w.kind === "week") return `waits: the week is behind${w.until ? ` · until ${dayAt(w.until)}` : ""}`;
  return "";
}

/** "Mon 09:00" from a local `YYYY-MM-DDTHH:MM`; "" when it does not read. */
const dayAt = (iso) => {
  const d = new Date(iso);
  return !iso || Number.isNaN(d.getTime()) ? "" : `${d.toLocaleDateString("en-US", { weekday: "short" })} ${hhmm(iso)}`;
};

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** *7 ideas · 23 results · 19 the first time · ≈$38 · 9 days* (spec 42 §2.3): under a met goal's flag; a part that is null is left out. */
export function tallyWords(t) {
  if (!t) return "";
  return [count(t.ideas, "idea", "ideas"), count(t.results, "result", "results"), `${t.first_time} the first time`,
    t.usd != null && `≈$${Math.round(t.usd)}`, t.days != null && count(t.days, "day", "days")].filter(Boolean).join(" · ");
}

/** *met, says Product manager · 18 October* (spec 42 §2.4). */
export function flagWords(f) {
  const d = new Date(f.at);
  return [`met, says ${f.by}`, Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`].filter(Boolean).join(" · ");
}

/** How far a goal is, in %: its ideas done, and the share of the tasks done of each idea at work. */
export function progressOf(mine) {
  if (!mine.length) return 0;
  const done = mine.filter((n) => n.state === "done").length;
  const part = mine.filter((n) => n.state !== "done" && n.progress?.total > 0).reduce((s, n) => s + n.progress.done / n.progress.total, 0);
  return Math.round(((done + part) / mine.length) * 100);
}

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** `core`: the board's frame. Returns {sheet, open(), seed(goals), raiseWhenSeen(goal, mark), met(goals)}. */
export function makeFlags(core) {
  const st = core.st;
  const flagsKey = () => `orkboard.flags.${st.snap?.project || ""}`;
  const raisedList = () => {
    try {
      const got = JSON.parse(localStorage.getItem(flagsKey()) || "null");
      return Array.isArray(got) ? got.filter((x) => typeof x === "string") : null;
    } catch { return null; }
  };
  const keepRaised = (slugs) => {
    try { localStorage.setItem(flagsKey(), JSON.stringify([...new Set([...(raisedList() || []), ...slugs])])); } catch { /* raised again next time */ }
  };
  let watch = null;                                      // the one mark on screen waits to raise its flag
  let unwatch = null;                                    // takes its observer and its listener away

  /** A phone with no list adds every met goal without raising any (the first start after this part). */
  function seed(goals) {
    if (raisedList() === null) keepRaised(goals.filter((g) => g.verdict?.met).map((g) => g.slug));
  }

  /** The shown goal's flag is raised once, when its mark is on screen (the page visible): six steps up from the foot of its box (not under
   *  reduced motion); the slug is kept and `opened` `flag` is logged. */
  function raiseWhenSeen(goal, mark) {
    unwatch?.();                                         // the header is drawn again and again: the last one's listener goes first
    const list = goal.verdict?.met ? raisedList() : null;
    if (!list || list.includes(goal.slug)) return;
    let done = false, inView = false;                    // whether the observer last saw the mark on screen
    const raise = () => {
      if (done || !inView || document.visibilityState !== "visible") return;
      done = true;
      unwatch?.();
      keepRaised([goal.slug]);
      core.call("ideas.log", { event: "opened", what: "flag", ref: goal.slug, device: "phone" });
      if (mark && !reducedMotion()) { mark.classList.add("is-raising"); setTimeout(() => mark.classList.remove("is-raising"), 700); }
    };
    document.addEventListener("visibilitychange", raise);
    unwatch = () => {
      done = true;
      watch?.disconnect();
      watch = null;
      document.removeEventListener("visibilitychange", raise);
      unwatch = null;
    };
    if (typeof IntersectionObserver === "function") {
      watch = new IntersectionObserver((seen) => { inView = seen[seen.length - 1].isIntersecting; raise(); });
      watch.observe(mark);
    } else { inView = true; raise(); }
  }

  // -- Flags (3): the goals met, a sheet from the menu; the list is asked for when it is opened ----------------------------
  let flagsAt = null;                                    // {rev, list}: the flags as `ideas.flags` gave them for this Board
  const list = h("ul", { class: "map-flags-list" });
  const sh = sheet("Flags", list);
  const fill = (flags) => list.replaceChildren(...flags.map((f) => h("li", {}, h("button", { class: "map-flag", type: "button",
    onclick: () => { sh.close(); core.open({ kind: "goal", slug: f.goal }, "flags"); } },
    h("span", { class: "map-flag-mark", "aria-hidden": "true" }, icon("flag")),
    h("span", { class: "map-flag-body" }, h("b", {}, f.title), h("small", { class: "muted" }, flagWords(f)), h("small", { class: "muted" }, tallyWords(f.tally)))),
    partyFold(core, f.goal))));
  async function load() {
    const rev = st.map?.rev;
    if (flagsAt && flagsAt.rev === rev) { fill(flagsAt.list); return; }
    const got = await core.call("ideas.flags");
    if (got) { flagsAt = { rev, list: got.flags || [] }; fill(flagsAt.list); }
  }

  return {
    sheet: sh,
    open() { sh.open(); load(); },
    seed,
    raiseWhenSeen,
    /** How many goals are met. */
    met: (goals) => goals.filter((g) => g.verdict?.met).length,
  };
}
