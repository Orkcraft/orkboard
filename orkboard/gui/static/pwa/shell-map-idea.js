// An expanded idea on the Map (docs/specs/48-map-ideas.md §4, §5, §7, decisions §61): the idea's card on top (its title, stage track,
// pips, ≈$, its wait, and what waits for the person: Start the work, or its results with Merge into dev · Send back · Drop), and under it
// the field — the plan's waves rising bottom-up (Wave 1 just above the members' row), a task's card in its agent's lane, tasks of one
// agent in one wave stacked with a count (a tap opens them as a sheet), the party members active in the stage in a row at the foot.
// The DOM follows the screen (the highest wave first, the members last), so the focus order is the visual order. A merged task leaves
// the field with one animation (none under reduced motion). Yellow is only on the agent the work stopped on (§6): a member who asks,
// the leader for a plan or a proposal, the agent of a failed task; a result at Review is muted ink, not a signal (decisions §54.1).
import { h, icon, sheet } from "./util.js";
import { whoHead } from "./shell-who.js";
import { resultActions, testsWords, changesWords, foundOf, foundWords } from "./shell-review.js";

export const STAGES = [["planning", "Planning"], ["implementation", "Implementation"], ["checking", "Checking"]];
export const STAGE_WORDS = Object.fromEntries(STAGES);
export const NEEDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed" };
export const TASK_WORDS = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", review: "in Review", failed: "needs you", held: "held" };
const MEMBER_WORDS = { work: "at work", next: "next", tonight: "tonight", free: "free" };
const SPIN = new Set(["work"]);
const GHOSTS = 3;                                       // merged cards that leave with the animation, in one idea, in one refresh
const GHOST_MS = 1500;
const SKIPPABLE = ["waiting", "ready", "held"];

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const usd = (n) => (n < 10 ? n.toFixed(2) : String(Math.round(n)));
const money = (n) => (n == null ? "" : `≈$${usd(n)} so far`);
export const stageOf = (n) => n.stage || (n.state === "done" ? "done" : (n.tasks || []).length && n.state === "working" ? "implementation" : "planning");

/** A member's state in words: *at work ↻*, *next*, *tonight*, *free*, or the Needs you words (`why`). */
export const memberWords = (state, why) => (state === "needs" ? NEEDS[why] || "needs you" : `${MEMBER_WORDS[state] || "free"}${SPIN.has(state) ? " ↻" : ""}`);

const left = (t) => t.state !== "merged" && t.state !== "dropped";
/** The tasks on the field in the idea's stage: the build tasks not merged in Implementation, the checks not passed in Checking. */
export function fieldTasks(n) {
  const stage = stageOf(n);
  if (stage !== "implementation" && stage !== "checking") return [];
  return (n.tasks || []).filter((t) => left(t) && (t.band === "check") === (stage === "checking"));
}

/** The lanes of an expanded idea: the leader in Planning, else the agents of its tasks in the stage, in the order they first appear. */
export function lanesOf(n, goal) {
  const party = goal.party || [];
  const info = (slug, name, head) => { const p = party.find((m) => m.slug === slug); return { slug, name: p?.name || name, head: p?.head || head, state: p?.state || "free", why: p?.why || "" }; };
  if (stageOf(n) === "planning") {
    const l = goal.leader;
    return l ? [{ ...info(l.slug, l.name, l.head), tasks: [] }] : [];
  }
  const lanes = [];
  for (const t of fieldTasks(n)) {
    const slug = t.by?.slug || "";
    let lane = lanes.find((x) => x.slug === slug);
    if (!lane) lanes.push(lane = { ...info(slug, t.by?.name || slug, t.head), tasks: [] });
    lane.tasks.push(t);
  }
  return lanes;
}

/** What a lane's member is doing on this idea: the work stopped on it (§6), else the party's state of it. */
function stateOf(n, lane) {
  if (stageOf(n) === "planning") {
    if (["asks", "plan", "proposal"].includes(n.needs_you)) return { state: "needs", why: n.needs_you };
  } else if (lane.tasks.some((t) => t.state === "failed")) return { state: "needs", why: "failed" };
  else if (lane.tasks.some((t) => t.state === "running" || t.state === "testing")) return { state: "work", why: "" };
  return lane.state === "needs" ? { state: "next", why: "" } : { state: lane.state, why: lane.why };      // a stop elsewhere is not a stop here
}

