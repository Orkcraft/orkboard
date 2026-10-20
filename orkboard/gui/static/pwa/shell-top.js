// The phone's top bar (docs/specs/33-v1-shell.md §6, spec 41 §2): the menu mark — it opens the drawer: Stop all, Spend today, the projects, the
// project's settings and the phone's (shell-projects.js, shell-drawer.js) · the goal shown, its craft's head (decisions §53) and its short name on one
// line: a tap picks another goal, Operations or the Map · what is left of the AI tools as one chip, only when a tool is low or its limits were not
// read — the smallest of all of them, a tap opens each tool's windows with when they reset. No frames: the words and icons alone. It slides away
// as the page scrolls down and comes back as it scrolls up. Roles only: warning at 20 % or less left, danger at 5 % or less.
import { h, sheet, icon } from "./util.js";
import { foot } from "./shell-forms.js";
import { makeProjects } from "./shell-projects.js";
import { makeSettings } from "./shell-drawer.js";
import { PRIORITY_WORDS } from "./shell-words.js";
import { CRAFT_WORDS, goalHead, goalMark } from "./shell-who.js";
import { OPS_VIEW } from "./shell-ops.js";

import { WARN, DANGER, levelOf, pct } from "./shell-limits.js";

export { WARN, DANGER, levelOf };
const MARKS = { claude: "✱", agy: "∩", codex: "◇", hermes: "☿", pi: "π", cursor: "▷" };
const GOAL_KEPT = "orkcraft.goal";                    // {project: goal slug}: the goal this phone showed last

/** The goal this phone showed last in this project ("" none). */
export const keptGoal = (project) => { try { return (JSON.parse(localStorage.getItem(GOAL_KEPT)) || {})[project || ""] || ""; } catch { return ""; } };
export function keepGoal(project, slug) {
  try { localStorage.setItem(GOAL_KEPT, JSON.stringify({ ...(JSON.parse(localStorage.getItem(GOAL_KEPT)) || {}), [project || ""]: slug })); } catch { /* this run only */ }
}
const GOAL_SHORT = { reading: "reading", asks: "asks you", ready: "ready" };
const SLIDE_PX = 6;                       // a scroll this far down hides the bar, this far up brings it back

/** "resets at 18:00", or with the day when it is not today. */
export function resetWords(iso, now = new Date()) {
  const d = new Date(iso);
  if (!iso || Number.isNaN(d.getTime())) return "";
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  return d.toDateString() === now.toDateString() ? `resets at ${hm}` : `resets ${d.toLocaleDateString([], { weekday: "short" })} ${hm}`;
}

