// A goal on the phone (docs/specs/35-goals-window.md §2, §11): the New goal / Edit goal sheet — a description, its craft (the head of its race
// marks the goal in the top bar, decisions §53) and a priority, and on Edit
// the title too (to correct the Taskmaster's) — and the goal's own screen (its Description, the Taskmaster's Summary, the Metrics, the
// Links, the Open questions with a box to answer). Saving sends the goal to the Taskmaster at once; it writes the rest.
import { h, sheet } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { PRIORITY_WORDS } from "./shell-words.js";
import { CRAFT_WORDS, RACE_WORDS, goalHead, whoHead } from "./shell-who.js";
import { limitsNote } from "./shell-limits.js";
import { makeNewGoal, makeParty } from "./shell-goal-new.js";

const CRAFTS = [["engineering", "peon"], ["design", "elf"], ["data", "goblin"], ["marketing", "gnome"], ["product", "lich"]];   // realm/roles.py RACES

export { PRIORITY_WORDS };
export const GOAL_STATE = { reading: "the Taskmaster is reading", asks: "asks you", ready: "ready" };
/** Who leads a goal (its party's leader: the Taskmaster when none, realm/goal_team.py). */
export const leaderName = (g) => g?.leader?.name || "Taskmaster";
/** A goal's state in words, its leader's name in them. */
export function goalState(g) {
  if (g?.state === "reading") return `${g?.leader?.name && g.leader.slug !== "taskmaster" ? g.leader.name : "the Taskmaster"} is reading`;
  return GOAL_STATE[g?.state] || "";
}
const STATUS_WORDS = { met: "met", "not met": "not met", unknown: "unknown" };
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
  const left = h("div", {});                         // what is left of the AI tools: reading the goal spends them
  const save = h("button", { class: "ork-btn primary big", type: "submit", disabled: true }, "Save goal");
  const cancel = h("button", { class: "ork-btn big", type: "button" }, "Cancel");
  const form = h("form", { class: "sheet-form" }, titleField, field("Description", about),
    field("Craft", h("div", { class: "row craft-pick" }, craftNow, craft), "Its head marks the goal in the top bar"),
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el), hint, left, foot(cancel, save));
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
  const wizard = makeNewGoal(core);                    // a new goal: one sheet (shell-goal-new.js)

  // -- a goal's team from its own screen (spec 41 §7): the Team and Checks folds of New goal, saved alone -----------------------
  const party = makeParty(core);
  const teamSave = h("button", { class: "ork-btn primary big", type: "button" }, "Save team");
  const teamSheet = sheet("Team", party.own, party.team, party.price, party.checks, foot(teamSave));
  let teamOf = "";
  teamSave.addEventListener("click", async () => {
    const p = party.get();
    teamSave.disabled = true;
    const got = await core.call("ideas.goal_save", { slug: teamOf, team: p.team, every: p.every, leader: p.leader, ...(p.party ? { party: p.party } : {}) });
    teamSave.disabled = false;
    if (!got?.slug) return;
    (got.notes || []).forEach((n) => core.flash(n));       // an agent of the party's the project has already: kept as it is
    teamSheet.close();
    core.refresh();
  });
  return {
    el: sh.el,
    sheets: [sh.el, wizard.el, teamSheet.el],
    /** Change the team of a goal (`g`: as `ideas.goal` sends it). */
    editTeam(g) {
      teamOf = g.slug;
      party.set({ leader: g.leader?.slug || "taskmaster", team: g.team || [], every: g.every || [], party: g.party || "" }, () => g.craft || "");
      teamSheet.open();
      party.open();
    },
    open(which = "", after = null) {
      if (!which) { wizard.open(after); return; }
      slug = which;
      then = after;
      const g = which ? (core.st.board?.tracks || []).find((t) => t.slug === which) : null;
      sh.title(g ? "Edit goal" : "New goal");
      titleField.hidden = !g;                          // a new goal has no title to type: the Taskmaster writes it
      title.value = g?.title || "";
      about.value = g?.about || "";
      priority.set(g?.priority || "normal");
      craft.value = g?.craft || "engineering";
      left.replaceChildren(limitsNote(core.st.snap) || "");
      drawCraft();
      save.disabled = !about.value.trim();
      sh.open();
      about.focus();
    },
  };
}

