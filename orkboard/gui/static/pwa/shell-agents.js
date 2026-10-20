// Agents, the second tab, a monitor (docs/specs/33-v1-shell.md §6, §8; spec 34 §3; spec 36 §5; spec 41 §8): a block per role — the Taskmaster
// says what it waits on or reads, the Grunt and the agents of your own are a card per live task (needs you first), each with its idea's
// short name small, and Edit — with + Add agent at the top (from the library, or your own). A role is one line: its head, its name, how many
// at once (×2) and what a task of it costs (≈ $0.40 a task), and under it, muted, its day and week (spent today; what a result costs and
// how often it is right the first time, once it has three merged; the Taskmaster's, its plans' tasks). A card opens its task on its own screen.
import { h, sheet, head as raceHead } from "./util.js";
import { steady } from "./shell-util.js";
import { makeAgentSheet } from "./shell-agent.js";
import { heldWords } from "./shell-words.js";
import { whoHead, CRAFT_WORDS, TIER_WORDS, RACE_WORDS } from "./shell-who.js";

const GRUNT = { running: ["working", "↻"], testing: ["testing", ""], review: ["at Review", ""], ready: ["queued", ""], held: ["held", "⏳"],
  failed: ["needs you", "⚠"] };
// The chips of a role in the order a person looks at them: what needs them, then what is moving, then what waits.
const ORDER = ["failed", "running", "testing", "ready", "held", "review"];
const rank = (c) => { const i = ORDER.indexOf(c.state); return i < 0 ? ORDER.length : i; };
const HINT = "At API prices, not your bill";
const RACE_OF = { engineering: "peon", design: "elf", data: "goblin", marketing: "gnome", product: "lich" };
const money = (n) => `≈$${n < 10 ? Number(n).toFixed(2) : Math.round(n)}`;
const FEW = 3;                                   // merged results (a Grunt's) or finished tasks (the Taskmaster's) before a week is said

export function gruntWords(c) {
  const [word, mark] = GRUNT[c.state] || [c.state, ""];
  if (c.state === "held") return heldWords(c.note, c.waits_title);
  if (c.state === "ready" && c.note) return "stopped";
  return mark ? `${word} ${mark}` : word;
}

