// The preview on its own full screen (docs/specs/33-v1-shell.md §6, §8): a goal's spec (29a's sections view), a goal's plan
// (scrolled to a to-do, said what it unblocks), a task (brief, state, log), a result's code (commits, then the files, each
// patch folded and scrolling sideways inside its own box — the page never does) or a *Pick one* (its tiles one to a screen, swiped; the note and the two answers under them:
// shell-pick-answer.js). Back (and the system back gesture) returns to the tab it came from; its actions sit in a bar pinned at the bottom.
import { h, icon } from "./util.js";
import { pctOf, pctRange, pctShort } from "./shell-spend.js";
import { pointedAt } from "./shell-lens.js";
import { steady } from "./shell-util.js";
import { stateWords } from "./shell-board.js";
import { resultActions, factsOf, foundOf, mergeReason } from "./shell-review.js";
import { gruntWords } from "./shell-agents.js";
import { goalBody, leaderName } from "./shell-goal.js";
import { changePrice, changeWords } from "./shell-arena-words.js";
import { heldWords } from "./shell-words.js";
import { limitsNote } from "./shell-limits.js";
import { who, whoHead, headWords, TIER_WORDS } from "./shell-who.js";
import { gateScreen } from "./shell-gate.js";
import { sign } from "./shell-marks.js";
import { pointerGuard } from "./shell-motion.js";
import { pickRow, pickSig, stopAll } from "./shell-picks.js";
import { screenBody } from "./shell-pick-answer.js";

const TALK_SHOWN = 6;
const LOG_MS = 5000;
const BUSY = new Set(["reading", "planning", "working"]);
// A section's colour role (app.css `.sec-*`), its mark (Office) and its kit icon.
const SECTIONS = { Gist: ["action", "✦"], Why: ["gold", "❖"], In: ["success", "＋"], Out: ["muted", "－"], Risks: ["danger", "⚠"],
  "Open questions": ["warning", "❓"], Estimate: ["gold", "≈"], Stages: ["action", "☰"], Decisions: ["muted", "✎"] };
const TASK_WORDS = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", picking: "asks you to pick", review: "at Review", merged: "merged",
  failed: "needs you", held: "held" };

