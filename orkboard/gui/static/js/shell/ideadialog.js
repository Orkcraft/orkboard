// New goal (docs/specs/50-parties-and-goals.md §3.3, §3.7; spec 35 §3): the card turned over from the pile — the element the goal will get (`.ork-elem.big`: the
// host's rule over the party's open goals, so it is what `ideas.add` answers), the text, the party (required: the one chosen on the board, else the first by priority;
// General is not listed), the lens of the party (lens.js: what the goal points at, beside its text) and the priority (default the party's). *Add the goal* adds it;
// *Put it back* closes the dialog — closed with text in it, the goal goes to tonight's queue (never lost); closed empty it adds nothing. The code's idea is a goal.
// Its head is *Your own goal* (docs/specs/61-your-own-goal.md: the goal in the person's words, `BlankGoal`).
// **By its type** (docs/specs/52-goal-types.md §4.2, §4.3): the type's sign and name in place of *Your own goal*, the party fixed (a type is its leader's), *Its
// title*, *What it is for*, the type's asks (one line each, none required), **Refs** when the type has them (*Links*; *Pictures you like*: a file, a paste or a drop,
// sent as `photos`), the lens (the type's first), **the join line** (arena/types.js: who joins, or a swap) and the priority. *Add the goal* sends `type`, `asks`
// and, when the join line is ticked, `join`; a goal kept for tonight never brings anyone.
// **In Ideation** (docs/specs/65-ideation.md §8) a goal is a pitch: one box, the lens, **Judge now** · **Tonight** · **Hold** (`PitchGoal`).
import { useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { goalList, track, PRIORITY_WORDS } from "../board/store.js";
import { act, mapData } from "./store.js";
import { Modal, closeDialog } from "./modals.js";
import { Lens, lensFirst, lensValue, noLens, useLenses } from "./lens.js";
import { Elem, Sign } from "../orkui.js";
import { nextElement } from "../arena/goalwords.js";
import { JoinLine, joinSet, joinStart, joinValue } from "../arena/types.js";
import { isIdeation } from "../arena/pitchwords.js";

const MAX_PICTURES = 4;                     // realm/idea_photos.py MAX_PHOTOS
const MAX_PX = 1600;                        // as the phone's (pwa/shell-idea-field.js): a JPEG of at most this, for the leader to read
const PICTURE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];
const REFS = "refs";                        // realm/goal_types.py REFS: the id of Refs' links among a goal's asks

export function IdeaDialog({ goal = "", type = null }) {
  return type ? html`<${TypedGoal} goal=${goal} type=${type} />` : html`<${BlankGoal} goal=${goal} />`;
}

function BlankGoal({ goal: first = "" }) {
  const parties = goalList();
  const [text, setText] = useState("");
  const [party, setParty] = useState(first || (parties.some((g) => g.slug === track.value) ? track.value : parties[0]?.slug) || "");
  const [mine, setMine] = useState("");                      // the person's own priority; "" = the party's
  const [busy, setBusy] = useState(false);
  const [lens, setLens] = useState(noLens);
  const info = useLenses(party);
  const priority = mine || parties.find((g) => g.slug === party)?.priority || "normal";
  const element = nextElement((mapData.value?.nodes || []).filter((n) => n.goal === party));
  const send = async () => {
    const t = text.trim();
    if (!t || !party || busy) return;
    setBusy(true);
    const pointed = lensValue(info, lens);
    const got = await act("ideas.add", { text: t, track: party, priority, ...(pointed.length ? { lens: pointed } : {}) });
    setBusy(false);
    if (got?.slug) closeDialog();
  };
  const close = async () => {                 // closed with text in it: tonight's queue
    const t = text.trim();
    closeDialog();
    const pointed = lensValue(info, lens);
    if (t && party) await act("ideas.add", { text: t, track: party, priority, night: true, ...(pointed.length ? { lens: pointed } : {}) });
  };
  if (isIdeation(mapData.value, party)) {
    return html`<${PitchGoal} parties=${parties} party=${party} setParty=${(p) => { setParty(p); setMine(""); }} text=${text} setText=${setText} info=${info} lens=${lens} setLens=${setLens} />`;
  }
  return html`<${Modal} title="New goal" onClose=${close} wide=${(info?.lenses || []).length > 1}
    foot=${html`<button type="button" class="ork-btn" onClick=${close}>Put it back</button>
      <button type="button" class="ork-btn primary" disabled=${!text.trim() || !party || busy} onClick=${send}
        title=${say("Add it: the Taskmaster drafts it at once, or tonight when its priority is Low")}>Add the goal</button>`}>
    <div class="shell-form">
      <div class="shell-blank" data-element=${element}><${Elem} name=${element} big=${true} /><b>Your own goal</b></div>
      <label class="shell-field"><span class="ok-font-label">Your goal</span>
        <textarea class="ork-field" rows="4" autofocus value=${text} aria-label="Your goal" placeholder="Your goal, in a few words or a few lines"
          onInput=${(e) => setText(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } }}></textarea></label>
      <label class="shell-field"><span class="ok-font-label">Belongs to party</span>
        <select class="ork-field" aria-label="Party" value=${party} onChange=${(e) => { setParty(e.target.value); setMine(""); }}>
          ${parties.map((g) => html`<option key=${g.slug} value=${g.slug}>${g.title}</option>`)}</select></label>
      <${Lens} info=${info} s=${lens} set=${setLens} />
      <label class="shell-field"><span class="ok-font-label">Priority</span>
        <select class="ork-field" aria-label="Priority" value=${priority} onChange=${(e) => setMine(e.target.value)}>
          ${Object.entries(PRIORITY_WORDS).map(([id, name]) => html`<option key=${id} value=${id}>${name}</option>`)}</select></label>
      <p class="ok-font-status ok-tone-muted">${say("High and Normal: the Taskmaster drafts it at once. Low: tonight. Closing this with text in it adds it to tonight's queue.")}</p>
    </div>
  <//>`;
}

