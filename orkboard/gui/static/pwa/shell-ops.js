// Operations on the phone (docs/specs/38-operations.md §10, "the phone"): the person's everyday work by templates, in the Board tab's
// select. The same as the desktop, as sheets: New… (a menu of the usable templates, then a template's form), the check (what was
// found, the doubts, the fields and draft parts to correct, the action's button), Operations' gear, a template's rules. The list
// is read again when the snapshot's `ops_rev` moves; it works with no project open (the operations are the person's).
import { h, sheet, icon } from "./util.js";
import { field, foot } from "./shell-forms.js";
import { TARGETS, hhmm } from "./shell-words.js";

export const OPS_VIEW = "ops";
const FORM_KEY = "orkcraft.ops.form.";            // a form closed with typed text keeps it for the next opening, on this phone only
const SPIN = () => h("span", { class: "spin", "aria-hidden": "true" }, "↻");
const first = (run, t) => {
  const part = t?.draft?.[0]?.name;
  return String((part ? run.draft?.[part] : Object.values(run.draft || {})[0]) || "").split("\n").find((l) => l.trim()) || "";
};

const kept = {
  get(name) { try { return JSON.parse(localStorage.getItem(FORM_KEY + name)) || {}; } catch { return {}; } },
  set(name, values) { try { localStorage.setItem(FORM_KEY + name, JSON.stringify(values)); } catch { /* this run only */ } },
  clear(name) { try { localStorage.removeItem(FORM_KEY + name); } catch { /* nothing kept */ } },
};

/** A manifest's field or draft part as a control: a box (long), a select (choice) or a line; `value` is what it starts with. */
function control(def, value, label) {
  const attrs = { class: "ork-field", "aria-label": label || def.label, placeholder: def.hint || "" };
  let el;
  if (def.type === "choice") {
    el = h("select", attrs, ...(def.options || []).map((o) => h("option", { value: o }, o)));
  } else if (def.type === "long") {
    el = h("textarea", { ...attrs, rows: "4", maxlength: "4000" });
  } else {
    el = h("input", { ...attrs, type: "text", maxlength: "4000" });
  }
  el.value = value ?? "";
  return el;
}

