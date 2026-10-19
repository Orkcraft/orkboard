// New idea's field on the phone, beyond its text: the goal's words to complete with (a row of them under the text, from
// `ideas.words`: a tap puts the word in place of the one being typed and a space after it), Photo (the camera or the
// library; each made a JPEG of at most MAX_PX before it goes, for the Taskmaster to read) and Speak (the browser's own
// speech to text, where it has one: the words go into the text as they are said).
import { h } from "./util.js";

const MAX_PX = 1600;
const MAX_PHOTOS = 4;                    // realm/idea_photos.py MAX_PHOTOS
const SHOWN = 6;                         // the words offered at once
const MIN_TYPED = 2;                     // letters typed before words are offered
const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;

/** A photo as a JPEG data URL of at most MAX_PX on its longer side. */
async function shrink(file) {
  const url = await new Promise((ok, fail) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = fail; r.readAsDataURL(file); });
  const img = new Image();
  img.src = url;
  await img.decode();
  const k = Math.min(1, MAX_PX / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.naturalWidth * k);
  canvas.height = Math.round(img.naturalHeight * k);
  canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.8);
}

/** The word being typed at the caret: {start, end, text}. */
export function typing(value, caret) {
  const before = value.slice(0, caret);
  const start = before.search(/\S*$/);
  return { start, end: caret, text: before.slice(start) };
}

/** The words that complete `typed` (case aside), in their order, not the word itself. */
export function completing(words, typed, n = SHOWN) {
  const low = typed.toLowerCase();
  if (low.length < MIN_TYPED) return [];
  return words.filter((w) => { const l = w.toLowerCase(); return l.startsWith(low) && l !== low; }).slice(0, n);
}

/** `text`: the idea's textarea. Returns {el, track(slug), photos(), reset()}. */
export function makeIdeaField(ctx, text) {
  let words = [];
  let wordsOf = "";
  let seq = 0;
  const strip = h("div", { class: "idea-words", role: "group", "aria-label": "Words to complete with", hidden: true });
  function offer() {
    const t = typing(text.value, text.selectionStart ?? text.value.length);
    const got = completing(words, t.text);
    strip.hidden = !got.length;
    strip.replaceChildren(...got.map((w) => h("button", { class: "word-chip", type: "button", "aria-label": `Complete with ${w}`,
      onpointerdown: (e) => e.preventDefault(),                       // the text keeps the focus: the keyboard stays up
      onclick: () => { const now = typing(text.value, text.selectionStart ?? text.value.length);
        text.setRangeText(`${w} `, now.start, now.end, "end");
        text.dispatchEvent(new Event("input", { bubbles: true }));
        text.focus(); } }, w)));
  }
  text.addEventListener("input", offer);
  text.addEventListener("click", offer);
  text.addEventListener("keyup", (e) => { if (e.key.startsWith("Arrow")) offer(); });

  // -- Photo --------------------------------------------------------------------------------------------------------
  let photos = [];                                   // data URLs
  const pick = h("input", { type: "file", accept: "image/*", multiple: true, hidden: true, "aria-label": "Photos to attach" });
  const photoBtn = h("button", { class: "ork-btn", type: "button", onclick: () => pick.click() }, "Photo");
  const thumbs = h("div", { class: "idea-photos", hidden: true });
  function drawPhotos() {
    thumbs.hidden = !photos.length;
    photoBtn.disabled = photos.length >= MAX_PHOTOS;
    thumbs.replaceChildren(...photos.map((url, i) => h("div", { class: "idea-photo" }, h("img", { src: url, alt: `Photo ${i + 1}` }),
      h("button", { class: "ork-btn", type: "button", "aria-label": `Remove photo ${i + 1}`, onclick: () => { photos.splice(i, 1); drawPhotos(); } }, "×"))));
  }
  pick.addEventListener("change", async () => {
    const files = [...pick.files].slice(0, MAX_PHOTOS - photos.length);
    pick.value = "";
    for (const f of files) {
      try { photos.push(await shrink(f)); } catch { ctx.flash("That photo could not be read: try another."); }
    }
    if (pick.files?.length > files.length) ctx.flash(`At most ${MAX_PHOTOS} photos go with an idea.`);
    drawPhotos();
  });

  // -- Speak: the browser's speech to text, put in at the caret as it is heard --------------------------------------
  let rec = null;
  const speak = h("button", { class: "ork-btn", type: "button", hidden: !Speech, "aria-pressed": "false" }, "Speak");
  function stopSpeaking() { if (rec) rec.stop(); }
  speak.addEventListener("click", () => {
    if (rec) { stopSpeaking(); return; }
    const at = text.selectionStart ?? text.value.length;
    const before = text.value.slice(0, at), after = text.value.slice(at);
    const gap = before && !/\s$/.test(before) ? " " : "";
    rec = new Speech();
    rec.lang = navigator.language || "en-US";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e) => {
      const said = [...e.results].map((r) => r[0].transcript).join("").trim();
      text.value = `${before}${said ? gap + said : ""}${after}`;
      text.dispatchEvent(new Event("input", { bubbles: true }));
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") ctx.flash("Orkline may not use the microphone: allow it in the phone’s settings for this browser.");
      else if (e.error !== "no-speech" && e.error !== "aborted") ctx.flash("Speech stopped: type it, or use the keyboard’s microphone.");
    };
    rec.onend = () => { rec = null; speak.textContent = "Speak"; speak.setAttribute("aria-pressed", "false"); speak.classList.remove("is-on"); };
    try {
      rec.start();
      speak.textContent = "Stop";
      speak.setAttribute("aria-pressed", "true");
      speak.classList.add("is-on");
    } catch { rec = null; ctx.flash("Speech could not start: type it, or use the keyboard’s microphone."); }
  });

  const el = h("div", { class: "idea-field-more" }, strip, h("div", { class: "row idea-tools" }, photoBtn, speak, pick), thumbs);
  return {
    el,
    speaks: Boolean(Speech),
    /** The goal whose words are offered: read once per goal while the sheet is open. */
    async track(slug) {
      if (!slug || slug === wordsOf) return;
      wordsOf = slug;
      words = [];
      const mine = ++seq;
      const r = await ctx.send("ideas.words", { track: slug });
      if (mine === seq && r.ok && Array.isArray(r.result?.words)) { words = r.result.words; offer(); }
    },
    /** The photos to send with the idea, as `ideas.add` takes them. */
    photos: () => photos.map((url) => ({ data: url.slice(url.indexOf(",") + 1) })),
    reset() { stopSpeaking(); photos = []; wordsOf = ""; drawPhotos(); strip.hidden = true; },
    stop: stopSpeaking,
    /** Speak at once (the button that opened the sheet was the tap the microphone needs). */
    listen() { if (Speech && !rec) speak.click(); },
  };
}
