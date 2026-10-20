// The ideas on the phone (docs/specs/35-goals-window.md §3, §11.3): New idea in a sheet — the text (with the goal's words to complete with,
// Photo and Speak: shell-idea-field.js), the goal and the priority, one button, Add — and one row per idea: its title, its priority as a mark, its state in words, and its actions. An idea that is in Needs you is
// not listed here; the done ones are folded at the end.
import { h, sheet, icon } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { PRIORITY_WORDS, hhmm } from "./shell-words.js";
import { makeIdeaField } from "./shell-idea-field.js";
import { makeLens } from "./shell-lens.js";
import { keepGoal } from "./shell-top.js";

const HOLD_MS = 450;                    // a card held this long can be dragged
const RANK = { high: 0, normal: 1, low: 2 };
const STATE_WORDS = { raw: "new", reading: "drafting", asks: "asks you", ready: "ready", planning: "planning",
  plan: "plan ready", working: "working", done: "done", failed: "needs you", proposed: "proposed" };
export const BUSY = new Set(["reading", "planning", "working"]);

/** The state of an idea row in words (§11.3); `spin`: a spinner goes before it. */
export function rowState(idea, titleOf = (slug) => slug) {
  const p = idea.progress;
  const q = idea.queue || (idea.state === "raw" ? "night" : "");
  if ((idea.state === "raw" || idea.state === "ready") && idea.held_until) return { text: `waits for limits · after ${hhmm(idea.held_until)}`, cls: "held" };
  if (idea.state === "raw") return q === "hold" ? { text: "stopped", cls: "raw" } : q === "now" ? { text: "queued", cls: "raw" } : { text: "tonight", cls: "raw" };
  if (idea.state === "reading" || idea.state === "planning") return { text: STATE_WORDS[idea.state], cls: "work", spin: true };
  if (idea.state === "plan" && idea.start_at === "night") return { text: "starts tonight", cls: "plan" };
  if (idea.state === "working") {
    const base = p && p.total ? `working ${p.done}/${p.total}` : "working";
    const waits = (idea.waits_on || []).length ? ` · waits for ${idea.waits_on.map(titleOf).join(", ")}` : "";
    return { text: base + waits, cls: "work" };
  }
  return { text: STATE_WORDS[idea.state] || idea.state, cls: idea.state };
}

