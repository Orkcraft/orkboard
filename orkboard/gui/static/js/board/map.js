// The Map (docs/specs/39-map.md §4, decisions §53): the preview's first tab, a trail for each goal, one under the other. A trail
// runs from how far the goal is (in %, at its start) through the ideas left to do — stops, from left to right, an idea right of
// the ideas it depends on, the ones that can go at once side by side (three at most, the rest a click away) — to the goal's flag,
// raised when its leader accepts it against its metrics (the verdict). An idea at work shows its tasks left, each with the head
// of the agent who does it, in the waves they go in; what is done is not on the trail (a click shows it). A stop is a chip: the
// head of who does it, its short name (two lines at most; the title is its label, spec 41 §3), a mark of its state (its words on hover); one that waits for the person is a gate (! on it). A view of `ideas.map`: it changes nothing, its one action is open. Words of a stop's state
// are the Board row's (`rowOf`).
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Icon, WhoHead } from "../orkui.js";
import { PRIORITY_WORDS, ask } from "./store.js";
import { mapData, mapSince, mapFolded, mapUi, mapView, preview, lookKey, logOpened, showIdea, showTask, showGoal, act as run } from "../shell/store.js";
import { skippable, spares } from "./idea.js";
import { Cards } from "./cards.js";
import { showWeek } from "../shell/look.js";
import { PartyFold } from "../shell/goalview.js";
import { openDialog } from "../shell/modals.js";
import { TASK_STATE, nodeView, tiersOf, wavesOf, spentWords, goalState, progressOf, leftToDo, trailCurve, trailEdges, tallyWords, flagWords } from "./maplayout.js";

const LANES = 3;                       // the stops side by side in one step of the trail, before "+N more"
const TASKS = 6;                       // the tasks left shown on a stop at work

const listed = (key) => mapUi.value[key] || [];
const toggle = (key, id) => {
  const list = listed(key);
  mapUi.value = { ...mapUi.value, [key]: list.includes(id) ? list.filter((x) => x !== id) : [...list, id] };
};

/** "checks 1/2 passed: Reviewer: passed · …": the checks that apply to an idea, for its chip's words. */
function checksWords(checks) {
  const on = (checks || []).filter((c) => c.applies);
  if (!on.length) return "";
  const passed = on.filter((c) => c.state === "passed").length;
  return `checks ${passed}/${on.length} passed: ${on.map((c) => `${c.name}: ${c.state === "passed" ? "passed" : TASK_STATE[c.state] || "to come"}`).join(" · ")}`;
}

/** The goal's party: its leader, then its builders and checkers (a checker says so). */
function Team({ team, leader }) {
  if (!(team || []).length && !leader) return null;
  const words = (team || []).map((t) => `${t.name}${t.every ? " (checks every idea)" : t.checks ? " (checks)" : ""}`).join(", ");
  const line = leader ? `Led by ${leader.name}${words ? ` · ${words}` : ""}` : `Team: ${words}`;
  return html`<p class="map-goal__team ok-font-status ok-tone-muted" aria-label=${line}>
    <span class="map-goal__heads">${[leader, ...(team || [])].filter(Boolean).map((t) => html`<${WhoHead} key=${t.slug} head=${t.head} small />`)}</span> ${line}</p>`;
}

/** An idea not yet planned is in the fog: its tasks are not known yet. */
const fog = (n) => !n.tasks.length && ["raw", "reading", "asks", "ready", "planning", "proposed"].includes(n.state);

/** Who does an idea now: the agent of its running task, else of its next task, else the goal's leader (it drafts and plans). */
export function stopHead(n, leader) {
  const left = n.tasks.filter(leftToDo);
  const t = left.find((x) => x.state === "running" || x.state === "testing") || left[0];
  return t?.head || leader?.head || null;
}

/** A timed wait (the night, the limits, the reserve) is a clock on the chip. */
const timed = (w) => ["night", "limits", "reserve", "week"].includes(w?.kind);

/** A stop: a chip — the head of who does it, its title, a mark of its state (its words on hover and to a screen reader) — and,
 *  for the idea at work, its tasks left as smaller chips, each with its agent's head, in the waves they go in. */
