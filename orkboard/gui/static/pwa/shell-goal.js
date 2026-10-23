// A party on the phone (docs/specs/35-goals-window.md §2, §11; spec 50 §0, §6): the Edit the party sheet — what it is for, its craft (the head of its race
// marks the party, decisions §53) and a priority, and the name too (to correct the Taskmaster's) — and the party's own screen (what it is for, the Taskmaster's Summary, its Links,
// the Open questions with a box to answer, what the party did). A party has no end: no Metrics, no verdict (a verdict of before is history, *Before: …*). Saving sends the party to the
// Taskmaster at once; it writes the rest. New party is shell-goal-new.js's.
import { h, sheet } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { PRIORITY_WORDS } from "./shell-words.js";
import { CRAFT_WORDS, RACE_WORDS, goalHead, whoHead } from "./shell-who.js";
import { limitsNote } from "./shell-limits.js";
import { flagWords } from "./shell-map.js";
import { makeNewGoal, makeParty, IDEATION_WHOLE } from "./shell-goal-new.js";

const CRAFTS = [["engineering", "peon"], ["design", "elf"], ["data", "goblin"], ["marketing", "gnome"], ["product", "lich"]];   // realm/roles.py RACES

export { PRIORITY_WORDS };
export const GOAL_STATE = { reading: "the Taskmaster is reading", asks: "asks you", ready: "ready" };
/** Who leads a party (the Taskmaster when none, realm/goal_team.py). */
export const leaderName = (g) => g?.leader?.name || "Taskmaster";
/** A party's state in words, its leader's name in them. */
export function goalState(g) {
  if (g?.state === "reading") return `${g?.leader?.name && g.leader.slug !== "taskmaster" ? g.leader.name : "the Taskmaster"} is reading`;
  return GOAL_STATE[g?.state] || "";
}
const isUrl = (l) => /^[a-z][a-z0-9+.-]*:\/\//i.test(l);

