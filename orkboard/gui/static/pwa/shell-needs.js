// What waits for an answer, as the stops along the bottom ask for it (docs/specs/35-goals-window.md §9, §10, spec 41 §9, spec 49 §6): the sheets that
// answer in full what a stop answers in one press. *More* of a question: the form with a box per question, the recommended answers filled in
// (`askForm`); a to-do (`todoSheet`): its why, its steps, then its one input — a secret, a choice, a confirm or a file — which is entered only over
// this paired link (29a). The stops (shell-stops.js) draw the rows and press the quick answers; the list, Later and the swipe went with the Needs you tab.
// Every stop has a way out that needs nothing from the person (spec 54 §3, decisions §67.4), here for the raised card and the sheet alike: a question *Let <asker> decide*; a file to-do *Describe it instead*
// (a field and Send) or *Go without it*; a choice *Let <leader> choose*; any other to-do *Go without it*. Each is quiet and acts at once.
import { h, sheet } from "./util.js";
import { field, foot } from "./shell-forms.js";

const MAX_FILE = 5 * 1024 * 1024;
const isList = /^([-*+]|\d+[.)])\s+/;

/** A spec's Open questions section as the list the keeper counts (realm/ideas.py `items`). */
export function questionsOf(text) {
  const lines = String(text || "").split("\n").map((l) => l.trim()).filter(Boolean);
  const marked = lines.filter((l) => isList.test(l)).map((l) => l.replace(isList, ""));
  return marked.length ? marked : lines;
}

const toBase64 = (file) => new Promise((ok, no) => {
  const r = new FileReader();
  r.onload = () => ok(String(r.result).split(",")[1] || "");
  r.onerror = () => no(r.error);
  r.readAsDataURL(file);
});