function Stop({ n, titles, since, leader, team }) {
  const v = nodeView(n, titles);
  const fresh = !!since && n.updated > since;
  const left = n.tasks.filter(leftToDo), doneTasks = n.tasks.length - left.length;
  const words = [v.needs && !v.words.includes(v.needs) ? `${v.words} · ${v.needs}` : v.words, v.wait, n.by_itself ? "by itself" : "", v.cost,
    checksWords(n.checks), fresh ? "new" : ""].filter(Boolean).join(" · ");
  const head = stopHead(n, leader);
  return html`<li class=${cls("map-node", { "is-gate": !!v.needs })} data-slug=${n.slug}>
    <button class=${cls("map-card trail-chip", { "is-needs": !!v.needs, "is-wait": !!v.wait, "is-fog": fog(n), "is-done": n.state === "done", "is-on": preview.value?.kind === "idea" && preview.value.slug === n.slug })}
      data-slug=${n.slug} data-state=${n.state} data-needs=${n.needs_you || ""} title=${`${n.title} · ${words}`} aria-label=${`${n.title}: ${words}`}
      onClick=${() => showIdea(n.slug, { via: "map" })}>
      ${head ? html`<${WhoHead} head=${head} small />` : html`<span class="trail-chip__nohead" aria-hidden="true"></span>`}
      <b class="map-card__title">${n.short || n.title}</b>
      ${v.needs ? html`<span class="trail-chip__mark is-gate" aria-hidden="true"><${Icon} name="warning-diamond" /></span>`
        : v.spin ? html`<span class="shell-spin trail-chip__mark" aria-hidden="true">↻</span>`
          : timed(n.waits) && n.state !== "done" ? html`<span class="trail-chip__mark" aria-hidden="true"><${Icon} name="clock" /></span>` : ""}
      ${fresh && html`<span class="map-card__new" aria-hidden="true">new</span>`}
    </button>
    ${left.length > 0 && n.state !== "done" && html`<div class="map-tasks" aria-label=${`Tasks of ${n.title}`}>
      ${wavesOf(left).map((wave, i) => html`<div key=${i} class="map-wave" data-wave=${i + 1}>
        ${wave.slice(0, TASKS).map((t) => {
          const said = `${t.title} · ${t.tag ? `${t.tag} · ` : ""}${TASK_STATE[t.state] || t.state}`;
          const check = (n.checks || []).find((c) => c.task === t.id);            // a task of a checker: it may be skipped before it runs
          const chip = html`<button type="button" class="map-task" data-state=${t.state} title=${said} aria-label=${said}
            onClick=${() => showTask(n.slug, t.id, { via: "map" })}>${t.head && html`<${WhoHead} head=${t.head} small />`}<span class="map-task__title">${t.short || t.title}</span></button>`;
          return check && skippable(check) ? html`<span key=${t.id} class="map-task-pair is-check">${chip}<button type="button" class="map-task__skip"
            aria-label=${`Skip the check: ${check.name}`} title=${`Skip the check: its run is spared${spares(check)}`}
            onClick=${() => run("ideas.check_skip", { slug: n.slug, by: check.by })}><${Icon} name="close" /></button></span>` : html`<span key=${t.id} class="map-task-pair">${chip}</span>`;
        })}</div>`)}
      ${doneTasks > 0 && html`<small class="map-tasks__done ok-tone-muted">${doneTasks} done</small>`}</div>`}
    <${Checks} n=${n} team=${team} />
  </li>`;
}

/** An idea not planned yet: the checks its plan will hold, each a chip with × to leave it out (its run spared), and the ones
 *  left out, faded, with + to take them again. Once planned, a check is its task's chip (× while it has not run). */