const PITCH_CHARS = 2000;                   // realm/pitches.py PITCH_CHARS: a pitch's words

/** New goal in Ideation (docs/specs/65-ideation.md §8): a pitch, one box (*What is the pitch?*), the lens a tap away, then **Judge now** (`ideas.add` at once: the
 *  four views read it now), **Tonight** (`night`) or **Hold** (`hold`: kept till the person judges it). No type, no asks, no priority. Closed with words in it, it is
 *  kept for tonight, as any goal. The text, the party and the lens are BlankGoal's, so a party picked in its select moves the words over. */
function PitchGoal({ parties, party, setParty, text, setText, info, lens, setLens }) {
  const [busy, setBusy] = useState(false);
  const g = parties.find((x) => x.slug === party);
  const lead = "the Investor";                         // Ideation's leader, always (realm/goal_team.py)
  const args = (more) => {
    const pointed = lensValue(info, lens);
    return { text: text.trim(), track: party, priority: g?.priority === "high" ? "high" : "normal", ...(pointed.length ? { lens: pointed } : {}), ...more };
  };
  const send = async (more) => {
    if (!text.trim() || busy) return;
    setBusy(true);
    const got = await act("ideas.add", args(more));
    setBusy(false);
    if (got?.slug) closeDialog();
  };
  const close = async () => {                 // closed with words in it: tonight's, never lost
    closeDialog();
    if (text.trim()) await act("ideas.add", args({ night: true }));
  };
  const off = !text.trim() || busy;
  return html`<${Modal} title="New goal" onClose=${close} wide=${(info?.lenses || []).length > 1}
    foot=${html`<button type="button" class="ork-btn" disabled=${off} title="Kept as it is: it is judged when you say" onClick=${() => send({ hold: true })}>Hold</button>
      <button type="button" class="ork-btn" disabled=${off} title="The night judges it, before any other work" onClick=${() => send({ night: true })}>Tonight</button>
      <button type="button" class="ork-btn primary" disabled=${off} title=${`The four views read it now, then the Skeptic and ${lead}`} onClick=${() => send({})}>Judge now</button>`}>
    <div class="shell-form arena-pitchform" data-party=${party}>
      <div class="shell-blank"><${Sign} name="target" big=${true} /><b>A pitch</b></div>
      <label class="shell-field"><span class="ok-font-label">What is the pitch?</span>
        <textarea class="ork-field" rows="5" autofocus value=${text} maxlength=${PITCH_CHARS} aria-label="What is the pitch?"
          placeholder="In a few words or a few lines: what, and for whom" onInput=${(e) => setText(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send({}); } }}></textarea></label>
      <label class="shell-field"><span class="ok-font-label">Belongs to party</span>
        <select class="ork-field" aria-label="Party" value=${party} onChange=${(e) => setParty(e.target.value)}>
          ${parties.map((x) => html`<option key=${x.slug} value=${x.slug}>${x.title}</option>`)}</select></label>
      <${Lens} info=${info} s=${lens} set=${setLens} />
      <p class="ok-font-status ok-tone-muted">Four views read it, each alone: product, market, engineering and design; the Skeptic makes the case against it, then ${lead} invests in it, reshapes it or passes, and says why. Nothing is built.</p>
    </div>
  <//>`;
}