// The party's leader as the preview's talk and plan say it (spec 62 §5): *the Taskmaster* inside a sentence, *The Taskmaster* at its start, any other leader by its name.
const the = (name) => (name === "Taskmaster" ? "the Taskmaster" : name);
const The = (name) => (name === "Taskmaster" ? "The Taskmaster" : name);
/** *Gist, Done when and Out*. */
const joined = (names) => (names.length < 2 ? names.join("") : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`);

const usd = (x) => `$${Number(x) < 10 ? Number(x).toFixed(1) : Math.round(Number(x))}`;
export const price = (e) => (e ? `~${pctRange(e.usd_low, e.usd_high) || `${usd(e.usd_low)}–${Number(e.usd_high) < 10 ? Number(e.usd_high).toFixed(1) : Math.round(Number(e.usd_high))}`}` : "");

const STAGES = ["goal", "spec", "plan", "work", "rework", "dropped"];

/** A goal's money so far (spec 36 §5): `≈$3.10 — party 0.40 · spec 0.50 …`, the stages at 0 left out; `—` when all are unpriced. */
export function spendLine(s) {
  if (!s) return "";
  const cents = (n) => Number(n).toFixed(2);
  if (s.usd == null) return "This goal so far: —";
  const parts = STAGES.filter((k) => s.stages?.[k]?.usd).map((k) => `${k === "goal" ? "party" : k} ${pctShort(s.stages[k].usd) || cents(s.stages[k].usd)}`);      // the leader reading the party
  return `This goal so far: ≈${pctOf(s.usd) || `$${cents(s.usd)}`}${parts.length ? ` — ${parts.join(" · ")}` : ""}`;
}

/** "tasks k2 and k3 wait for it": the tasks a to-do holds back. */
export function unblocks(todo) {
  const ids = todo.for || [];
  if (!ids.length) return "";
  const list = ids.length === 1 ? ids[0] : `${ids.slice(0, -1).join(", ")} and ${ids[ids.length - 1]}`;
  return `${ids.length === 1 ? "task" : "tasks"} ${list} ${ids.length === 1 ? "waits" : "wait"} for it`;
}

/** `core`: the board's frame; `ctx`: {send, flash}; `screens`: {agents}: the Agents pane, put in its own screen (the menu's Agents, spec 49 §10.1). */
export function makePreview(core, ctx, screens = {}) {
  const st = core.st;
  const back = h("button", { class: "ork-btn back", type: "button", "aria-label": "Back", onclick: () => core.back() }, "‹ Back");
  const title = h("h2", { class: "screen-title" });
  const body = h("div", { class: "screen-body" });
  const bar = h("div", { class: "screen-bar" });
  const el = h("section", { class: "screen", "aria-label": "Preview", hidden: true }, h("header", { class: "screen-head" }, back, title), body, bar);

  let data = null;                      // what the open preview reads: {page} | {task} | {task, diff}
  let timer = 0;
  let unfolded = new Set();             // sections open in a spec
  let section = "";                     // the section the ask box is about
  let asked = "";                       // the ask box's text, kept across a redraw
  let seq = 0;
  const fresh = steady(el);
  const guard = pointerGuard([el], () => draw(false));            // no lost tap, no lost drag: a pick's screen is not drawn again while a pointer is down on it (a bar being dragged, a tile being pressed)

  const failed = (r) => !r.ok || r.result?.error;
  /** The leader of the party a goal belongs to (the Map's goal whose slug is the page's `track`), by name. */
  const leadOf = (p) => leaderName((st.map?.goals || []).find((g) => g.slug === p.track));
  async function read(p) {
    if (p.kind === "agents") return;                    // its pane draws itself (shell-agents.js)
    if (p.kind === "pick") {                            // read with the Board (Needs you): nothing to ask
      seq += 1;
      data = { pick: pickRow(st, p.slug, p.task) };
      draw(false);
      return;
    }
    const mine = ++seq;
    const names = p.kind === "task" || p.kind === "result" ? [["ideas.task", { slug: p.slug, task: p.task }]]
      : p.kind === "goal" ? [["ideas.goal", { slug: p.slug }]] : p.kind === "doc" ? [["ideas.doc", { path: p.path }]]
        : p.kind === "gate" ? [["ideas.gate", {}]] : [["ideas.page", { slug: p.slug }]];
    if (p.kind === "result") names.push(["ideas.diff", { slug: p.slug, task: p.task }], ["ideas.spend", { idea: p.slug }]);
    const got = await Promise.all(names.map(([n, a]) => ctx.send(n, a)));
    if (mine !== seq || !st.preview) return;
    if (failed(got[0])) { ctx.flash(got[0].error || got[0].result?.error); if (p.kind === "doc") data = { doc: null }; else return; }
    else if (p.kind === "goal") data = { goal: got[0].result };
    else if (p.kind === "gate") data = { gate: got[0].result };
    else if (p.kind === "doc") data = { doc: got[0].result };
    else data = p.kind === "task" ? { task: got[0].result } : p.kind === "result" ? { task: got[0].result, diff: got[1].ok && !got[1].result?.error ? got[1].result : null,
      spend: got[2].ok && !got[2].result?.error ? got[2].result : null }
      : { page: got[0].result };
    draw(false);
    clearTimeout(timer);
    const live = data.task && (data.task.state === "running" || data.task.state === "testing");
    if (live || data.page?.busy || BUSY.has(data.page?.state) || data.goal?.busy) timer = setTimeout(() => st.preview && read(st.preview), live ? LOG_MS : 10000);
  }

  async function act(name, args, done) {
    const r = await ctx.send(name, args);
    if (failed(r)) { ctx.flash(r.error || r.result?.error); return null; }
    if (done) ctx.flash(done);
    await core.refresh();
    return r.result || {};
  }

  // -- a goal's spec ---------------------------------------------------------------------------------------------
  function sectionBlock(s) {
    const [role, icon] = SECTIONS[s.name] || ["muted", "•"];
    const on = unfolded.has(s.name);
    const more = s.text && s.text.trim() !== (s.thesis || "").trim();
    const block = h("div", { class: `sec sec-${role}${on ? " is-open" : ""}`, "data-section": s.name },
      h("button", { class: "sec-head", type: "button", "aria-expanded": String(on), onclick: () => { on ? unfolded.delete(s.name) : unfolded.add(s.name); draw(); } },
        h("span", { class: "sec-icon", "aria-hidden": "true" }, h("span", { class: "sec-glyph" }, icon)),
        h("span", { class: "sec-body" }, h("small", { class: "sec-name" }, s.name), h("b", { class: "thesis" }, s.thesis || "—")),
        h("span", { class: "chev", "aria-hidden": "true" }, on ? "⌃" : "⌄")));
    if (on) {
      block.append(h("div", { class: "sec-text" }, more ? h("p", {}, s.text) : null,
        h("button", { class: "ork-btn", type: "button", onclick: () => { section = s.name; draw(); document.getElementById("ask-field")?.focus(); } }, `Ask about ${s.name}`)));
    }
    return block;
  }

  function askBox(p) {
    const lead = leadOf(p);
    const field = h("textarea", { class: "ork-field", id: "ask-field", rows: "2", maxlength: "20000", "aria-label": `Ask or answer ${the(lead)}`,
      placeholder: section ? `About ${section}…` : `Ask or answer ${the(lead)}…` });
    field.value = asked;
    field.addEventListener("input", () => { asked = field.value; });
    const send = h("button", { class: "ork-btn", type: "button" }, "Send");
    send.addEventListener("click", async () => {
      const text = field.value.trim();
      if (!text) return;
      send.disabled = true;
      const args = { slug: p.slug, text };
      if (section) args.section = section;
      const r = await act("ideas.say", args, `Sent: ${the(lead)} answers in a moment.`);
      send.disabled = false;
      if (r) { asked = ""; field.value = ""; read(st.preview); }
    });
    return h("div", { class: "ask" }, section ? h("button", { class: "about", type: "button", "aria-label": "Ask about the whole goal instead",
      onclick: () => { section = ""; draw(); } }, `${section} ✕`) : null, h("div", { class: "row" }, field, send),
    p.busy && !p.revising && !["reading", "planning"].includes(p.state) ? h("p", { class: "muted", role: "status" }, `${The(lead)} is answering…`) : null);      // a talk is being answered (a draft or a plan says its own)
  }

  /** The changed line (spec 62 §6.1, §7.1), under the sections: the plan-making sections written since the plan, and the press that asks the party's leader to look again. Before the start it is
   *  *Re-plan* (`ideas.plan`); after it *Re-plan what is left* (`ideas.revise`): the leader proposes a plan change for the tasks not started, which waits in the hand. A done goal says nothing. */
  function changedLine(p, cur) {
    if (!(p.changed || []).length || p.state === "done") return null;
    const lead = leadOf(p), revising = Boolean(p.revising), waits = p.change != null;
    const words = !p.passed ? `${joined(p.changed)} changed since the plan.` : revising ? `${The(lead)} re-plans what is left…`
      : waits ? `${The(lead)} proposed a plan change: it waits for you.` : `${joined(p.changed)} changed since the work started: the tasks not started may change.`;
    const press = h("button", { class: "ork-btn", type: "button", "data-act": p.passed ? "revise" : "replan", disabled: Boolean(p.busy) || revising },
      !p.passed ? "Re-plan" : waits ? "Re-plan what is left again" : "Re-plan what is left");
    press.addEventListener("click", async () => {
      press.disabled = true;
      const r = await act(p.passed ? "ideas.revise" : "ideas.plan", { slug: p.slug }, p.passed ? `${The(lead)} re-plans what is left.` : `${The(lead)} is planning.`);
      if (r) read(cur); else press.disabled = false;
    });
    return h("div", { class: "changed-line", "data-state": !p.passed ? "before" : revising ? "revising" : waits ? "waits" : "after" }, h("p", { role: "status" }, words), press);
  }

  function planList(plan, p, todo = "") {
    const byId = new Map((plan.tasks || []).map((t) => [t.id, t]));
    const kids = [h("ul", { class: "tasks" }, ...(plan.tasks || []).map((t) => h("li", { class: `task t-${t.state}`, title: headWords(t.head) || null },
      h("button", { class: "linkish task-title", type: "button", onclick: () => core.open({ kind: "task", slug: p.slug, task: t.id }) }, whoHead(t.head, true), t.title),
      h("small", { class: "muted" }, [t.tag, t.head ? TIER_WORDS[t.head.tier] : t.tier, (t.after || []).length ? `after ${t.after.map((a) => byId.get(a)?.title || a).join(", ")}` : "",
        TASK_WORDS[t.state] && p.state !== "plan" ? TASK_WORDS[t.state] : "", t.state === "held" && t.note ? heldWords(t.note, t.waits_title) : "",
        t.commit ? `commit ${t.commit.slice(0, 7)}` : "", t.state === "failed" && t.error ? t.error : ""].filter(Boolean).join(" · ")))))];
    if ((plan.todos || []).length) {
      kids.push(h("h3", {}, "To-dos before it starts"), h("ul", { class: "todos" }, ...plan.todos.map((t) => h("li", { class: `plan-todo${t.id === todo ? " is-target" : ""}`, "data-todo": t.id },
        h("b", {}, t.title), " ", h("small", { class: "chip-kind" }, t.kind), t.why ? h("small", { class: "muted" }, t.why) : null,
        t.id === todo && unblocks(t) ? h("small", { class: "unblocks" }, unblocks(t)) : null))));
    }
    if (plan.estimate && p.state === "plan") kids.push(h("p", { class: "muted" }, `${plan.estimate.tasks} tasks, ${price(plan.estimate)} from Spend.`));
    return h("div", { class: "plan card" }, h("h3", {}, "The plan"), ...kids);
  }

  /** The checks the party holds this goal to (realm/idea_checks.py): passed, its task's state, or why it does not apply. */
  /** The checks of the goal (realm/idea_checks.py): passed, its task's state, why not, or skipped by the person. Skip spares a
   *  check that has not run (its task taken out of the plan); Take again, before a plan. */
  function checksLine(p, cur) {
    const checks = p.checks;
    if (!(checks || []).length) return null;
    const found = (c) => (c.found === 0 ? "clean" : `found ${c.found}: ${[c.fixed && `${c.fixed} fixed`, c.left && `${c.left} left`].filter(Boolean).join(", ")}`);
    const words = (c) => (c.skipped ? "skipped by you" : !c.applies ? `not needed: ${c.why}` : c.found != null ? found(c) : c.state === "passed" ? "passed" : c.state ? TASK_WORDS[c.state] || c.state : "in the plan to come");
    const skippable = (c) => c.applies && !c.skipped && (!c.state || ["waiting", "ready", "held"].includes(c.state));
    const spares = (c) => { const usd = Number(core.st.roles?.tier_costs?.[c.tier]); return usd > 0 ? ` · spares ≈ ${pctOf(usd) || `$${usd.toFixed(2)}`}` : ""; };
    const skip = (c, on) => act("ideas.check_skip", { slug: p.slug, by: c.by, ...(on ? {} : { skip: false }) },
      on ? `Skipped: ${c.name}.` : `${c.name} checks it again.`).then(() => read(cur));
    return h("div", { class: "checks-line", role: "list", "aria-label": "Checks" }, h("span", { class: "field-label" }, "Checks"),
      ...checks.map((c) => h("span", { class: `check-chip${c.applies && !c.skipped ? "" : " is-off"}${c.state === "passed" ? " is-passed" : ""}`, role: "listitem" },
        h("b", {}, c.state === "passed" ? icon("check") : null, c.name), h("small", {}, words(c)),
        skippable(c) ? h("button", { class: "ork-btn check-skip", type: "button", "aria-label": `Skip the check: ${c.name}`, onclick: () => skip(c, true) }, `Skip${spares(c)}`)
          : c.skipped && !p.plan ? h("button", { class: "ork-btn check-skip", type: "button", "aria-label": `Take the check again: ${c.name}`, onclick: () => skip(c, false) }, "Take again") : null)));
  }

  // why the Taskmaster's last step on it failed (a failed plan says its own under its button)
  const stateError = (p) => (["reading", "planning", "failed"].includes(p.state) ? "" : p.state_error || "");

  function ideaScreen(p, cur) {
    title.replaceChildren(h("span", { class: "muted" }, "Spec "), p.title);
    const talk = (p.talk || []).slice(-TALK_SHOWN), lead = leadOf(p);
    body.replaceChildren(...[
      h("p", { class: "muted" }, [p.size ? `Size ${p.size} · ` : "", stateWords({ state: p.state, progress: { done: (p.plan?.tasks || []).filter((t) => t.state === "merged").length, total: (p.plan?.tasks || []).length } })].join("")),
      stateError(p) ? h("p", { class: "warn", role: "alert" }, stateError(p)) : null,
      pointedAt(p.lens),
      checksLine(p, cur),
      ...(p.sections || []).map(sectionBlock),
      changedLine(p, cur),
      p.plan && ["plan", "working", "failed", "done"].includes(p.state) ? planList(p.plan, p) : null,
      talk.length ? h("h3", {}, "The talk") : null,
      talk.length ? h("div", { class: "talk" }, ...talk.map((t) => h("div", { class: `turn ${t.who}` },
        h("span", { class: "who" }, t.who === "you" ? "You" : The(lead), t.section ? ` · ${t.section}` : ""), h("p", {}, t.text)))) : null,
      askBox(p),
      h("p", { class: "muted" }, h("button", { class: "linkish", type: "button", onclick: () => dropIdea(p) }, "Delete this goal…"))].filter(Boolean));
    const n = p.plan?.estimate?.tasks ?? (p.plan?.tasks || []).length;
    const btn = (label, onclick, cls = "primary") => h("button", { class: `ork-btn ${cls} big`, type: "button", onclick }, label);
    const slug = p.slug;
    const left = limitsNote(core.st.snap);              // what is left of the AI tools, where a choice spends them
    const row = (core.st.board?.ideas || []).find((i) => i.slug === slug) || {};    // its queue: the Board's row says it
    switch (p.state) {
      case "raw": {                                     // the Board's list had these; the Board is the Map now (shell-map.js)
        if (row.held_until) return [left];
        const now = btn("Process now", () => act("ideas.queue", { slug, queue: "now" }, `${The(lead)} drafts it now.`).then(() => read(cur)));
        return (row.queue || "night") === "hold" ? [left, now, btn("Tonight", () => act("ideas.queue", { slug, queue: "night" }, "Kept for tonight.").then(() => read(cur)), "")]
          : row.queue === "now" ? [] : [left, now];
      }
      case "reading": case "planning": return [btn("Stop", () => act("ideas.read_stop", { slug }, "Stopped.").then(() => read(cur)), "danger")];
      case "ready": case "asks": return [left, btn("Take it to work", () => act("ideas.plan", { slug }, `${The(lead)} is planning.`).then(() => read(cur)))];
      case "plan": if (p.plan?.start_at === "night" || row.start_at === "night") return [left, btn("Start now", () => act("ideas.start_now", { slug }, "Started.").then(() => read(cur)))];
        return [left, btn(`Start · ${n} tasks · ${price(p.plan?.estimate)}`, () => act("ideas.start", { slug }, "Started.").then(() => read(cur)))];
      case "working": return [btn("Stop", () => act("ideas.stop", { slug }, "Stopped.").then(() => read(cur)), "danger")];
      case "failed": {
        const why = p.state_error || (p.plan?.tasks || []).find((t) => t.state === "failed")?.error || "";
        return [why ? h("p", { class: "warn" }, why) : null, btn("Start again", () => act("ideas.start", { slug }, "Started again.").then(() => read(cur)))];
      }
      default: return [];
    }
  }

  async function dropIdea(p) {
    if (!confirm("Drop this goal and its page?")) return;
    if (await act("ideas.drop", { slug: p.slug })) core.close();
  }

  // -- a plan, scrolled to a to-do ------------------------------------------------------------------------------
  /** The plan change that waits (spec 62 §6.4, §7.4), over the plan: its why, its rows (*+* added, *~* changed, *−* dropped, muted and struck) and what it costs. */
  function changeBlock(c) {
    const MARK = { add: "+", change: "~", drop: "−" }, WORD = { add: "added", change: "changed", drop: "dropped" };
    const cost = changePrice(c);
    return h("div", { class: "plan-change card", "data-change": "" }, h("h3", {}, "The change"), c.why ? h("p", { class: "change-why" }, c.why) : null,
      (c.rows || []).length ? h("ul", { class: "change-rows" }, ...c.rows.map((r) => h("li", { class: `change-row is-${r.op}`, "data-op": r.op },
        h("span", { class: "change-mark", role: "img", "aria-label": WORD[r.op] }, MARK[r.op]), h("span", { class: "change-title" }, r.title))))
        : h("p", { class: "muted" }, "The plan stays as it is."),
      cost ? h("p", { class: "muted change-cost", title: "At API prices, not your bill" }, cost) : null);
  }

  /** *Take the new plan* and *Keep the plan* on the plan's screen (the screen's bar): the answer, its toast, the screen read again. Nothing is dealt here: only a press in the hand deals (spec 57). */
  function changeBar(p, cur) {
    const both = [];
    const answer = (take) => async () => {
      both.forEach((b) => { b.disabled = true; });
      const r = await act("ideas.revise_answer", { slug: p.slug, take });
      if (r) ctx.flash(take ? changeWords(r) : "The plan stays as it was.");
      read(cur);
    };
    both.push(h("button", { class: "ork-btn primary big", type: "button", "data-act": "take-change", onclick: answer(true) }, "Take the new plan"),
      h("button", { class: "ork-btn big", type: "button", "data-act": "keep-change", onclick: answer(false) }, "Keep the plan"));
    return both;
  }

  function planScreen(p, cur) {
    title.replaceChildren(h("span", { class: "muted" }, "Plan "), p.title);
    if (!p.plan) { body.replaceChildren(h("p", { class: "muted" }, "This goal has no plan yet.")); return []; }
    body.replaceChildren(...[p.change ? changeBlock(p.change) : null, planList(p.plan, p, cur.todo)].filter(Boolean));
    requestAnimationFrame(() => body.querySelector(".plan-todo.is-target")?.scrollIntoView({ block: "center" }));
    const n = p.plan.estimate?.tasks ?? (p.plan.tasks || []).length;
    return [...(p.change ? changeBar(p, cur) : []), ...(p.state === "plan" ? [limitsNote(core.st.snap), h("button", { class: "ork-btn primary big", type: "button",
      onclick: () => act("ideas.start", { slug: p.slug }, "Started.").then(() => read(cur)) }, `Start · ${n} tasks · ${price(p.plan.estimate)}`)] : [])];
  }

  // -- a party, and a document it links ------------------------------------------------------------------------
  function goalScreen(g, cur) {
    title.replaceChildren(h("span", { class: "muted" }, "Party "), g.title);
    body.replaceChildren(...goalBody(g, core, act, asked, (v) => { asked = v; }));
    return [h("button", { class: "ork-btn big", type: "button", onclick: () => core.editGoal(g.slug) }, "Edit the party")];
  }
  // A Markdown file is read as the page renders it (the host's `html`, raw HTML already off); the rest as plain text.
  function docText(d, cur) {
    if (typeof d.html !== "string") return h("pre", { class: "log doc", "aria-label": cur.path }, d.text);
    const md = h("div", { class: "md doc", "aria-label": cur.path });
    md.innerHTML = d.html;
    return md;
  }
  function docScreen(d, cur) {
    title.replaceChildren(h("span", { class: "muted" }, "Document "), cur.path);
    body.replaceChildren(...[h("p", {}, h("button", { class: "linkish", type: "button", onclick: () => core.open({ kind: "goal", slug: cur.slug }) }, sign("before"), " Back to the party")),
      d ? docText(d, cur) : h("p", { class: "muted" }, "That document cannot be shown."),
      d?.truncated ? h("p", { class: "muted" }, "Cut here: the document is longer.") : null].filter(Boolean));
    return [];
  }

  // -- the gate: dev → main (shell-gate.js) ------------------------------------------------------------------------
  function gateView(g) {
    const screen = gateScreen(g, core, act);
    title.replaceChildren(...screen.title);
    body.replaceChildren(...screen.body);
    return screen.actions;
  }

  // -- a pick: the variants a task left, to choose from -------------------------------------------------------
  function pickScreen(row) {
    title.replaceChildren(h("span", { class: "muted" }, "Pick one "), row?.title || "");
    stopAll();                                          // new tiles: what played on the old ones does not play on
    body.replaceChildren(...(row ? screenBody(core, ctx, row) : [h("p", { class: "muted" }, "That pick is answered already.")]));
    return [];
  }

  // -- a task -------------------------------------------------------------------------------------------------
  function taskScreen(t, cur) {
    title.replaceChildren(h("span", { class: "muted" }, "Task "), t.title);
    const live = t.state === "running" || t.state === "testing";
    const log = h("pre", { class: "log", "aria-label": "Log" }, t.log || "Nothing logged yet.");
    body.replaceChildren(...[
      h("dl", { class: "facts" },
        h("dt", {}, "State"), h("dd", { "data-state": t.state }, TASK_WORDS[t.state] || t.state, t.note ? h("small", { class: "muted" }, ` ${t.state === "held" ? heldWords(t.note, t.waits_title) : t.note}`) : null),
        h("dt", {}, "Goal"), h("dd", {}, h("button", { class: "linkish", type: "button", onclick: () => core.open({ kind: "idea", slug: t.idea }) }, t.idea_title)),
        h("dt", {}, "Tier"), h("dd", {}, t.head ? who(t.head, true) : t.tier), h("dt", {}, "Branch"), h("dd", {}, h("code", {}, t.branch || "—")),
        h("dt", {}, "Round"), h("dd", {}, String(t.round || 1)), h("dt", {}, "Spend"), h("dd", {}, t.cost != null ? (pctOf(t.cost) ? `≈${pctOf(t.cost)}` : `$${Number(t.cost).toFixed(2)}`) : "—")),
      t.error ? h("p", { class: "warn", role: "alert" }, t.error) : null,
      h("h3", {}, "Brief"), h("p", { class: "brief" }, t.brief), h("h3", {}, "Log"), log].filter(Boolean));
    requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
    if (live) return [h("button", { class: "ork-btn danger big", type: "button", onclick: () => act("ideas.stop_task", { slug: t.idea, task: t.id }, "Stopped.").then(() => read(cur)) }, "Stop")];
    if (t.state === "review") return [h("button", { class: "ork-btn primary big", type: "button", onclick: () => core.open({ kind: "result", slug: t.idea, task: t.id }) }, "Open the result")];
    if (t.state === "picking") return [h("button", { class: "ork-btn primary big", type: "button", onclick: () => core.open({ kind: "pick", slug: t.idea, task: t.id }) }, "Pick one")];
    return [];
  }

  // -- a result's code ----------------------------------------------------------------------------------------
  function patch(text) {
    return h("pre", { class: "patch" }, ...text.split("\n").map((ln) => h("span", { class: `pl${ln.startsWith("+") && !ln.startsWith("+++") ? " is-add" : ln.startsWith("-") && !ln.startsWith("---") ? " is-del" : ln.startsWith("@@") ? " is-hunk" : ""}` }, ln)));
  }
  function file(f) {
    const box = h("details", { class: "file" }, h("summary", {}, h("code", {}, f.path), h("span", { class: "file-n" }, h("span", { class: "is-add" }, `+${f.added}`), " ", h("span", { class: "is-del" }, `−${f.removed}`))));
    box.addEventListener("toggle", () => {                       // the lines are drawn when it opens
      if (box.open && !box.querySelector(".patch, .too-large")) box.append(f.patch == null ? h("p", { class: "muted too-large" }, "Too large to show.") : patch(f.patch));
    });
    return box;
  }
  function resultScreen(t, diff, cur, spend) {
    title.replaceChildren(h("span", { class: "muted" }, "Code "), t.title);
    const r = (st.review?.results || []).find((x) => x.idea === cur.slug && x.task === cur.task);
    body.replaceChildren(...[
      h("p", { class: "muted" }, t.idea_title),
      spend ? h("p", { class: "muted spend-line", title: "At API prices, not your bill" }, spendLine(spend)) : null,
      r ? factsOf(r) : h("p", { class: "muted" }, "This result is no longer waiting at Review."),
      r ? foundOf(r) : null,
      r?.conflict ? h("p", { class: "warn" }, sign("alert"), ` ${r.conflict}`) : null,
      !diff ? h("p", { class: "muted" }, "Reading the code…") : h("div", { class: "code" },
        h("h3", {}, "Commits"), h("ol", { class: "commits" }, ...diff.commits.map((c) => h("li", {}, h("code", {}, c.sha), ` ${c.subject}`))),
        h("h3", {}, `Files changed (${diff.files.length})`), ...diff.files.map(file),
        diff.truncated ? h("p", { class: "muted" }, "Some files are too large to show.") : null)].filter(Boolean));
    return r ? [resultActions(core, r, () => core.close())] : [];
  }

  function draw(force = true) {
    const cur = st.preview;
    if (!cur || !data) return;
    if (cur.kind === "pick" && guard.waits()) return;   // a pointer is down on the pick's screen: drawn after it comes up
    // a redraw the town asked for waits while the person types and while nothing changed; one the person asked for (a fold, Ask about) is now. A pick's compares what it shows, not when it was asked.
    const sig = cur.kind === "pick" ? [cur, data.pick ? pickSig(data.pick) : null] : [cur, data, st.review?.results];
    if (!force && !fresh(JSON.stringify(sig))) return;
    if (force) fresh(JSON.stringify([...sig, Math.random()]));
    let actions = [];
    if (cur.kind === "idea") actions = ideaScreen(data.page, cur);
    else if (cur.kind === "plan") actions = planScreen(data.page, cur);
    else if (cur.kind === "goal") actions = goalScreen(data.goal, cur);
    else if (cur.kind === "doc") actions = docScreen(data.doc, cur);
    else if (cur.kind === "gate") actions = gateView(data.gate);
    else if (cur.kind === "task") actions = taskScreen(data.task, cur);
    else if (cur.kind === "pick") actions = pickScreen(data.pick);
    else actions = resultScreen(data.task, data.diff, cur, data.spend);
    bar.replaceChildren(...actions.filter(Boolean));
    bar.hidden = !actions.filter(Boolean).length;
  }

  return {
    el,
    show(p) {
      if (p.kind === "pick" && !pickRow(st, p.slug, p.task)) p = st.preview = { kind: "task", slug: p.slug, task: p.task };      // answered already (a Today row of before): its task's screen says where it is
      stopAll();
      fresh(`opened ${Math.random()}`);
      data = null;
      if (p.kind === "agents") {                        // the Agents pane in a screen of its own: it draws itself
        unfolded = new Set();
        el.hidden = false;
        title.replaceChildren("Agents");
        body.replaceChildren(screens.agents);
        bar.replaceChildren();
        bar.hidden = true;
        body.scrollTop = 0;
        return;
      }
      unfolded = new Set();
      section = "";
      asked = "";
      el.hidden = false;
      title.replaceChildren("…");
      body.replaceChildren(h("p", { class: "muted" }, "Opening…"));
      bar.replaceChildren();
      bar.hidden = true;
      body.scrollTop = 0;
      read(p);
    },
    hide() { el.hidden = true; clearTimeout(timer); seq += 1; data = null; stopAll(); },
    /** The town changed: read what is open again. */
    reload() { if (st.preview) read(st.preview); },
    redraw: () => draw(false),
  };
}
