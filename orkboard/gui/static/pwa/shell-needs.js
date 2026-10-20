// Needs you on the phone (docs/specs/35-goals-window.md §9, §10, §11.2), a screen of its own (the tab opens it): one list the
// backend sorted, every goal's, an icon per kind, the title and one line. Questions are cards answered there (spec 41 §9): each row's
// `asked` — the ask, its choices, the one the Taskmaster picks and why — as buttons with the recommended one pressed and marked
// *Recommended*, so one Send takes every recommendation; More for the form with a box per question, the recommended answers filled in;
// and Let the Taskmaster decide, which answers every question with its pick. A tap on another row opens what it is about: the plan on its screen, the to-do's sheet (its why, its steps, then its one
// input: a secret, a choice, a confirm or a file), the goal. A proposal is answered in its row: Take with a priority, No with a reason.
// Later (or a swipe to the left) puts a row away on this phone for LATER_MS; nothing is sent.
import { h, sheet, icon } from "./util.js";
import { field, foot, prioritySwitch } from "./shell-forms.js";
import { limitsNote } from "./shell-limits.js";

const LATER = "orkcraft.later";                       // {row key: until}, this phone's own
const LATER_MS = 4 * 3600 * 1000;
const SWIPE_PX = 80;
const keyOf = (n) => `${n.kind}:${n.idea || n.goal || n.op || ""}:${n.text || ""}`;
const later = {
  all() { try { return JSON.parse(localStorage.getItem(LATER)) || {}; } catch { return {}; } },
  put(n) {
    const now = Date.now(), all = Object.fromEntries(Object.entries(later.all()).filter(([, t]) => t > now));
    all[keyOf(n)] = now + LATER_MS;
    try { localStorage.setItem(LATER, JSON.stringify(all)); } catch { /* this run only */ }
  },
  has(n) { return (later.all()[keyOf(n)] || 0) > Date.now(); },
};

