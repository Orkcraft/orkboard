// What waits for you, along the bottom (docs/specs/49-one-window.md §6, §10.6, §11; spec 54 §2–§4, decisions §67): **every stop of the project** (every party's plan, question, proposal, to-do, Pick one and
// failure, and Operations') and every party's results to look at, fanned across the whole width and centred, only their tops showing (56 px, no line over them; no count: the fan is
// the count). In the order of their urgency (shell-arena-words.js `byUrgency`: red, what holds work back, what does not, the results; the oldest first) laid out with the most urgent in the middle, the next to its
// right, the next to its left and so outward (`fanPlaces`): the cards stay in the page in the urgency's order, so the keys and a screen reader read it, and their place in the row is the CSS order. A stop of another
// party wears that party's leader's small head (Operations' its sliders) and says its party on its raised card and in its label; *Open…* and *Open it on its own screen* show that party first. Every stop has a way
// out that needs nothing from the person (shell-needs.js): a question *Let <asker> decide*, a to-do *Describe it instead*, *Go without it* or *Let <leader> choose*. The create button floats over the field, not here (shell-fab.js). A tap pops one out: it leaps from its place in the
// fan to a raised sheet above the scrim (in steps, none under reduced motion; its place in the fan stays empty while it is up) with its gem, its kind, its head, its
// title and text, its quick answers as 44 px buttons and *Open it on its own screen*. A tap on the scrim lays it back. The answers are the commands Needs you had:
// a plan starts, a question is answered by one of its choices, a proposal is taken or left, a failure starts again; a result is merged, sent back or dropped. Each wears its goal's element
// (spec 50 §6.8) and draws its marks with orkUI's signs. A plan that gives work to no one of the party says so on its card and its raised one (spec 52 §5.7): *No one in the party does pixel art:
// Artist would.*, with *Add and start* (the agent joins, then the work starts) when its seat is free, else *Edit the party*; *Start without* keeps today's way.
import { h, icon } from "./util.js";
import { elem, sign } from "./shell-marks.js";
import { midHead, whoHead } from "./shell-who.js";
import { needsOf, failedOf, looksOf, nodesOf, pickedOf, planPrice, byUrgency, fanPlaces } from "./shell-arena-words.js";
import { resultActions, testsWords, changesWords, foundWords, foundOf } from "./shell-review.js";
import { OPS_VIEW } from "./shell-ops.js";
import { pointerGuard } from "./shell-motion.js";
import { thumbs, stopAll, countWords, pickSig } from "./shell-picks.js";
import { makePanel, forget } from "./shell-pick-answer.js";

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const KIND = { plan: "Plan ready", asks: "Asks you", goal: "Asks you", proposal: "Proposed", party: "Proposed", todo: "A to-do", failed: "Failed", look: "To look at",
  pick: "Pick one", op: "At your check", op_failed: "Failed", op_rules: "Proposed" };
const gemOf = (g) => h("span", { class: `ork-gem ${g.cls || ""}`.trim(), title: g.tip }, g.sign ? sign(g.sign) : g.text);       // a price, a mark or a sign (a failure's cross)
const CARD = 104, WIDTH = 330;                           // a card's width in the fan, and the room it was drawn for (the row's width less 30 px at each side)
const usd = (n) => `$${n < 10 ? n.toFixed(2) : Math.round(n)}`;
const plural = (n, one) => `${n} ${n === 1 ? one : `${one}s`}`;

/** A plan's missing line (spec 52 §4.4): *No one in the party does pixel art: Artist would.*, *… would, and 1 more.* when it misses more than one kind; "" when it misses no one. */
export function missingWords(missing) {
  const m = (missing || [])[0];
  if (!m) return "";
  const more = missing.length - 1;
  return `No one in the party does ${m.words}: ${m.name} would${more ? `, and ${more} more` : ""}.`;
}

/** `core`: the board's frame; `ctx`: {flash}; `needs`: shell-needs.js (the forms); `ops`: shell-ops.js.
 *  Returns {el, sheets, content(), draw(), pop(key)}. */
