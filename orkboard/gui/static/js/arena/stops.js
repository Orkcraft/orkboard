// What waits for you (docs/specs/49-one-window.md §6, docs/specs/54-one-hand.md §2–§3): the bottom row. Every stop of the project — a plan ready, a question, a
// proposal, a to-do, a failure, a pick, Operations' — each a framed item standing in a fan along the bottom edge, only its top showing, the most urgent in the middle
// (arenawords.js `laidOut`); one of another party says its party. Hovering or focusing one raises it whole, with its quick answers and a way out that needs nothing
// from the person (*Let … decide*, *Describe it instead*, *Go without it*, *Let … choose*). A press answers; a click outside the buttons opens it in the drawer. A *Pick one*
// (docs/specs/51-pick-one.md §6) holds its variants as small tiles, two by two (picks.js): a press on a strip picks one, *Take B* answers
// with it, *Pick, with a note…* (*Add a note…* once one is picked) opens the drawer where the note is written. A plan that gives work to no one of the party
// says so under its text (docs/specs/52-goal-types.md §4.4: *No one in the party does pixel art: Artist would.*) and offers *Add and start* when a seat is free.
// A plan started from here deals its cards onto the field (docs/specs/57-deal-on-start.md: `startPlan` keeps the stop's box), and so does a plan change taken (docs/specs/62-spec-after-start.md
// §6.2: *Take the new plan* or *Keep the plan*, the leader's price as the gem). While a stop is looked at, the cards it is about are ringed
// (docs/specs/58-stop-and-its-task.md: `aboutOf`); an answered stop fades where it stands, in the frame its task changes (motion.js `useLeaving`).
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Head, Icon, Sign } from "../orkui.js";
import { say, toast } from "../link.js";
import { act, showIdea, showPlan, showTask, showGoal, showResult, showPick, needsFocus } from "../shell/store.js";
import { ResultActions } from "../shell/review.js";
import { openDialog } from "../shell/modals.js";
import { TodoWays, named } from "../shell/tododialog.js";
import { run as runOp } from "../board/ops.js";
import { track } from "../board/store.js";
import { useHeld, useLeaving } from "./motion.js";
import { dealWaits, dropDeal, leaveParty, stopAbout, stopLook } from "./arenastate.js";
import { closeSpread } from "./spread.js";
import { askedOf, changeToast, fanOf, laidOut } from "./arenawords.js";
import { missingWords } from "./types.js";
import { Tiles, choiceOf } from "./picks.js";
import { manyWords, variantOf } from "./pickwords.js";

const SENT = "Sent: the Taskmaster answers in a moment.";

/** A plan started by a press in the hand (spec 57), or a plan change taken there (spec 62): the deal waits with the stop's box as it was at the press (raised then), the call is made, and a
 *  refusal takes the deal away. `e`: the press; `slug`: the plan's goal. The deal is kept before the call is answered, so that the render of the Board reread right after it finds it. */
async function startPlan(e, slug, name, args) {
  const box = e.currentTarget.closest(".arena-hc")?.getBoundingClientRect();
  const mine = box ? { left: box.left, top: box.top, width: box.width, height: box.height } : null;
  if (mine) dealWaits(slug, mine);
  const got = await act(name, args);
  if (!got) dropDeal();
  return got;
}

/** What a stop is about on the field (spec 58 §1): {task: "<goal>/<task>"} for a failed task, a pick and a result, {idea: "<goal>"} for a plan, a plan change, a question, a proposal and a to-do (the goal's cards,
 *  its Planning card), null for a stop of another party, Operations', and a party's own (it has no card here). */
export function aboutOf(s) {
  if (s.other || s.party?.ops) return null;
  const row = s.row;
  if (s.kind === "failed" && s.node && s.task) return { task: `${s.node.slug}/${s.task.id}` };
  if (s.kind === "pick" && row?.slug) return { task: `${row.slug}/${row.task}` };
  if (s.kind === "result" && s.result) return { task: `${s.result.idea}/${s.result.task}` };
  if (["plan", "change", "asks", "proposal", "todo"].includes(s.kind) && row?.idea) return { idea: row.idea };
  return null;
}

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