export function makeIdeaBlock(core, hooks) {
  const st = core.st;
  // -- a stack of several tasks of one agent in one wave: a tap opens them as a sheet ------------------------------------------------
  const stackBody = h("div", { class: "stack-list" });
  const stackSheet = sheet("Tasks", stackBody);

  const openTask = (n, t) => core.open({ kind: "task", slug: n.slug, task: t.id }, "map");
  const wordsOf = (t) => TASK_WORDS[t.state] || t.state;

  function openStack(n, lane, wave, tasks) {
    stackSheet.title(`${lane.name} · wave ${wave} · ${tasks.length}`);
    stackBody.replaceChildren(...tasks.map((t) => h("button", { class: `stack-row${t.state === "failed" ? " is-fail" : ""}`, type: "button", "data-task": t.id,
      onclick: () => { stackSheet.close(); openTask(n, t); } },
      whoHead(t.head, true), h("span", { class: "stack-title" }, t.short || t.title), h("small", { class: "muted" }, wordsOf(t)))));
    stackSheet.open();
  }

  /** One task's card: its short name, its state in words; dashed while it waits, danger when it failed, muted while it is in Review. */
  function taskCard(n, t, ghost = false) {
    const check = (n.checks || []).find((c) => c.task === t.id);
    const mark = t.state === "failed" ? " is-fail" : t.state === "review" ? " is-review" : t.state === "merged" ? " is-out" : SKIPPABLE.includes(t.state) ? " is-wait" : "";
    const words = t.state === "merged" ? "in dev" : wordsOf(t);
    const card = h("button", { class: `map-tcard${mark}`, type: "button", "data-task": t.id, "data-state": t.state, title: `${t.title} · ${words}`,
      "aria-label": `${t.title}: ${words}`, ...(ghost ? { "aria-hidden": "true", tabindex: "-1" } : { onclick: () => openTask(n, t) }) },
      h("span", { class: "tcard-title" }, t.short || t.title), h("span", { class: "tcard-state" }, words, t.state === "running" || t.state === "testing" ? " ↻" : ""));
    if (ghost) return h("div", { class: "map-stack card-out", "aria-hidden": "true" }, card);
    if (check && check.applies && !check.skipped && SKIPPABLE.includes(t.state)) {          // a checker's task not run yet may be skipped to spare its run
      return h("div", { class: "map-stack has-skip" }, card, h("button", { class: "map-skip", type: "button", "aria-label": `Skip the check: ${check.name}`,
        onclick: () => hooks.askSkip(n, check, true) }, icon("close")));
    }
    return card;
  }

  /** The cell of a lane in a wave: one card, or a stack (an offset edge behind it and its count). */
  function cell(n, lane, wave, tasks) {
    if (tasks.length === 1) return taskCard(n, tasks[0]);
    const front = tasks.find((t) => t.state === "failed") || tasks.find((t) => t.state === "running" || t.state === "testing") || tasks[0];
    const words = tasks.map((t) => `${t.short || t.title}, ${wordsOf(t)}`).join("; ");
    return h("div", { class: "map-stack is-stack" }, h("span", { class: "stack-back", "aria-hidden": "true" }),
      h("button", { class: `map-tcard${tasks.some((t) => t.state === "failed") ? " is-fail" : front.state === "review" ? " is-review" : ""}`, type: "button", "aria-haspopup": "dialog",
        "aria-label": `${tasks.length} tasks of ${lane.name} in wave ${wave}: ${words}`, title: words, onclick: () => openStack(n, lane, wave, tasks) },
        h("span", { class: "tcard-title" }, front.short || front.title), h("span", { class: "tcard-state" }, wordsOf(front))),
      h("span", { class: "stack-count", "aria-hidden": "true" }, String(tasks.length)));
  }

  // -- the merged cards that leave: one animation each, the first few, none under reduced motion, none on the first read --------------
  let seen = new Map(), seenGoal = "";
  const ghosts = new Map();
  /** Called once for each draw of a goal: tasks that were on the field a moment ago and are merged now are drawn leaving. */
  function observe(goalSlug, nodes) {
    const now = Date.now(), cur = new Map(), per = {};
    for (const n of nodes) for (const t of fieldTasks(n)) cur.set(`${n.slug}/${t.id}`, { idea: n.slug, task: t.id });
    if (seenGoal === goalSlug && !reducedMotion()) {
      for (const [k, info] of seen) {
        if (cur.has(k) || ghosts.has(k)) continue;
        const t = nodes.find((x) => x.slug === info.idea)?.tasks.find((x) => x.id === info.task);
        if (t?.state === "merged" && (per[info.idea] = (per[info.idea] || 0) + 1) <= GHOSTS) { ghosts.set(k, { until: now + GHOST_MS, t }); setTimeout(hooks.tick, GHOST_MS + 50); }
      }
    }
    seen = cur; seenGoal = goalSlug;
    for (const [k, g] of ghosts) if (g.until < now) ghosts.delete(k);
  }
  const ghostsOf = (n) => [...ghosts].filter(([k]) => k.startsWith(`${n.slug}/`)).map(([, g]) => g.t);

  // -- the idea's card ---------------------------------------------------------------------------------------------------------------
  function track(n) {
    const stage = stageOf(n), at = STAGES.findIndex(([k]) => k === stage);
    const done = stage === "done";
    return h("ol", { class: "stage-track", "aria-label": "Stages" }, ...STAGES.map(([k, word], i) => {
      const past = done || i < at, now = !done && i === at;
      return h("li", { class: `stage${past ? " is-past" : ""}${now ? " is-now" : ""}`, ...(now ? { "aria-current": "step" } : {}) },
        word, past ? h("span", { "aria-hidden": "true" }, " ✓") : null, past ? h("span", { class: "sr-only" }, ", passed") : null,
        now && n.round > 1 ? h("small", { class: "muted" }, ` · round ${n.round}`) : null);
    }));
  }

  function pips(n) {
    const tasks = n.tasks || [], total = tasks.length;
    if (!total) return null;
    const merged = tasks.filter((t) => t.state === "merged").length;
    const est = n.plan_estimate || n.estimate;
    return h("p", { class: "map-pips-line" },
      h("span", { class: "map-pips", "aria-hidden": "true" }, ...tasks.map((t) => h("i", { class: `pip${t.state === "merged" ? " pip-done" : t.state === "running" || t.state === "testing" ? " pip-work" : ""}` }))),
      ` ${merged} of ${total} ${total === 1 ? "task" : "tasks"} in dev`,
      n.usd != null ? h("span", { class: "muted" }, ` · ≈$${usd(n.usd)} so far`) : null,
      est ? h("span", { class: "muted" }, ` · plan ≈$${usd(est.usd_low)}–${usd(est.usd_high)}`) : null);
  }

  function resultRow(r) {
    const t = testsWords(r);
    return h("div", { class: "map-result", "data-task": r.task },
      h("b", {}, r.title),
      h("small", { class: "muted" }, r.round > 1 ? `round ${r.round} · ` : "", h("span", { class: `is-${t.tone}` }, `${t.mark} ${t.text}`.trim()), ` · ${changesWords(r.diff)}`,
        r.cost != null ? ` · $${usd(r.cost)}` : "", r.check ? ` · ${r.check}` : "", foundWords(r.findings) ? ` · ${foundWords(r.findings)}` : ""),
      foundOf(r), r.conflict ? h("small", { class: "warn" }, `⚠ ${r.conflict}`) : null,
      resultActions(core, r));
  }

  function actions(n) {
    const go = (name, done) => async () => { if (await core.call(name, { slug: n.slug, via: "map" })) { core.flash(done); core.refresh(); } };
    const plan = h("button", { class: "ork-btn big", type: "button", onclick: () => core.open({ kind: "plan", slug: n.slug }, "map") }, "Open the plan");
    if (n.needs_you === "plan" && !(n.waits_on || []).length) {
      const k = (n.tasks || []).length, est = n.estimate;
      return h("div", { class: "map-card-acts" }, h("button", { class: "ork-btn primary big", type: "button", "data-act": "start",
        "aria-label": `Start the work of “${n.title}”: ${k} ${k === 1 ? "task" : "tasks"}${est ? `, about $${usd(est.usd_low)}–${usd(est.usd_high)}` : ""}`, onclick: go("ideas.start", "Started.") }, "Start the work"), plan);
    }
    if (n.state === "plan" && n.start_at === "night" && !n.needs_you) {
      return h("div", { class: "map-card-acts" }, h("button", { class: "ork-btn primary big", type: "button", "data-act": "start-now", onclick: go("ideas.start_now", "Started.") }, "Start now"), plan);
    }
    if (n.state === "plan" || n.needs_you === "plan") return h("div", { class: "map-card-acts" }, plan);
    return null;
  }

  function card(n, words, wait, collapse) {
    const stage = stageOf(n), results = n.results || [];
    return h("div", { class: "map-card-frame" },
      h("button", { class: "map-open trail-chip map-card-title", type: "button", "aria-expanded": "true", "aria-label": `${n.title}: ${words}`, "data-words": words, title: n.title, onclick: collapse },
        h("span", { class: "idea-title" }, n.title), h("i", { class: "ork-chev", "aria-hidden": "true" })),
      track(n), pips(n), wait ? h("p", { class: "muted map-wait" }, wait) : null,
      actions(n),
      stage === "implementation" || stage === "checking"
        ? h("div", { class: "map-looks" }, h("h4", {}, "Waits for your look"),
          results.length ? h("div", {}, ...results.slice(0, 3).map(resultRow), results.length > 3 ? h("small", { class: "muted" }, `and ${results.length - 3} more`) : null)
            : h("p", { class: "muted" }, "Nothing waits for your look."))
        : null,
      h("button", { class: "linkish map-view", type: "button", onclick: () => core.open({ kind: "idea", slug: n.slug }, "map") }, "Open the idea"));
  }

  // -- the field ----------------------------------------------------------------------------------------------------------------------
  function planColumn(n, lane) {
    const stop = (cls) => ` is-stop${cls ? ` ${cls}` : ""}`;
    const cards = [];
    const k = (n.tasks || []).length, checks = (n.tasks || []).filter((t) => t.band === "check").length;
    if (k) {
      const ready = n.needs_you === "plan";
      cards.push(h("button", { class: `map-tcard${ready ? stop("") : ""}`, type: "button", title: `The plan of ${n.title}`, "aria-label": `The plan of ${n.title}${ready ? ": plan ready" : ""}`,
        onclick: () => core.open({ kind: "plan", slug: n.slug }, "map") },
        h("span", { class: "tcard-title" }, `${k - checks} ${k - checks === 1 ? "task" : "tasks"}${checks ? `, ${checks} ${checks === 1 ? "check" : "checks"}` : ""}`),
        h("span", { class: "tcard-state" }, ready ? "plan ready" : "the plan")));
    }
    for (const q of n.asked || []) {
      cards.push(h("button", { class: `map-tcard is-ask${stop("")}`, type: "button", "data-ask": "", title: q.ask, "aria-label": `${q.by?.name || lane?.name || "The leader"} asks: ${q.ask}`,
        onclick: () => core.open({ kind: "idea", slug: n.slug }, "map") },
        h("span", { class: "tcard-title" }, q.by?.head ? whoHead(q.by.head, true) : null, q.ask), h("span", { class: "tcard-state" }, "asks you")));
    }
    if (!cards.length) cards.push(h("span", { class: "muted map-empty" }, n.state === "proposed" ? "proposed" : "the plan comes"));
    return cards;
  }

  function field(n, goal) {
    const lanes = lanesOf(n, goal);
    if (!lanes.length) return null;
    const cols = lanes.length, planning = stageOf(n) === "planning";
    const waves = [];
    if (planning) waves.push({ label: "Plan", cells: [h("div", { class: "map-cell" }, ...planColumn(n, lanes[0]))] });
    else {
      const all = [...new Set(lanes.flatMap((l) => l.tasks.map((t) => t.wave || 1)))].sort((a, b) => b - a);
      const gone = ghostsOf(n);
      for (const w of all) {
        waves.push({ label: `Wave ${w}`, cells: lanes.map((l) => {
          const mine = l.tasks.filter((t) => (t.wave || 1) === w);
          const out = gone.filter((t) => (t.by?.slug || "") === l.slug && (t.wave || 1) === w).map((t) => taskCard(n, t, true));
          return h("div", { class: "map-cell" }, ...(mine.length ? [cell(n, l, w, mine)] : []), ...out);
        }) });
      }
    }
    return h("div", { class: "map-field", "data-lanes": String(Math.min(cols, 3)) },
      ...waves.map((w) => h("div", { class: "map-wave-row", role: "group", "aria-label": w.label, "data-wave": w.label },
        h("span", { class: "map-wave-label" }, w.label), h("div", { class: "map-cells" }, ...w.cells))),
      h("ul", { class: "map-members", "aria-label": "Who is on it" }, ...lanes.map((l) => {
        const s = stateOf(n, l), words = memberWords(s.state, s.why);
        return h("li", { class: `map-member${s.state === "needs" ? " is-stop" : ""}`, "data-member": l.slug, "aria-label": `${l.name}, ${words}` },
          whoHead(l.head, true), h("b", {}, l.name), h("small", { class: s.state === "needs" ? "" : "muted" }, words),
          l.tasks.length ? h("small", { class: "muted" }, ` ${l.tasks.length} ${l.tasks.length === 1 ? "task" : "tasks"}`) : null);
      })));
  }

  return { sheets: [stackSheet.el], observe, block: (n, goal, words, wait, collapse) => h("section", { class: "map-row map-idea", "data-slug": n.slug, "data-stage": stageOf(n), "aria-label": n.title },
    card(n, words, wait, collapse), field(n, goal)) };
}