export function makeAgents(core) {
  const el = h("section", { class: "pane agents", "aria-label": "Agents" });
  const fresh = steady(el);
  const sheetOf = makeAgentSheet(core);
  /** A role's day and week, muted under its line (spec 36 §2; the owner, 20 October): what it spent today; once it has FEW merged,
   * what a result cost and how often it was merged the first time; the Taskmaster's, how often its plans' tasks went the first time. */
  function week(role) {
    const w = role.week, today = role.spend_today ? `${money(role.spend_today)} today` : "";
    if (role.role === "taskmaster") return [today, w && w.finished >= FEW ? `${w.first_time}/${w.finished} tasks the first time` : ""].filter(Boolean).join(" · ");
    const said = w && w.merged >= FEW ? [w.usd_per_merged == null ? "" : `${money(w.usd_per_merged)} a result`, `${w.first_time}/${w.finished} the first time`] : [];
    const c = role.check_week;                     // a checker's week ends with its check (spec 43 §4.1)
    return [today, ...said, c?.checks ? `its check: ${c.checks} ${c.checks === 1 ? "idea" : "ideas"}, caught ${c.caught}` : ""].filter(Boolean).join(" · ");
  }

  /** A role in one line (spec 41 §8): its head · its name · ×2 · ≈ $0.40 a task; its words for a screen reader are on the line. */
  function head(role) {
    const hd = role.head, tm = role.role === "taskmaster";
    const usd = role.usd_task == null ? "" : `≈ $${Number(role.usd_task).toFixed(2)} a task`;
    const said = [hd ? `${/^[aeiou]/.test(RACE_WORDS[hd.race]) ? "an" : "a"} ${RACE_WORDS[hd.race]}` : "", CRAFT_WORDS[hd?.craft], TIER_WORDS[hd?.tier]].filter(Boolean).join(", ");
    // its day and week are read from the muted line under it, not said twice
    const label = [`${role.name}${said ? `: ${said}` : ""}`, tm ? "" : `up to ${role.max_parallel} at once`, usd ? `about $${Number(role.usd_task).toFixed(2)} a task` : ""]
      .filter(Boolean).join("; ");
    return h("div", { class: "role-head", role: "group", "aria-label": label },
      whoHead(hd), h("h3", {}, role.name),
      tm ? null : h("span", { class: "role-many", title: `Up to ${role.max_parallel} at once` }, `×${role.max_parallel}`),
      usd ? h("span", { class: "priced role-usd", title: HINT }, usd) : null,
      h("button", { class: "linkish", type: "button", "aria-label": `Edit ${role.name}`, onclick: () => sheetOf.open(role.role) }, "Edit"),
      week(role) ? h("small", { class: "muted role-facts", ...(week(role).includes("$") ? { title: HINT } : {}) }, week(role)) : null);
  }

  function taskmaster(role) {
    const chips = role.chips || [];
    const lead = chips.find((c) => c.state !== "waiting");
    const open = (c) => core.open(c.goal ? { kind: "goal", slug: c.goal } : { kind: "idea", slug: c.idea });
    const said = (c) => `${c.state === "talking" ? "talking about" : c.state} “${c.short || c.title}”`;
    const line = role.state === "waiting" && role.waits_on
      ? h("button", { class: "card chip is-wait", type: "button", onclick: () => core.open({ kind: "idea", slug: role.waits_on.idea }) }, role.waits_on.text)
      : lead ? h("button", { class: "card chip is-live", type: "button", onclick: () => open(lead) },
        h("span", { class: "spin", "aria-hidden": "true" }, "↻"), ` ${said(lead)}`)
        : h("p", { class: "muted" }, "Nothing to do.");
    return h("div", { class: "role", "data-role": "taskmaster" }, head(role), line);
  }

  function worker(role, done) {
    const chips = [...(role.chips || [])].sort((a, b) => rank(a) - rank(b));
    const labels = Object.fromEntries((core.st.roles?.kinds || []).map((k) => [k.kind, k.label.toLowerCase()]));
    const mine = done.filter((d) => (d.role || "grunt") === role.role);
    return h("div", { class: "role", "data-role": role.role === "grunt" ? "grunt" : "agent", "data-slug": role.role }, head(role),
      (role.kinds || []).length ? h("small", { class: "muted" }, `Takes: ${role.kinds.map((k) => labels[k] || k).join(", ")}`) : null,
      chips.length ? h("ul", { class: "chips" }, ...chips.map((c) => h("li", {},
        h("button", { class: `card chip is-${c.state}`, type: "button", "data-state": c.state, title: c.title, "aria-label": `${c.title}: ${gruntWords(c)}`,
          onclick: () => core.open({ kind: "task", slug: c.idea, task: c.task }) },
        whoHead(c.head, true), h("span", { class: "chip-state" }, gruntWords(c)), h("b", { class: "chip-name" }, c.short || c.title),
          h("small", { class: "muted chip-idea" }, [c.tag, c.idea_short || c.idea_title].filter(Boolean).join(" · ")),
          c.by === "auto" || c.night ? h("small", { class: "chip-why" }, [c.by === "auto" ? "by itself" : "", c.night ? "tonight" : ""].filter(Boolean).join(" · ")) : null))))
        : h("p", { class: "muted" }, "No task runs now."),
      mine.length ? h("details", { class: "done-today" }, h("summary", {}, `Done today (${mine.length})`),
        h("ul", { class: "chips" }, ...mine.map((d) => h("li", {}, h("button", { class: "card chip is-done", type: "button",
          onclick: () => core.open({ kind: "task", slug: d.idea, task: d.task }) }, d.title))))) : null);
  }

  // -- + Add agent: from the library (the agents this project has not), or your own (spec 41 §8) -------------------------------
  const libList = h("div", { class: "team-list library-list" });
  const choose = sheet("Add an agent", h("p", { class: "muted" }, "Pick one that comes with Orkline, or write your own."), libList,
    h("div", { class: "row" }, h("button", { class: "ork-btn big", type: "button", "data-own": "", onclick: () => { choose.close(); sheetOf.open(); } }, "Your own")));
  function drawLibrary() {
    const free = (core.st.roles?.library || []).filter((a) => !a.installed);
    libList.replaceChildren(h("h3", {}, "From the library"), ...(free.length ? free.map((a) => h("button", { class: "team-row", type: "button", "data-agent": a.id,
      "aria-label": `Add ${a.name}`, onclick: async () => {
        const got = await core.call("ideas.role_add", { id: a.id });
        if (got?.slug) { choose.close(); core.flash(`${a.name} is added.`); core.refresh(); }
      } }, raceHead(RACE_OF[a.craft] || "peon", a.tier || "warrior"), h("b", {}, a.name),
      h("small", { class: "muted" }, `${CRAFT_WORDS[a.craft] || a.craft} · ${TIER_WORDS[a.tier] || ""} · ${a.line || ""}`.replace(/ · +$/, "")),
      h("span", { class: "team-mark", "aria-hidden": "true" }, "+")))
      : [h("p", { class: "muted" }, "Every agent that comes with Orkline is already in this project.")]));
  }
  const openAdd = () => { drawLibrary(); choose.open(); };

  return {
    el,
    sheets: [sheetOf.el, choose.el],
    draw() {
      const a = core.st.agents;
      if (!fresh(JSON.stringify([a, core.st.roles]))) return;
      if (!a) { el.replaceChildren(h("h2", {}, "Agents"), h("p", { class: "muted" }, "Loading…")); return; }
      el.replaceChildren(h("div", { class: "pane-head" }, h("h2", {}, "Agents"),
        h("button", { class: "ork-btn primary", type: "button", onclick: openAdd }, "+ Add agent")),
      ...a.roles.map((r) => (r.role === "taskmaster" ? taskmaster(r) : worker(r, a.done_today || []))));
    },
  };
}
