// Add agent / Edit agent (docs/specs/34-v1-round-2.md §3, spec 36 §3, §5): a name, its craft (engineering, design, data or
// marketing: the race of its head, decisions §53; Taskmaster and Grunt are orks), a model (By Target or a tier: the gear on its
// head), how many may work at once, an instruction of at most 600 characters (added to every task prompt of that agent) and
// the task types it takes. An agent of your own can be deleted (its task types go back to Grunt, said before); Taskmaster and Grunt can be
// edited, not deleted. Grunt takes what no other agent takes (shown, not editable); the Taskmaster takes none. Add agent opens two ways
// (spec 41 §8): from the library (the agents this project has not: a click adds one, `ideas.role_add`) or your own (this form). For the
// Taskmaster and the Grunt, whose instruction is Orkboard's own, the field says *Added to what it is told* and *What it is told
// already* is above it, folded and read only (`told` of `ideas.roles`).
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { roles, act } from "./store.js";
import { Who, WhoHead, CRAFT_WORDS, RACE_WORDS, TIER_WORDS } from "../orkui.js";
import { toast } from "../link.js";

const CHARS = 600;                                  // roles.INSTRUCTION_CHARS
import { Modal, closeDialog } from "./modals.js";
import { pctOf } from "../spend.js";

const TOO_FEW = 3;                                  // idea_spend.TOO_FEW: a price a merged result is said from 3 merged on

/** What an agent did in the last 30 days (spec 42 §4), in words; read only (`record` of `ideas.roles`). */
export function recordWords(r) {
  const rec = r?.record, n = (k, one, many) => `${k} ${k === 1 ? one : many}`;
  if (r?.slug === "taskmaster") {
    return rec?.plans ? `The last 30 days: ${n(rec.plans, "plan", "plans")}; of their ${n(rec.finished, "task", "tasks")}, ${rec.first_time} merged the first time`
      : "No tasks in the last 30 days";
  }
  if (!rec?.finished) return "No tasks in the last 30 days";
  if (rec.finished < TOO_FEW) return `The last 30 days: ${n(rec.finished, "task", "tasks")}: too few to say more`;
  return `The last 30 days: ${n(rec.finished, "task", "tasks")}, ${rec.first_time} merged the first time${rec.usd_per_merged != null ? ` · ≈${pctOf(rec.usd_per_merged) || `$${rec.usd_per_merged.toFixed(2)}`} a merged result` : ""}`;
}

/** A checker's check in the last 30 days (spec 43 §4.1); "" for an agent that checks nothing, or has not yet. */
export function checkRecordWords(r) {
  const c = r?.record?.check, n = (k, one, many) => `${k} ${k === 1 ? one : many}`;
  if (!c || !c.checks) return "";
  if (c.checks < TOO_FEW) return `Its check, the last 30 days: ${n(c.checks, "goal", "goals")}: too few to say more`;
  return `Its check, the last 30 days: ${n(c.checks, "goal", "goals")}: ${c.clean} clean, caught ${c.caught}${c.usd_per_check != null ? ` · ≈${pctOf(c.usd_per_check) || `$${c.usd_per_check.toFixed(2)}`} a check` : ""}`;
}

const RACE_OF = { engineering: "peon", design: "elf", data: "goblin", marketing: "gnome", product: "lich" };

/** Add agent, the first way: the library's agents this project has not, a click adds one. */
function Library({ own }) {
  const free = (roles.value?.library || []).filter((a) => !a.installed);
  const add = async (a) => {
    const got = await act("ideas.role_add", { id: a.id });
    if (got?.slug) { closeDialog(); toast(`${a.name} is added.`); }
  };
  return html`<${Modal} title="Add an agent" onClose=${closeDialog}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button><button type="button" class="ork-btn primary" data-own onClick=${own}>Your own</button>`}>
    <p class="ok-tone-muted">Pick one that comes with Orkline, or write your own.</p>
    <h3 class="ok-font-label">From the library</h3>
    ${free.length ? html`<ul class="shell-library">${free.map((a) => html`<li key=${a.id}><button type="button" class="shell-library__row" data-agent=${a.id} aria-label=${`Add ${a.name}`} onClick=${() => add(a)}>
        <${WhoHead} head=${{ craft: a.craft, race: RACE_OF[a.craft] || "peon", tier: a.tier }} /><b>${a.name}</b><span aria-hidden="true">+</span>
        <small>${[CRAFT_WORDS[a.craft] || a.craft, TIER_WORDS[a.tier], a.line].filter(Boolean).join(" · ")}</small></button></li>`)}</ul>`
      : html`<p class="ok-tone-muted">Every agent that comes with Orkline is already in this project.</p>`}
  <//>`;
}

