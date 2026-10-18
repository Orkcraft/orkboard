// Needs you on the phone (docs/specs/35-goals-window.md §9, §10, §11.2): one list the backend sorted, an icon per kind, the title and one
// line. A tap opens what it is about: the questions of a spec or a goal as one form in a sheet (a box per question, one Send), the plan
// on its screen, the to-do's sheet (its why, its steps, then its one input: a secret, a choice, a confirm or a file), the goal. A proposal
// is answered in its row: Take with a priority, No with a reason.
import { h, sheet } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";

const ICONS = { goal: "🎯", asks: "❓", plan: "📋", todo: "☑️", failed: "⚠️", proposal: "💡", op: "☑️", op_failed: "⚠️", op_rules: "💡" };
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

export function makeNeeds(core, ctx, ops) {
  const st = core.st;

  // -- the questions of a spec or a goal: one form, one Send (§0's one round) ---------------------------------------------
  const qBody = h("form", { class: "sheet-form q-form" });
  const qSheet = sheet("Questions", qBody);
  async function askForm(n) {
    const isGoal = n.kind === "goal";
    const slug = isGoal ? n.goal : n.idea;
    const got = await core.call(isGoal ? "ideas.goal" : "ideas.page", { slug });
    if (!got) return;
    const qs = isGoal ? got.questions || [] : questionsOf((got.sections || []).find((s) => s.name === "Open questions")?.text);
    if (!qs.length) { core.open(isGoal ? { kind: "goal", slug } : { kind: "idea", slug }); return; }
    const boxes = qs.map((q, i) => h("textarea", { class: "ok-input", rows: "2", maxlength: "20000", "aria-label": `Answer ${i + 1}: ${q}`, placeholder: "Your answer, or leave it and the Taskmaster decides" }));
    const send = h("button", { class: "ok-btn primary big", type: "submit" }, "Send");
    const cancel = h("button", { class: "ok-btn big", type: "button", onclick: () => qSheet.close() }, "Cancel");
    qBody.replaceChildren(h("p", { class: "muted" }, n.title), ...qs.map((q, i) => field(`${i + 1}. ${q}`, boxes[i])), foot(cancel, send));
    qBody.onsubmit = async (e) => {
      e.preventDefault();
      send.disabled = true;
      const r = await core.call("ideas.answer", { slug, answers: boxes.map((b) => b.value.trim()), ...(isGoal ? { goal: true } : {}) });
      send.disabled = false;
      if (!r) return;
      qSheet.close();
      ctx.flash("Sent: the Taskmaster answers in a moment.");
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
      const f = h("input", { class: "ok-input", type: "password", autocomplete: "off", "aria-label": `${t.title}: the value`, placeholder: "The value" });
      const save = h("button", { class: "ok-btn primary big", type: "button", onclick: async () => {
        if (!f.value) return;
        save.disabled = true;
        const bad = await give(n.idea, t, { value: f.value }, true);
        f.value = "";
        if (bad) { tell(bad); save.disabled = false; }
      } }, "Store it");
      kids.push(f, h("p", { class: "muted hint" }, "It goes to this computer’s secret store over the paired link, never into a file or to a model."), save);
    } else if (t.kind === "file") {
      const pick = h("input", { class: "ok-input", type: "file", "aria-label": `${t.title}: the file`, ...((t.accept || []).length ? { accept: t.accept.join(",") } : {}) });
      const save = h("button", { class: "ok-btn primary big", type: "button", disabled: true }, "Send the file");
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
      kids.push(h("div", { class: "answers" }, ...(t.choices || []).map((c) => h("button", { class: "ok-btn big", type: "button",
        onclick: async () => { const bad = await give(n.idea, t, { value: c }, true); if (bad) tell(bad); } }, c))));
    } else {
      kids.push(h("button", { class: "ok-btn primary big", type: "button", onclick: async () => { const bad = await give(n.idea, t, {}, true); if (bad) tell(bad); } }, "Done"));
    }
    kids.push(say, h("p", { class: "muted" }, h("button", { class: "linkish", type: "button",
      onclick: () => { tSheet.close(); core.open({ kind: "plan", slug: n.idea, todo: t.id }); } }, "Open the plan")));
    tBody.replaceChildren(...kids);
    tSheet.title("To-do");
    tSheet.open();
  }

  // -- a proposal is answered in its row ----------------------------------------------------------------------------
  function proposal(n) {
    const prio = prioritySwitch(`prio-${n.idea}`);
    prio.set(n.priority || "normal");
    const reason = h("input", { class: "ok-input", type: "text", maxlength: "300", "aria-label": `Why not: ${n.title}`, placeholder: "Why not (optional)" });
    const act = async (take) => {
      const r = await core.call("ideas.proposal", { slug: n.idea, take, ...(take ? { priority: prio.get() } : reason.value.trim() ? { reason: reason.value.trim() } : {}) });
      if (r) core.refresh();
    };
    return h("div", { class: "card need need-proposal", "data-kind": "proposal", "data-idea": n.idea },
      h("span", { class: "need-mark", "aria-hidden": "true" }, ICONS.proposal),
      h("span", { class: "need-text" }, h("b", {}, n.title), n.text ? h("small", {}, n.text) : null,
        h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), prio.el),
        h("div", { class: "row" }, h("button", { class: "ok-btn primary", type: "button", onclick: () => act(true) }, "Take"),
          reason, h("button", { class: "ok-btn", type: "button", onclick: () => act(false) }, "No"))));
  }

  function row(n) {
    if (n.kind === "proposal") return proposal(n);
    const go = () => {
      if (n.kind === "op") ops.openCheck(n.op);
      else if (n.kind === "op_failed") ops.openRun(n.op);
      else if (n.kind === "op_rules") ops.openProposal(n);
      else if (n.kind === "goal" || n.kind === "asks") askForm(n);
      else if (n.kind === "todo") todoSheet(n);
      else core.open({ kind: "idea", slug: n.idea });
    };
    return h("button", { class: `card need need-${n.kind}`, type: "button", "data-kind": n.kind, onclick: go },
      h("span", { class: "need-mark", "aria-hidden": "true" }, ICONS[n.kind] || "•"),
      h("span", { class: "need-text" }, h("b", {}, n.title), n.text ? h("small", {}, n.text) : null),
      h("span", { class: "chev", "aria-hidden": "true" }, "›"));
  }

  return {
    sheets: [qSheet.el, tSheet.el],
    /** The list's nodes, narrowed to the chosen goal. */
    draw() {
      const all = (st.board?.needs_you || []).filter((n) => !st.track || n.goal === st.track || n.kind.startsWith("op"));   // Operations' rows are the person's, in every project and goal
      const kids = [h("h3", {}, "Needs you")];
      if (!all.length) kids.push(h("p", { class: "muted" }, "Nothing waits on you."));
      return [...kids, ...all.map(row)];
    },
  };
}