/** `core`: the board's frame (board.js). Returns {el, sheets, render(snapshot), draw()}. */
export function makeTop(core, ctx) {
  const st = core.st;
  const chip = h("button", { class: "limit-chip", type: "button", hidden: true, "aria-haspopup": "dialog" });
  const limitsBody = h("div", { class: "limits" });
  const limitsSheet = sheet("What is left", limitsBody);
  const settings = makeSettings(core, ctx, { close: () => projects.sheet.close() }, () => limitsSheet.open());
  const projects = makeProjects(core, ctx, settings);
  const menu = h("button", { class: "bar-btn menu", type: "button", "aria-label": "Menu", "aria-haspopup": "dialog", onclick: () => projects.open() }, icon("menu"));
  const goalChip = h("button", { class: "goal-chip", type: "button", "aria-haspopup": "dialog" });
  const el = h("header", { class: "board-bar" }, menu, h("div", { class: "board-name" }, goalChip), chip);

  // -- the goal shown: a sheet of the goals (their heads, priority and state), Operations, the Map, and New goal --------------
  const goalList = h("ul", { class: "goal-list" });
  const goalsSheet = sheet("Goals", goalList, foot(h("button", { class: "ork-btn primary big", type: "button",
    onclick: () => { goalsSheet.close(); core.editGoal(""); } }, "New goal")));
  const goals = () => (st.board?.tracks || []).filter((t) => t.slug !== "general" || t.count);   // General once it holds ideas (older ones)
  function show(track, view = "") {
    goalsSheet.close();
    if (track) { st.track = track; keepGoal(st.snap?.project, track); }
    st.view = view;
    if (st.tab !== "board") core.go("board");
    core.draw();
    window.scrollTo(0, 0);
  }
  function drawGoals() {
    const now = st.view === OPS_VIEW ? st.view : st.track;
    const row = (key, label, onclick, mark = null, line = null) => h("li", {}, h("button", { class: "goal-row", type: "button", "data-goal": key,
      "aria-current": key === now ? "true" : null, onclick }, mark, h("b", {}, label), line));
    goalList.replaceChildren(
      ...goals().map((g) => row(g.slug, g.title, () => show(g.slug), goalMark(g, st.roles?.roles, (g.team || []).length > 1),
        h("small", { class: "muted" }, [CRAFT_WORDS[g.craft] || CRAFT_WORDS.engineering, PRIORITY_WORDS[g.priority] || "Normal", GOAL_SHORT[g.state]].filter(Boolean).join(" · ")))),
      row(OPS_VIEW, "Operations", () => show("", OPS_VIEW)));
  }
  goalChip.addEventListener("click", () => { drawGoals(); goalsSheet.open(); });
  function drawChip() {
    const g = goals().find((x) => x.slug === st.track);
    const word = st.view === OPS_VIEW ? "Operations" : g ? (g.short || g.title) : st.board ? "No goal yet" : "";
    const full = st.view === OPS_VIEW ? "Operations" : g ? g.title : word;
    goalChip.hidden = !word;
    goalChip.replaceChildren(h("span", { class: "goal-chip__goal" }, ...(g ? [goalHead(g)] : []), h("b", {}, word), h("span", { "aria-hidden": "true" }, "▾")));   // the craft's head: the team's are on its card
    goalChip.setAttribute("aria-label", `Goal: ${full}. Choose another`);
    goalChip.title = full;
  }

  // Slides away as the page scrolls down, back as it scrolls up (or near the top); never while a screen is open over the tab.
  let lastY = window.scrollY;
  window.addEventListener("scroll", () => {
    const y = window.scrollY;
    if (Math.abs(y - lastY) < SLIDE_PX) return;
    el.classList.toggle("is-away", y > lastY && y > el.offsetHeight);
    lastY = y;
  }, { passive: true });

  chip.addEventListener("click", () => limitsSheet.open());
  function drawLimits(tools, unread) {
    limitsBody.replaceChildren(...tools.map((l) => h("div", { class: `limit ${levelOf(l.left)}`.trim() },
      h("b", {}, `${MARKS[l.provider] || ""} ${l.name} · ${pct(l.left)}`),
      ...(l.rows || []).map((r) => h("div", { class: "limit-row" }, h("span", {}, r.window), h("b", {}, pct(r.left)),
        h("span", { class: "muted" }, resetWords(r.reset)))))),
      ...unread.map((l) => h("div", { class: "limit" }, h("b", {}, `${MARKS[l.provider] || ""} ${l.name} · limits not read`),
        h("div", { class: "muted" }, l.error))));
  }

  return {
    el,
    /** The goal shown, drawn again with the Board. */
    draw() {
      drawChip();
      projects.sync();
      if (goalsSheet.el.open) drawGoals();
      if (window.scrollY <= el.offsetHeight) el.classList.remove("is-away");     // back at the top: always there
    },
    sheets: [...projects.sheets, goalsSheet.el, limitsSheet.el],
    render(s, rev) {
      projects.render(s, rev);
      settings.render(s);
      const tools = (s.limits || []).filter((l) => typeof l.left === "number");
      const unread = (s.limits || []).filter((l) => typeof l.left !== "number" && l.error);   // turned on, not read: never missing without a word
      const low = tools.some((l) => l.left <= WARN);
      chip.hidden = !low && !unread.length;                       // the chip is a signal; New goal, Take and Start say the rest
      drawLimits(tools, unread);
      if (chip.hidden) return;
      if (tools.length) {
        const worst = tools.reduce((a, b) => (b.left < a.left ? b : a));
        chip.className = `limit-chip ${levelOf(worst.left)}`.trim();
        chip.replaceChildren(h("span", { "aria-hidden": "true" }, MARKS[worst.provider] || worst.name[0]), " ", h("b", {}, pct(worst.left)),
          levelOf(worst.left) ? h("span", { "aria-hidden": "true" }, " ⚠") : null);
        chip.setAttribute("aria-label", `${worst.name}: ${pct(worst.left)} left`);
      } else {
        chip.className = "limit-chip";
        chip.replaceChildren(h("span", { "aria-hidden": "true" }, MARKS[unread[0].provider] || unread[0].name[0]), " ", h("b", {}, "?"));
        chip.setAttribute("aria-label", `${unread[0].name}: limits not read`);
      }
    },
  };
}