/** `core`: the board's frame; `ctx`: {deliver, flash}. Returns {sheets, openNew(goalSlug), list(ideas), wireDrag}. */
export function makeIdeas(core, ctx, goalSheet) {
  const st = core.st;
  const tracks = () => (st.board?.tracks || []).filter((t) => t.slug !== "general");

  // -- New idea: the text, its goal, its priority; Add. Closing the sheet with text in it adds it to tonight's queue, never lost. -----
  const field_ = h("textarea", { class: "ork-field", rows: "5", maxlength: "20000", enterkeyhint: "done", "aria-label": "The idea", placeholder: "An idea…" });
  const goalPick = h("select", { class: "ork-field", "aria-label": "Goal" });
  const priority = prioritySwitch("idea-priority");
  let touched = false;                               // the person chose the priority: a goal change leaves it
  priority.el.addEventListener("change", () => { touched = true; });
  const more = makeIdeaField(ctx, field_);
  const lens = makeLens(core, ctx);                  // what the idea points at, the goal's party's way (shell-lens.js)
  goalPick.addEventListener("change", () => {
    if (!touched) priority.set(tracks().find((t) => t.slug === goalPick.value)?.priority || "normal");
    more.track(goalPick.value);
    lens.track(goalPick.value);
  });
  const hint = h("p", { class: "muted hint" }, "High and Normal are drafted at once; Low waits for the night. Closing this with text in it keeps the idea for tonight."
    + (more.speaks ? "" : " Speak it with the keyboard’s microphone."));
  const add = h("button", { class: "ork-btn primary big", type: "button" }, "Add");
  const addSheet = sheet("New idea", field("The idea", field_), more.el, field("Goal", goalPick), lens.el,
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el), hint, foot(add));
  let saved = false;                                 // a button saved it: closing the sheet after it saves nothing more
  async function drop(night) {
    const text = field_.value.trim();
    if (!text || !goalPick.value) return null;
    saved = true;
    add.disabled = true;
    const short = text.length > 40 ? `${text.slice(0, 40)}…` : text;
    more.stop();
    const photos = more.photos(), pointed = lens.value();
    const args = { text, track: goalPick.value, priority: priority.get(), ...(night ? { night: true } : {}), ...(photos.length ? { photos } : {}),
      ...(pointed.length ? { lens: pointed } : {}) };
    const r = await ctx.deliver("ideas.add", args, `the idea “${short}”`);
    add.disabled = false;
    if (!r.ok || r.result?.error) { saved = false; ctx.flash(r.error || r.result?.error); return null; }
    field_.value = "";
    more.reset();
    lens.reset();
    st.track = args.track;                            // the Board shows the goal the idea went to: it is there
    keepGoal(st.snap?.project, args.track);
    return r;
  }
  add.addEventListener("click", async () => {
    const r = await drop(false);
    if (!r) return;
    addSheet.close();
    ctx.flash(r.kept ? (r.unphotographed ? "No signal: the idea is kept and goes when the town answers, without its photos (no room for them on this phone)."
      : "No signal: the idea is kept and goes when the town answers.")
      : r.result?.queue === "night" ? "Kept for tonight." : "Added: the Taskmaster drafts it now.");
    if (!r.kept) core.refresh();
  });
  addSheet.el.addEventListener("close", async () => {      // × · Esc · the backdrop: text in it is kept for tonight, never lost
    if (saved) { saved = false; return; }
    const r = field_.value.trim() ? await drop(true) : null;
    saved = false;
    if (r) { ctx.flash("Kept for tonight."); if (!r.kept) core.refresh(); }
  });
  function open(goal, voice = false) {
    saved = false;
    touched = false;
    const list = [...tracks()].sort((a, b) => (RANK[a.priority] ?? 1) - (RANK[b.priority] ?? 1) || (a.order ?? 0) - (b.order ?? 0));
    goalPick.replaceChildren(...list.map((t) => h("option", { value: t.slug }, t.title)));
    const on = list.find((t) => t.slug === (goal || st.track)) || list[0];
    goalPick.value = on.slug;
    priority.set(on.priority || "normal");
    more.reset();
    more.track(on.slug);
    lens.reset();
    lens.track(on.slug);
    addSheet.open();
    field_.focus();
    if (voice) more.listen();
  }
  /** New idea needs a goal: with none yet, New goal opens first and then this. `voice`: Speak at once. */
  function openNew(voice = false) {
    if (tracks().length) open("", voice);
    else goalSheet.open("", (slug) => open(slug, voice));
  }

  // New idea at the bottom right, under the thumb (and Speak above it, where the browser has speech to text).
  const fab = h("div", { class: "fab-stack", hidden: true },
    more.speaks ? h("button", { class: "fab small", type: "button", "aria-label": "Speak a new idea", onclick: () => openNew(true) }, "Speak") : null,
    h("button", { class: "fab", type: "button", "aria-label": "New idea", onclick: () => openNew() }, icon("plus")));

  // -- Delete asks first, on a sheet --------------------------------------------------------------------------------
  let doomed = null;
  const doomText = h("p", {});
  const sure = h("button", { class: "ork-btn danger big", type: "button" }, "Delete");
  const dropSheet = sheet("Delete this idea?", doomText, foot(h("button", { class: "ork-btn big", type: "button", onclick: () => dropSheet.close() }, "Keep it"), sure));
  sure.addEventListener("click", async () => {
    dropSheet.close();
    if (doomed && await core.call("ideas.drop", { slug: doomed.slug })) core.refresh();
  });

  // -- one row each ---------------------------------------------------------------------------------------------------
  const run = async (name, args) => { if (await core.call(name, args)) core.refresh(); };
  function actions(idea) {
    const btn = (label, onclick, cls = "") => h("button", { class: `ork-btn ${cls}`.trim(), type: "button", "aria-label": `${label}: ${idea.title}`, onclick }, label);
    const del = btn("Delete", () => { doomed = idea; doomText.textContent = `“${idea.title}” and its page are removed.`; dropSheet.open(); });
    const now = btn("Process now", () => run("ideas.queue", { slug: idea.slug, queue: "now" }), "now");
    if (idea.state === "raw" || idea.state === "ready") {
      if (idea.held_until) return [del];
      if (idea.state === "ready") return [];
      return (idea.queue || "night") === "hold" ? [now, btn("Tonight", () => run("ideas.queue", { slug: idea.slug, queue: "night" })), del] : [now, del];
    }
    if (idea.state === "reading" || idea.state === "planning") return [btn("Stop", () => run("ideas.read_stop", { slug: idea.slug }))];
    if (idea.state === "plan" && idea.start_at === "night") return [btn("Start now", () => run("ideas.start_now", { slug: idea.slug }), "now")];
    return [];
  }
  function card(idea) {
    const s = rowState(idea, (slug) => (st.board?.ideas || []).find((i) => i.slug === slug)?.title || slug);
    const acts = actions(idea);
    return h("li", { class: `idea-card state-${idea.state}`, "data-slug": idea.slug },
      h("button", { class: "idea-open", type: "button", onclick: () => core.open({ kind: "idea", slug: idea.slug }) },
        h("span", { class: "idea-title" }, idea.title),
        idea.thesis ? h("span", { class: "idea-thesis" }, idea.thesis) : null,
        h("span", { class: "idea-meta" },
          idea.size ? h("span", { class: "size", title: "Size" }, idea.size) : null,
          h("span", { class: `prio prio-${idea.priority || "normal"}` }, PRIORITY_WORDS[idea.priority] || "Normal"),
          h("span", { class: `state-word ${s.cls}` }, s.spin ? h("span", { class: "spin", "aria-hidden": "true" }, "↻") : null, s.spin ? " " : null, s.text))),
      acts.length ? h("div", { class: "idea-actions" }, ...acts) : null);
  }

  // Long-press, then drag: the held card lifts and follows the finger, the others make room; letting go says where
  // it goes (`ideas.move` with the card it goes before). A finger that moves before the hold scrolls instead.
  function wireDrag(list) {
    let timer = 0, from = null, y0 = 0, dragging = null, cards = [], mids = [], sticky = false;
    const stopTimer = () => { clearTimeout(timer); timer = 0; };
    list.addEventListener("contextmenu", (e) => e.preventDefault());
    list.addEventListener("pointerdown", (e) => {
      const li = e.target.closest?.(".idea-card");
      if (!li || (e.button !== undefined && e.button > 0)) return;
      from = { li, x: e.clientX, y: e.clientY, id: e.pointerId };
      timer = setTimeout(() => {
        dragging = li;
        cards = [...list.children];
        mids = cards.map((c) => { const b = c.getBoundingClientRect(); return b.top + b.height / 2; });
        y0 = from.y;
        li.classList.add("is-dragging");
        try { list.setPointerCapture(from.id); } catch { /* the finger stays on the card */ }
        navigator.vibrate?.(30);
      }, HOLD_MS);
    });
    list.addEventListener("pointermove", (e) => {
      if (!dragging) {
        if (from && Math.hypot(e.clientX - from.x, e.clientY - from.y) > 8) stopTimer();
        return;
      }
      dragging.style.transform = `translateY(${e.clientY - y0}px)`;
    });
    list.addEventListener("touchmove", (e) => { if (dragging) e.preventDefault(); }, { passive: false });
    const drop_ = async (e) => {
      stopTimer();
      if (!dragging) return;
      const li = dragging;
      dragging = null;
      sticky = true;                                                               // the click that follows is not a tap
      setTimeout(() => { sticky = false; }, 400);
      li.classList.remove("is-dragging");
      li.style.transform = "";
      if (e.type === "pointercancel") return;
      const others = cards.filter((c) => c !== li);
      const at = Math.max(0, mids.filter((m, i) => cards[i] !== li && m < e.clientY).length);
      if (others[at] === cards[cards.indexOf(li) + 1]) return;                      // where it was
      const args = { slug: li.dataset.slug };
      if (others[at]?.dataset.slug) args.before = others[at].dataset.slug;
      await core.call("ideas.move", args);
      core.refresh();
    };
    list.addEventListener("click", (e) => { if (sticky) { e.stopPropagation(); e.preventDefault(); } }, true);
    list.addEventListener("pointerup", drop_);
    list.addEventListener("pointercancel", drop_);
  }

  /** The section's nodes: New idea at its head, the rows, and the done ones folded. */
  function section() {
    const mine = (st.board?.ideas || []).filter((i) => i.track === st.track && !i.in_needs_you).sort((a, b) => a.order - b.order);
    const open_ = mine.filter((i) => i.state !== "done"), done = mine.filter((i) => i.state === "done");
    const list = h("ol", { class: "ideas" }, ...open_.map(card));
    wireDrag(list);
    return [h("div", { class: "section-head" }, h("h3", {}, "Ideas")),
      open_.length ? list : h("p", { class: "muted" }, "No ideas here yet. Drop one with + at the bottom: it costs nothing, the Taskmaster drafts it."),
      done.length ? h("details", { class: "done-ideas" }, h("summary", {}, `Done (${done.length})`), h("ol", { class: "ideas" }, ...done.map(card))) : null].filter(Boolean);
  }

  return { sheets: [addSheet.el, dropSheet.el], section, openNew, fab };
}
