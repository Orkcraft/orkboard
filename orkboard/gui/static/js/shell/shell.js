// The v1 shell (docs/specs/33-v1-shell.md §7): one screen, as an IDE. The Board on the left, Review on the right, the preview
// in the centre and Agents under it as VS Code's terminal (its top edge dragged to resize, Ctrl+J hides it; the height and
// the hidden state are kept in localStorage when there is one). Below 1 024 px wide the same panes are the phone's three
// tabs, the preview on its own screen. Always Office's calm look; no camp. The preview is tabs, the Map first (spec 39).
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Icon } from "../orkui.js";
import { town } from "../link.js";
import { board } from "../board/store.js";
import { needsCount } from "../board/today.js";
import { TopBar } from "./topbar.js";
import { BoardPane } from "./boardpane.js";
import { NeedsPane } from "./review.js";
import { AgentsPane } from "./agents.js";
import { Preview } from "./preview.js";
import { Dialogs } from "./dialogs.js";
import { SignIn } from "./signin.js";
import { StartScreen, currentProject, projectsOn } from "./projects.js";
import { resetFiles } from "./files.js";
import { resetGit } from "./gitpane.js";
import { openDialog } from "./modals.js";
import { preview, review, tab, agentsLayout, setLayout, refreshShell, closePreview, busy, logOpened, resetForProject, mapShown } from "./store.js";

const sheet = new URL("./shell.css", import.meta.url).href;
const boardSheet = new URL("../board/board.css", import.meta.url).href;
if (typeof document !== "undefined") {
  for (const href of [boardSheet, sheet]) {
    if (!document.querySelector(`link[href="${href}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }
  }
}

const NARROW = "(max-width: 1023px)";
const MIN_H = 96, MIN_PREVIEW = 160;

function useNarrow() {
  const [narrow, setNarrow] = useState(() => matchMedia(NARROW).matches);
  useEffect(() => {
    const m = matchMedia(NARROW), on = () => setNarrow(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return narrow;
}

const typing = (el) => !!el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable);

/** Below 1 024 px the shell is the phone's three tabs, in its order: Board · Agents · Needs you. Needs you is the signal (spec 41 §1, as the
 *  phone's): while an answer waits its mark is the warning diamond and its count the warning colour; with results only, the eye and a plain count. */
function Tabs() {
  const b = board.value, rv = review.value;
  const asks = b ? needsCount() : 0, results = rv ? rv.results.length : 0;
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const said = [asks ? `${asks} ${asks === 1 ? "waits" : "wait"} for your answer` : "", results ? plural(results, "result to check", "results to check") : ""].filter(Boolean);
  const count = { board: 0, agents: 0, needs: asks + results };
  return html`<nav class="shell-tabs ork-tabbar" role="tablist" aria-label="Board, Agents, Needs you">
    ${[["board", "Board"], ["agents", "Agents"], ["needs", "Needs you"]].map(([id, name]) => html`<button key=${id} role="tab"
      aria-selected=${tab.value === id} aria-label=${id === "needs" ? (said.length ? `Needs you: ${said.join(", ")}` : name) : count[id] ? `${name}, ${count[id]}` : name}
      class=${cls("shell-tab ork-tabbar__tab", { "is-on": tab.value === id })} onClick=${() => { tab.value = id; closePreview({ toBoard: true }); logOpened("tab", id); }}>
      <${Icon} name=${id === "needs" ? (asks > 0 ? "warning-diamond" : "eye") : id === "board" ? "list-box" : "robot"} />${name}${count[id] > 0 && html`<span class=${cls("shell-count ork-count", id === "needs" && asks > 0 ? "warning" : "on")}>${count[id]}</span>`}</button>`)}
  </nav>`;
}

export function Shell() {
  const t = town.value;
  const narrow = useNarrow();
  const centre = useRef();
  const { h, hidden } = agentsLayout.value;
  const project = projectsOn.value ? currentProject.value?.path || "" : "-";   // "-": Orkline's one fixed project
  // Another project is shown: nothing of the last one stays (its Board, its tree, its git, its preview).
  const was = useRef(null);
  if (was.current !== project) { was.current = project; resetForProject(project); resetFiles(); resetGit(); }
  // Fresh when the town says the ideas changed, and every 10 s while a model or a task runs.
  useEffect(() => { if (project) refreshShell(); }, [t.ideas_rev, project]);
  useEffect(() => {
    const id = setInterval(() => { if (currentProject.value && busy()) refreshShell(); }, 10000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    const key = (e) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "o") {   // Open folder…, as an IDE
        e.preventDefault();
        if (!document.querySelector("[aria-modal='true']")) openDialog("open-folder");
      } else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "j") {   // as VS Code's panel
        e.preventDefault();
        setLayout({ hidden: !agentsLayout.value.hidden });
      } else if (e.key === "Escape" && (preview.value || mapShown.value) && !typing(e.target) && !document.querySelector("[aria-modal='true']")) {
        closePreview();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const drag = (e) => {
    e.preventDefault();
    const move = (ev) => {
      const r = centre.current.getBoundingClientRect();
      setLayout({ h: Math.round(Math.max(MIN_H, Math.min(r.bottom - ev.clientY, r.height - MIN_PREVIEW))) });
    };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };
  const nudge = (e) => {
    const step = e.key === "ArrowUp" ? 24 : e.key === "ArrowDown" ? -24 : 0;
    if (!step) return;
    e.preventDefault();
    const now = h || Math.round(centre.current.getBoundingClientRect().height / 3);
    setLayout({ h: Math.max(MIN_H, now + step) });
  };
  if (!project) {
    return html`<div class="shell" data-narrow=${narrow} data-start="true"><${TopBar} /><${StartScreen} /><${Dialogs} /><${SignIn} /></div>`;
  }
  return html`<div class="shell" data-narrow=${narrow} data-tab=${tab.value} data-previewing=${!!preview.value}>
    <${TopBar} />
    <div class="shell-main">
      <${BoardPane} />
      <div class="shell-centre" ref=${centre} style=${h ? `--agents-h:${h}px` : ""}>
        <${Preview} />
        ${!hidden && !narrow && html`<div class="shell-split" role="separator" aria-orientation="horizontal" aria-label="Resize Agents"
          aria-valuenow=${h || undefined} tabindex="0" onPointerDown=${drag} onKeyDown=${nudge}></div>`}
        <${AgentsPane} />
      </div>
      <${NeedsPane} />
    </div>
    ${narrow && html`<${Tabs} />`}
    <${Dialogs} />
    <${SignIn} />
  </div>`;
}
