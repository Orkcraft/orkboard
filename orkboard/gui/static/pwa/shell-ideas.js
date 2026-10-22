// New goal on the phone (docs/specs/35-goals-window.md §3, spec 50 §6.7, spec 52 §5.6): the full-screen form a card of the create button's deck opens — *A blank goal* (or the goal type's sign and
// name), *for Tech · the Taskmaster reads it next*, the element it will get (shown, never named), *Its title*, *What it is for* (with the party's words to complete with, Photo and the mic mark at its
// corner: shell-idea-field.js), the party (a select; fixed by a type: a type is its leader's), the type's asks (one line each), **Refs** when the type has them (*Links*; the pictures are Photo's), the
// lens of its party (shell-lens.js; the type's first), the join line (shell-types.js), the priority, and *Add the goal* · *Put it back* at the foot. A goal is `ideas.add`'s `text`: its title is the first line of it. A goal's
// state in words (`rowState`) is said the same in the leader's column and on its screen.
import { h, sheet } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { hhmm } from "./shell-words.js";
import { makeIdeaField } from "./shell-idea-field.js";
import { makeLens } from "./shell-lens.js";
import { keepGoal } from "./shell-top.js";
import { elem, nextElement, sign } from "./shell-marks.js";
import { makeJoin } from "./shell-types.js";

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