export function AgentDialog({ slug = "" }) {
  const [own, setOwn] = useState(false);
  return slug || own ? html`<${AgentForm} slug=${slug} />` : html`<${Library} own=${() => setOwn(true)} />`;
}

function AgentForm({ slug = "" }) {
  const data = roles.value, r = slug ? data?.roles.find((x) => x.slug === slug) : null;
  const [name, setName] = useState(r?.name || "");
  const [model, setModel] = useState(r ? r.model : "");
  const [instruction, setInstruction] = useState(r?.instruction || "");
  const [many, setMany] = useState(r?.max_parallel || 2);
  const [craft, setCraft] = useState(r?.craft || "engineering");
  const [sure, setSure] = useState(false);
  const [busy, setBusy] = useState(false);
  const taskmaster = slug === "taskmaster", grunt = slug === "grunt";
  const crafts = data?.crafts || [];
  const one = crafts.find((c) => c.craft === craft);
  const head = one ? { craft, race: one.race, tier: one.heads?.[model] || (r?.head?.tier) || "warrior" } : r?.head;
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
      ...(taskmaster || grunt ? {} : { kinds: takes, craft }) });
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
      <label class="shell-field"><span class="ok-font-label">Craft</span>
        <select class="ork-field" aria-label="Craft" value=${craft} disabled=${taskmaster || grunt} onChange=${(e) => setCraft(e.target.value)}>
          ${(crafts.length ? crafts : [{ craft: "engineering", label: "Engineering", race: "peon" }]).map((c) => html`<option key=${c.craft} value=${c.craft}>
            ${CRAFT_WORDS[c.craft] || c.label}: ${/^[aeiou]/.test(RACE_WORDS[c.race]) ? "an" : "a"} ${RACE_WORDS[c.race]}</option>`)}</select>
        <small class="ok-tone-muted">${taskmaster || grunt ? "Taskmaster and Grunt are orks: engineering" : "Its head on Agents: the race says the craft, the gear the tier"}</small></label>
      <div class="shell-agent__who" aria-live="polite"><${Who} head=${head} /></div>
      ${r && html`<p class="shell-record ok-font-status ok-tone-muted" aria-label="The last 30 days">${recordWords(r)}</p>`}
      ${r && checkRecordWords(r) && html`<p class="shell-record ok-font-status ok-tone-muted" aria-label="Its check">${checkRecordWords(r)}</p>`}
      <label class="shell-field"><span class="ok-font-label">Model</span>
        <select class="ork-field" aria-label="Model" value=${model} onChange=${(e) => setModel(e.target.value)}>
          ${models.map((m) => html`<option key=${m.id} value=${m.id}>${m.label}</option>`)}</select>
        <small class="ok-tone-muted">By Target: the task's own tier, moved by the Target</small></label>
      <label class="shell-field"><span class="ok-font-label">At most at once</span>
        <select class="ork-field" aria-label="At most at once" value=${String(many)} onChange=${(e) => setMany(e.target.value)}>
          ${[1, 2, 3, 4, 5, 6, 7, 8].map((n) => html`<option key=${n} value=${String(n)}>${n}</option>`)}</select></label>
      ${r?.told && html`<details class="shell-told"><summary>What it is told already</summary><p class="shell-told__text">${r.told}</p></details>`}
      <label class="shell-field"><span class="ok-font-label">${r?.told ? "Added to what it is told" : "Instruction"} <small class=${over ? "ok-tone-error" : "ok-tone-muted"} data-testid="instruction-count">${instruction.length} / ${CHARS}</small></span>
        <textarea class="ork-field" rows="5" value=${instruction} aria-label=${r?.told ? "Added to what it is told" : "Instruction"} placeholder="Added to every task this agent does"
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
