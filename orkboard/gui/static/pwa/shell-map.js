// The Map on the phone (docs/specs/39-map.md §5, decisions §53): the desktop's trail, standing up. The goals are tabs along the top,
// each with how far it is (in %), the goal the top bar shows chosen; the goal's trail runs down from how far it is through the ideas
// left to do — a step under the ideas it depends on, the ones that can go at once side by side (two at most, the rest a tap away) —
// to its flag, raised when its leader accepts it against its metrics. An idea at work shows its tasks left with the heads of the
// agents who do them, in their waves; a stop that waits for the person is a gate. What is done is not on the trail (Done shows it).
// A tap opens the idea's screen, as from the Board; *new* marks what changed since the Map was last shown on this phone. A name is its
// short one on two lines at most (spec 41 §3), the title in the element's title and label. A node that waits for the person alone has one
// button beside its chip: Start (with its price), Start now or Process now (spec 41 §4).
import { h, icon, sheet } from "./util.js";
import { foot } from "./shell-forms.js";
import { keepGoal } from "./shell-top.js";
import { rowState, trailWords } from "./shell-ideas.js";
import { goalState, partyFold } from "./shell-goal.js";
import { PRIORITY_WORDS, hhmm, dayAt } from "./shell-words.js";
import { whoHead } from "./shell-who.js";
import { price } from "./shell-preview.js";

export const MAP_VIEW = "map";

const NEEDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed" };
const seenKey = (project) => `orkboard.map.seen.${project || ""}`;

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
  if (w.kind === "week") return w.until ? `waits: the week is behind · until ${dayAt(w.until)}` : "waits: the week is behind";
  if (w.kind === "sign_in") return `waits: ${w.tool || w.title || "the tool"}'s sign-in`;
  if (w.kind === "night") return "tonight";
  if (w.kind === "stopped") return "stopped";
  return "";
}

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

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** `core`: the board's frame; `goalSheet`: New goal. Returns {section(), enter()}. */
export function makeMap(core, goalSheet) {
  const st = core.st;
  let since = 0;                                        // the time the Map was last shown before this time (ms); 0: never, nothing is new

  /** The Map is shown now: what changed after the last time is *new* until the next time. */
  function enter() {
    const key = seenKey(st.snap?.project);
    let prev = 0;
    try { prev = Number(localStorage.getItem(key)) || 0; localStorage.setItem(key, String(Date.now())); } catch { /* the Map works without it */ }
    since = prev;
  }

  // -- the flag raised once on this phone, and the Flags fold (spec 42 §2) -----------------------------------------------------
  const flagsKey = () => `orkboard.flags.${st.snap?.project || ""}`;
  const foldKey = () => `orkboard.map.flags.${st.snap?.project || ""}`;
  const raisedList = () => {
    try {
      const got = JSON.parse(localStorage.getItem(flagsKey()) || "null");
      return Array.isArray(got) ? got.filter((x) => typeof x === "string") : null;
    } catch { return null; }
  };
  const keepRaised = (slugs) => {
    try { localStorage.setItem(flagsKey(), JSON.stringify([...new Set([...(raisedList() || []), ...slugs])])); } catch { /* raised again next time */ }
  };
  let watch = null;                                      // the one trail on screen waits to raise its flag

  /** A phone with no list adds every met goal without raising any (the first start after this part). */
  function seedRaised(goals) {
    if (raisedList() === null) keepRaised(goals.filter((g) => g.verdict?.met).map((g) => g.slug));
  }

  /** The chosen goal's flag is raised once, when its trail is on screen (this tab shown, the page visible): six steps up from the foot
   *  of its box (not under reduced motion); the slug is kept and `opened` `flag` is logged. */
  function raiseWhenSeen(goal, end) {
    watch?.disconnect();
    watch = null;
    const list = goal.verdict?.met ? raisedList() : null;
    if (!list || list.includes(goal.slug)) return;
    let done = false;
    const raise = () => {
      if (done || document.visibilityState !== "visible") return;
      done = true;
      watch?.disconnect();
      document.removeEventListener("visibilitychange", raise);
      keepRaised([goal.slug]);
      core.call("ideas.log", { event: "opened", what: "flag", ref: goal.slug, device: "phone" });
      const mark = end.querySelector(".trail-flag");
      if (mark && !reducedMotion()) { mark.classList.add("is-raising"); setTimeout(() => mark.classList.remove("is-raising"), 700); }
    };
    document.addEventListener("visibilitychange", raise);
    if (typeof IntersectionObserver === "function") {
      watch = new IntersectionObserver((seen) => { if (seen.some((e) => e.isIntersecting)) raise(); });
      watch.observe(end);
    } else raise();
  }

  let flagsAt = null;                                    // {rev, list}: the flags as `ideas.flags` gave them for this Map
  /** *Flags (3)*, the goals met, a fold at the foot of the Map; the list is asked for when it is opened. */
  function flagsFold(goals) {
    const met = goals.filter((g) => g.verdict?.met).length;
    if (!met) return null;
    const list = h("ul", { class: "map-flags-list" });
    let open = false;
    try { open = localStorage.getItem(foldKey()) === "open"; } catch { /* closed */ }
    const fill = (flags) => list.replaceChildren(...flags.map((f) => h("li", {}, h("button", { class: "map-flag", type: "button", onclick: () => core.open({ kind: "goal", slug: f.goal }, "flags") },
      h("span", { class: "map-flag-mark", "aria-hidden": "true" }, icon("flag")),
      h("span", { class: "map-flag-body" }, h("b", {}, f.title), h("small", { class: "muted" }, flagWords(f)), h("small", { class: "muted" }, tallyWords(f.tally)))), partyFold(core, f.goal))));
    async function load() {
      const rev = st.map?.rev;
      if (flagsAt && flagsAt.rev === rev) { fill(flagsAt.list); return; }
      const got = await core.call("ideas.flags");
      if (got) { flagsAt = { rev, list: got.flags || [] }; fill(flagsAt.list); }
    }
    const el = h("details", { class: "map-flags", "aria-label": "Flags", open: open ? "" : null }, h("summary", {}, `Flags (${met})`), list);
    el.addEventListener("toggle", () => {
      try { localStorage.setItem(foldKey(), el.open ? "open" : "closed"); } catch { /* not kept */ }
      if (el.open) load();
    });
    if (open) load();
    return el;
  }

  const LANES = 2;                                      // stops side by side in a step, before "+N more"
  const wide = new Set();                               // the goals whose steps show every stop side by side

  /** How far a goal is, in %: its ideas done, and the share of the tasks done of each idea at work. */
  function progressOf(mine) {
    if (!mine.length) return 0;
    const done = mine.filter((n) => n.state === "done").length;
    const part = mine.filter((n) => n.state !== "done" && n.progress?.total > 0).reduce((s, n) => s + n.progress.done / n.progress.total, 0);
    return Math.round(((done + part) / mine.length) * 100);
  }

  /** A task's waves: a task is in the wave after the deepest it follows. */
  function wavesOf(tasks) {
    const wave = {};
    const of = (t, seen = new Set()) => {
      if (wave[t.id]) return wave[t.id];
      if (seen.has(t.id)) return 1;
      seen.add(t.id);
      const deps = (t.after || []).map((id) => tasks.find((x) => x.id === id)).filter(Boolean);
      return (wave[t.id] = 1 + Math.max(0, ...deps.map((d) => of(d, seen))));
    };
    tasks.forEach((t) => of(t));
    const out = [];
    for (const t of tasks) (out[wave[t.id] - 1] ||= []).push(t);
    return out.filter(Boolean);
  }

  const TASK_WORDS = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", review: "at Review", failed: "needs you", held: "held" };
  const leftOf = (node) => (node.tasks || []).filter((t) => t.state !== "merged" && t.state !== "dropped");
  /** Who does an idea now: the agent of its running task, else of its next one, else the goal's leader (it drafts and plans). */
  function stopHead(node, leader) {
    const left = leftOf(node);
    const t = left.find((x) => x.state === "running" || x.state === "testing") || left[0];
    return t?.head || leader?.head || null;
  }
  // -- skipping a check, on the trail: a checker's chip is a button (a finger's size); it asks first, saying what it spares ---------
  let skipping = null;                                 // {node, check, planned}
  const skipText = h("p", {});
  const skipBtn = h("button", { class: "ork-btn primary big", type: "button" }, "Skip it");
  const skipSheet = sheet("Skip the check?", skipText,
    foot(h("button", { class: "ork-btn big", type: "button", onclick: () => skipSheet.close() }, "Keep it"), skipBtn));
  skipBtn.addEventListener("click", async () => {
    const s_ = skipping;
    skipSheet.close();
    if (s_ && await core.call("ideas.check_skip", { slug: s_.node.slug, by: s_.check.by })) core.refresh();
  });
  const spares = (c) => { const usd = Number(st.roles?.tier_costs?.[c.tier]); return usd > 0 ? ` It spares ≈ $${usd.toFixed(2)}.` : ""; };
  function askSkip(node, check, planned) {
    skipping = { node, check, planned };
    skipText.textContent = `${check.name} does not check “${node.title}”.${spares(check)} `
      + (planned ? "Its task is taken out of the plan before it runs; it comes back with the idea's next plan." : "The plan is made without it; you can take it again until then.");
    skipSheet.open();
  }
  const takeAgain = async (node, check) => { if (await core.call("ideas.check_skip", { slug: node.slug, by: check.by, skip: false })) core.refresh(); };
  const skippable = (c) => c.applies && !c.skipped && (!c.state || ["waiting", "ready", "held"].includes(c.state));

  function tasksLeft(node, team) {
    const left = leftOf(node);
    if (node.state === "done") return null;
    const checks = node.checks || [];
    if (!left.length) {                                 // not planned yet: the checks its plan will hold, each to leave out
      const mine = checks.filter((c) => c.applies && !c.task);
      if (!mine.length || (node.tasks || []).length) return null;
      const head = (c) => (team || []).find((t) => t.slug === c.by)?.head;
      return h("div", { class: "map-tasks map-checks", "aria-label": `Checks of ${node.title}` }, ...mine.map((c) => (c.skipped
        ? h("button", { class: "map-task check-step is-skipped", type: "button", "aria-label": `Take the check again: ${c.name}`, onclick: () => takeAgain(node, c) },
          head(c) ? whoHead(head(c), true) : null, h("span", { class: "map-task-title" }, c.name), icon("plus"))
        : h("button", { class: "map-task check-step", type: "button", "aria-label": `Skip the check: ${c.name}`, onclick: () => askSkip(node, c, false) },
          head(c) ? whoHead(head(c), true) : null, h("span", { class: "map-task-title" }, c.name), icon("close")))));
    }
    const done = node.tasks.length - left.length;
    return h("div", { class: "map-tasks", "aria-label": `Tasks of ${node.title}` },
      ...wavesOf(left).map((wave, i) => h("div", { class: "map-wave", "data-wave": String(i + 1) },
        ...wave.map((t) => {
          const check = checks.find((c) => c.task === t.id);
          if (check && skippable(check)) {                // a checker's task not run yet: a button to skip it
            return h("button", { class: "map-task check-step", type: "button", "data-state": t.state, "aria-label": `Skip the check: ${check.name}`,
              onclick: () => askSkip(node, check, true) }, t.head ? whoHead(t.head, true) : null, h("span", { class: "map-task-title" }, t.short || t.title), icon("close"));
          }
          return h("span", { class: "map-task", "data-state": t.state, title: `${t.title} · ${TASK_WORDS[t.state] || t.state}` },   // the idea's screen opens it
            t.head ? whoHead(t.head, true) : null, h("span", { class: "map-task-title" }, t.short || t.title), h("span", { class: "sr-only" }, ` · ${TASK_WORDS[t.state] || t.state}`));
        }))),
      done ? h("small", { class: "muted map-tasks-done" }, `${done} done`) : null);
  }

  /** "checks 1/2": how many of the checks that apply to an idea passed. */
  function checksMark(checks) {
    const on = (checks || []).filter((c) => c.applies);
    if (!on.length) return null;
    const passed = on.filter((c) => c.state === "passed").length;
    return h("span", { class: `map-mark map-checks${passed === on.length ? " is-passed" : ""}`,
      "aria-label": `Checks: ${passed} of ${on.length} passed: ${on.map((c) => c.name).join(", ")}` }, `checks ${passed}/${on.length}`);
  }

  /** A goal's team: its agents' heads, then their names, the checkers' marked. */
  /** The goal's party: its leader, then its builders and checkers (a checker says so). */
  function teamLine(team, leader) {
    if (!(team || []).length && !leader) return null;
    const words = (team || []).map((t) => `${t.name}${t.every ? " (checks every idea)" : t.checks ? " (checks)" : ""}`).join(", ");
    return h("p", { class: "map-team muted" }, h("span", { class: "team-mark-heads" }, ...[leader, ...(team || [])].filter(Boolean).map((t) => whoHead(t.head, true))),
      leader ? ` Led by ${leader.name}${words ? ` · ${words}` : ""}` : ` Team: ${words}`);
  }

  /** The one button a node that waits for the person alone has (spec 41 §4): {label, text, aria, run} or null. */
  function actionOf(node) {
    if (node.state === "done") return null;
    const slug = node.slug, title = node.title;
    const go = (name, args, done) => async () => { if (await core.call(name, { slug, ...args, via: "map" })) { if (done) core.flash(done); core.refresh(); } };
    if (node.state === "proposed" && node.proposed_by === "trail" && !node.needs_you) {          // its goal's leader laid it out (spec 46 §7): Take, at the goal's priority
      return { icon: null, text: "Take", aria: `Take “${title}”`, run: go("ideas.proposal", { take: true }, ""), key: "take" };
    }
    if (node.needs_you === "plan" && !(node.waits_on || []).length) {
      const n = (node.tasks || []).length, cost = price(node.estimate);
      return { icon: "play", text: cost, aria: `Start “${title}”: ${n} ${n === 1 ? "task" : "tasks"}${cost ? `, about ${cost.replace(/^~/, "")}` : ""}`,
        run: go("ideas.start", {}, "Started."), key: "start" };
    }
    if (node.state === "plan" && node.start_at === "night" && !node.needs_you) {
      return { icon: "play", text: "Start now", aria: `Start “${title}” now, instead of tonight`, run: go("ideas.start_now", {}, "Started."), key: "start-now" };
    }
    if (node.state === "raw" && ["night", "hold"].includes(node.queue) && !node.held_until) {
      return { icon: null, text: "Process now", aria: `Process “${title}” now`, run: go("ideas.queue", { queue: "now" }, "The Taskmaster drafts it now."), key: "process-now" };
    }
    return null;
  }

  /** A stop: a chip — the head of who does it, its title, a mark of its state (its words for a screen reader, all of them on its
   *  screen) — and, for the idea at work, its tasks left as smaller chips with their agents' heads. */
  function row(node, titleOf, leader, team) {
    const s = rowState(node, titleOf);
    const why = waitsWords(node);
    const needsHand = node.needs_you && node.state !== "done";
    const isNew = since && node.updated && Date.parse(node.updated) > since;
    const on = (node.checks || []).filter((c) => c.applies), passed = on.filter((c) => c.state === "passed").length;
    const words = [s.text, trailWords(node), why && why !== s.text && !s.text.includes(why) ? why : "", node.by_itself ? "by itself" : "",
      node.estimate ? `≈$${node.estimate.usd_low.toFixed(2)}–${node.estimate.usd_high.toFixed(2)}` : "", on.length ? `checks ${passed}/${on.length}` : "", isNew ? "new" : ""]
      .filter(Boolean).join(" · ");
    const head = stopHead(node, leader);
    const act = actionOf(node);
    const timed = ["night", "limits", "reserve", "week"].includes(node.waits?.kind) && node.state !== "done";
    return h("li", { class: `map-row state-${node.state}${needsHand ? " needs-hand" : ""}${node.waits && !needsHand ? " is-waiting" : ""}${node.state === "proposed" ? " is-proposed" : ""}${act ? " has-act" : ""}`,
      "data-slug": node.slug },
      h("div", { class: "map-line" },
        h("button", { class: "map-open trail-chip", type: "button", "aria-label": `${node.title}: ${words}`, "data-words": words, title: node.title,
          onclick: () => core.open({ kind: "idea", slug: node.slug }, "map") },
          head ? whoHead(head, true) : h("span", { class: "trail-chip-nohead", "aria-hidden": "true" }),
          h("span", { class: "idea-title" }, node.short || node.title),
          needsHand ? h("span", { class: "trail-mark is-gate", "aria-hidden": "true" }, icon("warning-diamond"))
            : s.spin ? h("span", { class: "spin trail-mark", "aria-hidden": "true" }, "↻")
              : timed ? h("span", { class: "trail-mark", "aria-hidden": "true" }, icon("clock")) : null,
          isNew ? h("span", { class: "map-new", "aria-hidden": "true" }, "new") : null),
        act ? h("button", { class: "ork-btn map-act", type: "button", "data-act": act.key, "aria-label": act.aria, onclick: act.run },
          act.icon ? icon(act.icon) : null, act.text ? h("span", {}, act.text) : null) : null),
      tasksLeft(node, team));
  }

  /** The goal's steps: its ideas left by tier, top to bottom, the ones of a tier side by side. */
  function steps(open) {
    const by = new Map();
    for (const n of open) by.set(n.tier || 1, [...(by.get(n.tier || 1) || []), n]);
    return [...by.keys()].sort((a, b) => a - b).map((t) => by.get(t).sort((a, b) => (a.needs_you ? 0 : 1) - (b.needs_you ? 0 : 1)));
  }

  function goalSection(goal, nodes, titleOf) {
    const mine = nodes.filter((n) => n.goal === goal.slug);
    const open = mine.filter((n) => n.state !== "done"), done = mine.filter((n) => n.state === "done");
    const money = goal.usd == null ? "—" : `≈$${Math.round(goal.usd)} so far`;
    const pct = progressOf(mine);
    const all = wide.has(goal.slug);
    const flag = goal.verdict ? (goal.verdict.met ? "is-met" : "is-not") : "";
    const board = (st.board?.tracks || []).find((t) => t.slug === goal.slug), onBoard = Boolean(board);
    const line = String(board?.summary || "").split("\n").find((l) => l.trim()) || "";
    const endWords = goal.verdict ? (goal.verdict.met ? `Met · ${goal.verdict.by}` : `Not met yet · ${goal.verdict.by}`) : open.length ? "The goal" : "Its ideas are done";
    const endMark = h("div", { class: `trail-end ${flag}`, "aria-label": `The flag: ${endWords}` }, h("span", { class: "trail-flag" }, icon("flag")), h("span", {}, endWords));
    raiseWhenSeen(goal, endMark);
    return h("section", { class: "map-goal", "data-goal": goal.slug, "aria-label": goal.title },        // its title: its tab's
      line ? h("p", { class: "goal-line" }, line) : null,
      h("p", { class: "map-goal-meta" }, h("span", { class: `prio prio-${goal.priority}` }, PRIORITY_WORDS[goal.priority] || "Normal"),
        goalState(goal) ? h("span", { class: `state-word ${goal.state === "reading" ? "work" : goal.state}` }, goalState(goal)) : null,
        h("span", {}, money),
        h("button", { class: "ork-btn small", type: "button", "aria-label": `Open goal ${goal.title}`, onclick: () => core.open({ kind: "goal", slug: goal.slug }) }, "Open"),
        onBoard ? h("button", { class: "ork-btn small", type: "button", "aria-label": `Edit goal ${goal.title}`, onclick: () => goalSheet.open(goal.slug) }, "Edit") : null),
      teamLine(goal.team, goal.leader),
      (goal.done_when || []).length ? h("details", { class: "map-done-when" }, h("summary", {}, `Done when · ${goal.done_when[0]}`),
        h("ul", {}, ...goal.done_when.map((l) => h("li", {}, l)))) : null,
      h("div", { class: "trail-v" },
        h("div", { class: "trail-start" }, h("b", { class: "trail-pct", "aria-label": `${pct} % of the way` }, `${pct} %`),
          h("span", { class: "muted" }, `${done.length} of ${mine.length} ideas`)),
        open.length ? h("ol", { class: "trail-steps" }, ...steps(open).map((step) => h("li", { class: "trail-step", "data-tier": String(step[0].tier || 1) },
          h("ul", { class: `trail-lanes${all || step.length < 2 ? "" : " is-two"}` }, ...(all ? step : step.slice(0, LANES)).map((n) => row(n, titleOf, goal.leader, goal.team))),
          step.length > LANES ? h("button", { class: "linkish trail-more", type: "button", onclick: () => { if (all) wide.delete(goal.slug); else wide.add(goal.slug); core.draw(); } },
            all ? "Fewer side by side" : `+${step.length - LANES} more side by side`) : null)))
          : h("p", { class: "muted trail-empty" }, "No idea left on the way."),
        endMark,
        goal.verdict?.met && goal.verdict.tally ? h("p", { class: "muted trail-tally" }, tallyWords(goal.verdict.tally)) : null),
      done.length ? h("details", { class: "done-ideas" }, h("summary", {}, `Done (${done.length})`),
        h("ol", { class: "ideas map-ideas" }, ...done.map((n) => row(n, titleOf, goal.leader, goal.team)))) : null);
  }

  /** The goals as tabs along the top, each with how far it is; a tap shows its trail (and is the goal the Board shows). */
  function tabs(goals, nodes, on) {
    return h("nav", { class: "map-goal-tabs", role: "tablist", "aria-label": "Goals" }, ...goals.map((g) => {
      const pct = progressOf(nodes.filter((n) => n.goal === g.slug));
      return h("button", { class: `map-goal-tab${g.slug === on ? " is-on" : ""}`, type: "button", role: "tab", "aria-selected": String(g.slug === on),
        "data-goal": g.slug, title: g.title, "aria-label": `${g.title}, ${g.verdict?.met ? "met" : `${pct} %`}`, onclick: () => {
          if ((st.board?.tracks || []).some((t) => t.slug === g.slug)) {        // the Board's goal too, as the top bar's
            st.track = g.slug; st.mapGoal = ""; keepGoal(st.snap?.project, g.slug);
          } else st.mapGoal = g.slug;
          core.draw();
        } },
        h("span", { class: "map-goal-tab-title" }, g.short || g.title), h("small", {}, g.verdict?.met ? "met" : `${pct} %`),
        h("i", { class: "map-goal-tab-bar", "aria-hidden": "true" }, h("i", { class: `map-goal-tab-fill p${Math.round(pct / 10) * 10}` })));
    }));
  }

  /** The Map's nodes for the Board tab: the goals' tabs and the chosen one's trail, or why there is none. */
  function section() {
    if (st.mapError) return [h("p", { class: "muted" }, st.mapError)];
    if (!st.map) return [h("p", { class: "muted" }, "Loading…")];
    const goals = st.map.goals;
    if (!st.map.goals.length) {
      return [h("p", { class: "muted" }, "No goals yet."), h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open() }, "New goal")];
    }
    const titles = new Map(st.map.nodes.map((n) => [n.slug, n.title]));
    const titleOf = (slug) => titles.get(slug) || slug;
    const on = goals.find((g) => g.slug === st.mapGoal) || goals.find((g) => g.slug === st.track) || goals[0];
    seedRaised(goals);
    return [tabs(goals, st.map.nodes, on.slug), goalSection(on, st.map.nodes, titleOf), flagsFold(goals)].filter(Boolean);
  }

  return { section, enter, sheets: [skipSheet.el] };
}