/** A question's way out (spec 54 §3.1): *Let <name> decide*, last and quiet; the one who asks answers with what it recommends. */
function Decide({ s, target, isGoal, name }) {
  const [busy, setBusy] = useState(false);
  const decide = async () => {
    setBusy(true);
    const got = await act("ideas.answer", { slug: target, decide: true, ...(isGoal ? { goal: true } : {}) });
    setBusy(false);
    if (got) toast(say(`Sent: ${named(name)} decides.`));
  };
  return html`<button type="button" class="ork-btn quiet arena-hc__q" disabled=${busy} aria-label=${`Let ${named(name)} decide: ${s.full}`}
    title="It answers with what it recommends" onClick=${decide}>Let ${named(name)} decide</button>`;
}

/** A pick's answers on the card: *Take B* once one is picked (it answers at once, `via: "hand"`), and the way to the drawer for the note. */
function PickAnswers({ s, see }) {
  const row = s.row, key = choiceOf(row).key, [busy, setBusy] = useState(false);
  const take = async () => { setBusy(true); await act("ideas.pick", { slug: row.slug, task: row.task, key, via: "hand" }); setBusy(false); };
  return html`${key && html`<button type="button" class="ork-btn primary arena-hc__q" disabled=${busy} title=${`Goes on with ${key} · ${variantOf(row, key)?.name || ""}`}
      aria-label=${`Take ${key}: ${s.full}`} onClick=${take}>Take ${key}</button>`}
    <button type="button" class="ork-btn arena-hc__q" title=${`The ${manyWords(row)} large, a note, None of them`} aria-label=${`${key ? "Add a note" : "Pick, with a note"}: ${s.full}`}
      onClick=${() => { see(); showPick(row.slug, row.task, { via: "hand" }); }}>${key ? "Add a note…" : "Pick, with a note…"}</button>`;
}

