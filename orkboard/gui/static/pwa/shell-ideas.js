// New goal on the phone (docs/specs/35-goals-window.md §3, spec 50 §6.7, spec 52 §5.6, spec 53 §2): the full-screen form the create button opens at once — it slides up (180 ms; none under reduced
// motion). From the top: **the party** (its leader's head, its name, *<leader> leads · k of n goals done*; a tap lists the project's parties and *+ New party*), the priority (*Low* says it waits for the
// night, and *Add the goal* says *Keep for tonight*), **the goal type** (the party's types, then *No type*, one picked; its line under the row), **the goal** — one field, three lines, Photo and the
// mic mark at its corner (shell-idea-field.js); its first line is its title —, the type's asks (one line each), **Refs** when the type has them (*Links*; the pictures are Photo's), the lens of the
// party (shell-lens.js: a typed goal shows its type's lens and no switch), the join line (shell-types.js) and, pinned at the foot, *Put it back* · *Add the goal*. A goal is `ideas.add`'s `text`.
// A goal's state in words (`rowState`) is said the same in the leader's column and on its screen.
import { h, sheet } from "./util.js";
import { foot, prioritySwitch } from "./shell-forms.js";
import { hhmm } from "./shell-words.js";
import { makeIdeaField } from "./shell-idea-field.js";
import { makeLens } from "./shell-lens.js";
import { keepGoal } from "./shell-top.js";
import { sign } from "./shell-marks.js";
import { makeJoin } from "./shell-types.js";
import { whoHead } from "./shell-who.js";
import { barWords } from "./shell-goals-words.js";
import { motionOn } from "./shell-motion.js";

const RANK = { high: 0, normal: 1, low: 2 };
const STATE_WORDS = { raw: "new", reading: "drafting", asks: "asks you", ready: "ready", planning: "planning",
  plan: "plan ready", working: "working", done: "done", failed: "needs you", proposed: "proposed" };
export const BUSY = new Set(["reading", "planning", "working"]);

/** The state of a goal's row in words (§11.3); `spin`: a spinner goes before it. */
export function rowState(idea, titleOf = (slug) => slug) {
  const p = idea.progress;
  const q = idea.queue || (idea.state === "raw" ? "night" : "");
  if ((idea.state === "raw" || idea.state === "ready") && idea.held_until) return { text: `waits for limits · after ${hhmm(idea.held_until)}`, cls: "held" };
  if (idea.state === "raw") return q === "hold" ? { text: "stopped", cls: "raw" } : q === "now" ? { text: "queued", cls: "raw" } : { text: idea.night_by === "board" ? "tonight, or sooner if the week has room" : "tonight", cls: "raw" };
  if (idea.state === "reading" || idea.state === "planning") return { text: STATE_WORDS[idea.state], cls: "work", spin: true };
  if (idea.state === "plan" && idea.start_at === "night") return { text: idea.night_by === "board" ? "starts tonight, or sooner if the week has room" : "starts tonight", cls: "plan" };
  if (idea.state === "working") {
    const base = p && p.total ? `working ${p.done}/${p.total}` : "working";
    const waits = (idea.waits_on || []).length ? ` · waits for ${idea.waits_on.map(titleOf).join(", ")}` : "";
    return { text: base + waits, cls: "work" };
  }
  return { text: STATE_WORDS[idea.state] || idea.state, cls: idea.state };
}

const ASK_CHARS = 300;                                // goal_types.ASK_CHARS: an ask is one line of at most this
const REFS = "refs";                                 // goal_types.REFS: Refs' links, sent among the asks
const SLIDE_MS = 180;                                // the form slides up and down, ease-out (spec 53 §2.1)
const BLANK_LINE = "A blank goal: only your words.";

