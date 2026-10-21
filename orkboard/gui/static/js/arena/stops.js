// What waits for you (docs/specs/49-one-window.md §6): the bottom row. The stops of the goal shown — a plan ready, a question, a
// proposal, a to-do, a failure — each a framed item standing in a fan along the bottom edge, only its top showing; hovering or
// focusing one raises it whole, with its quick answers. A press answers; a click outside the buttons opens it in the drawer.
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Head } from "../orkui.js";
import { say, toast } from "../link.js";
import { act, showIdea, showPlan, showTask, showGoal, showResult, needsFocus } from "../shell/store.js";
import { ResultActions } from "../shell/review.js";
import { openDialog } from "../shell/modals.js";
import { run as runOp } from "../board/ops.js";
import { useHeld } from "./motion.js";
import { askedOf, fanOf } from "./arenawords.js";

const SENT = "Sent: the Taskmaster answers in a moment.";

/** An answer and its refusal: the first button answers at once, the second opens one line (*Why not?*) that the third sends.
 *  `yes`, `ask`: the two buttons' [text, label]; `sure`: the sending button's label. */
function Decline({ s, yes, ask, sure, take, go }) {
  const [reason, setReason] = useState("");
  const [declining, setDeclining] = useState(false);
  return declining ? html`<div class="arena-hc__why">
      <input class="ork-field" value=${reason} aria-label=${`Why not: ${s.full}`} placeholder="Why not? (optional, one line)" autofocus
        onInput=${(e) => setReason(e.target.value)} onKeyDown=${(e) => { if (e.key === "Enter") go(reason.trim()); }} />
      <button type="button" class="ork-btn arena-hc__q" aria-label=${`${sure}: ${s.full}`} onClick=${() => go(reason.trim())}>${ask[0]}</button>
      <button type="button" class="ork-btn quiet arena-hc__q" onClick=${() => setDeclining(false)}>Cancel</button></div>`
    : html`<button type="button" class="ork-btn primary arena-hc__q" aria-label=${`${yes[1]}: ${s.full}`} onClick=${take}>${yes[0]}</button>
      <button type="button" class="ork-btn arena-hc__q" aria-label=${`${ask[1]}: ${s.full}`} onClick=${() => setDeclining(true)}>${ask[0]}</button>`;
}

function Answers({ s, g }) {
  if (s.kind === "result") return html`<${ResultActions} r=${s.result} />`;
  const row = s.row, n = s.node, slug = row?.idea || n?.slug || "";
  if (s.kind === "plan") {
    const night = n?.start_at === "night";
    return html`${night ? html`<button type="button" class="ork-btn primary arena-hc__q" title="Starts it now, not tonight" onClick=${() => act("ideas.start_now", { slug, via: "hand" })}>Start now</button>`
      : html`<button type="button" class="ork-btn primary arena-hc__q" title="Passes the plan; the work starts" onClick=${() => act("ideas.start", { slug, via: "hand" })}>Start the work</button>`}
      <button type="button" class="ork-btn arena-hc__q" title="The plan in the drawer" onClick=${() => showPlan(slug, "", { via: "hand" })}>Open the plan</button>`;
  }
  if (s.kind === "asks" || s.kind === "goal") {
    const isGoal = s.kind === "goal", target = isGoal ? row.goal : slug, asked = askedOf(row, n);
    const send = async (answers) => { const got = await act("ideas.answer", { slug: target, answers, ...(isGoal ? { goal: true } : {}) }); if (got) toast(say(SENT)); };
    const more = (picks) => openDialog("ask", { slug: target, goal: isGoal, title: row.title, asked: row.asked?.length ? asked : undefined, picks });
    const picks = asked.map((q) => (q.pick != null ? q.choices[q.pick] || "" : ""));
    if (asked.length === 1 && asked[0].choices.length) {
      return html`${asked[0].choices.map((c, i) => html`<button type="button" key=${c} class=${cls("ork-btn arena-hc__q is-text", { primary: i === asked[0].pick })}
          title=${i === asked[0].pick ? "Picked for you: one click answers" : "One click answers with this"} onClick=${() => send([c])}>${i === asked[0].pick ? "● " : ""}${c}</button>`)}
        <button type="button" class="ork-btn quiet arena-hc__q" onClick=${() => more(picks)}>Open…</button>`;
    }
    return html`${asked.length > 1 && html`<button type="button" class="ork-btn primary arena-hc__q" disabled=${!picks.some(Boolean)} onClick=${() => send(picks)}>Send the picks</button>`}
      <button type="button" class="ork-btn arena-hc__q" onClick=${() => more(picks)}>Open…</button>`;
  }
  if (s.kind === "proposal") {
    const take = () => act("ideas.proposal", { slug, take: true, priority: g?.priority || "normal" });
    return html`<${Decline} s=${s} yes=${["Take", "Take"]} ask=${["No", "No"]} sure="Decline" take=${take}
      go=${(reason) => act("ideas.proposal", { slug, take: false, ...(reason ? { reason } : {}) })} />`;
  }
  if (s.kind === "party") {
    const goal = row.goal;
    return html`<${Decline} s=${s} yes=${["Take it out", "Take it out"]} ask=${["Keep it", "Keep it"]} sure="Keep" take=${() => act("ideas.party_answer", { goal, take: true })}
      go=${(reason) => act("ideas.party_answer", { goal, take: false, ...(reason ? { reason } : {}) })} />`;
  }
  if (s.kind === "todo") return html`<button type="button" class="ork-btn arena-hc__q" onClick=${() => openDialog("todo", { idea: row.idea, todo: row.todo })}>Open…</button>`;
  if (s.kind === "failed") {
    return html`<button type="button" class="ork-btn primary arena-hc__q" title="Its idea’s tasks that are not merged or at Review run again"
        onClick=${() => act("ideas.start", { slug: n?.slug || row.idea, via: "hand" })}>Start again</button>
      <button type="button" class="ork-btn arena-hc__q" title="Its log; Drop is there, with a confirmation"
        onClick=${() => (s.task ? showTask(n.slug, s.task.id, { via: "hand" }) : showIdea(row.idea, { via: "hand" }))}>Open…</button>`;
  }
  if (s.kind === "op_rules") {
    const template = row.template;
    return html`<${Decline} s=${s} yes=${["Take", "Take the rules"]} ask=${["No", "No rules"]} sure="Decline the rules" take=${() => runOp("ops.rules_answer", { template, take: true })}
      go=${(reason) => runOp("ops.rules_answer", { template, take: false, ...(reason ? { reason } : {}) })} />`;
  }
  return html`<button type="button" class="ork-btn arena-hc__q" onClick=${() => openDialog("opcheck", { op: row.op })}>Open…</button>`;
}

