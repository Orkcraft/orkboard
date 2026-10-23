// A spend as the page says it (decisions §81): on Claude's subscription, its share of the five-hour window, estimated from
// its ≈$ at API prices over the rate the host learnt (sources/window_rate.py, the snapshot's `rate`). With no rate learnt
// (an API key, the first window not yet read) every helper says "" and its caller says the $ as before.
import { town } from "./link.js";

export const SHARE_TIP = "An estimate: its cost at API prices over what 1 % of Claude's five-hour window has cost on this machine";

const per = () => Number(town.value?.rate?.usd_per_pct) || 0;
const pct = (n) => (n === 0 ? "0" : n < 1 ? "<1" : String(Math.round(n)));
const ok = (n) => n != null && n !== "" && Number.isFinite(Number(n));

/** Whether a rate is learnt: the page says spends as shares of the window (and its hints say SHARE_TIP). */
export const rated = () => per() > 0;

/** *12 % of 5h* for $ at API prices (the caller adds its *≈* as it did to its $); "" with no rate (or no number). */
export const pctOf = (usd) => (rated() && ok(usd) ? `${pct(Math.abs(Number(usd)) / per())} % of 5h` : "");

/** *3 %*, for a part beside a whole said with pctOf; "" with no rate. */
export const pctShort = (usd) => (rated() && ok(usd) ? `${pct(Math.abs(Number(usd)) / per())} %` : "");

/** *3–8 % of 5h* for a range of $; "" with no rate. */
export function pctRange(low, high) {
  if (!rated() || !ok(low) || !ok(high)) return "";
  const a = pct(Number(low) / per()), b = pct(Number(high) / per());
  return a === b ? `${a} % of 5h` : `${a}–${b} % of 5h`;
}

/** *+3 % of 5h*, *−1–4 % of 5h*, *−1 to +3 % of 5h* for a change of $; "" with no rate. */
export function pctDelta(low, high) {
  if (!rated() || !ok(low) || !ok(high)) return "";
  if (low < 0 && high > 0) return `−${pct(-low / per())} to +${pct(high / per())} % of 5h`;
  const [x, y] = [Math.abs(low), Math.abs(high)].sort((m, n) => m - n), a = pct(x / per()), b = pct(y / per());
  return `${low < 0 || high < 0 ? "−" : "+"}${a === b ? a : `${a}–${b}`} % of 5h`;
}
