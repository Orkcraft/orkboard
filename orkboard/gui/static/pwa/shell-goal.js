// A goal on the phone (docs/specs/35-goals-window.md §2, §11): the New goal / Edit goal sheet — a description, its craft (the head of its race
// marks the goal in the top bar, decisions §53) and a priority, and on Edit
// the title too (to correct the Taskmaster's) — and the goal's own screen (its Description, the Taskmaster's Summary, the Metrics, the
// Links, the Open questions with a box to answer). Saving sends the goal to the Taskmaster at once; it writes the rest.
import { h, sheet } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { PRIORITY_WORDS } from "./shell-words.js";
import { CRAFT_WORDS, RACE_WORDS, goalHead } from "./shell-who.js";

const CRAFTS = [["engineering", "peon"], ["design", "elf"], ["data", "goblin"], ["marketing", "gnome"]];   // realm/roles.py RACES

export { PRIORITY_WORDS };
export const GOAL_STATE = { reading: "the Taskmaster is reading", asks: "asks you", ready: "ready" };
const isUrl = (l) => /^[a-z][a-z0-9+.-]*:\/\//i.test(l);

export function makeGoalSheet(core) {
  const title = h("input", { class: "ork-field", type: "text", "aria-label": "Title", placeholder: "The Taskmaster writes it; correct it here", maxlength: "120" });
  const titleField = field("Title", title);
  const about = h("textarea", { class: "ork-field", rows: "5", "aria-label": "Description", placeholder: "A few lines: what it is for", maxlength: "20000" });
  const craft = h("select", { class: "ork-field", "aria-label": "Craft" },
    ...CRAFTS.map(([c, race]) => h("option", { value: c }, `${CRAFT_WORDS[c]}: ${/^[aeiou]/.test(RACE_WORDS[race]) ? "an" : "a"} ${RACE_WORDS[race]}`)));
  const craftNow = h("span", { class: "craft-now", "aria-hidden": "true" });
  const drawCraft = () => craftNow.replaceChildren(goalHead({ craft: craft.value, race: Object.fromEntries(CRAFTS)[craft.value] }));
  craft.addEventListener("change", drawCraft);
  const priority = prioritySwitch();
  const hint = h("p", { class: "muted hint" }, "The Taskmaster reads it and writes the title, the summary, what counts as done and the links.");
  const save = h("button", { class: "ork-btn primary big", type: "submit", disabled: true }, "Save goal");
  const cancel = h("button", { class: "ork-btn big", type: "button" }, "Cancel");
  const form = h("form", { class: "sheet-form" }, titleField, field("Description", about),
    field("Craft", h("div", { class: "row craft-pick" }, craftNow, craft), "Its head marks the goal in the top bar"),
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el), hint, foot(cancel, save));
  const sh = sheet("New goal", form);
  let slug = "";
  let then = null;                                   // what to do with the goal's slug instead of opening its screen (New idea with no goal yet)
  about.addEventListener("input", () => { save.disabled = !about.value.trim(); });
  cancel.addEventListener("click", () => sh.close());
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!about.value.trim()) return;
    save.disabled = true;
    const args = { ...(slug ? { slug } : {}), about: about.value.trim(), craft: craft.value, priority: priority.get() };
    if (slug && title.value.trim()) args.title = title.value.trim();
    const got = await core.call("ideas.goal_save", args);
    save.disabled = !about.value.trim();
    if (!got?.slug) return;
    const after = then;
    then = null;
    sh.close();
    core.st.track = got.slug;
    await core.refresh();
    if (after) after(got.slug); else core.open({ kind: "goal", slug: got.slug });
  });
  sh.el.addEventListener("close", () => { then = null; });
  return {
    el: sh.el,
    open(which = "", after = null) {
      slug = which;
      then = after;
      const g = which ? (core.st.board?.tracks || []).find((t) => t.slug === which) : null;
      sh.title(g ? "Edit goal" : "New goal");
      titleField.hidden = !g;                          // a new goal has no title to type: the Taskmaster writes it
      title.value = g?.title || "";
      about.value = g?.about || "";
      priority.set(g?.priority || "normal");
      craft.value = g?.craft || "engineering";
      drawCraft();
      save.disabled = !about.value.trim();
      sh.open();
      about.focus();
    },
  };
}

/** The goal's screen: returns the nodes of its body (the preview puts them in). `act` is the preview's own (it flashes and reads again). */
export function goalBody(g, core, act, asked, setAsked) {
  const words = GOAL_STATE[g.state];
  const field_ = h("textarea", { class: "ork-field", id: "answer-field", rows: "2", maxlength: "20000", "aria-label": "Answer the Taskmaster", placeholder: "Answer the Taskmaster…" });
  field_.value = asked;
  field_.addEventListener("input", () => setAsked(field_.value));
  const send = h("button", { class: "ork-btn", type: "button" }, "Send");
  send.addEventListener("click", async () => {
    const text = field_.value.trim();
    if (!text) return;
    send.disabled = true;
    const r = await act("ideas.say", { slug: g.slug, text, goal: true }, "Sent: the Taskmaster answers in a moment.");
    send.disabled = false;
    if (r) { setAsked(""); field_.value = ""; }
  });
  const sec = (name, ...kids) => h("section", { class: "goal-sec", "aria-label": name }, h("h3", {}, name), ...kids);
  return [
    h("p", { class: "muted" }, [words || "not read yet", PRIORITY_WORDS[g.priority], g.deadline ? `by ${g.deadline}` : ""].filter(Boolean).join(" · ")),
    g.state_error && g.state === "raw" ? h("p", { class: "warn" }, g.state_error) : null,
    sec("Description", h("p", { class: "brief" }, g.description || "No description yet.")),
    sec("Summary", h("p", { class: "brief" }, g.summary || (g.state === "reading" ? "The Taskmaster is reading the goal…" : "Not written yet."))),
    sec("Metrics", g.metrics.length ? h("div", { class: "metrics" }, ...g.metrics.map((m) => h("div", { class: "card metric" }, h("b", {}, m.name),
      h("small", {}, `Target: ${m.target || "—"}`), h("small", { class: "muted" }, m.how ? `Counted: ${m.how}` : "How it is counted: not said yet")))) : h("p", { class: "muted" }, "No metric yet.")),
    sec("Links", g.links.length ? h("ul", { class: "links" }, ...g.links.map((l) => h("li", {}, isUrl(l)
      ? h("a", { href: l, target: "_blank", rel: "noopener noreferrer" }, l)
      : h("button", { class: "linkish", type: "button", onclick: () => core.open({ kind: "doc", slug: g.slug, path: l }) }, l)))) : h("p", { class: "muted" }, "No link.")),
    sec("Open questions", g.questions.length ? h("ul", { class: "links" }, ...g.questions.map((q) => h("li", {}, q)))
      : h("p", { class: "muted" }, g.state === "ready" ? "The Taskmaster has no question." : "No question yet."),
    h("div", { class: "ask" }, h("div", { class: "row" }, field_, send))),
    (g.talk || []).length ? h("div", { class: "talk" }, ...g.talk.slice(-6).map((t) => h("div", { class: `turn ${t.who}` },
      h("span", { class: "who" }, t.who === "you" ? "You" : "The Taskmaster"), h("p", {}, t.text)))) : null,
  ].filter(Boolean);
}