function Checks({ n, team }) {
  if (n.tasks.length || n.state === "done") return null;
  const mine = (n.checks || []).filter((c) => c.applies && !c.task);
  if (!mine.length) return null;
  const head = (c) => (team || []).find((t) => t.slug === c.by)?.head;
  return html`<div class="map-tasks map-checks" aria-label=${`Checks of ${n.title}`}>${mine.map((c) => html`<span key=${c.by}
      class=${cls("map-task-pair is-check", { "is-skipped": c.skipped })}>
    <span class="map-task" title=${c.skipped ? `${c.name}: skipped by you` : `${c.name}: in the plan to come${spares(c)}`}>${head(c) && html`<${WhoHead} head=${head(c)} small />`}<span class="map-task__title">${c.name}</span></span>
    ${c.skipped ? html`<button type="button" class="map-task__skip" aria-label=${`Take the check again: ${c.name}`} title="Take it again: the plan holds it"
        onClick=${() => run("ideas.check_skip", { slug: n.slug, by: c.by, skip: false })}><${Icon} name="plus" /></button>`
      : html`<button type="button" class="map-task__skip" aria-label=${`Skip the check: ${c.name}`} title=${`Leave it out of the plan: its run is spared${spares(c)}`}
        onClick=${() => run("ideas.check_skip", { slug: n.slug, by: c.by })}><${Icon} name="close" /></button>`}</span>`)}</div>`;
}

/** The flags this device raised (spec 42 §2.3): the goals' slugs under `orkboard.flags.<12 characters>`; null on a device with no list. */
const flagsKey = () => lookKey().replace("orkboard.look.", "orkboard.flags.");
function raisedList(key) {
  try {
    const got = JSON.parse(localStorage.getItem(key) || "null");
    return Array.isArray(got) ? got.filter((x) => typeof x === "string") : null;
  } catch { return null; }
}
function keepRaised(key, slugs) {
  try { localStorage.setItem(key, JSON.stringify([...new Set([...(raisedList(key) || []), ...slugs])])); } catch { /* the flag is raised again next time */ }
}
const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** A device with no list adds every met goal without raising any (the first start after this part). */
function seedRaised(m) {
  const key = flagsKey();
  if (key && raisedList(key) === null) keepRaised(key, m.goals.filter((g) => g.verdict?.met).map((g) => g.slug));
}

/** The goal's flag is raised once on this device, while its trail is on screen (the Map shown, the goal unfolded, the page visible):
 *  it moves up from the foot of its box in six steps (not under reduced motion), the slug is kept and `opened` `flag` is logged. */
function useRaise(g, ref) {
  const [raising, setRaising] = useState(false);
  const met = g.verdict?.met === true;
  useEffect(() => {
    const key = flagsKey();
    const list = key && met ? raisedList(key) : null;
    if (!list || list.includes(g.slug) || !ref.current) return undefined;
    let io, timer, done = false;
    const raise = () => {
      if (done || document.visibilityState !== "visible") return;
      done = true;
      io?.disconnect();
      keepRaised(key, [g.slug]);
      logOpened("flag", g.slug);
      if (!reducedMotion()) { setRaising(true); timer = setTimeout(() => setRaising(false), 700); }
    };
    if (typeof IntersectionObserver === "function") {
      io = new IntersectionObserver((seen) => { if (seen.some((e) => e.isIntersecting)) raise(); });
      io.observe(ref.current);
    } else raise();
    document.addEventListener("visibilitychange", raise);
    return () => { done = true; io?.disconnect(); clearTimeout(timer); document.removeEventListener("visibilitychange", raise); };
  }, [met, g.slug]);
  return raising;
}

