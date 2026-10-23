// A pitch's screen (docs/specs/65-ideation.md §8, decisions §78), a goal of Ideation in the drawer — `ideas.page`'s `pitch` (realm/pitches.py `face`): the pitch
// (its Gist, what it points at); the four views side by side, each with its head, *For*, *Against* and its question (a view not answered yet waits, dim); the case
// against, the Skeptic's; the decision, the Investor's — its answer large, why, the kill reasons in their words, where and as what type, the first step, the
// cheapest test, the goal it repeats —; what became of it (sent, naming the goal; passed, with the person's line) and the decisions before. At its foot what the
// person does, saying what happens: **Send to <party>** with the party's select beside it (the decision's party first; a party of the library the project lacks
// opens New party with it), **Change and judge again** (the words, changed, judged anew), **Pass** (a line why, optional), **Drop**; **Try again** after a
// failure, **Judge again** for a passed one, **Judge now** for one on hold or tonight. The pixel face is the headings' and the buttons'; the views' and the
// Investor's words are in the text face.
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { toast } from "../link.js";
import { Sign, WhoHead } from "../orkui.js";
import { act, closePreview, mapData, showIdea } from "./store.js";
import { openDialog } from "./modals.js";
import { ErrorLine } from "./errors.js";
import { PointedAt } from "./lens.js";
import { PITCH_STATE, pitchWords, sendDefault, sendTargets, sentWords, whereWords } from "../arena/pitchwords.js";

const List = ({ items, label }) => (items?.length ? html`<ul class="shell-pitch__list" aria-label=${label}>${items.map((x, i) => html`<li key=${i}>${x}</li>`)}</ul>`
  : html`<p class="ok-tone-muted">—</p>`);

/** One view: its head and name, *For*, *Against*, its question (the Engineering view's size too); a view that has not answered waits, dim. */
function View({ v, judging }) {
  return html`<section class=${cls("shell-pitch__view ork-frame", { "is-off": !v.answered })} data-view=${v.slug} aria-label=${v.name}>
    <h4 class="shell-pitch__who"><${WhoHead} head=${v.head} /> ${v.name}${v.size && html`<span class="board-size kit-well" title="How big it is, as the Engineering view reads it">${v.size}</span>`}</h4>
    ${v.answered ? html`<span class="ok-font-label">For</span><${List} items=${v.for} label="For" />
      <span class="ok-font-label">Against</span><${List} items=${v.against} label="Against" />
      ${v.question && html`<p class="shell-pitch__q"><span class="ok-tone-muted">Asks:</span> ${v.question}</p>`}`
      : html`<p class="ok-tone-muted">${judging ? "Reading it…" : "No answer yet."}</p>`}
  </section>`;
}

/** The Skeptic's case against it, and the kill reasons it names. */
function Case({ p }) {
  const c = p.case;
  return html`<section class="shell-goal__sec shell-pitch__case" aria-label="The case against" data-sec="case">
    <h3 class="board-sub"><${WhoHead} head=${p.skeptic?.head} small /> The case against</h3>
    ${c ? html`<p class="shell-pitch__words">${c.case}</p>
      ${c.kills.length > 0 && html`<ul class="shell-pitch__kills" aria-label="Its kill reasons">${c.kills.map((k) => html`<li key=${k.id} data-kill=${k.id}><${Sign} name="cross" /> ${k.words}</li>`)}</ul>`}`
      : html`<p class="ok-tone-muted">${p.state === "judging" ? `${p.skeptic?.name || "The Skeptic"} makes it once the four views have answered.` : "Not made yet."}</p>`}
  </section>`;
}

