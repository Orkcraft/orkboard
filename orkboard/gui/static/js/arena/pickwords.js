// Pick one's words (docs/specs/51-pick-one.md §0, §5, §6): pure functions over the Needs you row of kind `pick` (`ideas.board`'s `needs_you`: the task, its ask,
// its member, the kind of media and the variants with their signed addresses). No signal and no template here; picks.js (the tiles), stops.js (the stop along
// the bottom) and shell/pickview.js (the drawer's Pick one) draw what these say.

/** A kind's word: one, many (*4 pictures*, *3 sounds*, *2 clips*, *3 texts*). */
export const MEDIA = { image: ["picture", "pictures"], audio: ["sound", "sounds"], video: ["clip", "clips"], text: ["text", "texts"] };

export const NEEDS_NOTE = "A note says what to change: write one first";
export const NONE = "None of them: make new ones";

/** *4 pictures*. */
export function kindCount(row) {
  const [one, many] = MEDIA[row.media] || ["variant", "variants"];
  return `${row.n} ${row.n === 1 ? one : many}`;
}
/** What a pick's variants are called, many of them: *pictures*, *sounds*, *clips*, *texts*. */
export const manyWords = (row) => (MEDIA[row.media] || ["", "variants"])[1];
/** The group's name for a screen reader: *The pictures*. */
export const groupWords = (row) => `The ${manyWords(row)}`;
/** A variant's label: *B · monogram*. */
export const labelOf = (v) => `${v.key} · ${v.name}`;
/** The button that takes the picked one (*Take B*), or says what it waits for. */
export const takeWords = (key) => (key ? `Take ${key}` : "Take the one you pick");
/** *Say why, or what to change (it goes to Screens)*. */
export const noteWords = (by) => `Say why, or what to change (it goes to ${by?.name || "the one who made them"})`;
/** *3 s* of a sound or a clip as *0:03*; "" when the length is not known. */
export function lengthWords(seconds) {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "";
  const s = Math.round(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** A picture that is 64 px or less on its side is pixel art: drawn crisp (`image-rendering: pixelated`); never an SVG, never a larger one (§5). */
export const PIXEL_MAX = 64;
export const isPixel = (mime, w, h) => mime !== "image/svg+xml" && w > 0 && h > 0 && Math.max(w, h) <= PIXEL_MAX;
/** A picture is never drawn more than twice its size (§5); a vector has no size to keep. */
export const UPSCALE_MAX = 2;
export const isCapped = (mime, w, h) => mime !== "image/svg+xml" && w > 0 && h > 0;

/** The variant of a row with this key, null when there is none. */
export const variantOf = (row, key) => (row?.variants || []).find((v) => v.key === key) || null;

/** The pick row of a task among the Needs you rows, null when it is answered. */
export const rowOf = (needs, slug, task) => (needs || []).find((n) => n.kind === "pick" && n.slug === slug && n.task === task) || null;