/** `core`: the board's frame (board.js); `ctx`: {send, flash}. Returns {sheets, load, sync, section, openCheck, openRun, openRules}. */
export function makeOps(core, ctx) {
  const st = core.st;
  let data = null;                                  // the last ops.list
  let seen;                                         // the snapshot's ops_rev read last
  let seq = 0;
  const tpl = (name) => (data?.templates || []).find((t) => t.name === name);
  const run = (id) => (data?.runs || []).find((r) => r.id === id);
  const tell = (text) => ctx.flash(text);

  // -- reading ---------------------------------------------------------------------------------------------------------
  async function load() {
    const mine = ++seq;
    const r = await ctx.send("ops.list");
    if (mine !== seq || !r.ok || r.result?.error) return;
    data = r.result;
    st.ops = data;
    core.draw();
  }
  /** From the snapshot: read again when `ops_rev` moved (the first snapshot too). */
  function sync(rev) {
    if (rev === undefined || rev === seen) return;
    seen = rev;
    load();
  }
  /** A command that changes an operation: true when it went through. */
  async function act(name, args, said) {
    const r = await core.call(name, args);
    if (!r) return null;
    if (said) tell(said);
    load();
    return r;
  }

  // -- New…: the usable templates, then what cannot be used and why ------------------------------------------------------
  const menuBody = h("div", { class: "ops-menu" });
  const menuSheet = sheet("New…", menuBody);
  function openMenu() {
    const list = data?.templates || [];
    const usable = list.filter((t) => !t.unusable);
    menuBody.replaceChildren(
      usable.length ? null : h("p", { class: "muted" }, list.length ? "No template can be used yet." : "No template found."),
      ...usable.map((t) => h("button", { class: "card need", type: "button", "data-template": t.name,
        onclick: () => { menuSheet.close(); openForm(t); } }, h("span", { class: "need-text" }, h("b", {}, t.title)), h("span", { class: "chev", "aria-hidden": "true" }, "›"))),
      ...list.filter((t) => t.unusable).map((t) => h("p", { class: "muted ops-cant" }, h("b", {}, t.title), ` · ${t.unusable}`)));
    menuSheet.open();
  }

  // -- a template's form: the fields as the manifest says, `remember`ed ones prefilled, one button, Add ----------------------------
  const formBody = h("form", { class: "sheet-form ops-form" });
  const formSheet = sheet("New operation", formBody);
  function openForm(t) {
    const saved = kept.get(t.name);
    const inputs = Object.fromEntries(t.fields.map((f) => [f.name, control(f, saved[f.name] ?? f.default ?? "", f.label)]));
    const say = h("p", { class: "warn", role: "alert", hidden: true });
    const add = h("button", { class: "ork-btn primary big", type: "submit" }, "Add");
    const values = () => Object.fromEntries(Object.entries(inputs).map(([k, el]) => [k, el.value.trim()]));
    const stash = () => {
      const typed = Object.fromEntries(Object.entries(values()).filter(([k, v]) => v && v !== String(t.fields.find((f) => f.name === k)?.default ?? "")));
      if (Object.keys(typed).length) kept.set(t.name, typed); else kept.clear(t.name);
    };
    for (const el of Object.values(inputs)) el.addEventListener("input", stash);
    formBody.replaceChildren(h("p", { class: "muted" }, t.title),
      ...t.fields.map((f) => field(f.label + (f.required ? " *" : ""), inputs[f.name])),
      say, foot(h("button", { class: "ork-btn big", type: "button", onclick: () => formSheet.close() }, "Cancel"), add));
    formBody.onsubmit = async (e) => {
      e.preventDefault();
      add.disabled = true;
      const r = await ctx.send("ops.add", { template: t.name, fields: values() });
      add.disabled = false;
      if (!r.ok || r.result?.error) { say.textContent = r.error || r.result?.error || "That did not work"; say.hidden = false; return; }
      kept.clear(t.name);
      formSheet.close();
      tell(`Added: ${t.title}.`);
      load();
    };
    formSheet.title(t.title);
    formSheet.open();
    (Object.values(inputs)[0])?.focus();
  }

  // -- the check: found, doubts, the fields and parts to correct, the action's button ------------------------------------------
  const checkBody = h("form", { class: "sheet-form ops-check" });
  const checkSheet = sheet("Check", checkBody);
  async function openCheck(id) {
    if (!run(id)) await load();
    const r = run(id);
    const t = r && tpl(r.template);
    if (!r || !t || r.state !== "check") { tell("That operation is not waiting at your check any more."); core.refresh(); return; }
    const mine = (name) => String(r.fields?.[name] ?? "");
    const fieldInputs = Object.fromEntries(t.fields.map((f) => [f.name, control(f, mine(f.name), f.label)]));
    const partInputs = Object.fromEntries(t.draft.map((p) => [p.name, control(p, r.draft?.[p.name], p.label)]));
    const changedFields = () => Object.fromEntries(t.fields.filter((f) => fieldInputs[f.name].value !== mine(f.name)).map((f) => [f.name, fieldInputs[f.name].value.trim()]));
    const changedDraft = () => Object.fromEntries(t.draft.filter((p) => partInputs[p.name].value !== String(r.draft?.[p.name] ?? "")).map((p) => [p.name, partInputs[p.name].value]));
    const say = h("p", { class: "warn", role: "alert", hidden: true });
    const go = h("button", { class: "ork-btn primary big", type: "submit" }, t.act_label);
    const again = () => t.fields.some((f) => !f.at && f.name in changedFields());
    const sync_ = () => { go.textContent = again() ? "Prepare again" : t.act_label; };
    for (const el of [...Object.values(fieldInputs), ...Object.values(partInputs)]) el.addEventListener("input", sync_);
    const asked = t.fields.filter((f) => f.at);
    const other = t.fields.filter((f) => !f.at);
    checkBody.replaceChildren(
      h("p", { class: "muted" }, r.alone ? `${t.title} · by itself` : t.title),
      r.found.length ? h("ul", { class: "ops-found" }, ...r.found.map((f) => h("li", {}, h("b", {}, `${f.label}: `), f.value))) : null,
      ...r.doubts.map((d) => h("p", { class: "ops-doubt" }, h("span", { "aria-hidden": "true" }, "⚠️ "), d)),
      ...t.draft.map((p) => field(p.label, partInputs[p.name])),
      ...asked.map((f) => field(f.label, fieldInputs[f.name])),
      other.length ? h("details", { class: "ops-other" }, h("summary", {}, "Change what was asked"),
        h("p", { class: "muted hint" }, "A change here is read again: the button becomes Prepare again."),
        ...other.map((f) => field(f.label, fieldInputs[f.name]))) : null,
      say,
      foot(h("button", { class: "ork-btn big", type: "button", onclick: async () => { if (await act("ops.drop", { id }, "Dropped.")) checkSheet.close(); } }, "Drop"), go));
    checkBody.onsubmit = async (e) => {
      e.preventDefault();
      go.disabled = true;
      const redo = again();
      const res = await ctx.send(redo ? "ops.prepare" : "ops.act", { id, fields: changedFields(), draft: changedDraft() });
      go.disabled = false;
      if (!res.ok || res.result?.error) { say.textContent = res.error || res.result?.error || "That did not work"; say.hidden = false; sync_(); return; }
      checkSheet.close();
      tell(redo ? "Preparing again…" : `${t.act_label}: doing it.`);
      load();
    };
    checkSheet.title(t.title);
    checkSheet.open();
  }

  // -- a failed run: its line why, Try again (only when nothing was done), Add again, Drop --------------------------------------
  function failedActions(r, after) {
    const done = () => { after?.(); };
    return h("div", { class: "row" },
      r.acted === false ? h("button", { class: "ork-btn", type: "button", onclick: async () => { if (await act("ops.retry", { id: r.id })) done(); } }, "Try again") : null,
      h("button", { class: "ork-btn", type: "button", onclick: async () => { if (await act("ops.again", { id: r.id }, "Added again.")) done(); } }, "Add again"),
      h("button", { class: "ork-btn", type: "button", onclick: async () => { if (await act("ops.drop", { id: r.id }, "Dropped.")) done(); } }, "Drop"));
  }
  const runBody = h("div", { class: "todo-sheet ops-run" });
  const runSheet = sheet("Failed", runBody);
  async function openRun(id) {
    if (!run(id)) await load();
    const r = run(id);
    if (!r) { tell("That operation is gone."); core.refresh(); return; }
    runBody.replaceChildren(h("h3", {}, r.title), h("p", { class: "warn" }, r.why || "It failed"),
      r.acted === false ? null : h("p", { class: "muted" }, "It may have done part of its work: look at the tool before you add it again."),
      failedActions(r, () => runSheet.close()));
    runSheet.title("Failed");
    runSheet.open();
  }

  // -- Not right: what was wrong, if the person says --------------------------------------------------------------------------
  const wrongBox = h("textarea", { class: "ork-field", rows: "3", maxlength: "1000", "aria-label": "What was not right", placeholder: "What was not right (optional)" });
  let wrongId = "";
  const wrongSend = h("button", { class: "ork-btn primary big", type: "button", onclick: async () => {
    const why = wrongBox.value.trim();
    wrongSend.disabled = true;
    const r = await act("ops.not_right", { id: wrongId, ...(why ? { why } : {}) }, "Noted: it will check with you again.");
    wrongSend.disabled = false;
    if (r) wrongSheet.close();
  } }, "Send: not right");
  const wrongSheet = sheet("Not right", h("p", { class: "muted" }, "It did this by itself. Say what was wrong and it learns; it checks with you again."), field("What was not right", wrongBox),
    foot(h("button", { class: "ork-btn big", type: "button", onclick: () => wrongSheet.close() }, "Cancel"), wrongSend));
  function openWrong(id) { wrongId = id; wrongBox.value = ""; wrongSheet.open(); wrongBox.focus(); }

  // -- a template's rules, and a proposal waiting ------------------------------------------------------------------------------
  const rulesBox = h("textarea", { class: "ork-field", rows: "10", maxlength: "4000", "aria-label": "Rules", spellcheck: "false" });
  let rulesFor = "";
  const rulesSave = h("button", { class: "ork-btn primary big", type: "button", onclick: async () => {
    rulesSave.disabled = true;
    const r = await core.call("ops.rules_save", { template: rulesFor, text: rulesBox.value });
    rulesSave.disabled = false;
    if (r) { rulesSheet.close(); tell("Rules saved."); load(); }
  } }, "Save rules");
  const rulesSheet = sheet("Rules", h("p", { class: "muted" }, "What this template learned from your corrections. It reads these before it prepares. Change or delete a line."), field("Rules", rulesBox),
    foot(h("button", { class: "ork-btn big", type: "button", onclick: () => rulesSheet.close() }, "Cancel"), rulesSave));
  async function openRules(name) {
    const r = await core.call("ops.rules", { template: name });
    if (!r) return;
    rulesFor = name;
    rulesBox.value = r.text || "";
    rulesSheet.title(`Rules: ${tpl(name)?.title || name}`);
    rulesSheet.open();
  }

  /** The lines a template learned, answered in place: Take adds them to its rules; No may say why. */
  function proposalBlock(template, lines, done) {
    const why = h("input", { class: "ork-field", type: "text", maxlength: "300", "aria-label": `Why not: ${template}`, placeholder: "Why not (optional)" });
    const answer = async (take) => {
      const r = await core.call("ops.rules_answer", { template, take, ...(!take && why.value.trim() ? { reason: why.value.trim() } : {}) });
      if (r) { load(); core.refresh(); done?.(); }
    };
    return h("div", { class: "ops-proposal" },
      h("p", { class: "muted" }, "It would add these to its rules:"),
      h("ul", { class: "ops-lines" }, ...lines.map((l) => h("li", {}, l))),
      h("div", { class: "row" }, h("button", { class: "ork-btn primary", type: "button", onclick: () => answer(true) }, "Take"),
        why, h("button", { class: "ork-btn", type: "button", onclick: () => answer(false) }, "No")));
  }
  const propBody = h("div", { class: "todo-sheet" });
  const propSheet = sheet("Rules", propBody);
  function openProposal(n) {
    propBody.replaceChildren(h("h3", {}, n.title), proposalBlock(n.template, n.lines || [n.text], () => propSheet.close()));
    propSheet.title(`Rules: ${n.title}`);
    propSheet.open();
  }

  // -- the gear: Target, clean checks, a day's limit, a server for each key ----------------------------------------------------
  const gearBody = h("div", { class: "ops-gear" });
  const gearSheet = sheet("Operations settings", gearBody, foot(h("button", { class: "ork-btn primary big", type: "button", onclick: () => gearSheet.close() }, "Done")));
  async function setting(args) {
    const r = await core.call("ops.set", args);
    if (r) load();
    return r;
  }
  async function openGear() {
    const mine = () => data?.settings || {};
    const num = (key, label, lo, hi, hint) => {
      const el = h("input", { class: "ork-field", type: "number", min: String(lo), max: String(hi), inputmode: "numeric", "aria-label": label });
      el.value = String(mine()[key] ?? "");
      el.addEventListener("change", async () => { if (!(await setting({ [key]: Number(el.value) }))) el.value = String(mine()[key] ?? ""); });
      return field(label, el, hint);
    };
    const radios = TARGETS.map(([id, word, line]) => {
      const input = h("input", { type: "radio", name: "ops-target", value: id, "aria-label": word });
      input.checked = (mine().target || "balance") === id;
      input.addEventListener("change", () => setting({ target: id }));
      return h("label", { class: "target-pick" }, input, h("span", { class: "need-text" }, h("b", {}, word), h("small", {}, line)));
    });
    const needed = Object.entries(data?.servers_needed || {});
    const serverBox = h("div", { class: "ops-servers" }, needed.length ? h("p", { class: "muted" }, "Reading the servers…") : null);
    gearBody.replaceChildren(h("h3", {}, "Target"), h("p", { class: "muted" }, "How heavy Operations’ calls are."), ...radios,
      num("trust_after", "Goes by itself after N clean checks", 1, 5, "1 to 5 checks in a row you did not correct."),
      num("daily_alone", "By itself at most N a day", 1, 100, "1 to 100. Past it, every operation waits at your check."),
      needed.length ? h("h3", {}, "Servers") : null, serverBox);
    gearSheet.open();
    if (!needed.length) return;
    const got = await ctx.send("ops.servers");
    const names = got.ok && !got.result?.error ? got.result.servers || [] : [];
    serverBox.replaceChildren(...needed.map(([key, what]) => {
      const pick = h("select", { class: "ork-field", "aria-label": `Server for ${what}` },
        h("option", { value: "" }, "not connected"), ...names.map((n) => h("option", { value: n }, n)));
      pick.value = names.includes(mine().servers?.[key]) ? mine().servers[key] : "";
      pick.addEventListener("change", () => setting({ servers: { [key]: pick.value } }));
      return field(`Server for ${what}`, pick);
    }));
  }

  // -- the list: at your check · running · failed · done · templates ------------------------------------------------------------
  function checkRow(r) {
    const t = tpl(r.template);
    return h("button", { class: "card need need-op", type: "button", "data-op": r.id, onclick: () => openCheck(r.id) },
      h("span", { class: "need-mark" }, icon("checkbox")),
      h("span", { class: "need-text" }, h("b", {}, r.title), first(r, t) ? h("small", {}, first(r, t)) : null,
        h("small", {}, [r.why ? `at your check · ${r.why}` : "at your check", hhmm(r.at)].filter(Boolean).join(" · "))),
      h("span", { class: "chev", "aria-hidden": "true" }, "›"));
  }
  function runningRow(r) {
    const held = r.held_until ? r.why || `waits for limits · after ${hhmm(r.held_until)}` : "";   // why: the day's spend cap
    return h("div", { class: "card ops-run-row", "data-op": r.id },
      h("span", { class: "need-text" }, h("b", {}, r.title),
        h("small", { class: "state-word work" }, held ? null : SPIN(), held ? "" : " ", held || (r.state === "acting" ? "doing it" : "preparing"))),
      h("button", { class: "ork-btn", type: "button", "aria-label": `Stop: ${r.title}`, onclick: () => act("ops.stop", { id: r.id }, "Stopped.") }, "Stop"));
  }
  const failedRow = (r) => h("div", { class: "card ops-failed", "data-op": r.id },
    h("span", { class: "need-text" }, h("b", {}, r.title), h("small", { class: "warn" }, r.why || "It failed")), failedActions(r));
  function doneRow(r) {
    return h("div", { class: "card ops-done", "data-op": r.id },
      h("span", { class: "need-text" }, h("b", {}, r.title), first(r, tpl(r.template)) ? h("small", {}, first(r, tpl(r.template))) : null,
        r.alone ? h("small", { class: "muted" }, "by itself") : null),
      r.link ? h("a", { class: "ork-btn", href: r.link, target: "_blank", rel: "noopener noreferrer", "aria-label": `Open the result of ${r.title}` }, "Open") : null,
      r.alone ? h("button", { class: "ork-btn", type: "button", "aria-label": `Not right: ${r.title}`, onclick: () => openWrong(r.id) }, "Not right") : null);
  }
  function templateRow(t) {
    return h("div", { class: "card ops-template", "data-template": t.name },
      h("span", { class: "need-text" }, h("b", {}, t.title), h("small", { class: "muted" }, t.state_words || t.state),
        t.state === "alone" ? h("small", { class: "muted" }, `goes by itself: ${String(t.act_label).toLowerCase()} without asking you`) : null,
        t.unusable ? h("small", { class: "warn" }, t.unusable) : null),
      t.proposal ? proposalBlock(t.name, t.proposal.lines || []) : null,
      h("div", { class: "row" },
        t.state === "alone" ? h("button", { class: "ork-btn", type: "button", "aria-label": `Check again: ${t.title}`, onclick: () => act("ops.trust_reset", { template: t.name }, "It checks with you again.") }, "Check again") : null,
        h("button", { class: "ork-btn", type: "button", "aria-label": `Rules: ${t.title}`, onclick: () => openRules(t.name) }, "Rules")));
  }
  const unfolded = new Set();                      // a fold the person opened stays open when the list is drawn again
  function fold(title, n, rows, open) {
    const el = h("details", { class: "ops-fold", open: open || unfolded.has(title) || null }, h("summary", {}, `${title} (${n})`), ...rows);
    el.addEventListener("toggle", () => { if (el.open) unfolded.add(title); else unfolded.delete(title); });
    return el;
  }

  /** The nodes of Operations' list (in place of Needs you and the ideas). */
  function section() {
    if (!data) return [h("p", { class: "muted" }, "Loading…")];
    const runs = data.runs || [];
    const by = (f) => runs.filter(f).slice().reverse();
    const check = by((r) => r.state === "check");
    const going = by((r) => ["preparing", "acting", "held"].includes(r.state));
    const failed = by((r) => r.state === "failed");
    const done = by((r) => r.state === "done");
    const kids = [];
    if (check.length) kids.push(h("h3", {}, "At your check"), ...check.map(checkRow));
    if (going.length) kids.push(h("h3", {}, "Running"), ...going.map(runningRow));
    if (failed.length) kids.push(h("h3", {}, "Failed"), ...failed.map(failedRow));
    if (!check.length && !going.length && !failed.length) kids.push(h("p", { class: "muted" }, "Nothing waits on you here. New… starts an operation."));
    if (done.length) kids.push(fold("Done", done.length, done.map(doneRow), false));
    kids.push(fold("Templates", data.templates.length, data.templates.map(templateRow), data.templates.some((t) => t.proposal)));
    return kids;
  }

  return {
    sheets: [menuSheet.el, formSheet.el, checkSheet.el, runSheet.el, wrongSheet.el, rulesSheet.el, propSheet.el, gearSheet.el],
    load, sync, section, openMenu, openGear, openCheck, openRun, openProposal,
  };
}