export function makeGoalSheet(core) {
  const title = h("input", { class: "ork-field", type: "text", "aria-label": "Name", placeholder: "The Taskmaster writes it; correct it here", maxlength: "120" });
  const titleField = field("Name", title);
  const about = h("textarea", { class: "ork-field", rows: "5", "aria-label": "What it is for", placeholder: "A few lines: what it is for", maxlength: "20000" });
  const craft = h("select", { class: "ork-field", "aria-label": "Craft" },
    ...CRAFTS.map(([c, race]) => h("option", { value: c }, `${CRAFT_WORDS[c]}: ${/^[aeiou]/.test(RACE_WORDS[race]) ? "an" : "a"} ${RACE_WORDS[race]}`)));
  const craftNow = h("span", { class: "craft-now", "aria-hidden": "true" });
  const drawCraft = () => craftNow.replaceChildren(goalHead({ craft: craft.value, race: Object.fromEntries(CRAFTS)[craft.value] }));
  craft.addEventListener("change", drawCraft);
  const priority = prioritySwitch();
  const hint = h("p", { class: "muted hint" }, "The Taskmaster reads it and writes the name and the summary.");
  const left = h("div", {});                         // what is left of the AI tools: reading the party spends them
  const save = h("button", { class: "ork-btn primary big", type: "submit", disabled: true }, "Save party");
  const cancel = h("button", { class: "ork-btn big", type: "button" }, "Cancel");
  const form = h("form", { class: "sheet-form" }, titleField, field("What it is for", about),
    field("Craft", h("div", { class: "row craft-pick" }, craftNow, craft), "Its head marks the party in the top bar"),
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), priority.el), hint, left, foot(cancel, save));
  const sh = sheet("Edit the party", form);
  let slug = "";
  let then = null;                                   // what to do with the party's slug instead of opening its screen (New goal with no party yet)
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
  const wizard = makeNewGoal(core);                    // a new party: one sheet (shell-goal-new.js)

  // -- a party's members from its own screen or the dial (spec 41 §7): the party's and the checks' folds of New party, saved alone -----------------------
  const party = makeParty(core);
  const teamSave = h("button", { class: "ork-btn primary big", type: "button" }, "Save the party");
  const teamSheet = sheet("The party", party.team, party.checks, foot(teamSave));
  let teamOf = "";
  teamSave.addEventListener("click", async () => {
    const p = party.get();
    teamSave.disabled = true;
    const got = await core.call("ideas.goal_save", { slug: teamOf, team: p.team, every: p.every, leader: p.leader, ...(p.party ? { party: p.party } : {}) });
    teamSave.disabled = false;
    if (!got?.slug) return;
    for (const note of got.notes || []) core.flash(note);
    teamSheet.close();
    core.refresh();
  });
  return {
    el: sh.el,
    sheets: [sh.el, wizard.el, teamSheet.el],
    /** Change the members of a party (`g`: as `ideas.goal` sends it). */
    editTeam(g) {
      teamOf = g.slug;
      party.set({ leader: g.leader?.slug || "taskmaster", team: g.team || [], every: g.every || [], party: g.party || "" }, () => g.craft || "");
      teamSheet.open();
    },
    /** `preset`: New party with that party of the library picked (a pitch sent to a party the project lacks, spec 65 §5). */
    open(which = "", after = null, preset = "") {
      if (!which) { wizard.open(after, preset); return; }
      slug = which;
      then = after;
      const g = which ? (core.st.board?.tracks || []).find((t) => t.slug === which) : null;
      sh.title("Edit the party");
      titleField.hidden = !g;                          // a new party has no name to type: the Taskmaster writes it
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

/** The party's screen: returns the nodes of its body (the preview puts them in). `act` is the preview's own (it flashes and reads again).
 * Its leader speaks in it: reads the party, asks, and is answered. A party has no metrics and no verdict (a verdict of before is history). */
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
    g.verdict?.met ? h("p", { class: "muted", "data-sec": "before" }, `Before: ${flagWords(g.verdict)}`) : null,
    teamSec(g, core, sec),
    h("section", { class: "goal-sec", "aria-label": "What the party did" }, partyFold(core, g.slug)),
    sec("What it is for", h("p", { class: "brief" }, g.description || "Not written yet.")),
    sec("Summary", h("p", { class: "brief" }, g.summary || (g.state === "reading" ? `${the} is reading it…` : "Not written yet."))),
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
  const lines = [`${lead.name} (leads)${lead.usd != null ? `: ${usdWords(lead.usd)} for the party, the drafts and the plans` : ""}`];
  for (const m of w.members) {
    lines.push(`${m.name}: ${plural(m.tasks, "task", "tasks")}, ${m.first_time ? `${m.first_time} merged the first time` : "none merged the first time"}${m.usd != null ? ` · ${usdWords(m.usd)}` : ""}`);
  }
  for (const c of w.checks) {
    lines.push(`${c.name}: checked ${plural(c.applied, "goal", "goals")}: ${c.clean} clean, caught ${c.caught}${c.left ? ` (${c.left} left)` : ""}`
      + `${c.usd != null ? ` · ${usdWords(c.usd)}` : ""}${c.skipped ? ` · skipped ${c.skipped}` : ""}${c.before ? ` · ${c.before} ended without findings` : ""}`);
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

// What the person has half done in Save it to your parties, kept apart from the DOM so a redraw puts it back (party → {name, replace}).
const naming = new Map();

/** **Save it to your parties**, under the party: it asks a name (*Engineering party*), asks again before it replaces a party of that name, and says after
 *  *Saved: pick it for a party in any project.* */
export function savePartyEl(g, core) {
  const wrap = h("div", { class: "party-save" });
  const draw = () => {
    const now = naming.get(g.slug);
    if (!now) {
      wrap.replaceChildren(h("button", { class: "linkish", type: "button", onclick: () => { naming.set(g.slug, { name: `${CRAFT_WORDS[g.craft] || "Engineering"} party`, replace: "" }); draw(); } }, "Save it to your parties"));
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
      if (got) { naming.delete(g.slug); core.flash("Saved: pick it for a party in any project."); draw(); }
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

/** The party's members in one line — the heads with their names — and Change (spec 41 §7). */
function teamSec(g, core, sec) {
  const roles = core.st.roles?.roles || [];
  const lib = core.st.roles?.library || [];
  const mine = [g.leader?.slug || "taskmaster", ...(g.team || [])];
  const pick = (id) => {
    const r = roles.find((x) => x.slug === id), a = lib.find((x) => x.id === id);
    return { name: r?.name || a?.name || id, head: r?.head || (a ? { craft: a.craft, race: { engineering: "peon", design: "elf", data: "goblin", marketing: "gnome", product: "lich" }[a.craft] || "peon", tier: a.tier } : null) };
  };
  const ideation = lib.find((a) => a.id === mine[0])?.pitch === true;        // Ideation keeps its four views and its skeptic: no seat changes (spec 65 §1)
  return sec("The party", h("p", { class: "team-line" }, ...mine.map(pick).flatMap((m, i) => [i ? " · " : "", whoHead(m.head, true), " ", m.name])),
    ideation ? h("p", { class: "cap", "data-sec": "ideation" }, IDEATION_WHOLE)
      : h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", "data-change": "team", "aria-label": "Change the party",
        onclick: () => core.editTeam(g) }, "Change")),
    savePartyEl(g, core));
}