/** `core`: the board's frame; `ctx`: {deliver, flash}. Returns {sheets, openNew(partySlug, type)}. */
export function makeIdeas(core, ctx, goalSheet) {
  const st = core.st;
  const parties = () => (st.board?.tracks || []).filter((t) => t.slug !== "general");

  // -- New goal: its title, what it is for, its party, its priority; Add the goal. Closing the form with words in it adds the goal to tonight's queue, never lost. -----
  const title = h("input", { class: "ork-field", type: "text", maxlength: "120", "aria-label": "Its title", placeholder: "What should become possible" });
  const field_ = h("textarea", { class: "ork-field", rows: "5", maxlength: "20000", enterkeyhint: "done", "aria-label": "What it is for", placeholder: "Who needs it, and how you will know it is done" });
  const partyPick = h("select", { class: "ork-field", "aria-label": "Party" });
  const priority = prioritySwitch("idea-priority");
  let touched = false;                               // the person chose the priority: a party change leaves it
  priority.el.addEventListener("change", () => { touched = true; });
  const more = makeIdeaField(ctx, field_);
  const lens = makeLens(core, ctx);                  // what the goal points at, the party's way (shell-lens.js)
  const who = h("p", { class: "muted newgoal__for" });
  const mark = h("span", { class: "newgoal__mark" });
  const kind = h("b", { class: "newgoal__kind" }, "A blank goal");                       // *A blank goal*, or the type's sign and name
  const partyField = field("Party", partyPick);
  const partyFixed = h("div", { class: "field newgoal__party", hidden: true }, h("span", { class: "field-label" }, "Party"), h("b", {}));
  const asks = h("div", { class: "newgoal__asks", hidden: true });
  const links = h("input", { class: "ork-field", type: "text", maxlength: String(ASK_CHARS), "aria-label": "Links", "data-ask": REFS, placeholder: "Links to things you like" });
  const refs = h("div", { class: "newgoal__refs", hidden: true }, h("span", { class: "field-label" }, "Refs"), field("Links", links),
    h("p", { class: "muted newgoal__likes" }, "Pictures you like: add them with Photo, under What it is for."));
  const join = makeJoin(core);
  let typed = null;                                  // the goal type the form was opened by (the map's `types` entry), null for a blank goal
  const hint = h("p", { class: "muted hint" }, "High and Normal are drafted at once; Low waits for the night. Closing this with words in it keeps the goal for tonight."
    + (more.speaks ? "" : " Speak it with the keyboard’s microphone."));
  const add = h("button", { class: "ork-btn primary big", type: "button", disabled: true }, "Add the goal");
  const putBack = h("button", { class: "ork-btn quiet big", type: "button", "data-act": "put-back" }, "Put it back");
  const addSheet = sheet("New goal", h("div", { class: "newgoal__head" }, kind, who), partyFixed,
    h("div", { class: "newgoal__el" }, mark, h("span", { class: "muted" }, "Its element marks every task of it.")),
    field("Its title", title), field("What it is for", h("div", { class: "idea-box" }, field_, more.mic)), more.el, partyField, asks, refs, lens.el, join.el,
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el), hint, foot(putBack, add));
  addSheet.el.classList.add("full");
  const words = () => [title.value.trim(), field_.value.trim()].filter(Boolean).join("\n\n");     // the goal's text: its title is the first line of it
  const sync = () => { add.disabled = !words(); };
  title.addEventListener("input", sync);
  field_.addEventListener("input", sync);

  const leaderWords = (g) => (g?.leader?.slug && g.leader.slug !== "taskmaster" ? g.leader.name : "the Taskmaster");
  /** *for Tech · Taskmaster reads it next* and the element a goal of the party will get. */
  function party(slug) {
    const g = (st.map?.goals || []).find((x) => x.slug === slug);
    who.textContent = g ? `for ${g.title} · ${leaderWords(g)} reads it next` : "";
    partyFixed.querySelector("b").textContent = g?.title || "";
    mark.replaceChildren(elem(nextElement((st.map?.nodes || []).filter((n) => n.goal === slug)), { big: true }) || "");
  }
  partyPick.addEventListener("change", () => {
    if (!touched) priority.set(parties().find((t) => t.slug === partyPick.value)?.priority || "normal");
    more.track(partyPick.value);
    lens.track(partyPick.value);
    party(partyPick.value);
  });
  let saved = false;                                 // a button saved it: closing the form after it saves nothing more
  async function drop(night) {
    const text = words();
    if (!text || !partyPick.value) return null;
    saved = true;
    add.disabled = true;
    const short = text.length > 40 ? `${text.slice(0, 40)}…` : text;
    more.stop();
    const photos = more.photos(), pointed = lens.value();
    const said = Object.fromEntries([...asks.querySelectorAll("input[data-ask]"), ...(typed?.refs ? [links] : [])]
      .map((i) => [i.dataset.ask, i.value.trim()]).filter(([, v]) => v));
    const { name: joiner, ...joined } = (!night && typed && join.value()) || {};            // a goal kept for tonight never changes the party
    const args = { text, track: partyPick.value, priority: priority.get(), ...(night ? { night: true } : {}), ...(photos.length ? { photos } : {}),
      ...(pointed.length ? { lens: pointed } : {}), ...(typed ? { type: typed.id } : {}), ...(Object.keys(said).length ? { asks: said } : {}),
      ...(joined.add ? { join: joined } : {}) };
    const r = await ctx.deliver("ideas.add", args, `the goal “${short}”`);
    sync();
    if (!r.ok || r.result?.error) { saved = false; ctx.flash(r.error || r.result?.error); return null; }
    title.value = "";
    field_.value = "";
    more.reset();
    lens.reset();
    r.joinedName = r.result?.joined ? joiner || r.result.joined.add : "";
    r.leader = leaderWords((st.map?.goals || []).find((x) => x.slug === args.track));
    st.track = args.track;                            // the Board shows the party the goal went to: it is there
    keepGoal(st.snap?.project, args.track);
    return r;
  }
  add.addEventListener("click", async () => {
    const r = await drop(false);
    if (!r) return;
    addSheet.close();
    ctx.flash(r.kept ? (r.unphotographed ? "No signal: the goal is kept and goes when the town answers, without its photos (no room for them on this phone)."
      : "No signal: the goal is kept and goes when the town answers.")
      : r.result?.queue === "night" ? "Kept for tonight." : r.joinedName ? `Added: ${r.joinedName} joined the party; ${r.leader} drafts it now.` : "Added: the Taskmaster drafts it now.");
    if (!r.kept) core.refresh();
  });
  putBack.addEventListener("click", () => addSheet.close());
  addSheet.el.addEventListener("close", async () => {      // Put it back · Close · Esc · the backdrop: words in it are kept for tonight, never lost
    if (saved) { saved = false; return; }
    const r = words() ? await drop(true) : null;
    saved = false;
    if (r) { ctx.flash("Kept for tonight."); if (!r.kept) core.refresh(); }
  });
  /** The form by a goal type (`t`: the map's `types` entry) or blank (null): its head, the party fixed or picked, its asks, Refs and the join line. */
  function byType(t) {
    typed = t;
    kind.replaceChildren(...(t ? [sign(t.sign, "", { big: true }), h("span", {}, t.name)] : ["A blank goal"]));
    kind.dataset.type = t ? t.id : "";
    partyField.hidden = Boolean(t);
    partyFixed.hidden = !t;
    asks.replaceChildren(...(t?.asks || []).map((a) => field(a.label, h("input", { class: "ork-field", type: "text", maxlength: String(ASK_CHARS), "data-ask": a.id,
      "aria-label": a.label, placeholder: a.hint || "" }))));
    asks.hidden = !(t?.asks || []).length;
    links.value = "";
    refs.hidden = !t?.refs;
    if (t) join.set(t.missing); else join.reset();
  }
  function open(slug, type = null) {
    saved = false;
    touched = false;
    const list = [...parties()].sort((a, b) => (RANK[a.priority] ?? 1) - (RANK[b.priority] ?? 1) || (a.order ?? 0) - (b.order ?? 0));
    partyPick.replaceChildren(...list.map((t) => h("option", { value: t.slug }, t.title)));
    const on = list.find((t) => t.slug === (slug || st.track)) || list[0];
    byType(type);
    partyPick.value = on.slug;
    priority.set(on.priority || "normal");
    title.value = "";
    field_.value = "";
    sync();
    party(on.slug);
    more.reset();
    more.track(on.slug);
    lens.reset();
    lens.track(on.slug, type?.lens || "");
    addSheet.open();
    title.focus();
  }
  /** New goal needs a party: with none yet, New party opens first and then this. `type`: a goal type of the party's (the map's `types` entry), null for a blank goal. */
  function openNew(slug = "", type = null) {
    if (parties().length) open(slug, type);
    else goalSheet.open("", (made) => open(made));
  }

  return { sheets: [addSheet.el], openNew };
}