/** One goal's trail: the start (how far, the done ones), its steps of stops, the flag; the lines drawn once laid out. */
function Trail({ g, nodes, edges, titles, since }) {
  const root = useRef(), last = useRef(""), end = useRef();
  const raising = useRaise(g, end);
  const [lines, setLines] = useState([]);
  const open = nodes.filter((n) => n.state !== "done");
  const steps = tiersOf(open);
  const wide = listed("lanes").includes(g.slug);
  const shownSlugs = steps.flatMap((s) => (wide ? s : s.slice(0, LANES)).map((n) => n.slug));
  const ways = trailEdges(shownSlugs, edges);
  const measure = () => {
    const el = root.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const at = (slug, side) => {
      const box = (slug === "@start" ? el.querySelector(".trail-start__dot") : slug === "@end" ? el.querySelector(".trail-end__flag")
        : el.querySelector(`.map-card[data-slug="${CSS.escape(slug)}"]`))?.getBoundingClientRect();
      return box && { x: (side === "out" ? box.right : box.left) - r.left, y: box.top + box.height / 2 - r.top };
    };
    const out = [];
    for (const e of ways) {
      const a = at(e.from, "out"), b = at(e.to, "in");
      if (a && b) out.push({ from: e.from, to: e.to, d: trailCurve(a, b) });
    }
    const key = JSON.stringify(out);
    if (key !== last.current) { last.current = key; setLines(out); }
  };
  useLayoutEffect(measure);                                         // after every render: a stop's tasks move what is beside it
  useEffect(() => {
    if (typeof ResizeObserver !== "function") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(root.current);
    return () => ro.disconnect();
  }, []);
  const pct = progressOf(nodes), done = nodes.filter((n) => n.state === "done");
  const doneOpen = listed("done").includes(g.slug);
  const flag = g.verdict ? (g.verdict.met ? "is-met" : "is-not") : "";
  const endWords = g.verdict ? (g.verdict.met ? `Met · ${g.verdict.by}` : `Not met yet · ${g.verdict.by}`) : open.length ? "The goal" : "Its ideas are done";
  return html`<div class="map-scroll"><div class="trail" ref=${root}>
    <svg class="map-lines" aria-hidden="true">${lines.map((l) => html`<path key=${l.from + l.to} d=${l.d} data-from=${l.from} data-to=${l.to} />`)}</svg>
    <div class="trail-start">
      <span class="trail-start__dot" aria-hidden="true"></span>
      <b class="trail-start__pct" aria-label=${`${pct} % of the way`}>${pct} %</b>
      <span class="ok-font-status ok-tone-muted">${done.length} of ${nodes.length} ideas</span>
      ${done.length > 0 && html`<button class="board-link map-done__btn" aria-expanded=${doneOpen} onClick=${() => toggle("done", g.slug)}>Done (${done.length})</button>`}
    </div>
    ${steps.map((step, i) => {
      const shown = wide ? step : step.slice(0, LANES);
      return html`<ul key=${i} class="map-tier trail-step" data-tier=${step[0].tier}>
        ${shown.map((n) => html`<${Stop} key=${n.slug} n=${n} titles=${titles} since=${since} leader=${g.leader} team=${g.team} />`)}
        ${step.length > LANES && html`<li class="trail-more"><button class="board-link" aria-expanded=${wide} onClick=${() => toggle("lanes", g.slug)}>
          ${wide ? "Fewer side by side" : `+${step.length - LANES} more side by side`}</button></li>`}</ul>`;
    })}
    ${!steps.length && html`<p class="trail-empty ok-tone-muted">No idea left on the way.</p>`}
    <div class=${cls("trail-end", flag)} ref=${end} aria-label=${`The flag: ${endWords}`}>
      <span class=${cls("trail-end__flag", { "is-raising": raising })}><${Icon} name="flag" /></span>
      <span class="ok-font-status">${endWords}</span>
      ${g.verdict?.met && g.verdict.tally && html`<span class="trail-end__tally ok-font-status ok-tone-muted">${tallyWords(g.verdict.tally)}</span>`}
    </div>
  </div>
  ${doneOpen && html`<ul class="map-done__list" aria-label=${`Done in ${g.title}`}>${done.map((n) => html`<${Stop} key=${n.slug} n=${n} titles=${titles} since=${since} leader=${g.leader} team=${g.team} />`)}</ul>`}
  </div>`;
}