function Answers({ s, g, see }) {
  if (s.kind === "result") return html`<${ResultActions} r=${s.result} />`;
  if (s.kind === "pick") return html`<${PickAnswers} s=${s} see=${see} />`;
  const row = s.row, n = s.node, slug = row?.idea || n?.slug || "";
  if (s.kind === "plan") {
    const night = n?.start_at === "night", miss = row?.missing || [];
    if (miss.length && !night) {
      const m = miss[0];
      const join = async (e) => { const got = await startPlan(e, slug, "ideas.start", { slug, join: { add: m.agent }, via: "hand" }); if (got) toast(`${m.name} joined the party; the work started.`); };
      const without = (e) => startPlan(e, slug, "ideas.start", { slug, via: "hand" });
      return m.free ? html`<button type="button" class="ork-btn primary arena-hc__q" title=${`${m.name} joins the party, then the work starts`} onClick=${join}>Add and start</button>
          <button type="button" class="ork-btn arena-hc__q" title="Passes the plan as it is; the Grunt does that work" onClick=${without}>Start without</button>`
        : html`<button type="button" class="ork-btn primary arena-hc__q" title="Passes the plan as it is; the Grunt does that work" onClick=${without}>Start without</button>
          <button type="button" class="ork-btn arena-hc__q" title="Change a member of the party" onClick=${() => { see(); openDialog("goal", { slug: row.goal || g?.slug }); }}>Edit the party</button>`;
    }
    return html`${night ? html`<button type="button" class="ork-btn primary arena-hc__q" title="Starts it now, not tonight" onClick=${(e) => startPlan(e, slug, "ideas.start_now", { slug, via: "hand" })}>Start now</button>`
      : html`<button type="button" class="ork-btn primary arena-hc__q" title="Passes the plan; the work starts" onClick=${(e) => startPlan(e, slug, "ideas.start", { slug, via: "hand" })}>Start the work</button>`}
      <button type="button" class="ork-btn arena-hc__q" title="The plan in the drawer" onClick=${() => { see(); showPlan(slug, "", { via: "hand" }); }}>Open the plan</button>`;
  }
  if (s.kind === "change") {
    const take = async (e) => {
      const got = await startPlan(e, slug, "ideas.revise_answer", { slug, take: true, via: "hand" });
      if (!got) return;
      if (!got.added) dropDeal();                                                   // nothing new to deal: it would wait 6 s for a card that does not come
      toast(changeToast(got));
    };
    const keep = async () => { if (await act("ideas.revise_answer", { slug, take: false, via: "hand" })) toast(changeToast({})); };
    return html`<button type="button" class="ork-btn primary arena-hc__q" title="The tasks not started take the change; the ones that started stay as they are" onClick=${take}>Take the new plan</button>
      <button type="button" class="ork-btn arena-hc__q" title="The plan stays as it is" onClick=${keep}>Keep the plan</button>`;
  }
  if (s.kind === "asks" || s.kind === "goal") {
    const isGoal = s.kind === "goal", target = isGoal ? row.goal : slug, asked = askedOf(row, n);
    const send = async (answers) => { const got = await act("ideas.answer", { slug: target, answers, ...(isGoal ? { goal: true } : {}) }); if (got) toast(say(SENT)); };
    const more = (picks) => { see(); openDialog("ask", { slug: target, goal: isGoal, title: row.title, asked: row.asked?.length ? asked : undefined, picks }); };
    const picks = asked.map((q) => (q.pick != null ? q.choices[q.pick] || "" : ""));
    const decide = html`<${Decide} s=${s} target=${target} isGoal=${isGoal} name=${isGoal ? s.party.lead : asked.find((q) => q.by?.name)?.by?.name || s.party.lead} />`;
    if (asked.length === 1 && asked[0].choices.length) {
      return html`${asked[0].choices.map((c, i) => html`<button type="button" key=${c} class=${cls("ork-btn arena-hc__q is-text", { primary: i === asked[0].pick })}
          title=${i === asked[0].pick ? "Picked for you: one click answers" : "One click answers with this"} onClick=${() => send([c])}>${i === asked[0].pick ? "● " : ""}${c}</button>`)}
        <button type="button" class="ork-btn quiet arena-hc__q" onClick=${() => more(picks)}>Open…</button>${decide}`;
    }
    return html`${asked.length > 1 && html`<button type="button" class="ork-btn primary arena-hc__q" disabled=${!picks.some(Boolean)} onClick=${() => send(picks)}>Send the picks</button>`}
      <button type="button" class="ork-btn arena-hc__q" onClick=${() => more(picks)}>Open…</button>${decide}`;
  }
  if (s.kind === "proposal") {
    const take = () => act("ideas.proposal", { slug, take: true, priority: s.g?.priority || g?.priority || "normal" });
    return html`<${Decline} s=${s} yes=${["Take", "Take"]} ask=${["No", "No"]} sure="Decline" take=${take}
      go=${(reason) => act("ideas.proposal", { slug, take: false, ...(reason ? { reason } : {}) })} />`;
  }
  if (s.kind === "party") {
    const goal = row.goal;
    return html`<${Decline} s=${s} yes=${["Take it out", "Take it out"]} ask=${["Keep it", "Keep it"]} sure="Keep" take=${() => act("ideas.party_answer", { goal, take: true })}
      go=${(reason) => act("ideas.party_answer", { goal, take: false, ...(reason ? { reason } : {}) })} />`;
  }
  if (s.kind === "todo") {
    return html`<button type="button" class="ork-btn arena-hc__q" onClick=${() => { see(); openDialog("todo", { idea: row.idea, todo: row.todo, lead: s.party.lead }); }}>Open…</button>
      <${TodoWays} idea=${row.idea} todo=${row.todo} lead=${s.party.lead} agent=${row.todo?.by?.name} />`;
  }
  if (s.kind === "failed") {
    return html`<button type="button" class="ork-btn primary arena-hc__q" title="Its goal’s tasks that are not merged or at Review run again"
        onClick=${() => act("ideas.start", { slug: n?.slug || row.idea, via: "hand" })}>Start again</button>
      <button type="button" class="ork-btn arena-hc__q" title="Its log; Drop is there, with a confirmation"
        onClick=${() => { see(); if (s.task) showTask(n.slug, s.task.id, { via: "hand" }); else showIdea(row.idea, { via: "hand" }); }}>Open…</button>`;
  }
  if (s.kind === "op_rules") {
    const template = row.template;
    return html`<${Decline} s=${s} yes=${["Take", "Take the rules"]} ask=${["No", "No rules"]} sure="Decline the rules" take=${() => runOp("ops.rules_answer", { template, take: true })}
      go=${(reason) => runOp("ops.rules_answer", { template, take: false, ...(reason ? { reason } : {}) })} />`;
  }
  return html`<button type="button" class="ork-btn arena-hc__q" onClick=${() => { see(); openDialog("opcheck", { op: row.op }); }}>Open…</button>`;
}

