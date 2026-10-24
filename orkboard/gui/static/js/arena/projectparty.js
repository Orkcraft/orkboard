// A goal's party from the Orkmaster (docs/specs/70-orkmaster-and-the-project.md §4): New goal on the project's level has no party at first. `usePartyFor` asks `ideas.party_for` (with the goal's type, again when the
// type changes) and holds the party picked — the one the Orkmaster suggests until the person picks another —; `ItsParty` is the field: a line *Orkmaster suggests <party>* with its fit (*takes it whole*,
// *needs <agent>*, *no one there does it*) and every party of the project as a chip to pick, each with its own fit. With no type the line is *Any party*, Ideation's chip last with *a pitch*.
// An older host (no `ideas.party_for`) gives the parties as the Map has them, the first suggested. Nothing is written and no model is called: the Orkmaster only says.
import { useEffect, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { command } from "../link.js";
import { mapData } from "../shell/store.js";
import { fitWords, suggestsWords } from "./projectwords.js";

/** The parties as the Map has them, in the Board's order, when the host cannot say more. */
const fromMap = () => {
  const parties = (mapData.value?.goals || []).filter((g) => g.slug !== "general").map((g) => ({ party: g.slug, name: g.short || g.title, fits: g.ideation ? "pitch" : "", missing: [] }));
  return { parties: [...parties.filter((p) => p.fits !== "pitch"), ...parties.filter((p) => p.fits === "pitch")], suggested: parties.find((p) => p.fits !== "pitch")?.party || parties[0]?.party || "" };
};

/** `on`: the New goal is the project's (a party's own asks nothing); `typeId`: the goal's type, "" for *Your own goal*. {parties, suggested, picked, pick, typed, ready}. */
export function usePartyFor(on, typeId = "") {
  const [got, setGot] = useState(null), [mine, setMine] = useState("");
  useEffect(() => {
    if (!on) return undefined;
    let live = true;
    setMine("");
    command("ideas.party_for", typeId ? { type: typeId } : {}).then((r) => { if (live) setGot(r && !r.error && Array.isArray(r.parties) ? r : fromMap()); }).catch(() => { if (live) setGot(fromMap()); });
    return () => { live = false; };
  }, [on, typeId]);
  const parties = got?.parties || [], suggested = got?.suggested || parties[0]?.party || "";
  const picked = parties.some((p) => p.party === mine) ? mine : suggested;
  return { parties, suggested, picked, pick: setMine, typed: !!typeId, ready: !!got && !!picked };
}

/** **Its party**: what the Orkmaster suggests, and the parties to pick. */
export function ItsParty({ pf }) {
  const { parties, suggested, picked, pick, typed } = pf, best = parties.find((p) => p.party === suggested);
  return html`<div class="shell-field arena-itsparty" role="group" aria-label="Its party" data-picked=${picked}>
    <span class="ok-font-label">Its party</span>
    ${typed && best ? html`<p class="ok-font-status arena-itsparty__says" data-fit=${best.fits}><b>${suggestsWords(best.name)}</b> · <span class="ok-tone-muted">${fitWords(best)}</span></p>`
      : html`<p class="ok-font-status ok-tone-muted arena-itsparty__says">Any party</p>`}
    <div class="arena-itsparty__chips" role="radiogroup" aria-label="Its party">${parties.map((p) => html`<button key=${p.party} type="button" role="radio" data-party=${p.party}
      class=${cls("ork-btn arena-itsparty__chip", { "is-suggested": p.party === suggested })} aria-checked=${p.party === picked} onClick=${() => pick(p.party)}>
      <b>${p.name}</b>${fitWords(p) && html`<small>${fitWords(p)}</small>`}</button>`)}</div>
  </div>`;
}
