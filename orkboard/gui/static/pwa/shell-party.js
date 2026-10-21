// The party's sheet, its gate and the flag line (docs/specs/50-parties-and-goals.md §6.2, §6.8). **About this party** (a sheet, opened from the Goals sheet's head: *About Tech ›*): What it is for, The party,
// Checks on every goal, What it costs (what it did so far and its price a goal), Its flags, and for a party with a verdict of before, *Before: …*; *Edit the party*, *Add to the party* and *Save it to your
// parties*. The gate, quiet (no green) at the right of the goals bar: *dev → main* with its count, or *main ✓* (disabled) when main is up to date. After a gate's merge that raised flags, **the flag line**
// stands under the goals bar, once per device (`localStorage` `orkcraft.flags.goals`): *⚑ 3 flags raised · <a>, <b> and 1 more are in main*, its × 44 px; a press on it opens About this party at *Its flags*.
import { h, icon, sheet } from "./util.js";
import { sign } from "./shell-marks.js";
import { modelOf } from "./shell-arena-words.js";
import { savePartyEl } from "./shell-goal.js";
import { flagWords as oldFlagWords } from "./shell-map.js";
import { FLAGS_SHOWN, flagLine, flagTally, flagsOf, freshFlags, priceRange } from "./shell-goals-words.js";

const SEEN = "orkcraft.flags.goals";                  // {project: the newest flag's time this phone has seen, in ms}: the flag line is said once
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** *2 free seats in this party*, or *the party is full: change a member*. */
export function seatWords(free) {
  return free ? `${free} free ${free === 1 ? "seat" : "seats"} in this party` : "the party is full: change a member";
}
const BAND_WORDS = { lead: "leads", build: "builds", check: "checks" };
const UNIT = { lead: "a plan", build: "a result", check: "a goal" };

const seenOf = (project) => { try { const v = JSON.parse(localStorage.getItem(SEEN) || "{}")[project]; return typeof v === "number" ? v : null; } catch { return null; } };
const keepSeen = (project, ms) => {
  try { localStorage.setItem(SEEN, JSON.stringify({ ...(JSON.parse(localStorage.getItem(SEEN) || "{}")), [project]: ms })); } catch { /* said again next time */ }
};