/** The Investor's decision: the answer large, why, the kill reasons, where and as what, the first step, the cheapest test, the goal it repeats. */
function Decision({ p }) {
  const d = p.decision, who = p.investor?.name || "The Investor";
  if (!d) {
    return html`<section class="shell-goal__sec shell-pitch__decision" aria-label="Decision" data-sec="decision">
      <h3 class="board-sub"><${WhoHead} head=${p.investor?.head} small /> Decision</h3>
      <p class="ok-tone-muted">${p.state === "judging" ? `${who} decides after the case against.` : "None yet."}</p></section>`;
  }
  const where = whereWords(d);
  return html`<section class="shell-goal__sec shell-pitch__decision" aria-label="Decision" data-sec="decision" data-answer=${d.answer}>
    <h3 class="board-sub"><${WhoHead} head=${p.investor?.head} small /> Decision</h3>
    <p class="shell-pitch__answer" data-answer=${d.answer}>${d.word}</p>
    ${d.reshaped && html`<p class="ok-tone-muted">${who} said invest; its kill reasons made it a reshape.</p>`}
    <span class="ok-font-label">Why</span><${List} items=${d.why} label="Why" />
    ${d.kills.length > 0 && html`<span class="ok-font-label">Kill reasons</span>
      <ul class="shell-pitch__kills" aria-label="Kill reasons">${d.kills.map((k) => html`<li key=${k.id} data-kill=${k.id}><${Sign} name="cross" /> ${k.words}</li>`)}</ul>`}
    <dl class="shell-facts shell-pitch__facts">
      ${where && html`<dt>Where</dt><dd data-fact="where">${where}</dd>`}
      ${d.first && html`<dt>First step</dt><dd data-fact="first">${d.first}</dd>`}
      ${d.test && html`<dt>Cheapest test</dt><dd data-fact="test">${d.test}</dd>`}
      ${d.like && html`<dt>It repeats</dt><dd data-fact="like"><button type="button" class="board-link" onClick=${() => showIdea(d.like.slug)}>${d.like.title}</button></dd>`}
    </dl>
  </section>`;
}

/** Sent, passed, and the decisions there were before it was judged again. */
function After({ p }) {
  return html`${p.sent && html`<p class="shell-pitch__after" data-after="sent"><${Sign} name="check" /> ${sentWords(p.sent)}${p.sent.goal && html` · <button type="button" class="board-link" onClick=${() => showIdea(p.sent.goal)}>Open the goal</button>`}</p>`}
    ${p.passed && html`<p class="shell-pitch__after" data-after="passed">Passed${p.passed.why ? html`: <span class="shell-pitch__words">${p.passed.why}</span>` : ""}</p>`}
    ${p.before?.length > 0 && html`<details class="shell-pitch__before"><summary>Before (${p.before.length})</summary>
      <ul class="shell-pitch__list">${p.before.map((d, i) => html`<li key=${i}><b>${d.word}</b>${d.why?.length ? ` · ${d.why.join(" ")}` : ""}</li>`)}</ul></details>`}`;
}

/** **Send to <party>** with its select: the decision's party first. A party of the library the project lacks opens New party with it. */
function Send({ slug, d }) {
  const targets = sendTargets(mapData.value, d);
  const [to, setTo] = useState(() => sendDefault(targets, d));
  const [busy, setBusy] = useState(false);
  const t = targets.find((x) => x.slug === to);
  const send = async () => {
    if (!t || busy) return;
    if (t.preset) { openDialog("goal", { preset: t.slug }); return; }        // A's refusal (*Make the <name> party first*): New party with that preset
    setBusy(true);
    const got = await act("ideas.pitch_send", { slug, party: t.slug, via: "pitch" });
    setBusy(false);
    if (got?.slug) toast(`Sent: a new goal in ${t.name}, drafted now.`);
  };
  if (!targets.length) return html`<p class="ok-tone-muted">No party to send it to yet: make one first.</p>`;
  return html`<span class="shell-pitch__send">
    <select class="ork-field" aria-label="Send to party" value=${to} onChange=${(e) => setTo(e.target.value)}>
      ${targets.map((x) => html`<option key=${x.slug} value=${x.slug}>${x.name}${x.preset ? " (make it first)" : ""}</option>`)}</select>
    <button type="button" class="ork-btn primary" disabled=${busy || !t} title=${t?.preset ? `${t.name} is not a party of this project yet: this opens New party with it` : "A new goal in that party, drafted now; the pitch is sent"}
      onClick=${send}>Send to ${t?.name || "…"}</button></span>`;
}