/** What a click outside the buttons opens. */
function open(s) {
  const row = s.row, n = s.node, via = { via: "hand" };
  if (s.kind === "result") showResult(s.result.idea, s.result.task, via);
  else if (s.kind === "plan" || s.kind === "change") showPlan(row.idea, "", via);
  else if (s.kind === "asks" || s.kind === "proposal") showIdea(row.idea, via);
  else if (s.kind === "goal" || s.kind === "party") showGoal(row.goal, via);
  else if (s.kind === "todo") showPlan(row.idea, row.todo?.id || "", via);
  else if (s.kind === "failed") (s.task ? showTask(n.slug, s.task.id, via) : showIdea(row.idea, via));
  else if (s.kind === "pick") showPick(row.slug, row.task, via);
  else openDialog("opcheck", { op: row.op });
}

/** A stop of another party opens there (spec 54 §2.2): that party is shown first, as a pick of it in the parties' list; a quick answer acts in place. */
const toParty = (s) => {
  if (!s.other) return;
  closeSpread();
  leaveParty();
  track.value = s.party.slug;
};

function Stop({ s, g, place, of }) {
  const fan = fanOf(place, of), pick = s.kind === "pick", other = s.other, p = s.party;
  const see = () => toParty(s);
  const label = other ? `${s.label} in ${p.name}` : s.label;
  const about = aboutOf(s), ghost = !!s.ghost, said = `link-${s.key.replace(/[^\w-]/g, "_")}`;
  const look = (el) => {                                           // looked at while raised: the pointer over it or the focus in it (spec 58 §2.1)
    if (ghost) return;
    if (el.matches(":hover, :focus-within")) { stopLook.value = s.key; stopAbout.value = about; }
    else if (stopLook.value === s.key) { stopLook.value = ""; stopAbout.value = null; }
  };
  const gone = (e) => { const el = e.currentTarget; setTimeout(() => el.isConnected && look(el), 0); };       // after the pointer or the focus has moved on
  const unlook = () => { if (stopLook.value === s.key) { stopLook.value = ""; stopAbout.value = null; } };
  useEffect(() => { if (ghost) unlook(); }, [ghost]);               // answered or withdrawn: nothing stays ringed
  useEffect(() => unlook, []);
  return html`<div class=${cls("arena-hc ork-frame", { alert: s.tone === "alert", danger: s.tone === "danger", "is-compact": s.small, "is-other": other, "is-leaving": ghost, "is-raised": ghost && s.raised })}
      data-kind=${s.kind} data-key=${s.key} data-party=${p.slug} style=${`--rot:${fan.rot}deg;--dy:${fan.dy}px;--z:${fan.z};order:${place}`} inert=${ghost || undefined} aria-hidden=${ghost ? "true" : undefined}
      onpointerenter=${(e) => look(e.currentTarget)} onfocusin=${(e) => look(e.currentTarget)} onpointerleave=${gone} onfocusout=${gone}>
    <button type="button" class="arena-hc__open" aria-label=${`${label}: ${s.full}`} aria-describedby=${about ? said : undefined} title=${pick ? `${s.full} · ${s.text}` : undefined} onClick=${() => { see(); open(s); }}>
      <span class="arena-hc__top">${s.gem !== "" && html`<span class=${cls("ork-gem", { danger: s.tone === "danger" })} title=${s.gemTip}>${typeof s.gem === "object" ? html`<${Sign} name=${s.gem.sign} />` : s.gem}</span>`}
        <span class=${cls("arena-hc__kind", { "is-no": s.tone === "danger" })}>${s.label}</span>
        ${s.small && s.head && html`<span class="arena-hc__who" title=${s.whoTip}><${Head} race=${s.head.race} tier=${s.head.tier} /></span>`}</span>
      ${other && html`<span class="arena-hc__party" title=${p.ops ? p.name : `${p.name} · led by ${p.lead}`}>${p.ops ? html`<${Icon} name="sliders" />` : p.head && html`<${Head} race=${p.head.race} tier=${p.head.tier} />`}</span>`}
      ${!s.small && html`<span class="arena-art">${s.head && html`<${Head} race=${s.head.race} tier=${s.head.tier} size="mid" />`}</span>`}
      ${!pick && html`<span class="arena-banner">${other ? `${p.name} · ${s.title}` : s.title}</span><span class="arena-hc__text" title=${s.text}>${s.text}</span>`}
      ${s.why && html`<span class="arena-hc__note" title=${s.why}>${s.why}</span>`}
      ${s.kind === "plan" && (s.row?.missing || []).length > 0 && html`<span class="arena-hc__miss">${missingWords(s.row.missing)}</span>`}
    </button>
    ${about && html`<span id=${said} hidden>${about.task ? ", its task is ringed on the field" : ", its goal is ringed on the field"}</span>`}
    ${pick && html`<${Tiles} row=${s.row} />`}
    <div class="arena-hc__quick" role="group" aria-label=${s.kind === "asks" || s.kind === "goal" ? "Answer in one click" : pick ? "Pick one" : "Quick moves"}><${Answers} s=${s} g=${g} see=${see} /></div>
  </div>`;
}

