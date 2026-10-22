// Two sheets (docs/specs/49-one-window.md §7, §8, §10.4; spec 50 §6.1): Today, the day of the party shown (what happened since midnight, newest first,
// a tap opens it; then the Done goals), and What is left of your AI tools (a line per tool: its mark and name, ten diamonds, the last one hatched for the reserve
// kept for tonight, its %, and when the tightest window resets). Both are bottom sheets (util.js `sheet`). Today's button is an item of the menu (a clock, *Today* and the
// count of the day's events); the tools' is in the top bar: the worst tool's diamonds alone (its % is in the sheet, the label and the title). The words and the lists come in (shell-arena.js); nothing is read here.
import { h, sheet, icon } from "./util.js";
import { WARN, levelOf, pct } from "./shell-limits.js";
import { glyph, sign } from "./shell-marks.js";

const MARKS = new Set(["claude", "codex", "agy", "cursor", "hermes", "pi", "pipeline"]);   // the tools orkUI draws a mark for
const TONE = { ok: "ok", danger: "no", muted: "muted", alert: "alert", ink: "" };      // alert: a *Pick one* that waits

/** "resets at 18:00", or with the day when it is not today. */
export function resetWords(iso, now = new Date()) {
  const d = new Date(iso);
  if (!iso || Number.isNaN(d.getTime())) return "";
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  return d.toDateString() === now.toDateString() ? `resets at ${hm}` : `resets ${d.toLocaleDateString([], { weekday: "short" })} ${hm}`;
}

/** A tool's mark at 16 × 16 from orkUI's marks (its first letter for a tool without one). */
function toolMark(l) {
  const id = String(l.provider || "");
  return MARKS.has(id) ? h("img", { class: "ork-mark", src: `marks/harness-${id}.png`, srcset: `marks/harness-${id}@2x.png 2x`, width: 16, height: 16, alt: "", draggable: "false" })
    : h("span", { class: "tool-letter", "aria-hidden": "true" }, (l.name || "?")[0]);
}

/** `n` diamonds of `total`, `kept` of the lit ones hatched (what the Board keeps for tonight). */
function crystals(on, total, kept = 0) {
  return h("span", { class: "ork-crystals", "aria-hidden": "true" },
    ...Array.from({ length: total }, (_, i) => h("i", { class: i < on - kept ? "on" : i < on ? "kept" : "" })));
}

/** The tightest window of a tool (the one with the least left) and when it resets. */
const tightest = (l) => (l.rows || []).filter((r) => typeof r.left === "number").reduce((a, b) => (a && a.left <= b.left ? a : b), null);

/** A row's title: the gate's (*dev → main*, the host writes it with the arrow) draws the arrow as orkUI's sign; what a person or an agent wrote keeps its words. */
function titleOf(e) {
  const gate = e.open?.kind === "gate" && /^(.+) → (.+)$/.exec(e.title || "");
  return gate ? [gate[1], " ", sign("after"), " ", gate[2]] : [e.title];
}

/** `core`: the board's frame. Returns {el, sheet, set({events, done}), open()}: the menu's Today item and its sheet. */
export function makeToday(core) {
  const count = h("span", { class: "ork-count" }, "0");
  const el = h("button", { class: "ork-btn menu-today", type: "button", "aria-haspopup": "dialog", "aria-label": "Today: what happened, no events", "data-act": "today" }, icon("clock"), "Today", count);
  const body = h("div", { class: "today" });
  const sh = sheet("Today", body);
  let shown = { events: [], done: [] };

  function draw() {
    const { events, done } = shown;
    body.replaceChildren(
      events.length ? h("div", { class: "today-list" }, ...events.map((e) => h("button", { class: "hrow", type: "button", "data-open": e.open?.kind || "",
        onclick: () => { sh.close(); e.go?.(); } },
      h("span", { class: `hrow__mark ${TONE[e.tone] ?? ""}`.trim(), "aria-hidden": "true" }, glyph(e.mark, e.words)),
      h("span", { class: "hrow__body" }, h("span", { class: "hrow__what" }, ...titleOf(e)), h("span", { class: "cap" }, `${e.at} · ${e.words}`)))))
        : h("p", { class: "muted" }, "Nothing happened on this party today."),
      h("h3", {}, `Done · ${done.length}`),
      ...done.map((d) => h("button", { class: "hrow done-row", type: "button", "data-idea": d.slug, onclick: () => { sh.close(); d.go?.(); } },
        h("span", { class: "hrow__mark ok", "aria-hidden": "true" }, sign("check")),
        h("span", { class: "hrow__body" }, h("span", { class: "hrow__what" }, d.title), h("span", { class: "cap" }, d.words)))));
  }
  el.addEventListener("click", () => { draw(); sh.open(); core.log("today"); });
  return {
    el,
    sheet: sh,
    /** The events of the goal shown (newest first) and its Done ideas: `{events: [{at, mark, tone, words, title, open, go}], done: [{slug, title, words, go}]}`. */
    set(data) {
      shown = data;
      count.textContent = String(data.events.length);
      el.setAttribute("aria-label", `Today: what happened, ${data.events.length === 1 ? "1 event" : `${data.events.length} events`}`);
      if (sh.el.open) draw();
    },
    open: () => el.click(),
  };
}