/** The goal's screen: returns the nodes of its body (the preview puts them in). `act` is the preview's own (it flashes and reads again).
 * Its leader speaks in it: reads the goal, answers, and, when the goal's ideas are done, accepts it against its metrics (the verdict). */
export function goalBody(g, core, act, asked, setAsked) {
  const words = goalState(g), lead = leaderName(g), the = g?.leader?.slug && g.leader.slug !== "taskmaster" ? lead : `The ${lead}`;
  const field_ = h("textarea", { class: "ork-field", id: "answer-field", rows: "2", maxlength: "20000", "aria-label": `Answer ${lead}`, placeholder: `Answer ${lead}…` });
  field_.value = asked;
  field_.addEventListener("input", () => setAsked(field_.value));
  const send = h("button", { class: "ork-btn", type: "button" }, "Send");
  send.addEventListener("click", async () => {
    const text = field_.value.trim();
    if (!text) return;
    send.disabled = true;
    const r = await act("ideas.say", { slug: g.slug, text, goal: true }, `Sent: ${lead} answers in a moment.`);
    send.disabled = false;
    if (r) { setAsked(""); field_.value = ""; }
  });
  const sec = (name, ...kids) => h("section", { class: "goal-sec", "aria-label": name }, h("h3", {}, name), ...kids);
  return [
    h("p", { class: "muted" }, [words || "not read yet", PRIORITY_WORDS[g.priority], g.deadline ? `by ${g.deadline}` : ""].filter(Boolean).join(" · ")),
    g.state_error && g.state === "raw" ? h("p", { class: "warn" }, g.state_error) : null,
    g.state_error && g.state !== "raw" && /^Not accepted/.test(g.state_error) ? h("p", { class: "warn" }, g.state_error) : null,
    verdictSec(g, core, act, sec, lead),
    teamSec(g, core, sec),
    h("section", { class: "goal-sec", "aria-label": "What the party did" }, partyFold(core, g.slug)),
    sec("Description", h("p", { class: "brief" }, g.description || "No description yet.")),
    sec("Summary", h("p", { class: "brief" }, g.summary || (g.state === "reading" ? `${the} is reading the goal…` : "Not written yet."))),
    sec("Metrics", g.metrics.length ? h("div", { class: "metrics" }, ...g.metrics.map((m) => h("div", { class: "card metric" }, h("b", {}, m.name),
      h("small", {}, `Target: ${m.target || "—"}`), h("small", { class: "muted" }, m.how ? `Counted: ${m.how}` : "How it is counted: not said yet")))) : h("p", { class: "muted" }, "No metric yet.")),
    sec("Links", g.links.length ? h("ul", { class: "links" }, ...g.links.map((l) => h("li", {}, isUrl(l)
      ? h("a", { href: l, target: "_blank", rel: "noopener noreferrer" }, l)
      : h("button", { class: "linkish", type: "button", onclick: () => core.open({ kind: "doc", slug: g.slug, path: l }) }, l)))) : h("p", { class: "muted" }, "No link.")),
    sec("Open questions", g.questions.length ? h("ul", { class: "links" }, ...g.questions.map((q) => h("li", {}, q)))
      : h("p", { class: "muted" }, g.state === "ready" ? `${the} has no question.` : "No question yet."),
    h("div", { class: "ask" }, h("div", { class: "row" }, field_, send))),
    (g.talk || []).length ? h("div", { class: "talk" }, ...g.talk.slice(-6).map((t) => h("div", { class: `turn ${t.who}` },
      h("span", { class: "who" }, t.who === "you" ? "You" : the), h("p", {}, t.text)))) : null,
  ].filter(Boolean);
}

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const usdWords = (usd) => `≈$${usd.toFixed(2)}`;

