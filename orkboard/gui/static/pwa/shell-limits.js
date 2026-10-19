// What is left of the AI tools, said where a choice spends them (New goal, Take, Take it to work, Start): one muted line, the tools'
// own words in the top bar's sheet. The top bar shows its chip only when a tool is low (WARN) or its limits were not read.
import { h } from "./util.js";

export const WARN = 0.2;
export const DANGER = 0.05;
export const pct = (left) => `${Math.round(left * 100)} %`;
export const levelOf = (left) => (left <= DANGER ? "is-danger" : left <= WARN ? "is-warn" : "");

/** "What is left: Claude 62 % · Antigravity 15 %" ("" when no tool's limits are read). */
export function limitsLine(snap) {
  const tools = (snap?.limits || []).filter((l) => typeof l.left === "number");
  return tools.length ? `What is left: ${tools.map((l) => `${l.name} ${pct(l.left)}`).join(" · ")}` : "";
}

/** The line as a node, warning when a tool is low (null when there is none). */
export function limitsNote(snap) {
  const line = limitsLine(snap);
  if (!line) return null;
  const low = (snap.limits || []).some((l) => typeof l.left === "number" && l.left <= WARN);
  return h("p", { class: `muted limits-note${low ? " is-warn" : ""}` }, line);
}