/** `core`: the board's frame (st, open, call, editGoal); `ctx`: {send}. Returns {sheets, bar(model), line(slug), watch(), open(slug, at)}. */
export function makeParty(core, ctx) {
  const st = core.st;
  const body = h("div", { class: "party-about" });
  const sh = sheet("About this party", body);
  let shown = "", got = null, allFlags = false;       // the party the sheet is about, what `ideas.goal` read of it, whether every flag is listed
  const asking = new Set();

  // -- the party's price a goal (`ideas.party_price`), asked once for a party as it stands --------------------------------------------------------------
  const priceKey = (g) => JSON.stringify([g.leader?.slug || "taskmaster", (g.team || []).map((m) => m.slug), (g.team || []).filter((m) => m.every).map((m) => m.slug), g.craft || ""]);
  function wantPrice(g) {
    const key = priceKey(g);
    st.prices = st.prices || {};
    if (key in st.prices || asking.has(key)) return;
    asking.add(key);
    const args = { leader: g.leader?.slug || "taskmaster", team: (g.team || []).map((m) => m.slug), every: (g.team || []).filter((m) => m.every).map((m) => m.slug), ...(g.craft ? { craft: g.craft } : {}) };
    ctx.send("ideas.party_price", args).then((r) => {
      asking.delete(key);
      st.prices[key] = r.ok && r.result && !r.result.error ? { low: r.result.low, high: r.result.high } : null;
      core.draw();
      if (sh.el.open) draw();
    });
  }
  const priceOf = (g) => (st.prices || {})[priceKey(g)] || null;

  // -- the gate, quiet ---------------------------------------------------------------------------------------------------------------------------------
  function gateBox() {
    const g = st.gate;
    if (!g || g.same || !g.main) return null;                  // dev and main are one branch: there is no gate
    const n = (g.ideas || []).length, off = !g.commits && !n;
    const words = off ? "main is up to date" : `${n ? plural(n, "goal") : plural(g.commits, "commit")} in ${g.into} wait for ${g.main}`;
    return h("button", { class: "gbar__gate gate__btn", type: "button", disabled: off, title: words, "aria-label": `${g.into} → ${g.main}: ${words}${off ? "" : ". Open the gate"}`,
      "data-act": "gate", onclick: () => core.open({ kind: "gate" }, "gate") },
    ...(off ? [g.main, sign("check")] : [g.into, sign("after"), g.main, h("span", { class: "ork-count" }, String(n || g.commits))]));
  }

  // -- About this party --------------------------------------------------------------------------------------------------------------------------------
  function draw() {
    const g = (st.map?.goals || []).find((x) => x.slug === shown);
    const m = g ? modelOf(st, shown) : null;
    if (!g || !m) { body.replaceChildren(h("p", { class: "muted" }, "That party is gone.")); return; }
    wantPrice(g);
    const sec = (name, ...kids) => h("section", { class: "party-about__sec", "aria-label": name, "data-sec": name }, h("h3", {}, name), ...kids);
    const line = (t, cls = "") => h("p", { class: `cap${cls ? ` ${cls}` : ""}` }, t);
    const summary = String(got?.summary || "").split("\n")[0].trim();
    const forWords = [g.brief, summary && !String(g.brief || "").includes(summary) ? summary : ""].filter(Boolean);
    const members = m.members.map((x) => line([x.name, BAND_WORDS[x.band], x.price && x.price !== "—" ? `${x.price} ${UNIT[x.band]}` : ""].filter(Boolean).join(" · ")));
    const checkers = m.members.filter((x) => x.band === "check").map((x) => {
      const c = x.role?.check_week;
      return line(`${x.name} checks ${x.rule}${c?.checks ? ` · caught ${c.caught || 0}/${c.checks} lately` : ""}`);
    });
    const spent = [g.usd != null ? `≈$${Number(g.usd).toFixed(2)} so far` : "", g.today?.merged ? `today ${g.today.merged} merged · ≈$${Number(g.today.usd).toFixed(2)}` : ""].filter(Boolean);
    const range = priceRange(priceOf(g));
    const flags = flagsOf(m.nodes);
    const listed = allFlags ? flags : flags.slice(0, FLAGS_SHOWN);
    const before = g.verdict?.met ? line(`Before: ${oldFlagWords(g.verdict)}`) : null;
    const edit = h("button", { class: "ork-btn", type: "button", "data-act": "edit-party", onclick: () => { sh.close(); core.editGoal(g.slug); } }, "Edit the party");
    const add = h("button", { class: "ork-btn", type: "button", "data-act": "add-member", title: seatWords(m.freeBuild + m.freeCheck), onclick: () => { sh.close(); core.editParty(g.slug); } }, "Add to the party");
    body.replaceChildren(...[
      h("button", { class: "party-about__who", type: "button", "data-act": "party-screen", "aria-label": `Open the party ${g.title}`, onclick: () => { sh.close(); core.open({ kind: "goal", slug: g.slug }, "party"); } },
        h("span", {}, h("b", {}, g.title), ` · led by ${g.leader?.name || "Taskmaster"}`), h("i", { class: "ork-chev right", "aria-hidden": "true" })),
      sec("What it is for", ...(forWords.length ? forWords.map((t) => line(t)) : [line("Not written yet.")])),
      sec("The party", ...members),
      sec("Checks on every goal", ...(checkers.length ? checkers : [line("No checker in the party.")])),
      sec("What it costs", ...(spent.length ? [line(spent.join(" · "))] : []), range ? line(`about ${range} a goal with this party`) : null),
      sec("Its flags", ...(listed.length ? listed.map((f) => h("p", { class: "cap party-about__flag", "data-idea": f.slug }, sign("flag"), ` ${f.short} · ${flagTally(f)}`))
        : [line("None yet: a goal raises its flag when the gate takes it into main.")]),
      flags.length > FLAGS_SHOWN && !allFlags ? h("button", { class: "ork-btn quiet", type: "button", "data-act": "all-flags", onclick: () => { allFlags = true; draw(); } }, `All ${flags.length}`) : null),
      before,
      h("div", { class: "party-about__acts" }, edit, add, savePartyEl(g, core)),
      h("p", { class: "cap party-about__seats" }, seatWords(m.freeBuild + m.freeCheck))].filter(Boolean));
  }

  /** Opens the sheet on a party; `at`: a block to scroll to (*Its flags*). */
  function open(slug, at = "") {
    shown = slug;
    got = null;
    allFlags = false;
    draw();
    sh.open();
    const toAt = () => { if (at) body.querySelector(`[data-sec="${at}"]`)?.scrollIntoView({ block: "start" }); };
    requestAnimationFrame(toAt);
    ctx.send("ideas.goal", { slug }).then((r) => { if (r.ok && r.result && !r.result.error && shown === slug) { got = r.result; draw(); toAt(); } });
  }

  // -- the flag line: after a gate's merge that raised flags, once per device -----------------------------------------------------------------------------
  /** Reads what the Map says of the flags: ones newer than this phone saw make the line (and light their rows in the Goals sheet once); the first start keeps all and says none. */
  function watch() {
    const project = st.snap?.project || "";
    if (!st.map || !project) return;
    const seen = seenOf(project);
    const { fresh, newest } = freshFlags(st.map.nodes, seen ?? 0);
    if (seen === null) { keepSeen(project, newest); return; }
    if (!fresh.length) return;
    keepSeen(project, newest);
    st.flagLine = { flags: fresh };
    st.lit = new Set(fresh.map((f) => f.slug));
  }

  /** The flag line (a node, or null): under the party's line, never over the work. */
  function flagNode(slug) {
    if (!st.flagLine) return null;
    const words = flagLine(st.flagLine.flags);
    return h("div", { class: "flagline", role: "status", "data-act": "flag-line" },
      h("button", { class: "flagline__body", type: "button", "aria-label": `${words.head} · ${words.tail}. Its flags`, onclick: () => open(slug, "Its flags") },
        sign("flag"), h("span", { class: "flagline__words" }, h("b", {}, words.head), ` · ${words.tail}`)),
      h("button", { class: "ork-btn quiet flagline__close", type: "button", "aria-label": "Close", onclick: () => { st.flagLine = null; core.draw(); } }, icon("close")));
  }

  return { sheets: [sh.el], gate: gateBox, line: flagNode, watch, open, sheet: sh };
}