export function makeStops(core, ctx, needs, ops) {
  const st = core.st;
  const hand = h("div", { class: "hand", role: "group", "aria-label": "Waits for you" });
  const empty = h("p", { class: "cap handzone__empty", hidden: true }, "Nothing waits for you.");
  const el = h("section", { class: "handzone", "aria-label": "Waits for you" }, empty, hand);          // the fan takes the whole width and stays centred on the screen

  // -- the raised one: a modal over the scrim; its place in the fan is empty while it is up ------------------------------------------------------
  const body = h("div", { class: "raised-in" });
  const dlg = h("dialog", { class: "raised-dlg", "aria-label": "Waits for you" }, body);
  const lower = () => { if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) lower(); });
  dlg.addEventListener("close", () => { stopAll(); st.hand = ""; mark(); core.draw(); });          // what changed while it was up shows now: the fan does not shift under it; a sound does not play on under it

  let items = [], places = [], sigs = "", raisedSig = "", raisedParty = null;          // `places[i]`: where in the row the i-th most urgent lies; `raisedParty`: the party of the stop raised (null: the one shown)
  const guard = pointerGuard([el, dlg], () => api.draw());      // no lost tap: a draw waits while a pointer is down on the fan or the raised one (spec 50 §6.9)

  // -- the stops of the goal, each with its quick answers ----------------------------------------------------------------------------------------------
  const btn = (label, run, { primary = false, tip = "", text = false, disabled = false, attrs = {} } = {}) => h("button", { class: `ork-btn${primary ? " primary" : ""}${text ? " answer" : ""}`,
    type: "button", title: tip || null, disabled, onclick: run, ...attrs }, label);
  /** A command of the stops: laid back first (the toast shows), then read again. */
  const go = (name, args, said) => async () => {
    const r = await core.call(name, typeof args === "function" ? args() : args);              // read when pressed: a line typed on the raised one counts
    if (!r) return;
    lower();
    if (said) ctx.flash(said);
    core.refresh();
  };
  /** A press that opens something else: the stop is laid back, the party it belongs to is shown first when it is not the one shown (a pick of it in the parties' list, Operations too), then it opens (spec 54 §2.2). */
  const away = (open, via = "hand") => () => {
    const party = raisedParty;
    lower();
    if (party) { if (party.ops) core.pickOps(); else core.pick(party.slug); }
    open(via);
  };

  /** Every stop of the project and every party's results to look at, each as an item (spec 54 §2.1): the parties' in the Map's order, Operations' after them. The filter (spec 50 §3.5) is each party's own:
   *  only the picked goals' stops and results. A stop of another party than the one shown says its party. */
  function build() {
    const shown = core.parties().shown;                       // a party's slug, or OPS_VIEW
    const out = [];
    for (const goal of st.map?.goals || []) {
      const slug = goal.slug, lead = goal.leader?.head || null;
      const nodes = Object.fromEntries(nodesOf(st, slug).map((n) => [n.slug, n]));
      const picks = pickedOf(st, slug), keep = (idea) => !picks.length || picks.includes(idea);       // the filter: only the picked goals' stops and results
      const party = slug === shown ? null : { slug, name: goal.short || goal.title, head: lead };
      const tag = (it, node, at, goalName) => ({ ...it, element: node?.element || "", at: at || "", party, goalName: goalName || "" });
      for (const n of needsOf(st, slug).filter((x) => keep(x.idea))) out.push(tag(needItem(n, nodes[n.idea], goal, lead), nodes[n.idea], n.at, n.idea ? nodes[n.idea]?.short || nodes[n.idea]?.title || n.title : ""));
      for (const { node, task } of failedOf(st, slug).filter(({ node: x }) => keep(x.slug))) out.push(tag(failedItem(node, task), node, task.finished, node.short || node.title));
      for (const r of looksOf(st, slug).filter((x) => keep(x.idea))) out.push(tag(lookItem(r, nodes[r.idea]), nodes[r.idea], r.finished, r.idea_title));
    }
    const party = shown === OPS_VIEW ? null : { ops: true, name: "Operations" };
    for (const n of (st.board?.needs_you || []).filter((x) => x.kind.startsWith("op"))) out.push({ ...opItem(n), at: n.at || "", party, goalName: "" });
    return out;
  }

  function needItem(n, node, goal, lead) {
    const base = { key: `${n.kind}:${n.idea || n.goal}:${n.todo?.id || (n.kind === "pick" ? n.task : "")}`, kind: n.kind, title: n.title, sig: n, open: n.idea ? { kind: "idea", slug: n.idea } : { kind: "goal", slug: n.goal } };
    const asking = n.kind === "asks" || n.kind === "goal", q = asking ? needs.askedOf(n)[0] : null;
    if (n.kind === "plan") {
      const tasks = node?.tasks || [], checks = tasks.filter((t) => t.band === "check").length, price = planPrice(node?.plan_estimate || node?.estimate);
      const night = node?.start_at === "night", missing = n.missing || [], first = missing[0];
      const openPlan = () => btn("Open the plan", away((via) => core.open({ kind: "plan", slug: n.idea }, via)), { attrs: { "data-act": "open-plan" } });
      const without = () => btn("Start without", go("ideas.start", { slug: n.idea, via: "hand" }, "Started."), { primary: !first?.free, tip: "Passes the plan as it is; the work starts", attrs: { "data-act": "start" } });
      let quick;
      if (night) quick = () => [btn("Start now", go("ideas.start_now", { slug: n.idea, via: "hand" }, "Started."), { primary: true, tip: "Starts the plan now, instead of tonight", attrs: { "data-act": "start-now" } }), openPlan()];
      else if (first?.free) {
        quick = () => [btn("Add and start", go("ideas.start", { slug: n.idea, join: { add: first.agent }, via: "hand" }, `${first.name} joined the party; the work started.`),
          { primary: true, tip: `${first.name} joins the party, then the work starts`, attrs: { "data-act": "add-start" } }), without()];
      } else if (first) quick = () => [without(), btn("Edit the party", away(() => core.editParty(n.goal)), { attrs: { "data-act": "edit-party" } })];
      else {
        quick = () => [btn("Start the work", go("ideas.start", { slug: n.idea, via: "hand" }, "Started."), { primary: true, tip: "Passes the plan; the work starts", attrs: { "data-act": "start" } }), openPlan()];
      }
      return { ...base, gem: { text: price || "—", tip: "What the plan should cost, at API prices" }, big: lead,
        text: tasks.length ? `${plural(tasks.length - checks, "task")}${checks ? `, ${plural(checks, "check")}` : ""}` : n.text, miss: missingWords(missing),
        open: { kind: "plan", slug: n.idea }, quickLabel: "Quick moves", quick };
    }
    if (asking) {
      const isGoal = n.kind === "goal", slug = isGoal ? n.goal : n.idea, asked = needs.askedOf(n);
      const answer = (answers) => go("ideas.answer", { slug, answers, ...(isGoal ? { goal: true } : {}) }, needs.SENT);
      const picks = asked.map((x) => (x.pick != null ? x.choices[x.pick] || "" : ""));
      let quick;
      if (asked.length === 1 && q.choices.length) {
        quick = () => [...q.choices.map((c, j) => btn(`${j === q.pick ? "● " : ""}${c}`, answer([c]), { primary: j === q.pick, text: true,
          tip: j === q.pick ? "Picked for you: one tap answers" : "One tap answers with this", attrs: { "data-choice": String(j) } })), needs.decideButton(n, lower)];
      } else if (asked.length > 1) {
        quick = () => [btn("Send the picks", answer(picks), { primary: true, disabled: !picks.some(Boolean), tip: "Answers each question with its recommended choice", attrs: { "data-act": "picks" } }),
          btn("Open…", away(() => needs.askForm(n, picks)), { attrs: { "data-act": "more" } }), needs.decideButton(n, lower)];
      } else quick = () => [btn("Open…", away(() => needs.askForm(n)), { attrs: { "data-act": "more" } }), needs.decideButton(n, lower)];
      return { ...base, gem: { text: "?", tip: "A question costs nothing" }, small: q?.by?.head || null, whoTip: q?.by?.name ? `asked by ${q.by.name}` : "",
        text: q ? `“${q.ask}”` : n.text || "", quickLabel: "Answer in one tap", quick };
    }
    if (n.kind === "proposal" || n.kind === "party") {
      const party = n.kind === "party";
      const reason = h("input", { class: "ork-field", type: "text", maxlength: "300", "aria-label": `Why not: ${n.title}`, placeholder: party ? "Why not? (optional, one line)" : "Why not? (optional)" });
      const say = (take) => go(party ? "ideas.party_answer" : "ideas.proposal", () => (party ? { goal: n.goal, take, ...(!take && reason.value.trim() ? { reason: reason.value.trim() } : {}) }
        : { slug: n.idea, take, ...(take ? { priority: goal?.priority || n.priority || "normal" } : reason.value.trim() ? { reason: reason.value.trim() } : {}) }));
      return { ...base, gem: { text: "—", tip: "Not planned yet" }, big: lead, text: n.text || "", quickLabel: "Quick moves",
        quick: () => [btn(party ? "Take it out" : "Take", say(true), { primary: true, tip: party ? "Takes the proposed change out of the party" : "Puts it on the Board as a new goal", attrs: { "data-act": "take" } }),
          reason, btn(party ? "Keep it" : "No", say(false), { tip: party ? "Keeps the party as it is" : "Leaves it out", attrs: { "data-act": "no" } })] };
    }
    if (n.kind === "pick") {                                // a task left variants of one kind: the tiles 2 × 2, the note, Take B, None of them (spec 51 §7)
      let panel = null;
      const mine = () => (panel ||= makePanel(core, ctx, n, { via: "hand", after: lower }));
      return { ...base, sig: pickSig(n), gem: { text: String(n.n ?? n.variants.length), tip: `${countWords(n.n ?? n.variants.length, n.media)} to pick from` }, small: n.by?.head || null,
        whoTip: n.by?.name ? `made by ${n.by.name}` : "", text: `“${n.ask}”`, thumbs: () => thumbs(n), more: () => [mine().tiles, mine().note, mine().say], quickLabel: "Pick one",
        quick: () => [mine().take, mine().none], open: { kind: "pick", slug: n.slug, task: n.task } };
    }
    if (n.kind === "todo") {
      return { ...base, gem: { text: "·", tip: "A to-do costs nothing" }, text: n.todo?.why || n.text || n.title, quickLabel: "Quick moves", open: { kind: "plan", slug: n.idea, todo: n.todo?.id },
        quick: () => [btn("Open…", away(() => needs.todoSheet(n)), { primary: true, attrs: { "data-act": "todo" } }), ...needs.todoOuts(n, lower)] };
    }
    // a failure of the whole idea (a task that failed is the Map's, below)
    return { ...base, cls: "is-fail", tone: "danger", gem: { sign: "cross", cls: "danger", tip: "It failed" }, text: n.text || "Something failed", quickLabel: "Quick moves",
      quick: () => [btn("Start again", go("ideas.start", { slug: n.idea, via: "hand" }, "Started again."), { primary: true, tip: "Runs this goal's tasks that are not merged or in Review again", attrs: { "data-act": "again" } }),
        btn("Open…", away((via) => core.open({ kind: "idea", slug: n.idea }, via)), { attrs: { "data-act": "more" } })] };
  }

  function failedItem(node, t) {
    return { key: `failed:${node.slug}/${t.id}`, kind: "failed", cls: "is-fail", tone: "danger", title: t.title, sig: [node.slug, t], small: t.head || null, whoTip: `${t.by?.name || "Grunt"}’s task`,
      gem: { sign: "cross", cls: "danger", tip: "It failed" }, text: t.error || "failed", open: { kind: "task", slug: node.slug, task: t.id }, quickLabel: "Quick moves",
      quick: () => [btn("Start again", go("ideas.start", { slug: node.slug, via: "hand" }, "Started again."), { primary: true, tip: "Runs this goal's tasks that are not merged or in Review again", attrs: { "data-act": "again" } }),
        btn("Open…", away((via) => core.open({ kind: "task", slug: node.slug, task: t.id }, via)), { attrs: { "data-act": "more" } })] };
  }

  function lookItem(r, node) {
    const t = (node?.tasks || []).find((x) => x.id === r.task), tw = testsWords(r);
    return { key: `look:${r.idea}/${r.task}`, kind: "look", cls: "is-look", tone: "look", title: r.title, sig: r, small: t?.head || null, whoTip: t?.by?.name ? `${t.by.name}${r.check ? " · its check" : ""}` : "",
      gem: { text: r.cost != null ? usd(r.cost) : "—", cls: "dim", tip: "What it cost, at API prices" },
      text: [r.idea_title, h("span", {}, tw.mark ? sign(tw.mark) : null, tw.mark ? " " : "", tw.text), changesWords(r.diff), foundWords(r.findings)].filter(Boolean)
        .flatMap((x, i) => (i ? [" · ", x] : [x])),
      plain: [r.idea_title, `${tw.mark} ${tw.text}`.trim(), changesWords(r.diff), foundWords(r.findings)].filter(Boolean).join(" · "),
      more: () => foundOf(r),                           // a check's findings left, one line each, under its facts
      open: { kind: "result", slug: r.idea, task: r.task }, quickLabel: "Quick moves", quick: () => [resultActions(core, r, lower)] };
  }

  function opItem(n) {
    const failed = n.kind === "op_failed";
    return { key: `${n.kind}:${n.op || n.template}`, kind: n.kind, cls: failed ? "is-fail" : "", tone: failed ? "danger" : "", title: n.title, sig: n,
      gem: failed ? { sign: "cross", cls: "danger", tip: "It failed" } : { text: n.kind === "op_rules" ? "—" : "·", tip: "" }, text: [n.text, n.kind === "op" ? n.why : ""].filter(Boolean).join(" · "), quickLabel: "Quick moves",
      open: null, quick: () => [btn("Open…", away(() => (n.kind === "op" ? ops.openCheck(n.op) : failed ? ops.openRun(n.op) : ops.openProposal(n))), { primary: true, attrs: { "data-act": "open-op" } })] };
  }

  // -- the fan ----------------------------------------------------------------------------------------------------------------------------------------
  /** Turn, rise, order and overlap of the card at place `i` of `n` in the row: each turned 3° a step from the middle and 3 px lower a step², the middle ones higher, overlapping so that they all fit
   *  the width the row has and each shows its top. */
  function fan(i, n) {
    const off = i - (n - 1) / 2;
    const ov = n > 1 ? Math.max(8, Math.ceil((n * CARD - WIDTH) / (n - 1) / 2)) : 0;
    return { rot: off * 3, dy: Math.round(off * off * 3), z: 10 + i, ov };
  }

  const labelOf = (it) => `${KIND[it.kind]}: ${it.title}${it.party ? ` (${it.party.name})` : ""}`;          // a stop of another party names it
  /** The party's mark: its leader's small head, Operations' its sliders. */
  const partyMark = (p) => (p.ops ? icon("sliders") : p.head ? whoHead(p.head, true) : null);

  /** The card of the i-th most urgent stop: it stays at the i-th place of the page (the keys' and a screen reader's order) and lies at its place of the fan (CSS order); the first and the last of the row keep no outer overlap. */
  function card(it, i, n) {
    const place = places[i], f = fan(place, n);
    const b = h("button", { class: `hc ${it.cls || ""}${st.hand === it.key ? " is-up" : ""}`.trim(), type: "button", "data-stop": it.key, "data-kind": it.kind, "data-place": String(place),
      "aria-label": labelOf(it), onclick: () => pop(it.key) },
    h("span", { class: "hc__top" }, gemOf(it.gem),
      h("span", { class: `hc__kind${it.tone === "danger" ? " no" : it.tone === "look" ? " muted" : ""}` }, KIND[it.kind]), elem(it.element)),
    it.party ? h("span", { class: "hc__party", "data-party": it.party.ops ? "ops" : it.party.slug, title: it.party.name }, partyMark(it.party)) : null,
    it.miss ? h("span", { class: "hc__miss" }, it.miss) : null, it.thumbs ? it.thumbs() : null);
    for (const [k, v] of [["--rot", `${f.rot}deg`], ["--dy", `${f.dy}px`], ["--z", String(f.z)], ["--ov", `${f.ov}px`]]) b.style.setProperty(k, v);
    b.style.order = String(place);
    if (place === 0) b.style.marginLeft = "0px";                             // the fan never spills onto the margins
    if (place === n - 1) b.style.marginRight = "0px";
    return b;
  }

  // -- the raised one --------------------------------------------------------------------------------------------------------------------------------
  function raise(it, i, n) {
    const frame = it.tone === "danger" ? " danger" : it.tone === "look" ? "" : " alert";
    const f = fan(places[i], n);
    const quick = h("div", { class: "raised__quick", role: "group", "aria-label": it.quickLabel }, ...it.quick());
    const raised = h("div", { class: `raised ork-frame${frame}${it.kind === "pick" ? " is-pick" : ""}`, role: "document", "data-stop": it.key, "data-kind": it.kind },
      h("div", { class: "raised__top" }, gemOf(it.gem),
        h("span", { class: `raised__kind${it.tone === "danger" ? " no" : it.tone === "look" ? " muted" : ""}` }, KIND[it.kind]), elem(it.element), h("span", { class: "spacer" }),
        it.small ? whoHead(it.small, false) : null,
        h("button", { class: "ork-btn quiet", type: "button", "aria-label": "Put it back", onclick: lower }, icon("close"))),
      it.big ? h("span", { class: "art" }, midHead(it.big)) : null,
      h("span", { class: "banner" }, it.title),
      it.party ? h("p", { class: "cap raised__goal", "data-party": it.party.ops ? "ops" : it.party.slug }, partyMark(it.party), " ", [it.party.name, it.goalName].filter(Boolean).join(" · ")) : null,   // *<party> · <goal>*
      h("div", { class: "raised__text" }, it.text),
      it.miss ? h("p", { class: "muted raised__miss" }, it.miss) : null,
      it.more ? it.more() : null,
      quick,
      it.open ? h("button", { class: "ork-btn quiet", type: "button", "data-act": "open-screen", onclick: away((via) => core.open(it.open, via)) }, "Open it on its own screen") : null);
    raised.style.setProperty("--rot", `${f.rot}deg`);
    return raised;
  }

  function mark() {
    for (const b of hand.children) b.classList.toggle("is-up", b.dataset.stop === st.hand);
  }

  /** Pops the stop `key` (the first of the goal when none) out of the fan. */
  function pop(key) {
    const at = items.findIndex((i) => i.key === (key || items[0]?.key));
    if (at < 0) return false;
    const opening = !dlg.open;
    st.hand = items[at].key;
    showRaised(at, opening);
    mark();
    if (opening) { if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", ""); }
    return true;
  }

  /** The raised one's content; only the pop that opens it leaps (a draw of the same stop, with the Board changed, does not leap again). */
  function showRaised(at, leaps = false) {
    const it = items[at];
    raisedParty = it.party;
    const node = raise(it, at, items.length);
    node.classList.toggle("is-pop", leaps && !reducedMotion());
    stopAll();                                              // new tiles replace the old: what played there does not play on unseen
    body.replaceChildren(node);
    dlg.setAttribute("aria-label", labelOf(it));
    raisedSig = it.key + JSON.stringify(it.sig);
  }

  const api = {
    el,
    sheets: [dlg],
    /** What is acted on only while the town answers. */
    content: () => [hand, empty, dlg],
    items: () => items,
    pop,
    keys: () => items.map((i) => i.key),
    /** Drawn again only when what the row shows changed: a line half typed in a raised one stays, and the fan does not shift while a stop is popped (spec 49 §11). */
    draw() {
      if (guard.waits()) return;
      forget((st.board?.needs_you || []).filter((n) => n.kind === "pick"));        // a draft of a pick that is answered is let go
      items = byUrgency(build());
      places = fanPlaces(items.length);
      const sig = JSON.stringify(items.map((i) => [i.key, i.kind, i.gem, i.title, i.plain ?? i.text, i.miss, i.element, i.sig, i.party, i.goalName])) + st.hand;
      if (sig !== sigs && !dlg.open) {
        sigs = sig;
        hand.replaceChildren(...items.map((it, i) => card(it, i, items.length)));
        empty.hidden = items.length > 0;
      }
      if (st.hand) {
        const at = items.findIndex((i) => i.key === st.hand);
        if (at < 0) { if (dlg.open) lower(); st.hand = ""; mark(); } else if (dlg.open && raisedSig !== items[at].key + JSON.stringify(items[at].sig)) showRaised(at);
      }
    },
  };
  return api;
}
