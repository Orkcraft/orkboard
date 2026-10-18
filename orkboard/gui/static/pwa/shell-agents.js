// Agents, the second tab, a monitor (docs/specs/33-v1-shell.md §6, §8; spec 34 §3; spec 36 §5): a block per role — the Taskmaster says
// what it waits on or reads, the Grunt and the agents of your own are a card per live task (needs you first), each with its idea's
// title small, and Edit — with + Add agent at the top. A role's head says its model, how many at once, what it cost today and, once
// it has three merged results, its week. A card opens its task on its own screen.
import { h } from "./util.js";
import { steady } from "./shell-util.js";
import { makeAgentSheet } from "./shell-agent.js";
import { heldWords } from "./shell-words.js";

const GRUNT = { running: ["working", "↻"], testing: ["testing", ""], review: ["at Review", ""], ready: ["queued", ""], held: ["held", "⏳"],
  failed: ["needs you", "⚠"] };
// The chips of a role in the order a person looks at them: what needs them, then what is moving, then what waits.
const ORDER = ["failed", "running", "testing", "ready", "held", "review"];
const rank = (c) => { const i = ORDER.indexOf(c.state); return i < 0 ? ORDER.length : i; };
const HINT = "At API prices, not your bill";
const FEW = 3;                                   // merged results (a Grunt's) or finished tasks (the Taskmaster's) before a week is said

export function gruntWords(c) {
  const [word, mark] = GRUNT[c.state] || [c.state, ""];
  if (c.state === "held") return heldWords(c.note, c.waits_title);
  if (c.state === "ready" && c.note) return "stopped";
  return mark ? `${word} ${mark}` : word;
}

const money = (n) => `≈$${n < 10 ? n.toFixed(2) : Math.round(n)}`;

export function makeAgents(core) {
  const el = h("section", { class: "pane agents", "aria-label": "Agents" });
  const fresh = steady(el);
  const sheetOf = makeAgentSheet(core);
  const modelWords = (r) => (core.st.roles?.models || []).find((m) => m.id === r.model)?.label || (r.model ? `${r.model} (set by hand)` : "By Target");
  const priced = (text) => h("span", { class: "priced", title: HINT }, text);

  /** The week (spec 36 §2): what a result costs and how often it is merged the first time; said once there are enough to say. */
  function week(role) {
    const w = role.week;
    if (!w) return null;
    if (role.role === "taskmaster") return w.finished >= FEW ? [`${w.first_time}/${w.finished} tasks the first time`] : null;
    if (w.merged < FEW) return null;
    return [w.usd_per_merged == null ? null : priced(`${money(w.usd_per_merged)} a result`), `${w.first_time}/${w.finished} the first time`].filter(Boolean);
  }

  function head(role) {
    const bits = [modelWords(role), role.role === "taskmaster" ? null : `up to ${role.max_parallel}`,
      role.spend_today ? priced(`${money(role.spend_today)} today`) : null, ...(week(role) || [])].filter(Boolean);
    const facts = h("small", { class: "muted role-facts" });
    bits.forEach((b, i) => facts.append(...(i ? [" · "] : []), b));
    return h("div", { class: "role-head" }, h("h3", {}, role.name),
      h("button", { class: "linkish", type: "button", "aria-label": `Edit ${role.name}`, onclick: () => sheetOf.open(role.role) }, "Edit"), facts);
  }

  function taskmaster(role) {
    const chips = role.chips || [];
    const lead = chips.find((c) => c.state !== "waiting");
    const open = (c) => core.open(c.goal ? { kind: "goal", slug: c.goal } : { kind: "idea", slug: c.idea });
    const said = (c) => `${c.state === "talking" ? "talking about" : c.state} “${c.title}”`;
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
        h("button", { class: `card chip is-${c.state}`, type: "button", "data-state": c.state,
          onclick: () => core.open({ kind: "task", slug: c.idea, task: c.task }) },
        h("span", { class: "chip-state" }, gruntWords(c)), h("b", {}, c.title), h("small", { class: "muted" }, c.idea_title),
          c.by === "auto" || c.night ? h("small", { class: "chip-why" }, [c.by === "auto" ? "by itself" : "", c.night ? "tonight" : ""].filter(Boolean).join(" · ")) : null))))
        : h("p", { class: "muted" }, "No task runs now."),
      mine.length ? h("details", { class: "done-today" }, h("summary", {}, `Done today (${mine.length})`),
        h("ul", { class: "chips" }, ...mine.map((d) => h("li", {}, h("button", { class: "card chip is-done", type: "button",
          onclick: () => core.open({ kind: "task", slug: d.idea, task: d.task }) }, d.title))))) : null);
  }

  return {
    el,
    sheets: [sheetOf.el],
    draw() {
      const a = core.st.agents;
      if (!fresh(JSON.stringify([a, core.st.roles]))) return;
      if (!a) { el.replaceChildren(h("h2", {}, "Agents"), h("p", { class: "muted" }, "Loading…")); return; }
      el.replaceChildren(h("div", { class: "pane-head" }, h("h2", {}, "Agents"),
        h("button", { class: "ok-btn primary", type: "button", onclick: () => sheetOf.open() }, "+ Add agent")),
      ...a.roles.map((r) => (r.role === "taskmaster" ? taskmaster(r) : worker(r, a.done_today || []))));
    },
  };
}