/** `core`: the board's frame; `ctx`: {deliver, flash}. Returns {sheets, openNew(partySlug)}. */
export function makeIdeas(core, ctx, goalSheet) {
  const st = core.st;
  const parties = () => [...(st.board?.tracks || [])].filter((t) => t.slug !== "general")
    .sort((a, b) => (RANK[a.priority] ?? 1) - (RANK[b.priority] ?? 1) || (a.order ?? 0) - (b.order ?? 0));       // the Board's order
  const goalOf = (slug) => (st.map?.goals || []).find((x) => x.slug === slug);
  const leaderName = (g) => g?.leader?.name || "Taskmaster";
  const leaderWords = (g) => (g?.leader?.slug && g.leader.slug !== "taskmaster" ? g.leader.name : "the Taskmaster");     // in a sentence

  // -- New goal: the party, its priority, its type, the goal; Add the goal. Closing the form with words in it adds the goal to tonight's queue, never lost. ---------------
  const text = h("textarea", { class: "ork-field", rows: "3", maxlength: "20000", enterkeyhint: "done", "aria-label": "The goal", placeholder: "In a line or a few" });
  let partyNow = "";
  const priority = prioritySwitch("idea-priority");
  let touched = false;                               // the person chose the priority: a party change leaves it
  const more = makeIdeaField(ctx, text);
  const lens = makeLens(core, ctx);                  // what the goal points at, the party's way (shell-lens.js)

  // The party: a button with the leader's head, the name and the count; a tap lists the project's parties.
  const partyHead = h("span", { class: "newgoal__head" });
  const partyName = h("b", { class: "newgoal__name" });
  const partyLine = h("small", { class: "muted newgoal__line" });
  const partyBtn = h("button", { class: "newgoal__party", type: "button", "aria-haspopup": "listbox", "aria-expanded": "false", "data-act": "party" },
    partyHead, h("span", { class: "newgoal__who" }, partyName, partyLine), h("i", { class: "ork-chev", "aria-hidden": "true" }));
  const partyList = h("div", { class: "newgoal__parties", role: "listbox", "aria-label": "Parties" });
  const newParty = h("button", { class: "newgoal__newparty", type: "button", "data-act": "new-party" }, h("b", {}, "+ New party"), h("span", { class: "muted" }, "one of yours, or from the library"));
  const partyMenu = h("div", { class: "newgoal__menu", hidden: true }, partyList, newParty);
  const pickParty = (slug) => {
    partyMenu.hidden = true;
    partyBtn.setAttribute("aria-expanded", "false");
    if (slug !== partyNow) setParty(slug);
  };
  function drawParties() {
    partyList.replaceChildren(...parties().map((t) => {
      const g = goalOf(t.slug);
      const on = t.slug === partyNow;
      return h("button", { class: `newgoal__opt${on ? " is-on" : ""}`, type: "button", role: "option", "aria-selected": String(on), "data-goal": t.slug, onclick: () => pickParty(t.slug) },
        g?.leader?.head ? whoHead(g.leader.head) : h("span", { class: "newgoal__head" }), h("span", { class: "newgoal__who" }, h("b", { class: "newgoal__name" }, t.title),
          h("small", { class: "muted newgoal__line" }, g ? `${leaderName(g)} · ${barWords(g)}` : "")), on ? sign("check", "Picked") : null);
    }));
  }
  const closeParties = () => { partyMenu.hidden = true; partyBtn.setAttribute("aria-expanded", "false"); };
  partyBtn.addEventListener("click", () => {
    const open = partyMenu.hidden;
    if (open) drawParties();
    partyMenu.hidden = !open;
    partyBtn.setAttribute("aria-expanded", String(open));
  });
  // Esc puts the list away first; the form stays.
  const escList = (e) => { if (e.key === "Escape" && !partyMenu.hidden) { e.preventDefault(); e.stopPropagation(); closeParties(); partyBtn.focus(); } };
  partyBtn.addEventListener("keydown", escList);
  partyMenu.addEventListener("keydown", escList);

  // The priority: *Low* says what happens.
  const lowLine = h("p", { class: "muted newgoal__low", hidden: true }, "Waits for the night: the leader reads it then.");
  const add = h("button", { class: "ork-btn primary big", type: "button", disabled: true }, "Add the goal");
  const putBack = h("button", { class: "ork-btn quiet big", type: "button", "data-act": "put-back" }, "Put it back");
  function lowOrNot() {
    const low = priority.get() === "low";
    lowLine.hidden = !low;
    add.textContent = low ? "Keep for tonight" : "Add the goal";
  }
  priority.el.addEventListener("change", () => { touched = true; lowOrNot(); });

  // The goal type: the party's types, then *No type*; one picked.
  let typed = null;                                  // the goal type picked (the map's `types` entry), null for a blank goal
  let types = [];
  const typesRow = h("div", { class: "newgoal__types", role: "radiogroup", "aria-label": "Goal type" });
  const typeLine = h("p", { class: "muted newgoal__typeline" });
  const typeBlock = h("div", { class: "field newgoal__type", hidden: true }, h("span", { class: "field-label" }, "Goal type"), typesRow, typeLine);
  const asks = h("div", { class: "newgoal__asks", hidden: true });
  const links = h("input", { class: "ork-field", type: "text", maxlength: String(ASK_CHARS), "aria-label": "Links", "data-ask": REFS, placeholder: "Links to things you like" });
  const refs = h("div", { class: "newgoal__refs", hidden: true }, h("span", { class: "field-label" }, "Refs"),
    h("label", { class: "field" }, h("span", { class: "field-label" }, "Links"), links),
    h("p", { class: "muted newgoal__likes" }, "Pictures you like: add them with Photo, under The goal."));
  const join = makeJoin(core);
  function pickType(t) {
    typed = t;
    for (const b of typesRow.children) b.setAttribute("aria-checked", String(b.dataset.type === (t ? t.id : "")));
    typeLine.textContent = t ? t.line : BLANK_LINE;
    text.placeholder = t ? "In a line or a few" : "What should become possible";
    asks.replaceChildren(...(t?.asks || []).map((a) => h("label", { class: "field" }, h("span", { class: "field-label" }, a.label),
      h("input", { class: "ork-field", type: "text", maxlength: String(ASK_CHARS), "data-ask": a.id, "aria-label": a.label, placeholder: a.hint || "" }))));
    asks.hidden = !(t?.asks || []).length;
    links.value = "";
    refs.hidden = !t?.refs;
    if (t) join.set(t.missing); else join.reset();
    lens.track(partyNow, t?.lens || "", Boolean(t));
  }
  function drawTypes() {
    typeBlock.hidden = !types.length;
    typesRow.replaceChildren(...types.map((t) => h("button", { class: "newgoal__chip", type: "button", role: "radio", "data-type": t.id, "aria-checked": "false", onclick: () => pickType(t) },
      sign(t.sign), h("span", {}, t.name))),
    h("button", { class: "newgoal__chip is-blank", type: "button", role: "radio", "data-type": "", "aria-checked": "false", onclick: () => pickType(null) }, h("span", {}, "No type")));
  }

  const box = h("div", { class: "field newgoal__goal" }, h("span", { class: "field-label newgoal__goallabel" }, "The goal", h("small", { class: "faint" }, "its first line is its title")),
    h("div", { class: "idea-box" }, text, more.mic));
  const hint = h("p", { class: "muted hint", hidden: more.speaks }, "Speak it with the keyboard’s microphone.");
  const addSheet = sheet("New goal", partyBtn, partyMenu,
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el, lowLine), typeBlock, box, more.el, hint, asks, refs, lens.el, join.el, foot(putBack, add));
  addSheet.el.classList.add("full", "newgoal");
  const words = () => text.value.trim();             // the goal's text: its title is the first line of it
  const sync = () => { add.disabled = !words(); };
  text.addEventListener("input", sync);

  // -- The form slides up from the bottom and down again: 180 ms, ease-out, a transform; none under reduced motion. -------------------------------------------------------
  let sliding = null;
  function slideUp() {
    sliding?.cancel();
    sliding = null;
    if (motionOn() && addSheet.el.animate) addSheet.el.animate([{ transform: "translateY(100%)" }, { transform: "none" }], { duration: SLIDE_MS, easing: "ease-out" });
  }
  function leave() {
    if (!addSheet.el.open || sliding) return;
    if (!motionOn() || !addSheet.el.animate) { addSheet.close(); return; }
    sliding = addSheet.el.animate([{ transform: "none" }, { transform: "translateY(100%)" }], { duration: SLIDE_MS, easing: "ease-out", fill: "forwards" });
    const run = sliding;
    run.finished.catch(() => {}).then(() => { addSheet.close(); run.cancel(); if (sliding === run) sliding = null; });
  }
  addSheet.bar.addEventListener("click", (e) => { if (e.target === addSheet.shut) { e.stopPropagation(); leave(); } }, true);
  addSheet.el.addEventListener("click", (e) => { if (e.target === addSheet.el) { e.stopPropagation(); leave(); } }, true);
  addSheet.el.addEventListener("cancel", (e) => { e.preventDefault(); leave(); });

  /** The party picked: its leader's head and count on the button, its types dealt (the first picked), its words and lenses read. */
  function setParty(slug) {
    partyNow = slug;
    partyBtn.dataset.goal = slug;
    const t = parties().find((x) => x.slug === slug);
    const g = goalOf(slug);
    partyHead.replaceChildren(...(g?.leader?.head ? [whoHead(g.leader.head)] : []));
    partyName.textContent = t?.title || g?.title || "";
    partyLine.textContent = g ? `${leaderName(g)} leads · ${barWords(g)}` : "";
    partyBtn.setAttribute("aria-label", `Party: ${partyName.textContent}. ${partyLine.textContent}`.trim());
    if (!touched) { priority.set(t?.priority || "normal"); lowOrNot(); }
    types = Array.isArray(g?.types) ? g.types : [];
    more.track(slug);
    drawTypes();
    pickType(types[0] || null);
  }
  newParty.addEventListener("click", () => {
    closeParties();
    goalSheet.open("", async (made) => { await core.refresh(); if (parties().some((t) => t.slug === made)) setParty(made); });
  });

  let saved = false;                                 // a button saved it: closing the form after it saves nothing more
  async function drop(night) {
    const body = words();
    if (!body || !partyNow) return null;
    saved = true;
    add.disabled = true;
    const short = body.length > 40 ? `${body.slice(0, 40)}…` : body;
    more.stop();
    const photos = more.photos(), pointed = lens.value();
    const said = Object.fromEntries([...asks.querySelectorAll("input[data-ask]"), ...(typed?.refs ? [links] : [])]
      .map((i) => [i.dataset.ask, i.value.trim()]).filter(([, v]) => v));
    const { name: joiner, ...joined } = (!night && typed && join.value()) || {};            // a goal kept for tonight never changes the party
    const args = { text: body, track: partyNow, priority: priority.get(), ...(night ? { night: true } : {}), ...(photos.length ? { photos } : {}),
      ...(pointed.length ? { lens: pointed } : {}), ...(typed ? { type: typed.id } : {}), ...(Object.keys(said).length ? { asks: said } : {}),
      ...(joined.add ? { join: joined } : {}) };
    const r = await ctx.deliver("ideas.add", args, `the goal “${short}”`);
    sync();
    if (!r.ok || r.result?.error) { saved = false; ctx.flash(r.error || r.result?.error); return null; }
    text.value = "";
    more.reset();
    lens.reset();
    r.joinedName = r.result?.joined ? joiner || r.result.joined.add : "";
    r.leader = leaderWords(goalOf(args.track));
    st.track = args.track;                            // the Board shows the party the goal went to: it is there
    keepGoal(st.snap?.project, args.track);
    return r;
  }
  add.addEventListener("click", async () => {
    const r = await drop(false);
    if (!r) return;
    leave();
    ctx.flash(r.kept ? (r.unphotographed ? "No signal: the goal is kept and goes when the town answers, without its photos (no room for them on this phone)."
      : "No signal: the goal is kept and goes when the town answers.")
      : r.result?.queue === "night" ? "Kept for tonight." : r.joinedName ? `Added: ${r.joinedName} joined the party; ${r.leader} drafts it now.` : "Added: the Taskmaster drafts it now.");
    if (!r.kept) core.refresh();
  });
  putBack.addEventListener("click", leave);
  addSheet.el.addEventListener("close", async () => {      // Put it back · Close · Esc · the backdrop: words in it are kept for tonight, never lost
    closeParties();
    if (saved) { saved = false; return; }
    const r = words() ? await drop(true) : null;
    saved = false;
    if (r) { ctx.flash("Kept for tonight."); if (!r.kept) core.refresh(); }
  });
  function open(slug) {
    saved = false;
    touched = false;
    const list = parties();
    const on = list.find((t) => t.slug === (slug || st.track)) || list[0];
    text.value = "";
    sync();
    more.reset();
    lens.reset();
    closeParties();
    setParty(on.slug);
    addSheet.open();
    slideUp();
    text.focus();
  }
  /** New goal needs a party: with none yet, New party opens first and then this. */
  function openNew(slug = "") {
    if (parties().length) open(slug);
    else goalSheet.open("", (made) => open(made));
  }

  return { sheets: [addSheet.el], openNew };
}