/** What a click outside the buttons opens. */
function open(s) {
  const row = s.row, n = s.node, via = { via: "hand" };
  if (s.kind === "result") showResult(s.result.idea, s.result.task, via);
  else if (s.kind === "plan") showPlan(row.idea, "", via);
  else if (s.kind === "asks" || s.kind === "proposal") showIdea(row.idea, via);
  else if (s.kind === "goal" || s.kind === "party") showGoal(row.goal, via);
  else if (s.kind === "todo") showPlan(row.idea, row.todo?.id || "", via);
  else if (s.kind === "failed") (s.task ? showTask(n.slug, s.task.id, via) : showIdea(row.idea, via));
  else openDialog("opcheck", { op: row.op });
}

function Stop({ s, g, at, of }) {
  const fan = fanOf(at, of);
  return html`<div class=${cls("arena-hc ork-frame", { alert: s.tone === "alert", danger: s.tone === "danger", "is-compact": s.small })} data-kind=${s.kind} data-key=${s.key}
      style=${`--rot:${fan.rot}deg;--dy:${fan.dy}px;--z:${fan.z}`}>
    <button type="button" class="arena-hc__open" aria-label=${`${s.label}: ${s.full}`} onClick=${() => open(s)}>
      <span class="arena-hc__top"><span class=${cls("ork-gem", { danger: s.tone === "danger" })} title=${s.gemTip}>${s.gem}</span>
        <span class=${cls("arena-hc__kind", { "is-no": s.tone === "danger" })}>${s.label}</span>
        ${s.small && s.head && html`<span class="arena-hc__who" title=${s.whoTip}><${Head} race=${s.head.race} tier=${s.head.tier} /></span>`}</span>
      ${!s.small && html`<span class="arena-art">${s.head && html`<${Head} race=${s.head.race} tier=${s.head.tier} size="mid" />`}</span>`}
      <span class="arena-banner">${s.title}</span>
      <span class="arena-hc__text" title=${s.text}>${s.text}</span>
    </button>
    <div class="arena-hc__quick" role="group" aria-label=${s.kind === "asks" || s.kind === "goal" ? "Answer in one click" : "Quick moves"}><${Answers} s=${s} g=${g} /></div>
  </div>`;
}

/** The fan; a stop does not shift while one is raised (motion.js `useHeld`). */
export function Stops({ g, stops }) {
  const box = useRef();
  const shown = useHeld(box, stops, (s) => s.key);
  const focus = needsFocus.value;
  useEffect(() => { if (focus) box.current?.querySelector(".arena-hc__open")?.focus(); }, [focus]);
  return html`<div class="arena-hand" role="region" aria-label="Waits for you" ref=${box}>
    ${!shown.length && html`<p class="arena-cap arena-hand__empty">Nothing waits for you on this goal.</p>`}
    ${shown.map((s, i) => html`<${Stop} key=${s.key} s=${s} g=${g} at=${i} of=${shown.length} />`)}
  </div>`;
}
