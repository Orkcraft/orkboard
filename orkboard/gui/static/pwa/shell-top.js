// The phone's top bar (docs/specs/33-v1-shell.md §6): the folder — the drawer of projects — · the project, small, over the goal shown, its
// craft's head (decisions §53): a tap picks another goal, Operations or the Map · ! with how many rows Needs you
// (its screen) · what is left of the AI tools as one chip, only when a tool is low or its limits were not read — the smallest of all of
// them, a tap opens each tool's windows with when they reset — · the gear: today's Spend, Stop all and the settings (Push after
// merging). No frames: the words and icons alone. It slides away as the page scrolls down and comes back as it scrolls up. Roles only:
// warning at 20 % or less left, danger at 5 % or less.
import { h, sheet, icon } from "./util.js";
import { foot } from "./shell-forms.js";
import { makeProjects } from "./shell-projects.js";
import { PRIORITY_WORDS } from "./shell-words.js";
import { CRAFT_WORDS, goalHead } from "./shell-who.js";
import { OPS_VIEW } from "./shell-ops.js";
import { MAP_VIEW } from "./shell-map.js";

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

/** `core`: the board's frame (board.js). Returns {el, sheets, render(snapshot), drawGear()}. */
export function makeTop(core, ctx) {
  const st = core.st;
  const chip = h("button", { class: "limit-chip", type: "button", hidden: true, "aria-haspopup": "dialog" });
  const spend = h("p", { class: "board-spend muted" });
  const projects = makeProjects(core, ctx);
  const goalChip = h("button", { class: "goal-chip", type: "button", "aria-haspopup": "dialog" });
  const stop = h("button", { class: "ork-btn danger board-stop", type: "button" }, "Stop all");
  const gear = h("button", { class: "bar-btn gear", type: "button", "aria-label": "Settings" }, icon("sliders"));
  const needsChip = h("button", { class: "needs-chip", type: "button", hidden: true, onclick: () => core.go("needs") });
  const el = h("header", { class: "board-bar" }, projects.chip, h("div", { class: "board-name" }, goalChip), needsChip, chip, gear);

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
    const now = st.view === OPS_VIEW || st.view === MAP_VIEW ? st.view : st.track;
    const row = (key, label, onclick, mark = null, line = null) => h("li", {}, h("button", { class: "goal-row", type: "button", "data-goal": key,
      "aria-current": key === now ? "true" : null, onclick }, mark, h("b", {}, label), line));
    goalList.replaceChildren(
      ...goals().map((g) => row(g.slug, g.title, () => show(g.slug), goalHead(g),
        h("small", { class: "muted" }, [CRAFT_WORDS[g.craft] || CRAFT_WORDS.engineering, PRIORITY_WORDS[g.priority] || "Normal", GOAL_SHORT[g.state]].filter(Boolean).join(" · ")))),
      row(OPS_VIEW, "Operations", () => show("", OPS_VIEW)),
      row(MAP_VIEW, "Map", () => { show("", MAP_VIEW); core.showMap(); }, null, h("small", { class: "muted" }, "Every goal, its ideas and tasks on one screen")));
  }
  goalChip.addEventListener("click", () => { drawGoals(); goalsSheet.open(); });
  function drawChip() {
    const g = goals().find((x) => x.slug === st.track);
    const word = st.view === OPS_VIEW ? "Operations" : st.view === MAP_VIEW ? "Map" : g ? g.title : st.board ? "No goal yet" : "";
    goalChip.hidden = !word;
    goalChip.replaceChildren(h("small", { class: "goal-chip__project" }, st.snap?.project || ""),
      h("span", { class: "goal-chip__goal" }, ...(g ? [goalHead(g)] : []), h("b", {}, word), h("span", { "aria-hidden": "true" }, "▾")));
    goalChip.setAttribute("aria-label", `Goal: ${word}. Choose another`);
  }

  // Slides away as the page scrolls down, back as it scrolls up (or near the top); never while a screen is open over the tab.
  let lastY = window.scrollY;
  window.addEventListener("scroll", () => {
    const y = window.scrollY;
    if (Math.abs(y - lastY) < SLIDE_PX) return;
    el.classList.toggle("is-away", y > lastY && y > el.offsetHeight);
    lastY = y;
  }, { passive: true });

  // Stop all: a tap asks first (the confirm is a sheet whose button sits away from this one), as the town's does.
  const really = h("button", { class: "ork-btn danger", type: "button" }, "Stop every ork");
  const stopSheet = sheet("Stop all",
    h("p", {}, "Every ork at work stops now, and every idea's tasks with them: their sessions are interrupted and their processes ended."),
    really);
  stop.addEventListener("click", () => { gearSheet.close(); stopSheet.open(); });
  really.addEventListener("click", async () => {
    stopSheet.close();
    const r = await ctx.send("halt");
    ctx.flash(r.ok ? `Stopped: ${r.result} session(s)` : r.error);
  });

  const limitsBody = h("div", { class: "limits" });
  const limitsSheet = sheet("What is left", limitsBody);
  chip.addEventListener("click", () => limitsSheet.open());
  function drawLimits(tools, unread) {
    limitsBody.replaceChildren(...tools.map((l) => h("div", { class: `limit ${levelOf(l.left)}`.trim() },
      h("b", {}, `${MARKS[l.provider] || ""} ${l.name} · ${pct(l.left)}`),
      ...(l.rows || []).map((r) => h("div", { class: "limit-row" }, h("span", {}, r.window), h("b", {}, pct(r.left)),
        h("span", { class: "muted" }, resetWords(r.reset)))))),
      ...unread.map((l) => h("div", { class: "limit" }, h("b", {}, `${MARKS[l.provider] || ""} ${l.name} · limits not read`),
        h("div", { class: "muted" }, l.error))));
  }

  // The analytics zip (gui/ideas.py `ideas.logs`), handed over the paired link and saved as a file on this phone.
  async function download(days) {
    const got = await core.call("ideas.logs", { days });
    if (!got?.data) return;
    const bytes = Uint8Array.from(atob(got.data), (c) => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }));
    const a = h("a", { href: url, download: got.name || "orkline-logs.zip" });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    ctx.flash("The logs are downloaded.");
  }

  // Pair a phone: a phone does not pair another one (the listener refuses `phones.*` to a phone, docs/design/mobile.md §2): this sheet says
  // where it is done and how the phone will reach the computer.
  const pairSheet = sheet("Pair a phone",
    h("p", {}, "A phone is paired from the computer, never from another phone: that keeps a lost phone from adding more."),
    h("ol", { class: "steps" },
      h("li", {}, "On the computer, open the gear → Pair a phone: it shows a QR code and says how long the code lasts."),
      h("li", {}, "Scan the code with this phone’s camera: Orkline opens in the browser and pairs.")),
    h("h3", {}, "How the phone reaches the computer"),
    h("ul", { class: "steps" },
      h("li", {}, "On the same Wi-Fi as the computer."),
      h("li", {}, "Anywhere on your tailnet, when Tailscale runs on the computer and the phone."),
      h("li", {}, "Away from home? Install Tailscale on the computer and the phone.")),
    foot(h("button", { class: "ork-btn primary big", type: "button", onclick: () => pairSheet.close() }, "Done")));
  const pushBox = h("input", { type: "checkbox", id: "push-after" });
  // The Board's two settings (spec 35 §5, §7, §11): plans start by themselves (on), and the night's hours.
  const autoBox = h("input", { type: "checkbox", id: "autostart" });
  const nightFrom = h("input", { class: "ork-field", type: "time", "aria-label": "Night from" });
  const nightTo = h("input", { class: "ork-field", type: "time", "aria-label": "Night to" });
  const gearSheet = sheet("Settings", spend, h("div", { class: "row" }, stop,
    h("button", { class: "ork-btn", type: "button", onclick: () => { gearSheet.close(); limitsSheet.open(); } }, "What is left")),
    h("label", { class: "check-line", for: "push-after" }, pushBox, h("span", {}, "Push after merging (sends your code to origin)")),
    h("label", { class: "check-line", for: "autostart" }, autoBox, h("span", {}, "Start plans by themselves")),
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Night"), h("div", { class: "row night-row" }, nightFrom, h("span", {}, "to"), nightTo)),
    h("h3", {}, "Your phone"),
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => pairSheet.open() }, "Pair a phone")),
    h("h3", {}, "Download today's logs"),
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => download(1) }, "Today"),
      h("button", { class: "ork-btn", type: "button", onclick: () => download(7) }, "The last 7 days")),
    h("p", { class: "muted" }, "What you did and what the orks did, kept on the computer. Off by default."));
  gear.addEventListener("click", () => {
    pushBox.checked = Boolean(core.st.review?.push);
    autoBox.checked = core.st.board?.autostart !== false;
    [nightFrom.value, nightTo.value] = String(core.st.board?.night || "01:00-07:00").split("-");
    gearSheet.open();
  });
  autoBox.addEventListener("change", async () => { await core.call("ideas.board_set", { autostart: autoBox.checked }); core.refresh(); });
  const setNight = async () => {
    if (!nightFrom.value || !nightTo.value) return;
    if (await core.call("ideas.board_set", { night: `${nightFrom.value}-${nightTo.value}` })) core.refresh();
  };
  nightFrom.addEventListener("change", setNight);
  nightTo.addEventListener("change", setNight);
  pushBox.addEventListener("change", async () => { await core.call("ideas.into", { push: pushBox.checked }); core.refresh(); });

  return {
    el,
    /** The goal shown and how many rows Needs you, drawn again with the Board. */
    draw(needs = 0) {
      needsChip.hidden = !needs;
      needsChip.classList.toggle("is-on", st.tab === "needs");
      needsChip.replaceChildren(h("b", { "aria-hidden": "true" }, "!"), h("span", {}, String(needs)));
      needsChip.setAttribute("aria-label", `Needs you, ${needs}`);
      drawChip();
      if (goalsSheet.el.open) drawGoals();
      if (window.scrollY <= el.offsetHeight) el.classList.remove("is-away");     // back at the top: always there
    },
    sheets: [...projects.sheets, goalsSheet.el, stopSheet.el, limitsSheet.el, gearSheet.el, pairSheet.el],
    render(s, rev) {
      projects.render(s, rev);
      const gold = s.hud?.show_gold ? s.hud.gold : "";
      spend.replaceChildren(...(gold ? [h("span", { class: "word" }, "Spend today"), " ", h("b", {}, gold)] : []));
      spend.hidden = !gold;
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