// What needs the person, by kind, as orkUI's pixel icon (as the desktop's js/orkui.js NEED_ICONS).
const ICONS = { goal: "flag", asks: "warning-diamond", plan: "list-box", todo: "checkbox", failed: "square-alert", proposal: "lightbulb",
  op: "checkbox", op_failed: "square-alert", op_rules: "sliders" };
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
  /** A card's questions as `asked` says them; a row without it (or a page of before) has the plain lines, no choices. */
  const askedOf = (n) => (n.asked?.length ? n.asked : (n.questions || (n.text ? [n.text] : [])).filter(Boolean).map((ask) => ({ ask, choices: [], pick: null, why: "" }))).slice(0, 3);
  const SENT = "Sent: the Taskmaster answers in a moment.";
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
    qBody.replaceChildren(h("p", { class: "muted" }, n.title), ...asked.map((q, i) => field(`${i + 1}. ${q.ask}`, boxes[i], q.why || null)), foot(cancel, send));
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
    kids.push(say, h("p", { class: "muted" }, h("button", { class: "linkish", type: "button",
      onclick: () => { tSheet.close(); core.open({ kind: "plan", slug: n.idea, todo: t.id }); } }, "Open the plan")));
    tBody.replaceChildren(...kids);
    tSheet.title("To-do");
    tSheet.open();
  }

  // -- questions answered in their card: the recommended answer pressed, one Send; More for the whole form ---------------
  function quick(n) {
    const asked = askedOf(n);
    const isGoal = n.kind === "goal", slug = isGoal ? n.goal : n.idea;
    const picked = asked.map((q) => (q.pick != null ? q.choices[q.pick] || "" : ""));
    const send = h("button", { class: "ork-btn primary", type: "button" }, "Send");
    const sync = () => { send.disabled = !picked.some(Boolean); };
    const blocks = asked.map((q, i) => {
      const btns = q.choices.map((c, j) => {
        const reco = j === q.pick;
        const b = h("button", { class: `ork-btn answer${reco ? " is-recommended" : ""}`, type: "button", "aria-pressed": String(picked[i] === c), "data-choice": String(j),
          onclick: () => {
            picked[i] = picked[i] === c ? "" : c;
            for (const x of btns) x.setAttribute("aria-pressed", String(x.dataset.choice === String(q.choices.indexOf(picked[i]))));
            sync();
          } }, c, reco ? h("small", { class: "recommended" }, "Recommended") : null);
        return b;
      });
      return h("div", { class: "quick-q" }, h("p", {}, q.ask), q.choices.length ? h("div", { class: "answers" }, ...btns) : null,
        q.why ? h("small", { class: "muted why" }, q.why) : null);
    });
    sync();
    send.addEventListener("click", async () => {
      send.disabled = true;
      const r = await core.call("ideas.answer", { slug, answers: picked, ...(isGoal ? { goal: true } : {}) });
      if (!r) { sync(); return; }
      ctx.flash(SENT);
      core.refresh();
    });
    const decide = h("button", { class: "linkish decide", type: "button", onclick: async () => {
      decide.disabled = true;
      const r = await core.call("ideas.answer", { slug, decide: true, ...(isGoal ? { goal: true } : {}) });
      if (!r) { decide.disabled = false; return; }
      ctx.flash(SENT);
      core.refresh();
    } }, "Let the Taskmaster decide");
    const more = h("button", { class: "ork-btn", type: "button", onclick: () => askForm(n, [...picked]) }, "More");
    return h("div", { class: `card need need-${n.kind} quick`, "data-kind": n.kind, "data-idea": n.idea || null, "data-goal": n.goal || null },
      h("span", { class: "need-mark" }, icon(ICONS[n.kind] || "flag")),
      h("span", { class: "need-text" }, h("b", {}, n.title), ...blocks,
        h("div", { class: "row" }, send, more, laterBtn(n)), decide));
  }

  const laterBtn = (n) => h("button", { class: "ork-btn", type: "button", "aria-label": `Later: ${n.title}`, onclick: () => putAway(n) }, "Later");
  function putAway(n) { later.put(n); core.draw(); ctx.flash("Put away for a few hours, on this phone."); }

  /** A swipe to the left puts the row away (Later); a vertical move scrolls as ever. */
  function swipeable(el, n) {
    let x0 = null, y0 = 0, dx = 0;
    el.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse") { x0 = e.clientX; y0 = e.clientY; dx = 0; } });
    el.addEventListener("pointermove", (e) => {
      if (x0 === null) return;
      dx = e.clientX - x0;
      if (Math.abs(e.clientY - y0) > Math.abs(dx)) { x0 = null; el.style.transform = ""; return; }
      if (dx < 0) el.style.transform = `translateX(${dx}px)`;
    });
    const end = () => {
      if (x0 === null) return;
      x0 = null;
      el.style.transform = "";
      if (dx < -SWIPE_PX) putAway(n);
    };
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", end);
    return el;
  }

  // -- a proposal is answered in its row ----------------------------------------------------------------------------
  function proposal(n) {
    const prio = prioritySwitch(`prio-${n.idea}`);
    prio.set(n.priority || "normal");
    const reason = h("input", { class: "ork-field", type: "text", maxlength: "300", "aria-label": `Why not: ${n.title}`, placeholder: "Why not (optional)" });
    const act = async (take) => {
      const r = await core.call("ideas.proposal", { slug: n.idea, take, ...(take ? { priority: prio.get() } : reason.value.trim() ? { reason: reason.value.trim() } : {}) });
      if (r) core.refresh();
    };
    return h("div", { class: "card need need-proposal", "data-kind": "proposal", "data-idea": n.idea },
      h("span", { class: "need-mark" }, icon(ICONS.proposal)),
      h("span", { class: "need-text" }, h("b", {}, n.title), n.text ? h("small", {}, n.text) : null,
        h("div", { class: "field" }, h("span", { class: "field-label" }, "Priority"), prio.el),
        h("div", { class: "row" }, h("button", { class: "ork-btn primary", type: "button", onclick: () => act(true) }, "Take"),
          reason, h("button", { class: "ork-btn", type: "button", onclick: () => act(false) }, "No")), limitsNote(st.snap)));
  }

  function row(n) {
    if (n.kind === "proposal") return proposal(n);
    if (n.kind === "goal" || n.kind === "asks") return swipeable(quick(n), n);
    const go = () => {
      if (n.kind === "op") ops.openCheck(n.op);
      else if (n.kind === "op_failed") ops.openRun(n.op);
      else if (n.kind === "op_rules") ops.openProposal(n);
      else if (n.kind === "goal" || n.kind === "asks") askForm(n);
      else if (n.kind === "todo") todoSheet(n);
      else core.open({ kind: "idea", slug: n.idea });
    };
    return swipeable(h("button", { class: `card need need-${n.kind}`, type: "button", "data-kind": n.kind, onclick: go },
      h("span", { class: "need-mark" }, icon(ICONS[n.kind] || "flag")),
      h("span", { class: "need-text" }, h("b", {}, n.title), n.text ? h("small", {}, n.text) : null),
      h("span", { class: "chev", "aria-hidden": "true" }, "›")), n);
  }

  let showLater = false;
  const waiting = () => st.board?.needs_you || [];

  return {
    sheets: [qSheet.el, tSheet.el],
    /** What the screen shows, to draw it again only when it changed. */
    key: () => JSON.stringify([waiting(), showLater, waiting().map((n) => later.has(n)), Boolean(st.snap?.limits)]),
    /** How many rows wait on the person now (the ones put away Later aside): the top bar's ! says it. */
    count: () => waiting().filter((n) => !later.has(n)).length,
    /** The screen's nodes: every goal's rows, then the ones put away, folded. */
    draw() {
      const all = waiting(), now = all.filter((n) => !later.has(n)), away = all.filter((n) => later.has(n));
      const kids = now.length ? now.map(row) : [h("p", { class: "muted" }, "Nothing waits on you.")];
      if (away.length) {
        kids.push(h("button", { class: "linkish", type: "button", onclick: () => { showLater = !showLater; core.draw(); } },
          showLater ? `Hide the ${away.length} put away` : `Put away for later (${away.length}): show`));
        if (showLater) kids.push(...away.map(row));
      }
      return kids;
    },
  };
}