/** The buttons at the foot, by the pitch's state; Change and Pass open their one line in place. */
function Actions({ pg, p }) {
  const [mode, setMode] = useState("");                 // "" · "change" · "pass" · "drop"
  const [text, setText] = useState("");
  const [why, setWhy] = useState("");
  const slug = pg.slug, st = p.state, words = (pg.sections || []).find((s) => s.name === "Gist")?.text || "";
  const drop = async () => { if (await act("ideas.drop", { slug })) closePreview(); };
  const again = async () => { if (await act("ideas.pitch_again", { slug, text: text.trim() || words, via: "pitch" })) { setMode(""); toast("Judged again: the four views read it now."); } };
  const pass = async () => { if (await act("ideas.pitch_pass", { slug, ...(why.trim() ? { why: why.trim() } : {}), via: "pitch" })) { setMode(""); toast("Passed: kept with its why; the next pitch like it is judged against it."); } };
  const judge = () => act("ideas.judge", { slug, via: "pitch" });
  if (mode === "change") {
    return html`<div class="shell-pitch__edit"><textarea class="ork-field" rows="4" autofocus value=${text} maxlength="2000" aria-label="The pitch, changed" onInput=${(e) => setText(e.target.value)}></textarea>
      <div class="board-row"><button type="button" class="ork-btn primary" disabled=${!text.trim()} title="Its words changed, judged anew; the decision there was is kept" onClick=${again}>Judge it again</button>
        <button type="button" class="ork-btn" onClick=${() => setMode("")}>Cancel</button></div></div>`;
  }
  if (mode === "pass") {
    return html`<div class="board-row shell-pitch__pass"><input class="ork-field" autofocus value=${why} maxlength="300" aria-label="Why you pass" placeholder="Why not? (optional, one line)"
        onInput=${(e) => setWhy(e.target.value)} onKeyDown=${(e) => { if (e.key === "Enter") pass(); }} />
      <button type="button" class="ork-btn primary" title="Kept with its why: every later pitch is judged against it" onClick=${pass}>Pass it</button>
      <button type="button" class="ork-btn" onClick=${() => setMode("")}>Cancel</button></div>`;
  }
  if (mode === "drop") {
    return html`<div class="board-row"><span>Drop this pitch and its page? Its views and its decision go too.</span>
      <button type="button" class="ork-btn danger" onClick=${drop}>Drop it</button><button type="button" class="ork-btn" onClick=${() => setMode("")}>Keep it</button></div>`;
  }
  const change = html`<button type="button" class="ork-btn" title="Change its words, then the four views read it anew" onClick=${() => { setText(words); setMode("change"); }}>Change and judge again</button>`;
  const dropBtn = html`<button type="button" class="ork-btn danger" title="The pitch and its page go" onClick=${() => setMode("drop")}>Drop</button>`;
  if (st === "judging") return html`<p class="ok-tone-muted">Being judged: the views answer one by one.</p>`;
  return html`<div class="board-row shell-pitch__acts">
    ${st === "judged" && html`<${Send} slug=${slug} d=${p.decision} />${change}
      <button type="button" class="ork-btn" title="Kept with its why: every later pitch is judged against it" onClick=${() => setMode("pass")}>Pass</button>`}
    ${st === "failed" && html`<button type="button" class="ork-btn primary" title="The views, the case against and the decision are asked again" onClick=${judge}>Try again</button>${change}`}
    ${st === "passed" && html`<button type="button" class="ork-btn primary" title="Judged anew, as it is: the four views read it again" onClick=${() => act("ideas.pitch_again", { slug, via: "pitch" })}>Judge again</button>`}
    ${st === "raw" && html`<button type="button" class="ork-btn primary" title="The four views read it now" onClick=${judge}>Judge now</button>`}
    ${dropBtn}</div>`;
}

export function PitchView({ pg }) {
  const p = pg.pitch, words = (pg.sections || []).find((s) => s.name === "Gist")?.text || "";
  const node = (mapData.value?.nodes || []).find((n) => n.slug === pg.slug);
  const line = pitchWords({ ...(node || {}), ...pg, pitch: p });
  return html`<div class="shell-result"><div class="shell-result__body shell-goal shell-pitch" data-state=${p.state}>
    <div class="board-bar"><span class="shell-ptab__kind">Pitch</span><span class="board-state" data-state=${p.state}>${line}</span></div>
    <div class="shell-goal__head"><h2>${pg.title}</h2><span class="ok-tone-muted">${PITCH_STATE[p.state] || ""}</span></div>
    ${p.state === "failed" && pg.state_error && html`<${ErrorLine} text=${pg.state_error} />`}
    <section class="shell-goal__sec" aria-label="The pitch" data-sec="pitch"><h3 class="board-sub">The pitch</h3>
      <p class="shell-brief shell-pitch__words">${words || html`<span class="ok-tone-muted">No words.</span>`}</p>
      <${PointedAt} lens=${pg.lens} /></section>
    <section class="shell-goal__sec" aria-label="The views" data-sec="views"><h3 class="board-sub">The views</h3>
      <div class="shell-pitch__views">${(p.views || []).map((v) => html`<${View} key=${v.slug} v=${v} judging=${p.state === "judging"} />`)}</div></section>
    <${Case} p=${p} />
    <${Decision} p=${p} />
    <${After} p=${p} />
  </div>
  <footer class="shell-result__foot"><${Actions} key=${`${pg.slug}:${p.state}`} pg=${pg} p=${p} /></footer></div>`;
}