/** A picture the person likes, as `ideas.add`'s `photos` takes it: a JPEG of at most MAX_PX on its longer side, as a data URL. */
async function shrink(file) {
  const url = await new Promise((ok, fail) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = fail; r.readAsDataURL(file); });
  const img = new Image();
  img.src = url;
  await img.decode();
  const k = Math.min(1, MAX_PX / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(img.naturalWidth * k));
  canvas.height = Math.max(1, Math.round(img.naturalHeight * k));
  canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85);
}

/** Refs (§4.2): *Links*, one line; *Pictures you like*: *Add a picture* (a file), or a paste or a drop on the form; small thumbnails with ×. */
function Refs({ links, setLinks, pictures, pick }) {
  const file = useRef();
  return html`<div class="shell-field arena-refs"><span class="ok-font-label">Refs</span>
    <label class="shell-field"><span class="ok-font-label">Links</span>
      <input class="ork-field" maxlength="300" value=${links} aria-label="Links" placeholder="Pages or products you like, their links" onInput=${(e) => setLinks(e.target.value)} /></label>
    <span class="ok-font-label">Pictures you like</span>
    <div class="arena-refs__pics">
      ${pictures.list.map((url, i) => html`<span key=${i} class="arena-refs__pic"><img src=${url} alt=${`Picture ${i + 1}`} />
        <button type="button" class="ork-btn" aria-label=${`Remove picture ${i + 1}`} onClick=${() => pictures.drop(i)}>×</button></span>`)}
      <button type="button" class="ork-btn" disabled=${pictures.list.length >= MAX_PICTURES} onClick=${() => file.current?.click()}>Add a picture</button>
      <input ref=${file} type="file" accept=${PICTURE_TYPES.join(",")} multiple hidden onChange=${(e) => { pick([...e.target.files]); e.target.value = ""; }} />
    </div>
    <p class="ok-font-status ok-tone-muted">PNG, JPEG, WEBP or GIF: a file, or paste or drop one on this form.</p></div>`;
}

