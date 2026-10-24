// A release on the desktop (docs/specs/68-release-and-route.md §3, §7.3, §7.6): New goal of *A release* asks **What goes in** — the goals that raised their flag in the parties the release's party
// releases from since its last release that is out (`ideas.release_candidates`), each a row with its element, its title, its party and its flag's date, ticked; one an open release holds is greyed
// with *In 1.4 already* and cannot be ticked; none: *Nothing has raised its flag since 1.3.* and the goal can still be added. And **Releases from** in New party and Edit the party: the project's
// parties to tick, *Every party but Ideation* by default for the Release party. Orkboard submits nothing: the person says a release is out (arena/goals.js *Mark it out*).
import { useEffect, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { command } from "../link.js";
import { Elem } from "../orkui.js";
import { mapData } from "./store.js";
import { flagDay } from "../arena/goalwords.js";

/** **What goes in**: `party` the release's party (read again when it changes), `goes` the slugs ticked, `setGoes` their setter. A goal that is free starts ticked. */
export function GoesIn({ party, goes, setGoes }) {
  const [got, setGot] = useState(null);                       // null while it is read, else {since, candidates}
  useEffect(() => {
    let live = true;
    setGot(null);
    command("ideas.release_candidates", { party }).then((r) => {
      if (!live) return;
      const list = r?.candidates || [];
      setGot({ since: r?.since || null, candidates: list });
      setGoes(list.filter((c) => !c.held).map((c) => c.goal));
    }).catch(() => { if (live) { setGot({ since: null, candidates: [] }); setGoes([]); } });
    return () => { live = false; };
  }, [party]);
  const flip = (slug, on) => setGoes(on ? [...goes.filter((x) => x !== slug), slug] : goes.filter((x) => x !== slug));
  const since = got?.since ? (got.since.version ? `since ${got.since.version}` : "since the last release") : "since the start";
  return html`<div class="shell-field arena-goesin" role="group" aria-label="What goes in" data-sec="goes-in"><span class="ok-font-label">What goes in</span>
    ${!got ? html`<p class="ok-tone-muted">Reading…</p>`
      : got.candidates.length ? html`<ul class="arena-goesin__list">${got.candidates.map((c) => html`<li key=${c.goal}>
          <label class=${cls("arena-goesin__row", { "is-held": !!c.held })} data-goal=${c.goal}>
            <input type="checkbox" aria-label=${c.title} data-goal=${c.goal} checked=${!c.held && goes.includes(c.goal)} disabled=${!!c.held} onChange=${(e) => flip(c.goal, e.target.checked)} />
            <${Elem} name=${c.element} dim=${!!c.held} />
            <span class="arena-goesin__text"><b class="arena-goesin__title">${c.title}</b>
              <small class="ok-tone-muted">${[c.party_name || c.party, flagDay(c.at), c.held ? `In ${c.held} already` : ""].filter(Boolean).join(" · ")}</small></span></label></li>`)}</ul>`
      : html`<p class="ok-tone-muted" data-sec="none">Nothing has raised its flag ${since}.</p>`}
  </div>`;
}

const key = (list) => JSON.stringify([...list].sort());

/** The state of **Releases from**: `self` the party's slug ("" for a new one), `saved` its `releases_from`, `leads` its leader is the Release manager, `offers` it can take *A release*.
 *  A Release party releases from *every party but Ideation* when it was set to none (`[]`), so all are ticked then and one stays; another party that offers *A release* takes its own flags, so none is
 *  ticked then. `value()` is what `ideas.goal_save` takes as `releases_from`, or undefined when the person changed nothing. */
export function useReleasesFrom({ self = "", saved = [], leads = false, offers = leads }) {
  const parties = (mapData.value?.goals || []).filter((g) => g.slug !== self && g.slug !== "general" && !g.ideation), slugs = parties.map((g) => g.slug);
  const start = () => (leads && !saved.length ? slugs : saved.filter((s) => slugs.includes(s)));
  const [ticked, setTicked] = useState(start), [first, setFirst] = useState(() => key(start()));
  useEffect(() => { const s = start(); setTicked(s); setFirst(key(s)); }, [leads, offers, slugs.join(",")]);
  const shown = !!offers && parties.length > 0;
  return { parties, ticked, setTicked, leads, shown,
    value: () => (!shown || key(ticked) === first ? undefined : leads && ticked.length === parties.length ? [] : ticked) };
}

/** **Releases from**: the project's parties to tick (not this one, Ideation or General). `rf`: `useReleasesFrom`'s. */
export function ReleasesFrom({ rf }) {
  if (!rf.shown) return null;
  const { parties, ticked, leads } = rf, all = leads && ticked.length === parties.length;
  const words = leads ? (all ? "Every party but Ideation" : "Only the ticked parties") : ticked.length ? "Its own flags and the ticked parties’" : "Its own flags";
  const flip = (slug, box) => {
    if (box.checked) rf.setTicked([...ticked, slug]);
    else if (leads && ticked.length === 1) box.checked = true;                                          // a Release party keeps one: none would mean every party
    else rf.setTicked(ticked.filter((x) => x !== slug));
  };
  return html`<div class="shell-field arena-releasesfrom" role="group" aria-label="Releases from" data-sec="releases-from"><span class="ok-font-label">Releases from</span>
    <div class="arena-releasesfrom__list">${parties.map((g) => html`<label key=${g.slug} class="arena-releasesfrom__row" data-goal=${g.slug}>
      <input type="checkbox" aria-label=${g.short || g.title} data-goal=${g.slug} checked=${ticked.includes(g.slug)} onChange=${(e) => flip(g.slug, e.target)} />
      <span>${g.short || g.title}</span></label>`)}</div>
    <p class="ok-font-status ok-tone-muted" role="status">${words}</p></div>`;
}
