// A release on the phone (docs/specs/68-release-and-route.md §3, §7.3, §7.6): New goal of *A release* asks **What goes in** — the goals that raised their flag in the parties the release's party releases
// from since its last release that is out (`ideas.release_candidates`), each a row with its element, its title, its party and its flag's date, ticked; one an open release holds is greyed with *In 1.4
// already* and cannot be ticked; none: *Nothing has raised its flag since 1.3.* and the goal can still be added. And **Releases from** in Edit the party and New party: the project's parties to tick,
// *Every party but Ideation* by default for the Release party. Orkboard submits nothing: the person says a release is out (shell-goals.js *Mark it out*).
import { h } from "./util.js";
import { elem } from "./shell-marks.js";
import { flagDate } from "./shell-goals-words.js";

/** The list of **What goes in**. `core`: the board's frame (call). Returns {el, load(party), value(), reset()}: `value()` is `ideas.add`'s `goes_in`. */
export function makeGoesIn(core) {
  let party = "", rows = [], since = null, ticked = new Set(), loaded = false, seq = 0;
  const el = h("section", { class: "goesin field", "aria-label": "What goes in", "data-sec": "goes-in", hidden: true });

  function sinceWords() {
    if (!since) return "since the start";
    return since.version ? `since ${since.version}` : "since the last release";
  }
  function row(r) {
    const held = Boolean(r.held), on = ticked.has(r.goal);
    const box = h("input", { type: "checkbox", "data-goal": r.goal, "aria-label": r.title, ...(on ? { checked: true } : {}), ...(held ? { disabled: true } : {}) });
    box.addEventListener("change", () => { if (box.checked) ticked.add(r.goal); else ticked.delete(r.goal); });
    return h("label", { class: `goesin__row${held ? " is-held" : ""}`, "data-goal": r.goal },
      box, elem(r.element, { dim: held }), h("span", { class: "goesin__text" }, h("b", { class: "goesin__title" }, r.title),
        h("small", { class: "muted goesin__meta" }, [r.party_name || r.party, flagDate(r.at), held ? `In ${r.held} already` : ""].filter(Boolean).join(" · "))));
  }
  function draw() {
    el.hidden = false;
    el.replaceChildren(h("span", { class: "field-label" }, "What goes in"),
      !loaded ? h("p", { class: "muted goesin__empty" }, "Reading…")
        : rows.length ? h("div", { class: "goesin__list" }, ...rows.map(row)) : h("p", { class: "muted goesin__empty", "data-sec": "none" }, `Nothing has raised its flag ${sinceWords()}.`));
  }

  return {
    el,
    /** The release's party picked: what goes in is read for it (a goal that is free is ticked). */
    async load(which) {
      party = which;
      rows = []; since = null; ticked = new Set(); loaded = false;
      const mine = ++seq;
      draw();
      const got = await core.call("ideas.release_candidates", { party });
      if (mine !== seq) return;
      if (got) { rows = got.candidates || []; since = got.since || null; ticked = new Set(rows.filter((r) => !r.held).map((r) => r.goal)); }
      loaded = true;
      draw();
    },
    value: () => rows.filter((r) => !r.held && ticked.has(r.goal)).map((r) => r.goal),
    reset() { seq += 1; party = ""; rows = []; since = null; ticked = new Set(); loaded = false; el.hidden = true; el.replaceChildren(); },
  };
}

/** *Releases from*: the project's parties to tick (not this one, Ideation or General). `core`: the board's frame (st). Returns {el, set({self, saved, leads, offers}), get()}.
 *  A Release party (its leader is the Release manager) releases from *every party but Ideation* when it was set to none (`[]`), so all are ticked then and one stays; another party that offers *A release* takes its own
 *  flags, so none is ticked then. `get()`: what `ideas.goal_save` takes as `releases_from`, or null when the person changed nothing. */
export function makeReleasesFrom(core) {
  let parties = [], ticked = new Set(), first = "", leads = false;
  const el = h("section", { class: "releasesfrom field", "aria-label": "Releases from", "data-sec": "releases-from", hidden: true });
  const key = (set) => JSON.stringify([...set].sort());
  function draw() {
    const all = leads && ticked.size === parties.length;
    const words = leads ? (all ? "Every party but Ideation" : "Only the ticked parties") : (ticked.size ? "Its own flags and the ticked parties’" : "Its own flags");
    el.replaceChildren(h("span", { class: "field-label" }, "Releases from"),
      h("div", { class: "releasesfrom__list" }, ...parties.map((g) => {
        const on = ticked.has(g.slug);
        const box = h("input", { type: "checkbox", "data-goal": g.slug, "aria-label": g.short || g.title, ...(on ? { checked: true } : {}) });
        box.addEventListener("change", () => {
          if (box.checked) ticked.add(g.slug); else if (leads && ticked.size === 1) box.checked = true; else ticked.delete(g.slug);      // a Release party keeps one: none would mean every party
          draw();
        });
        return h("label", { class: "releasesfrom__row", "data-goal": g.slug }, box, h("span", {}, g.short || g.title));
      })),
      h("p", { class: "muted releasesfrom__words", role: "status" }, words));
  }
  return {
    el,
    /** `self`: the party's slug ("" for a new one); `saved`: its `releases_from`; `leads`: its leader is the Release manager; `offers`: it can take *A release*. Hidden otherwise. */
    set({ self = "", saved = [], leads: lead = false, offers = lead } = {}) {
      leads = lead;
      parties = (core.st.map?.goals || []).filter((g) => g.slug !== self && g.slug !== "general" && !g.ideation);
      const slugs = new Set(parties.map((g) => g.slug));
      ticked = new Set(leads && !saved.length ? slugs : saved.filter((s) => slugs.has(s)));
      first = key(ticked);
      el.hidden = !(offers && parties.length);
      if (!el.hidden) draw(); else el.replaceChildren();
    },
    get() {
      if (el.hidden || key(ticked) === first) return null;
      return leads && ticked.size === parties.length ? [] : [...ticked];
    },
  };
}
