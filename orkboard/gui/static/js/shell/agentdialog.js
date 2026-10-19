// Add agent / Edit agent (docs/specs/34-v1-round-2.md §3, spec 36 §3, §5): a name, a model (By Target or a tier), how many
// may work at once, an instruction of at most 600 characters (added to every task prompt of that agent) and the task types
// it takes. An agent of your own can be deleted (its task types go back to Grunt, said before); Taskmaster and Grunt can be
// edited, not deleted. Grunt takes what no other agent takes (shown, not editable); the Taskmaster takes none.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { roles, act } from "./store.js";

const CHARS = 600;                                  // roles.INSTRUCTION_CHARS
import { Modal, closeDialog } from "./modals.js";

export function AgentDialog({ slug = "" }) {
  const data = roles.value, r = slug ? data?.roles.find((x) => x.slug === slug) : null;
  const [name, setName] = useState(r?.name || "");
  const [model, setModel] = useState(r ? r.model : "");
  const [instruction, setInstruction] = useState(r?.instruction || "");
  const [many, setMany] = useState(r?.max_parallel || 2);
  const [sure, setSure] = useState(false);
  const [busy, setBusy] = useState(false);
  const taskmaster = slug === "taskmaster", grunt = slug === "grunt";
  const models = (data?.models || []).filter((m) => m.id || !taskmaster);          // By Target for everyone but the Taskmaster
  if (r?.hand_model && !models.some((m) => m.id === r.model)) models.push({ id: r.model, label: `${r.model} (set by hand)` });
  const mine = data ? data.kinds.filter((k) => k.role === slug).map((k) => k.label.toLowerCase()) : [];
  const [takes, setTakes] = useState(() => mine.length ? (data?.kinds || []).filter((k) => k.role === slug).map((k) => k.kind) : []);
  const roleName = (id) => data?.roles.find((x) => x.slug === id)?.name || id;
  const tick = (kind, on) => setTakes(on ? [...takes, kind] : takes.filter((k) => k !== kind));
  const over = instruction.length > CHARS;
  const save = async (e) => {
    e?.preventDefault();
    if (!name.trim() || busy || over) return;
    setBusy(true);
    const got = await act("ideas.role_save", { ...(slug ? { slug } : {}), name: name.trim(), model, max_parallel: Number(many), instruction,
      ...(taskmaster || grunt ? {} : { kinds: takes }) });
    setBusy(false);
    if (got?.slug) closeDialog();
  };
  const drop = async () => { setBusy(true); const got = await act("ideas.role_drop", { slug }); setBusy(false); if (got?.ok) closeDialog(); };
  return html`<${Modal} title=${slug ? `Edit agent` : "Add agent"} onClose=${closeDialog}
    foot=${sure ? html`<span class="shell-modal__sure">${mine.length ? `Its task types (${mine.join(", ")}) go back to Grunt.` : "No task type uses it."} Delete ${r?.name}?</span>
        <button type="button" class="ork-btn" onClick=${() => setSure(false)}>Keep it</button>
        <button type="button" class="ork-btn danger" disabled=${busy} onClick=${drop}>Delete agent</button>`
      : html`${slug && !r?.builtin && html`<button type="button" class="ork-btn danger shell-modal__left" onClick=${() => setSure(true)}>Delete…</button>`}
        <button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
        <button type="submit" form="agent-form" class="ork-btn primary" disabled=${!name.trim() || busy || over}>Save agent</button>`}>
    <form id="agent-form" class="shell-form" onSubmit=${save}>
      <label class="shell-field"><span class="ok-font-label">Name</span>
        <input class="ork-field" autofocus required value=${name} aria-label="Name" placeholder="Docs scribe" onInput=${(e) => setName(e.target.value)} /></label>
      <label class="shell-field"><span class="ok-font-label">Model</span>
        <select class="ork-field" aria-label="Model" value=${model} onChange=${(e) => setModel(e.target.value)}>
          ${models.map((m) => html`<option key=${m.id} value=${m.id}>${m.label}</option>`)}</select>
        <small class="ok-tone-muted">By Target: the task's own tier, moved by the Target</small></label>
      <label class="shell-field"><span class="ok-font-label">At most at once</span>
        <select class="ork-field" aria-label="At most at once" value=${String(many)} onChange=${(e) => setMany(e.target.value)}>
          ${[1, 2, 3, 4, 5, 6, 7, 8].map((n) => html`<option key=${n} value=${String(n)}>${n}</option>`)}</select></label>
      <label class="shell-field"><span class="ok-font-label">Instruction <small class=${over ? "ok-tone-error" : "ok-tone-muted"} data-testid="instruction-count">${instruction.length} / ${CHARS}</small></span>
        <textarea class="ork-field" rows="5" value=${instruction} aria-label="Instruction" placeholder="Added to every task this agent does"
          onInput=${(e) => setInstruction(e.target.value)}></textarea>
        ${over && html`<small class="ok-tone-error" role="alert">Only the first ${CHARS} characters go to the ork: shorten it</small>`}</label>
      ${!taskmaster && html`<fieldset class="shell-field shell-takes"><legend class="ok-font-label">Takes</legend>
        ${(data?.kinds || []).map((k) => html`<label key=${k.kind} class="shell-takes__row"><input type="checkbox" aria-label=${k.label} disabled=${grunt}
          checked=${grunt ? k.role === "grunt" : takes.includes(k.kind)} onChange=${(e) => tick(k.kind, e.target.checked)} />
          <span>${k.label}</span><small class="ok-tone-muted">now ${roleName(k.role)}</small></label>`)}
        ${grunt && html`<small class="ok-tone-muted">Grunt takes what no other agent takes</small>`}</fieldset>`}
    </form>
  <//>`;
}