function Goal({ g, nodes, edges, titles, since }) {
  const folded = mapFolded.value.includes(g.slug);
  const more = listed("more").includes(g.slug);
  const lines = g.done_when || [];
  const fold = () => { mapFolded.value = folded ? mapFolded.value.filter((x) => x !== g.slug) : [...mapFolded.value, g.slug]; };
  return html`<section class="map-goal" aria-label=${g.title} data-goal=${g.slug} data-folded=${folded}>
    <header class="map-goal__head">
      <button class="map-fold" aria-expanded=${!folded} aria-label=${`${folded ? "Unfold" : "Fold"} ${g.title}`} onClick=${fold}><${Chev} dir=${folded ? "right" : "down"} /></button>
      <h3 class="map-goal__title">${g.title}</h3>
      <span class="board-prio" data-priority=${g.priority}>${PRIORITY_WORDS[g.priority] || "Normal"}</span>
      <span class="map-goal__state ok-tone-muted">${goalState(g.state)}</span>
      <span class="map-goal__count">${progressOf(nodes)} %</span>
      <span class="map-goal__usd ok-tone-muted">${spentWords(g.usd)}</span>
      ${g.verdict && html`<span class=${`map-goal__verdict ${g.verdict.met ? "ok-tone-ok" : "ok-tone-error"}`}>${g.verdict.met ? `accepted by ${g.verdict.by}` : `not met, says ${g.verdict.by}`}</span>`}
    </header>
    ${!folded && html`<${Team} team=${g.team} leader=${g.leader} />${lines.length > 0 && html`<p class="map-goal__when ok-font-status ok-tone-muted">done when ${lines[0]}${lines.length > 1 && !more ? html` <button class="board-link" onClick=${() => toggle("more", g.slug)}>and ${lines.length - 1} more</button>` : ""}
      ${more ? lines.slice(1).map((l) => html`<br />done when ${l}`) : ""}</p>`}
      <${Trail} g=${g} nodes=${nodes} edges=${edges} titles=${titles} since=${since} />`}
  </section>`;
}

const FLAGS_OPEN = "@flags:open";                                   // in the folds kept with the tabs: the Flags fold is closed until it is opened

/** The foot of the Map (spec 42 §2.4): *Flags (3)*, the goals met, with their tally; the list is asked for when the fold is opened. */
function MapFoot({ m }) {
  const met = m.goals.filter((g) => g.verdict?.met).length;
  const open = mapFolded.value.includes(FLAGS_OPEN);
  const [flags, setFlags] = useState(null);
  useEffect(() => {
    if (!open || !met) return undefined;
    let on = true;
    ask("ideas.flags").then((got) => { if (on && got) setFlags(got.flags || []); });
    return () => { on = false; };
  }, [open, met, m.rev]);
  const fold = () => { mapFolded.value = open ? mapFolded.value.filter((x) => x !== FLAGS_OPEN) : [...mapFolded.value, FLAGS_OPEN]; };
  return html`<div class="map-foot">
    ${met > 0 && html`<section class="map-flags" aria-label="Flags">
      <button type="button" class="board-link map-flags__btn" aria-expanded=${open} onClick=${fold}>Flags (${met})</button>
      ${open && html`<ul class="map-flags__list">${(flags || []).map((f) => html`<li key=${f.goal}>
        <button type="button" class="map-flag" onClick=${() => showGoal(f.goal, { via: "flags" })}>
          <span class="map-flag__mark" aria-hidden="true"><${Icon} name="flag" /></span>
          <span class="map-flag__body"><b>${f.title}</b><span class="ok-font-status ok-tone-muted">${flagWords(f)}</span>
            <span class="ok-font-status ok-tone-muted">${tallyWords(f.tally)}</span></span></button>
        <${PartyFold} slug=${f.goal} /></li>`)}</ul>`}
    </section>`}
    <button type="button" class="board-link map-foot__week" onClick=${showWeek}>Last week</button>
  </div>`;
}

export function MapView() {
  const m = mapData.value, since = mapSince.value;
  const el = useRef();
  useLayoutEffect(() => { if (el.current) el.current.scrollTop = mapView.top; }, []);       // the Map keeps its scroll when its tab comes back
  if (!m) return html`<p class="ok-tone-muted map-note">Reading the Map…</p>`;
  seedRaised(m);
  const titles = Object.fromEntries(m.nodes.map((n) => [n.slug, n.title]));
  const goalOf = Object.fromEntries(m.nodes.map((n) => [n.slug, n.goal]));
  return html`<div class="map" ref=${el} aria-label="Map" onScroll=${(e) => { mapView.top = e.currentTarget.scrollTop; }}>
    <${Cards} />
    ${!m.goals.length ? html`<div class="shell-empty"><p>No goals yet</p><p><button class="ork-btn primary" onClick=${() => openDialog("goal")}>New goal</button></p></div>`
      : m.goals.map((g) => html`<${Goal} key=${g.slug} g=${g} nodes=${m.nodes.filter((n) => n.goal === g.slug)}
        edges=${m.edges.filter((e) => goalOf[e.to] === g.slug)} titles=${titles} since=${since} />`)}
    <${MapFoot} m=${m} />
  </div>`;
}