/** What a party did (spec 43 §2.3), a line each, in the text face: the leader's steps, each member's tasks, each checker's checks. */
export function partyLines(w) {
  if (!w.ideas) return ["No work yet"];
  const lead = w.leader;
  const lines = [`${lead.name} (leads)${lead.usd != null ? `: ${usdWords(lead.usd)} for the goal, the drafts and the plans` : ""}`];
  for (const m of w.members) {
    lines.push(`${m.name}: ${plural(m.tasks, "task", "tasks")}, ${m.first_time ? `${m.first_time} merged the first time` : "none merged the first time"}${m.usd != null ? ` · ${usdWords(m.usd)}` : ""}`);
  }
  for (const c of w.checks) {
    lines.push(`${c.name}: checked ${plural(c.applied, "idea", "ideas")}: ${c.clean} clean, caught ${c.caught}${c.left ? ` (${c.left} left)` : ""}`
      + `${c.usd != null ? ` · ${usdWords(c.usd)}` : ""}${c.skipped ? ` · skipped ${c.skipped}` : ""}${c.before ? ` · ${c.before} before findings were kept` : ""}`);
  }
  return lines;
}

/** *What the party did*: a fold, closed at first, that reads `ideas.party` when it is opened and says it once (`opened` `party`). */
export function partyFold(core, slug) {
  const body = h("div", {}, h("p", { class: "muted" }, "Reading…"));
  const el = h("details", { class: "party-work" }, h("summary", {}, "What the party did"), body);
  el.addEventListener("toggle", async () => {
    if (!el.open) return;
    core.call("ideas.log", { event: "opened", what: "party", ref: slug, device: "phone" });
    const got = await core.call("ideas.party", { goal: slug });
    if (got) body.replaceChildren(h("ul", { class: "party-lines" }, ...partyLines(got).map((l) => h("li", {}, l))));
  });
  return el;
}

// What the person has half done in Save this party, kept apart from the DOM so a redraw puts it back (goal → {name, replace}).
const naming = new Map();

/** **Save this party**, under the Team: it asks a name (*Engineering party*), asks again before it replaces a party of that name, and says after
 *  *Saved: pick it for a goal in any project.* */
function savePartyEl(g, core) {
  const wrap = h("div", { class: "party-save" });
  const draw = () => {
    const now = naming.get(g.slug);
    if (!now) {
      wrap.replaceChildren(h("button", { class: "linkish", type: "button", onclick: () => { naming.set(g.slug, { name: `${CRAFT_WORDS[g.craft] || "Engineering"} party`, replace: "" }); draw(); } }, "Save this party"));
      return;
    }
    const send = async (replacing) => {
      const name = now.name.trim().replace(/\s+/g, " ");
      if (!replacing) {                                          // a taken name asks before it replaces
        const have = await core.call("ideas.parties");
        const hit = (have?.parties || []).find((p) => p.name.toLowerCase() === name.toLowerCase());
        if (hit) { now.replace = hit.name; draw(); return; }
      }
      const got = await core.call("ideas.party_save", { goal: g.slug, name, ...(replacing ? { replace: true } : {}) });      // a refusal is flashed
      if (got) { naming.delete(g.slug); core.flash("Saved: pick it for a goal in any project."); draw(); }
    };
    if (now.replace) {
      wrap.replaceChildren(h("p", { class: "party-save-ask", role: "alert" }, `Replace your party “${now.replace}”?`,
        h("button", { class: "ork-btn primary", type: "button", onclick: () => send(true) }, "Replace it"),
        h("button", { class: "ork-btn", type: "button", onclick: () => { now.replace = ""; draw(); } }, "Cancel")));
      return;
    }
    const field = h("input", { class: "ork-field", type: "text", "aria-label": "Name of your party", maxlength: "40" });
    field.value = now.name;
    const go = h("button", { class: "ork-btn primary", type: "submit", disabled: !now.name.trim() }, "Save");
    field.addEventListener("input", () => { now.name = field.value; go.disabled = !field.value.trim(); });
    const form = h("form", { class: "row party-save-form" }, field, go, h("button", { class: "ork-btn", type: "button", onclick: () => { naming.delete(g.slug); draw(); } }, "Cancel"));
    form.addEventListener("submit", (e) => { e.preventDefault(); if (now.name.trim()) send(false); });
    wrap.replaceChildren(form);
  };
  draw();
  return wrap;
}

