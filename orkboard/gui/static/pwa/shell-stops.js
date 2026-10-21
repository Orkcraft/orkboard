// What waits for you, along the bottom (docs/specs/49-one-window.md §6, §10.6, §11): the stops of the goal shown (a plan, a question, a proposal, a to-do, a
// failure) and, after them, the results to look at, fanned, only their tops showing (56 px, no line over them). A tap pops one out: it leaps from its place in the
// fan to a raised sheet above the scrim (in steps, none under reduced motion; its place in the fan stays empty while it is up) with its gem, its kind, its head, its
// title and text, its quick answers as 44 px buttons and *Open it on its own screen*. A tap on the scrim lays it back. The answers are the commands Needs you had:
// a plan starts, a question is answered by one of its choices, a proposal is taken or left, a failure starts again; a result is merged, sent back or dropped.
import { h } from "./util.js";
import { midHead, whoHead } from "./shell-who.js";
import { needsOf, failedOf, looksOf, nodesOf, planPrice } from "./shell-arena-words.js";
import { resultActions, testsWords, changesWords, foundWords } from "./shell-review.js";
import { OPS_VIEW } from "./shell-ops.js";

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const KIND = { plan: "Plan ready", asks: "Asks you", goal: "Asks you", proposal: "Proposed", party: "Proposed", todo: "A to-do", failed: "Failed", look: "To look at",
  op: "At your check", op_failed: "Failed", op_rules: "Proposed" };
const CARD = 104, WIDTH = 222;                           // a card's width in the fan, and the room it was drawn for (the row between its two 64 px margins: the count and the create button)
const usd = (n) => `$${n < 10 ? n.toFixed(2) : Math.round(n)}`;
const plural = (n, one) => `${n} ${n === 1 ? one : `${one}s`}`;

/** `core`: the board's frame; `ctx`: {flash}; `needs`: shell-needs.js (the forms); `ops`: shell-ops.js; `fab`: the create button (shell-dial.js), docked at the row's right margin.
 *  Returns {el, sheets, content(), draw(), pop(key)}. */