/** `core`: the board's frame. Returns {el, sheet, render(snapshot), open()}: the bar's chip (the worst tool's diamonds) and the sheet it opens. */
export function makeTools(core) {
  const chip = h("button", { class: "limit-chip", type: "button", hidden: true, "aria-haspopup": "dialog" });
  const body = h("div", { class: "limits" });
  const sh = sheet("What is left of your AI tools", body);
  chip.addEventListener("click", () => sh.open());
  return {
    el: chip,
    sheet: sh,
    open: () => sh.open(),
    render(s) {
      const all = s.limits || [];
      const tools = all.filter((l) => typeof l.left === "number");
      const unread = all.filter((l) => typeof l.left !== "number" && l.error);   // turned on, not read: never missing without a word
      const keep = Math.round((s.reserve?.share || 0) * 10);
      const lines = tools.map((l) => {
        const on = Math.round(l.left * 10), kept = l.provider === "claude" ? Math.min(on, keep) : 0, at = tightest(l);
        const words = at && at.reset ? resetWords(at.reset) : "";
        const tip = `${l.name}: ${pct(l.left)} left${kept ? `, ${kept * 10} % of it kept for ${s.reserve?.night ? "the morning" : "tonight"}` : ""}${words ? ` · ${words}` : ""}`;
        return [h("div", { class: `crow ${levelOf(l.left)}`.trim(), title: tip, "data-tool": l.provider },
          toolMark(l), h("span", { class: "crow__name" }, l.name), crystals(on, 10, kept), h("b", {}, pct(l.left))),
        words ? h("span", { class: "cap crow__reset" }, `${l.name} ${words}`) : null];
      });
      const keeps = tools.some((l) => l.provider === "claude") && keep > 0;
      body.replaceChildren(...lines.flat().filter(Boolean),
        ...unread.map((l) => h("div", { class: "crow", "data-tool": l.provider }, toolMark(l), h("span", { class: "crow__name" }, l.name), h("span", { class: "muted" }, "not read"),
          h("span", { class: "cap crow__reset" }, l.error))),
        ...(keeps ? [h("span", { class: "cap faint" }, `hatched: kept for ${s.reserve?.night ? "the morning" : "tonight"}`)] : []));
      chip.hidden = !tools.length && !unread.length;
      if (chip.hidden) return;
      if (tools.length) {
        const worst = tools.reduce((a, b) => (b.left < a.left ? b : a));
        chip.className = `limit-chip ${levelOf(worst.left)}`.trim();
        chip.replaceChildren(toolMark(worst), crystals(Math.round(worst.left * 5), 5));       // the diamonds alone, so that the party's name has the room: the number is the sheet's, the label's and the title's
        chip.setAttribute("aria-label", `What is left of your AI tools: ${worst.name} ${pct(worst.left)}`);
        chip.title = `${worst.name}: ${pct(worst.left)} left`;
      } else {
        chip.className = "limit-chip";
        chip.replaceChildren(toolMark(unread[0]), " ", h("b", {}, "?"));
        chip.setAttribute("aria-label", `What is left of your AI tools: ${unread[0].name} not read`);
        chip.title = `${unread[0].name}: not read`;
      }
    },
  };
}