/** The goal's team in one line — the heads with their names — and Change (spec 41 §7). */
function teamSec(g, core, sec) {
  const roles = core.st.roles?.roles || [];
  const lib = core.st.roles?.library || [];
  const mine = [g.leader?.slug || "taskmaster", ...(g.team || [])];
  const pick = (id) => {
    const r = roles.find((x) => x.slug === id), a = lib.find((x) => x.id === id);
    return { name: r?.name || a?.name || id, head: r?.head || (a ? { craft: a.craft, race: { engineering: "peon", design: "elf", data: "goblin", marketing: "gnome", product: "lich" }[a.craft] || "peon", tier: a.tier } : null) };
  };
  return sec("Team", h("p", { class: "team-line" }, ...mine.map(pick).flatMap((m, i) => [i ? " · " : "", whoHead(m.head, true), " ", m.name])),
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", "data-change": "team", "aria-label": "Change the team",
      onclick: () => core.editTeam(g) }, "Change")), saveParty(g, core));
}

/** *Save this party*, quiet, beside Change (spec 43 §6.3): asks a name (filled with *Engineering party*), saves the goal's party among the person's,
 * and says where to pick it. A taken name asks *Replace your party “…”?* first. */
function saveParty(g, core) {
  const name = h("input", { class: "ork-field", type: "text", "aria-label": "Name of your party", maxlength: "40" });
  const go = h("button", { class: "ork-btn primary", type: "submit" }, "Save");
  const cancel = h("button", { class: "ork-btn", type: "button" }, "Cancel");
  const form = h("form", { class: "party-save-form", "aria-label": "Save this party", hidden: true }, name, h("div", { class: "row" }, go, cancel));
  const open = h("button", { class: "ork-btn quiet", type: "button", "data-save-party": "" }, "Save this party");
  open.addEventListener("click", () => { name.value = `${CRAFT_WORDS[g.craft] || "Your"} party`; form.hidden = false; open.hidden = true; name.focus(); });
  cancel.addEventListener("click", () => { form.hidden = true; open.hidden = false; });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const typed = name.value.trim().replace(/\s+/g, " ");
    if (!typed) return;
    go.disabled = true;
    const taken = ((await core.call("ideas.parties", {}))?.parties || []).find((p) => p.name.toLowerCase() === typed.toLowerCase());
    const got = !taken || confirm(`Replace your party “${taken.name}”?`)
      ? await core.call("ideas.party_save", { goal: g.slug, name: typed, ...(taken ? { replace: true } : {}) }) : null;
    go.disabled = false;
    if (!got) return;
    form.hidden = true;
    open.hidden = false;
    core.flash("Saved: pick it for a goal in any project.");
  });
  return h("span", { class: "party-save" }, open, form);
}

/** The goal's verdict: met or not, each metric's status and why, the next ideas (each added with a tap); and the button that
 * asks the leader to accept the goal — once its ideas are all done, or again after a verdict. */