export function makeNeeds(core, ctx) {
  const st = core.st;

  // -- the questions of a spec or a goal: one form, one Send (§0's one round) ---------------------------------------------
  const qBody = h("form", { class: "sheet-form q-form" });
  const qSheet = sheet("Questions", qBody);
  /** A card's questions as `asked` says them; a row without it (or a page of before) has the plain lines, no choices. */
  const askedOf = (n) => (n.asked?.length ? n.asked : (n.questions || (n.text ? [n.text] : [])).filter(Boolean).map((ask) => ({ ask, choices: [], pick: null, why: "" }))).slice(0, 3);
  const SENT = "Sent: the Taskmaster answers in a moment.";

  // -- the ways out (spec 54 §3) ------------------------------------------------------------------------------------------------------
  const THE = (name) => (name === "Taskmaster" ? "the Taskmaster" : name);                 // the Taskmaster takes its article, the others are named
  const goalOf = (slug) => (st.map?.goals || []).find((g) => g.slug === slug);
  const leaderOf = (n) => THE(goalOf(n.goal)?.leader?.name || "Taskmaster");
  const askerOf = (n) => THE(askedOf(n)[0]?.by?.name || goalOf(n.goal)?.leader?.name || "Taskmaster");
  const quiet = (label, attrs, run) => h("button", { class: "ork-btn quiet", type: "button", ...attrs, onclick: run }, label);
  /** *Let <asker> decide*, last and quiet: the question is answered with each recommended choice (`ideas.answer {decide: true}`); `after`: what is put away once it is sent. */
  function decideButton(n, after) {
    const isGoal = n.kind === "goal", who = askerOf(n);
    return quiet(`Let ${who} decide`, { "data-act": "decide", title: `${who} answers with the choice it recommends for each question` }, async () => {
      const r = await core.call("ideas.answer", { slug: isGoal ? n.goal : n.idea, decide: true, ...(isGoal ? { goal: true } : {}) });
      if (!r) return;
      if (after) after();
      ctx.flash(`Sent: ${who} decides.`);
      core.refresh();
    });
  }
  /** A to-do's ways out, under its own input (`ideas.todo`): a file *Describe it instead* (a field and Send) and *Go without it*; a choice *Let <leader> choose*; any other *Go without it*.
   *  `after`: what is put away once one is sent; `onError(text)`: where a refusal is said (the sheet's line; else the toast). Returns the nodes. */
  function todoOuts(n, after, onError) {
    const t = n.todo, leader = leaderOf(n);
    const send = async (extra, said) => {
      const r = await core.call("ideas.todo", { idea: n.idea, id: t.id, ...extra }, onError);
      if (!r) return false;
      if (after) after();
      ctx.flash(said);
      core.refresh();
      return true;
    };
    const without = (label, tip) => quiet(label, { "data-act": "skip", title: tip }, () => send({ skip: true }, `Done: ${leader}’s plan goes on without it.`));
    if (t.kind === "choice") return [without(`Let ${leader} choose`, `${leader} chooses one of them, and says which and why`)];
    if (t.kind !== "file") return [without("Go without it", "Its tasks run without it, and say so if they cannot")];
    const words = h("textarea", { class: "ork-field", rows: "3", maxlength: "2000", "aria-label": "What should it look like?", placeholder: "What should it look like?" });
    const go = h("button", { class: "ork-btn", type: "button", "data-act": "describe-send", disabled: true }, "Send");
    words.addEventListener("input", () => { go.disabled = !words.value.trim(); });
    go.addEventListener("click", async () => { go.disabled = true; if (!(await send({ done: true, words: words.value.trim() }, `Sent: the words go to ${leader}.`))) go.disabled = !words.value.trim(); });
    const form = h("div", { class: "describe", hidden: true }, words, go);
    const open = quiet("Describe it instead", { "data-act": "describe", "aria-expanded": "false", title: "Say it in words instead of a file" }, () => {
      form.hidden = !form.hidden;
      open.setAttribute("aria-expanded", String(!form.hidden));
      if (!form.hidden) words.focus();
    });
    return [open, form, without("Go without it", "Its tasks run without it, and say so if they cannot")];
  }
  async function askForm(n, picks = []) {
    const isGoal = n.kind === "goal";
    const slug = isGoal ? n.goal : n.idea;
    let asked = n.asked?.length ? n.asked : null;
    if (!asked) {
      const got = await core.call(isGoal ? "ideas.goal" : "ideas.page", { slug });
      if (!got) return;
      const lines = isGoal ? got.questions || [] : questionsOf((got.sections || []).find((s) => s.name === "Open questions")?.text);
      asked = lines.map((ask) => ({ ask, choices: [], pick: null, why: "" }));
    }
    if (!asked.length) { core.open(isGoal ? { kind: "goal", slug } : { kind: "idea", slug }); return; }
    const boxes = asked.map((q, i) => {
      const box = h("textarea", { class: "ork-field", rows: "2", maxlength: "20000", "aria-label": `Answer ${i + 1}: ${q.ask}`, placeholder: "Your answer, or leave it and the Taskmaster decides" });
      box.value = picks[i] ?? (q.pick != null ? q.choices[q.pick] || "" : "");     // the recommended answers filled in
      return box;
    });
    const send = h("button", { class: "ork-btn primary big", type: "submit" }, "Send");
    const cancel = h("button", { class: "ork-btn big", type: "button", onclick: () => qSheet.close() }, "Cancel");
    qBody.replaceChildren(h("p", { class: "muted" }, n.title), ...asked.map((q, i) => field(`${i + 1}. ${q.ask}`, boxes[i], q.why || null)),
      h("div", { class: "outs" }, decideButton(n, () => qSheet.close())), foot(cancel, send));
    qBody.onsubmit = async (e) => {
      e.preventDefault();
      send.disabled = true;
      const r = await core.call("ideas.answer", { slug, answers: boxes.map((b) => b.value.trim()), ...(isGoal ? { goal: true } : {}) });
      send.disabled = false;
      if (!r) return;
      qSheet.close();
      ctx.flash(SENT);
      core.refresh();
    };
    qSheet.open();
    boxes[0].focus();
  }

  // -- a to-do (§9): its why, its steps, then its one input ------------------------------------------------------------
  const tBody = h("div", { class: "todo-sheet" });
  const tSheet = sheet("To-do", tBody);
  async function give(idea, todo, extra, done) {
    const r = await ctx.send("ideas.todo", { idea, id: todo.id, done, ...extra });
    if (!r.ok || r.result?.error) return r.error || r.result?.error || "That did not work";
    tSheet.close();
    await core.refresh();
    return "";
  }
  function todoSheet(n) {
    const t = n.todo;
    const say = h("p", { class: "warn", role: "alert", hidden: true });
    const tell = (text) => { say.textContent = text; say.hidden = !text; };
    const kids = [h("h3", {}, t.title)];
    if (t.why) kids.push(h("p", { class: "muted" }, t.why));
    if ((t.steps || []).length) kids.push(h("ol", { class: "steps" }, ...t.steps.map((s) => h("li", {}, s))));
    if (t.kind === "secret") {
      const f = h("input", { class: "ork-field", type: "password", autocomplete: "off", "aria-label": `${t.title}: the value`, placeholder: "The value" });
      const save = h("button", { class: "ork-btn primary big", type: "button", onclick: async () => {
        if (!f.value) return;
        save.disabled = true;
        const bad = await give(n.idea, t, { value: f.value }, true);
        f.value = "";
        if (bad) { tell(bad); save.disabled = false; }
      } }, "Store it");
      kids.push(f, h("p", { class: "muted hint" }, "It goes to this computer’s secret store over the paired link, never into a file or to a model."), save);
    } else if (t.kind === "file") {
      const pick = h("input", { class: "ork-field", type: "file", "aria-label": `${t.title}: the file`, ...((t.accept || []).length ? { accept: t.accept.join(",") } : {}) });
      const save = h("button", { class: "ork-btn primary big", type: "button", disabled: true }, "Send the file");
      pick.addEventListener("change", () => { save.disabled = !pick.files?.length; tell(""); });
      save.addEventListener("click", async () => {
        const f = pick.files?.[0];
        if (!f) return;
        if (f.size > MAX_FILE) { tell("That file is over 5 MB."); return; }
        save.disabled = true;
        const bad = await give(n.idea, t, { file: { name: f.name, data: await toBase64(f) } }, true);
        if (bad) { save.disabled = false; tell(/paired|computer/i.test(bad) ? "At the computer: give this file there. A file is taken only over the paired link." : bad); }
      });
      kids.push(pick, h("p", { class: "muted hint" }, "At most 5 MB. It is kept on this computer, never in the repository or in a prompt."), save);
    } else if (t.kind === "choice") {
      kids.push(h("div", { class: "answers" }, ...(t.choices || []).map((c) => h("button", { class: "ork-btn big", type: "button",
        onclick: async () => { const bad = await give(n.idea, t, { value: c }, true); if (bad) tell(bad); } }, c))));
    } else {
      kids.push(h("button", { class: "ork-btn primary big", type: "button", onclick: async () => { const bad = await give(n.idea, t, {}, true); if (bad) tell(bad); } }, "Done"));
    }
    kids.push(h("div", { class: "outs", role: "group", "aria-label": "Other ways" }, ...todoOuts(n, () => tSheet.close(), tell)));
    kids.push(say, h("p", { class: "muted" }, h("button", { class: "linkish", type: "button",
      onclick: () => { tSheet.close(); core.open({ kind: "plan", slug: n.idea, todo: t.id }); } }, "Open the plan")));
    tBody.replaceChildren(...kids);
    tSheet.title("To-do");
    tSheet.open();
  }

  return {
    sheets: [qSheet.el, tSheet.el],
    askForm, todoSheet, askedOf, decideButton, todoOuts,
    SENT,
  };
}