function TypedGoal({ goal: party, type: t }) {
  const g = goalList().find((x) => x.slug === party) || {};
  const shown = (mapData.value?.goals || []).find((x) => x.slug === party) || {};
  const leader = shown.leader?.slug && shown.leader.slug !== "taskmaster" ? shown.leader.name : "the Taskmaster";
  const [title, setTitle] = useState("");
  const [about, setAbout] = useState("");
  const [asks, setAsks] = useState({});
  const [links, setLinks] = useState("");
  const [list, setList] = useState([]);                      // Refs' pictures, as data URLs
  const [mine, setMine] = useState("");
  const [busy, setBusy] = useState(false);
  const [lens, setLens] = useState(() => lensFirst(t));
  const [join, setJoin] = useState(() => joinStart(t.missing));
  const info = useLenses(party);
  const priority = mine || g.priority || "normal";
  const element = nextElement((mapData.value?.nodes || []).filter((n) => n.goal === party));
  const text = [title.trim(), about.trim()].filter(Boolean).join("\n\n");          // the goal's text: its title is the first line of it

  const pick = async (files) => {
    const room = MAX_PICTURES - list.length, got = [];
    for (const f of files.filter((x) => PICTURE_TYPES.includes(x.type)).slice(0, Math.max(0, room))) {
      try { got.push(await shrink(f)); } catch { toast("That picture could not be read: try another.", "warning"); }
    }
    if (got.length) setList((now) => [...now, ...got].slice(0, MAX_PICTURES));
  };
  const pictures = { list, drop: (i) => setList((now) => now.filter((_, k) => k !== i)) };
  const paste = (e) => {
    const files = [...(e.clipboardData?.files || [])].filter((f) => PICTURE_TYPES.includes(f.type));
    if (!t.refs || !files.length) return;
    e.preventDefault();
    pick(files);
  };
  const drop = (e) => {
    if (!t.refs) return;
    e.preventDefault();
    pick([...(e.dataTransfer?.files || [])]);
  };

  const args = (night) => {
    const said = Object.fromEntries(Object.entries({ ...asks, ...(t.refs ? { [REFS]: links } : {}) }).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
    const pointed = lensValue(info, lens), joined = night ? null : joinValue(t.missing, join);
    const photos = t.refs ? list.map((url) => ({ data: url.slice(url.indexOf(",") + 1) })) : [];
    return { text, track: party, priority, type: t.id, ...(Object.keys(said).length ? { asks: said } : {}), ...(photos.length ? { photos } : {}),
      ...(pointed.length ? { lens: pointed } : {}), ...(joined ? { join: joined } : {}), ...(night ? { night: true } : {}) };
  };
  const send = async () => {
    if (!text || busy) return;
    setBusy(true);
    const got = await act("ideas.add", args(false));
    setBusy(false);
    if (!got?.slug) return;
    closeDialog();
    if (got.joined?.add) {
      const name = (t.missing || []).find((m) => m.agent === got.joined.add)?.name || got.joined.add;
      toast(`Added: ${name} joined the party; ${leader} drafts it now.`);
    }
  };
  const close = async () => {                 // closed with words in it: tonight's queue, with its type and asks, never with who joins
    closeDialog();
    if (text) await act("ideas.add", args(true));
  };
  return html`<${Modal} title="New goal" onClose=${close} wide=${true}
    foot=${html`<button type="button" class="ork-btn" onClick=${close}>Put it back</button>
      <button type="button" class="ork-btn primary" disabled=${!text || busy} onClick=${send}
        title=${`Add it: ${leader} drafts it at once, or tonight when its priority is Low`}>Add the goal</button>`}>
    <div class="shell-form arena-typed" data-type=${t.id} onPaste=${paste} onDragOver=${(e) => { if (t.refs) e.preventDefault(); }} onDrop=${drop}>
      <div><div class="arena-typed__head"><${Sign} name=${t.sign} big=${true} /><b>${t.name}</b></div>
        <p class="ok-font-status ok-tone-muted arena-typed__for">for ${g.title || shown.title || party} · ${leader} reads it next</p></div>
      <div class="arena-typed__el" data-element=${element}><${Elem} name=${element} big=${true} /><span class="ok-font-status ok-tone-muted">Its element marks every task of it.</span></div>
      <label class="shell-field"><span class="ok-font-label">Its title</span>
        <input class="ork-field" maxlength="120" autofocus value=${title} aria-label="Its title" placeholder="What should become possible" onInput=${(e) => setTitle(e.target.value)} /></label>
      <label class="shell-field"><span class="ok-font-label">What it is for</span>
        <textarea class="ork-field" rows="3" value=${about} aria-label="What it is for" placeholder="Who needs it, and how you will know it is done"
          onInput=${(e) => setAbout(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } }}></textarea></label>
      ${(t.asks || []).map((a) => html`<label key=${a.id} class="shell-field" data-ask=${a.id}><span class="ok-font-label">${a.label}</span>
        <input class="ork-field" maxlength="300" value=${asks[a.id] || ""} aria-label=${a.label} placeholder=${a.hint || ""}
          onInput=${(e) => setAsks((now) => ({ ...now, [a.id]: e.target.value }))} /></label>`)}
      ${t.refs && html`<${Refs} links=${links} setLinks=${setLinks} pictures=${pictures} pick=${pick} />`}
      <${Lens} info=${info} s=${lens} set=${setLens} />
      <${JoinLine} missing=${t.missing} state=${join} set=${(i, patch) => setJoin((now) => joinSet(now, i, patch))} />
      <label class="shell-field"><span class="ok-font-label">Priority</span>
        <select class="ork-field" aria-label="Priority" value=${priority} onChange=${(e) => setMine(e.target.value)}>
          ${Object.entries(PRIORITY_WORDS).map(([id, name]) => html`<option key=${id} value=${id}>${name}</option>`)}</select></label>
      <p class="ok-font-status ok-tone-muted">High and Normal: ${leader} drafts it at once. Low: tonight. Closing this with words in it keeps it for tonight, and no one joins.</p>
    </div>
  <//>`;
}
