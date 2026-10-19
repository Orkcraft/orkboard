// Add agent / Edit agent on the phone, a sheet (docs/specs/34-v1-round-2.md §3; spec 36 §3, §5): a name, its craft (the race of its head,
// decisions §53; Taskmaster and Grunt are orks), a model (By Target, or a tier: the gear on its head),
// how many may work at once, an instruction of at most 600 characters added to every task prompt of that agent, and the task types it
// takes. An agent of your own can be deleted (its task types go back to Grunt, said first); Taskmaster and Grunt can be edited, not
// deleted; Grunt's types are shown, not editable, and the Taskmaster takes none. `assign`: a task type a new agent starts with.
import { h, sheet } from "./util.js";
import { field, foot } from "./shell-forms.js";
import { who, CRAFT_WORDS, RACE_WORDS } from "./shell-who.js";

const LIMIT = 600;

export function makeAgentSheet(core) {
  const name = h("input", { class: "ork-field", type: "text", "aria-label": "Name", placeholder: "Docs scribe", maxlength: "40", required: true });
  const craft = h("select", { class: "ork-field", "aria-label": "Craft" });
  const craftHint = h("small", { class: "muted" });
  const whoNow = h("div", { class: "craft-now", "aria-live": "polite" });
  const model = h("select", { class: "ork-field", "aria-label": "Model" });
  const many = h("select", { class: "ork-field", "aria-label": "At most at once" }, ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => h("option", { value: String(n) }, String(n))));
  const modelHint = h("small", { class: "muted" }, "By Target: the task's own tier, moved by the Target");
  const instruction = h("textarea", { class: "ork-field", rows: "5", "aria-label": "Instruction", placeholder: "Added to every task this agent does" });
  const counter = h("small", { class: "muted counter", "aria-live": "polite" });
  const longNote = h("p", { class: "warn", hidden: true }, "Only the first 600 characters go to the ork: shorten it");
  const takesBox = h("fieldset", { class: "field takes" });
  const note = h("p", { class: "muted", hidden: true });
  const save = h("button", { class: "ork-btn primary big", type: "submit", disabled: true }, "Save agent");
  const cancel = h("button", { class: "ork-btn big", type: "button" }, "Cancel");
  const del = h("button", { class: "linkish", type: "button" }, "Delete…");
  const sureText = h("p", { class: "warn" });
  const sureBtn = h("button", { class: "ork-btn danger big", type: "button" }, "Delete agent");
  const keep = h("button", { class: "ork-btn big", type: "button" }, "Keep it");
  const sure = h("div", { class: "sure", hidden: true }, sureText, sureBtn, keep);
  const form = h("form", { class: "sheet-form" }, field("Name", name), field("Craft", craft), craftHint, whoNow, field("Model", model), modelHint, field("At most at once", many), field("Instruction", instruction), counter, longNote, takesBox,
    note, h("div", {}, del), sure, foot(cancel, save));
  const sh = sheet("Add agent", form);
  let slug = "", assign = "";
  const ok = () => !!name.value.trim() && instruction.value.trim().length <= LIMIT;
  const count = () => {
    const n = instruction.value.trim().length;
    counter.textContent = `${n} / ${LIMIT}`;
    counter.classList.toggle("warn", n > LIMIT);
    save.disabled = !ok();
  };
  /** The head the agent will wear: its craft's race at the tier its model gives under the Target (ideas.roles `crafts`). */
  const drawWho = () => {
    const c = (core.st.roles?.crafts || []).find((x) => x.craft === craft.value);
    whoNow.replaceChildren(c ? who({ craft: c.craft, race: c.race, tier: c.heads?.[model.value] || "warrior" }) : "");
  };
  craft.addEventListener("change", drawWho);
  model.addEventListener("change", drawWho);
  name.addEventListener("input", count);
  instruction.addEventListener("input", count);
  cancel.addEventListener("click", () => sh.close());
  del.addEventListener("click", () => {
    const mine = (core.st.roles?.kinds || []).filter((k) => k.role === slug).map((k) => k.label.toLowerCase());
    sureText.textContent = `${mine.length ? `Its task types (${mine.join(", ")}) go back to Grunt.` : "No task type uses it."} Delete ${name.value}?`;
    sure.hidden = false;
    del.hidden = true;
  });
  keep.addEventListener("click", () => { sure.hidden = true; del.hidden = false; });
  sureBtn.addEventListener("click", async () => {
    const got = await core.call("ideas.role_drop", { slug });
    if (got?.ok) { sh.close(); core.refresh(); }
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!name.value.trim()) return;
    save.disabled = true;
    const kinds = slug === "grunt" || slug === "taskmaster" ? {} : { kinds: [...takesBox.querySelectorAll("input:checked")].map((i) => i.value), craft: craft.value };
    const got = await core.call("ideas.role_save", { ...(slug ? { slug } : {}), name: name.value.trim(), model: model.value, max_parallel: Number(many.value),
      instruction: instruction.value, ...kinds });
    save.disabled = !ok();
    if (got?.slug) { sh.close(); core.refresh(); }
  });
  /** The five task types as boxes, each with whose it is now; Grunt's are shown, not editable; the Taskmaster takes none. */
  function takes(data, r) {
    const none = r?.slug === "taskmaster";
    takesBox.hidden = none;
    if (none) return;
    const grunt = r?.slug === "grunt";
    const names = Object.fromEntries((data?.roles || []).map((x) => [x.slug, x.name]));
    takesBox.replaceChildren(h("legend", { class: "field-label" }, "Takes"), ...(data?.kinds || []).map((k) => {
      const box = h("input", { type: "checkbox", value: k.kind, "aria-label": k.label, disabled: grunt || undefined });
      box.checked = grunt ? k.role === "grunt" : r ? k.role === r.slug : k.kind === assign;
      return h("label", { class: "take-row", "data-kind": k.kind }, box, h("span", {}, k.label), h("small", { class: "muted" }, `now ${names[k.role] || k.role}`));
    }), grunt ? h("small", { class: "muted" }, "Grunt takes what no other agent takes") : null);
  }

  return {
    el: sh.el,
    open(which = "", kind = "") {
      slug = which;
      assign = kind;
      const data = core.st.roles, r = which ? (data?.roles || []).find((x) => x.slug === which) : null;
      sh.title(r ? "Edit agent" : "Add agent");
      name.value = r?.name || "";
      const hand = r?.hand_model ? [{ id: r.model, label: `${r.model} (set by hand)` }] : [];
      model.replaceChildren(...[...(data?.models || []), ...hand].filter((m) => m.id || r?.slug !== "taskmaster").map((m) => h("option", { value: m.id }, m.label)));
      model.value = r ? r.model : "";
      const crafts = data?.crafts?.length ? data.crafts : [{ craft: "engineering", label: "Engineering", race: "peon" }];
      craft.replaceChildren(...crafts.map((c) => h("option", { value: c.craft }, `${CRAFT_WORDS[c.craft] || c.label}: ${/^[aeiou]/.test(RACE_WORDS[c.race]) ? "an" : "a"} ${RACE_WORDS[c.race]}`)));
      craft.value = r?.craft || "engineering";
      craft.disabled = r?.slug === "taskmaster" || r?.slug === "grunt";
      craftHint.textContent = craft.disabled ? "Taskmaster and Grunt are orks: engineering" : "Its head on Agents: the race says the craft, the gear the tier";
      drawWho();
      modelHint.hidden = r?.slug === "taskmaster";
      many.value = String(r?.max_parallel || 2);
      instruction.value = r?.instruction_long || r?.instruction || "";
      longNote.hidden = !r?.instruction_long;
      takes(data, r);
      note.hidden = !assign;
      note.textContent = assign ? `It starts with every task of the type “${assign}”.` : "";
      del.hidden = !r || r.builtin;
      sure.hidden = true;
      count();
      sh.open();
      name.focus();
    },
  };
}