function verdictSec(g, core, act, sec, lead) {
  const mine = (core.st.board?.ideas || []).filter((i) => i.track === g.slug);
  const done = mine.length > 0 && mine.every((i) => i.state === "done");
  const v = g.verdict;
  if (!v && !done) return null;
  const accepting = g.busy && g.state !== "reading";
  const ask = h("button", { class: `ork-btn${v ? "" : " primary"}`, type: "button", disabled: accepting,
    onclick: () => act("ideas.goal_accept", { slug: g.slug }, `${lead} is accepting the goal.`) }, v ? `Ask ${lead} again` : `Ask ${lead} to accept`);
  if (!v) {
    return sec("Verdict", h("p", { class: "muted" }, accepting ? `${lead} is accepting the goal against its metrics…`
      : `Its ideas are done: ${lead} accepts the goal against its metrics, not against the work done.`), h("div", { class: "row" }, ask));
  }
  const add = (text) => act("ideas.add", { text, track: g.slug, priority: "normal" }, "Added: drafted now.");
  return sec("Verdict",
    h("p", { class: `verdict-line ${v.met ? "is-met" : "is-not"}` }, h("b", {}, v.met ? "Goal met" : "Not met yet"), ` · by ${v.by || lead}`),
    v.verdict ? h("p", { class: "brief" }, v.verdict) : null,
    v.metrics?.length ? h("ul", { class: "verdict-metrics", "aria-label": "Metrics, as accepted" }, ...v.metrics.map((m) => h("li", { class: `status-${m.status.replace(" ", "-")}` },
      h("b", {}, m.name), ` · ${STATUS_WORDS[m.status] || m.status}`, m.why ? h("small", { class: "muted" }, m.why) : null))) : null,
    v.next?.length ? h("div", { class: "verdict-next", role: "group", "aria-label": "Next ideas" }, h("h4", {}, "Next ideas"),
      ...v.next.map((x) => h("div", { class: "row" }, h("span", {}, x),
        h("button", { class: "ork-btn", type: "button", "aria-label": `Add as idea: ${x}`, onclick: () => add(x) }, "Add as idea")))) : null,
    h("div", { class: "row" }, ask));
}

const usdWords = (usd) => (usd == null ? "" : ` · ≈$${usd.toFixed(2)}`);
const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** The lines of *What the party did* (spec 43 §2.3) from `ideas.party`'s object: [{text, head?}], the leader, each member, each check. */
export function partyLines(w) {
  if (!w.ideas) return [{ text: "No work yet" }];
  const lead = w.leader;
  return [
    { head: lead.head, text: `${lead.name} (leads): ${lead.usd != null ? `≈$${lead.usd.toFixed(2)} for the goal, the drafts and the plans` : "the goal, the drafts and the plans"}` },
    ...w.members.map((m) => ({ head: m.head, text: `${m.name}: ${count(m.tasks, "task", "tasks")}, ${m.first_time} merged the first time${usdWords(m.usd)}` })),
    ...w.checks.map((c) => ({ head: c.head, text: `${c.name}: ${c.applied || c.clean || c.caught
      ? `checked ${count(c.applied, "idea", "ideas")}: ${c.clean} clean, caught ${c.caught}${c.left ? ` (${c.left} left)` : ""}` : "no idea checked yet"}`
      + `${usdWords(c.usd)}${c.skipped ? ` · skipped ${c.skipped}` : ""}${c.before ? ` · ${c.before} before findings were kept` : ""}` })),
  ];
}

/** *What the party did*: a fold, closed at first; what a goal's party did is read when it is opened, and logged (spec 43 §2.3). */
export function partyFold(core, slug) {
  const list = h("ul", { class: "party-work-list", "aria-label": "What the party did" });
  const el = h("details", { class: "party-work" }, h("summary", {}, "What the party did"), list);
  el.addEventListener("toggle", async () => {
    if (!el.open) return;
    core.call("ideas.log", { event: "opened", what: "party", ref: slug, device: "phone" });
    const got = await core.call("ideas.party", { goal: slug });
    if (got && el.open) list.replaceChildren(...partyLines(got).map((l) => h("li", {}, l.head ? whoHead(l.head, true) : "", l.head ? " " : "", h("span", {}, l.text))));
  });
  return el;
}