/** The fan, the most urgent in the middle (spec 54 §2.3): `stops` come in urgency's order and stay in it in the page (the keys and a screen reader read it), laid out from the
 *  middle by their `order`; a stop does not shift while one is raised (motion.js `useHeld`). A long hand overlaps more, so that it fits. */
export function Stops({ g = null, stops }) {
  const box = useRef();
  const shown = useLeaving(box, useHeld(box, stops, (s) => s.key), (s) => s.key);                // a stop that leaves fades where it stands (spec 58 §4)
  const focus = needsFocus.value, n = shown.length;
  useEffect(() => { if (focus) box.current?.querySelector(".arena-hc__open")?.focus(); }, [focus]);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return undefined;
    const fit = () => el.style.setProperty("--ov", `${n > 1 ? Math.min(78, Math.max(14, (156 - (el.clientWidth - 156) / (n - 1)) / 2)) : 14}px`);        // each side of a card, so that the row fits
    fit();
    const watch = typeof ResizeObserver === "function" ? new ResizeObserver(fit) : null;
    watch?.observe(el);
    return () => watch?.disconnect();
  }, [n]);
  const at = laidOut(n);
  return html`<div class="arena-hand" role="region" aria-label="Waits for you" ref=${box}>
    ${!n && html`<p class="arena-cap arena-hand__empty">Nothing waits for you.</p>`}
    ${shown.map((s, i) => html`<${Stop} key=${s.key} s=${s} g=${g} place=${at[i]} of=${n} />`)}
  </div>`;
}