export function makeStops(core, ctx, needs, ops, fab) {
  const st = core.st;
  const hand = h("div", { class: "hand", role: "group", "aria-label": "Waits for you" });
  const empty = h("p", { class: "cap handzone__empty", hidden: true }, "Nothing waits for you on this goal.");
  // the row is [count | fan | create button] with two equal 64 px margins, so the fan stays centred on the screen
  const countN = h("b", {}, "0");
  const count = h("span", { class: "handcount", hidden: true }, countN, h("span", {}, "for you"));
  const el = h("section", { class: "handzone", "aria-label": "Waits for you" }, count, fab || null, empty, hand);

  // -- the raised one: a modal over the scrim; its place in the fan is empty while it is up ------------------------------------------------------
  const body = h("div", { class: "raised-in" });
  const dlg = h("dialog", { class: "raised-dlg", "aria-label": "Waits for you" }, body);
  const lower = () => { if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) lower(); });
  dlg.addEventListener("close", () => { st.hand = ""; mark(); core.draw(); });          // what changed while it was up shows now: the fan does not shift under it

  let items = [], sigs = "", raisedSig = "";

  // -- the stops of the goal, each with its quick answers ----------------------------------------------------------------------------------------------
  const btn = (label, run, { primary = false, tip = "", text = false, disabled = false, attrs = {} } = {}) => h("button", { class: `ork-btn${primary ? " primary" : ""}${text ? " answer" : ""}`,
    type: "button", title: tip || null, disabled, onclick: run, ...attrs }, label);
  /** A command of the stops: laid back first (the toast shows), then read again. */
  const go = (name, args, said) => async () => {
    const r = await core.call(name, args);
    if (!r) return;
    lower();
    if (said) ctx.flash(said);
    core.refresh();
  };
  const away = (open, via = "hand") => () => { lower(); open(via); };

  function headOf(st_, slug) { return (st_.map?.goals || []).find((g) => g.slug === slug)?.leader?.head || null; }

  /** The items of the goal shown, in the host's order: its Needs you rows, its failed tasks, then its results to look at. */
  function build() {
    const slug = st.track;
    if (st.view === OPS_VIEW) return (st.board?.needs_you || []).filter((n) => n.kind.startsWith("op")).map(opItem);
    const nodes = Object.fromEntries(nodesOf(st, slug).map((n) => [n.slug, n]));
    const goal = (st.map?.goals || []).find((g) => g.slug === slug);
    const lead = headOf(st, slug);
    const out = needsOf(st, slug).map((n) => needItem(n, nodes[n.idea], goal, lead));
    out.push(...failedOf(st, slug).map(({ node, task }) => failedItem(node, task)));
    out.push(...looksOf(st, slug).map((r) => lookItem(r, nodes[r.idea])));
    return out;
  }

  function needItem(n, node, goal, lead) {
    const base = { key: `${n.kind}:${n.idea || n.goal}:${n.todo?.id || ""}`, kind: n.kind, title: n.title, sig: n, open: n.idea ? { kind: "idea", slug: n.idea } : { kind: "goal", slug: n.goal } };
    const asking = n.kind === "asks" || n.kind === "goal", q = asking ? needs.askedOf(n)[0] : null;
    if (n.kind === "plan") {
      const tasks = node?.tasks || [], checks = tasks.filter((t) => t.band === "check").length, price = planPrice(node?.plan_estimate || node?.estimate);
      const night = node?.start_at === "night";
      return { ...base, gem: { text: price || "—", tip: "What the plan should cost, at API prices" }, big: lead,
        text: tasks.length ? `${plural(tasks.length - checks, "task")}${checks ? `, ${plural(checks, "check")}` : ""}` : n.text,
        open: { kind: "plan", slug: n.idea }, quickLabel: "Quick moves",
        quick: () => [night ? btn("Start now", go("ideas.start_now", { slug: n.idea, via: "hand" }, "Started."), { primary: true, tip: "Starts the plan now, instead of tonight", attrs: { "data-act": "start-now" } })
          : btn("Start the work", go("ideas.start", { slug: n.idea, via: "hand" }, "Started."), { primary: true, tip: "Passes the plan; the work starts", attrs: { "data-act": "start" } }),
        btn("Open the plan", away((via) => core.open({ kind: "plan", slug: n.idea }, via)), { attrs: { "data-act": "open-plan" } })] };
    }
    if (asking) {
      const isGoal = n.kind === "goal", slug = isGoal ? n.goal : n.idea, asked = needs.askedOf(n);
      const answer = (answers) => go("ideas.answer", { slug, answers, ...(isGoal ? { goal: true } : {}) }, needs.SENT);
      const picks = asked.map((x) => (x.pick != null ? x.choices[x.pick] || "" : ""));
      let quick;
      if (asked.length === 1 && q.choices.length) {
        quick = () => q.choices.map((c, j) => btn(`${j === q.pick ? "● " : ""}${c}`, answer([c]), { primary: j === q.pick, text: true,
          tip: j === q.pick ? "Picked for you: one tap answers" : "One tap answers with this", attrs: { "data-choice": String(j) } }));
      } else if (asked.length > 1) {
        quick = () => [btn("Send the picks", answer(picks), { primary: true, disabled: !picks.some(Boolean), tip: "Answers each question with its recommended choice", attrs: { "data-act": "picks" } }),
          btn("Open…", away(() => needs.askForm(n, picks)), { attrs: { "data-act": "more" } })];
      } else quick = () => [btn("Open…", away(() => needs.askForm(n)), { attrs: { "data-act": "more" } })];
      return { ...base, gem: { text: "?", tip: "A question costs nothing" }, small: q?.by?.head || null, whoTip: q?.by?.name ? `asked by ${q.by.name}` : "",
        text: q ? `“${q.ask}”` : n.text || "", quickLabel: "Answer in one tap", quick };
    }
    if (n.kind === "proposal" || n.kind === "party") {
      const party = n.kind === "party";
      const reason = h("input", { class: "ork-field", type: "text", maxlength: "300", "aria-label": `Why not: ${n.title}`, placeholder: party ? "Why not? (optional, one line)" : "Why not? (optional)" });
      const say = (take) => go(party ? "ideas.party_answer" : "ideas.proposal", party ? { goal: n.goal, take, ...(!take && reason.value.trim() ? { reason: reason.value.trim() } : {}) }
        : { slug: n.idea, take, ...(take ? { priority: goal?.priority || n.priority || "normal" } : reason.value.trim() ? { reason: reason.value.trim() } : {}) });
      return { ...base, gem: { text: "—", tip: "Not planned yet" }, big: lead, text: n.text || "", quickLabel: "Quick moves",
        quick: () => [btn(party ? "Take it out" : "Take", say(true), { primary: true, tip: party ? "Takes the proposed change out of the party" : "Puts it on the Board as a new idea", attrs: { "data-act": "take" } }),
          reason, btn(party ? "Keep it" : "No", say(false), { tip: party ? "Keeps the party as it is" : "Leaves it out", attrs: { "data-act": "no" } })] };
    }
    if (n.kind === "todo") {
      return { ...base, gem: { text: "·", tip: "A to-do costs nothing" }, text: n.todo?.why || n.text || n.title, quickLabel: "Quick moves", open: { kind: "plan", slug: n.idea, todo: n.todo?.id },
        quick: () => [btn("Open…", away(() => needs.todoSheet(n)), { primary: true, attrs: { "data-act": "todo" } })] };
    }
    // a failure of the whole idea (a task that failed is the Map's, below)
    return { ...base, cls: "is-fail", tone: "danger", gem: { text: "✗", cls: "danger", tip: "It failed" }, text: n.text || "Something failed", quickLabel: "Quick moves",
      quick: () => [btn("Start again", go("ideas.start", { slug: n.idea, via: "hand" }, "Started again."), { primary: true, tip: "Runs this idea's tasks that are not merged or in Review again", attrs: { "data-act": "again" } }),
        btn("Open…", away((via) => core.open({ kind: "idea", slug: n.idea }, via)), { attrs: { "data-act": "more" } })] };
  }

  function failedItem(node, t) {
    return { key: `failed:${node.slug}/${t.id}`, kind: "failed", cls: "is-fail", tone: "danger", title: t.title, sig: [node.slug, t], small: t.head || null, whoTip: `${t.by?.name || "Grunt"}’s task`,
      gem: { text: "✗", cls: "danger", tip: "It failed" }, text: t.error || "failed", open: { kind: "task", slug: node.slug, task: t.id }, quickLabel: "Quick moves",
      quick: () => [btn("Start again", go("ideas.start", { slug: node.slug, via: "hand" }, "Started again."), { primary: true, tip: "Runs this idea's tasks that are not merged or in Review again", attrs: { "data-act": "again" } }),
        btn("Open…", away((via) => core.open({ kind: "task", slug: node.slug, task: t.id }, via)), { attrs: { "data-act": "more" } })] };
  }

  function lookItem(r, node) {
    const t = (node?.tasks || []).find((x) => x.id === r.task), tw = testsWords(r);
    return { key: `look:${r.idea}/${r.task}`, kind: "look", cls: "is-look", tone: "look", title: r.title, sig: r, small: t?.head || null, whoTip: t?.by?.name ? `${t.by.name}${r.check ? " · its check" : ""}` : "",
      gem: { text: r.cost != null ? usd(r.cost) : "—", cls: "dim", tip: "What it cost, at API prices" },
      text: [r.idea_title, `${tw.mark} ${tw.text}`.trim(), changesWords(r.diff), foundWords(r.findings)].filter(Boolean).join(" · "),
      open: { kind: "result", slug: r.idea, task: r.task }, quickLabel: "Quick moves", quick: () => [resultActions(core, r, lower)] };
  }

  function opItem(n) {
    const failed = n.kind === "op_failed";
    return { key: `${n.kind}:${n.op || n.template}`, kind: n.kind, cls: failed ? "is-fail" : "", tone: failed ? "danger" : "", title: n.title, sig: n,
      gem: failed ? { text: "✗", cls: "danger", tip: "It failed" } : { text: n.kind === "op_rules" ? "—" : "·", tip: "" }, text: n.text || "", quickLabel: "Quick moves",
      open: null, quick: () => [btn("Open…", away(() => (n.kind === "op" ? ops.openCheck(n.op) : failed ? ops.openRun(n.op) : ops.openProposal(n))), { primary: true, attrs: { "data-act": "open-op" } })] };
  }

  // -- the fan ----------------------------------------------------------------------------------------------------------------------------------------
  /** Turn, rise, order and overlap of the card at `i` of `n`: each turned 3° a step from the middle and 3 px lower a step², the middle ones higher, overlapping so that they all fit
   *  the width the row has and each shows its top. */
  function fan(i, n) {
    const off = i - (n - 1) / 2;
    const ov = n > 1 ? Math.max(8, Math.ceil((n * CARD - WIDTH) / (n - 1) / 2)) : 0;
    return { rot: off * 3, dy: Math.round(off * off * 3), z: 10 + i, ov };
  }

  function card(it, i, n) {
    const f = fan(i, n);
    const b = h("button", { class: `hc ${it.cls || ""}${st.hand === it.key ? " is-up" : ""}`.trim(), type: "button", "data-stop": it.key, "data-kind": it.kind,
      "aria-label": `${KIND[it.kind]}: ${it.title}`, onclick: () => pop(it.key) },
    h("span", { class: "hc__top" }, h("span", { class: `ork-gem ${it.gem.cls || ""}`.trim(), title: it.gem.tip }, it.gem.text),
      h("span", { class: `hc__kind${it.tone === "danger" ? " no" : it.tone === "look" ? " muted" : ""}` }, KIND[it.kind])));
    for (const [k, v] of [["--rot", `${f.rot}deg`], ["--dy", `${f.dy}px`], ["--z", String(f.z)], ["--ov", `${f.ov}px`]]) b.style.setProperty(k, v);
    return b;
  }

  // -- the raised one --------------------------------------------------------------------------------------------------------------------------------
  function raise(it, i, n) {
    const frame = it.tone === "danger" ? " danger" : it.tone === "look" ? "" : " alert";
    const f = fan(i, n);
    const quick = h("div", { class: "raised__quick", role: "group", "aria-label": it.quickLabel }, ...it.quick());
    const raised = h("div", { class: `raised ork-frame${frame}`, role: "document", "data-stop": it.key, "data-kind": it.kind },
      h("div", { class: "raised__top" }, h("span", { class: `ork-gem ${it.gem.cls || ""}`.trim(), title: it.gem.tip }, it.gem.text),
        h("span", { class: `raised__kind${it.tone === "danger" ? " no" : it.tone === "look" ? " muted" : ""}` }, KIND[it.kind]), h("span", { class: "spacer" }),
        it.small ? whoHead(it.small, false) : null,
        h("button", { class: "ork-btn quiet", type: "button", "aria-label": "Put it back", onclick: lower }, "×")),
      it.big ? h("span", { class: "art" }, midHead(it.big)) : null,
      h("span", { class: "banner" }, it.title),
      h("div", { class: "raised__text" }, it.text),
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
    const node = raise(it, at, items.length);
    node.classList.toggle("is-pop", leaps && !reducedMotion());
    body.replaceChildren(node);
    dlg.setAttribute("aria-label", `${KIND[it.kind]}: ${it.title}`);
    raisedSig = it.key + JSON.stringify(it.sig);
  }

  return {
    el,
    sheets: [dlg],
    /** What is acted on only while the town answers: not the create button (New idea is kept with no signal). */
    content: () => [hand, empty, dlg],
    items: () => items,
    pop,
    keys: () => items.map((i) => i.key),
    /** Drawn again only when what the row shows changed: a line half typed in a raised one stays, and the fan does not shift while a stop is popped (spec 49 §11). */
    draw() {
      items = build();
      const sig = JSON.stringify(items.map((i) => [i.key, i.kind, i.gem, i.title, i.text, i.sig])) + st.hand;
      if (sig !== sigs && !dlg.open) {
        sigs = sig;
        hand.replaceChildren(...items.map((it, i) => card(it, i, items.length)));
        empty.hidden = items.length > 0;
        count.hidden = !items.length;
        countN.textContent = String(items.length);
        countN.className = items.some((i) => i.kind !== "look") ? "warn" : "";           // a stop is among them: the alert colour, not only results
        count.title = `${plural(items.length, "thing")} ${items.length === 1 ? "waits" : "wait"} for you on this goal: a tap on one pops it out`;
      }
      if (st.hand) {
        const at = items.findIndex((i) => i.key === st.hand);
        if (at < 0) { if (dlg.open) lower(); st.hand = ""; mark(); } else if (dlg.open && raisedSig !== items[at].key + JSON.stringify(items[at].sig)) showRaised(at);
      }
    },
  };
}
