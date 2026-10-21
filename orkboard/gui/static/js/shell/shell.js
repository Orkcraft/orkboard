// The one window (docs/specs/49-one-window.md, decisions §62): the top bar, the goal tabs, and under them the goal's arena — the day's
// strip, Planning over the leader, the field with its party, results, stops and limits (js/arena/). Anything opened slides in as a
// drawer from the right (spec 49 §9): the preview's tabs, Agents and Files. Always Office's calm look; no camp.
import { useEffect, useRef } from "preact/hooks";
import { html } from "../html.js";
import { town } from "../link.js";
import { TopBar } from "./topbar.js";
import { Preview } from "./preview.js";
import { Dialogs } from "./dialogs.js";
import { StartScreen, currentProject, projectsOn } from "./projects.js";
import { resetFiles } from "./files.js";
import { resetGit } from "./gitpane.js";
import { openDialog } from "./modals.js";
import { drawerOpen, refreshShell, hideDrawer, busy, resetForProject } from "./store.js";
import { Arena } from "../arena/arena.js";
import { solo } from "../arena/arenastate.js";
import { GoalTabs } from "../arena/goaltabs.js";

const sheets = ["../board/board.css", "./shell.css", "../arena/arena.css"].map((p) => new URL(p, import.meta.url).href);
if (typeof document !== "undefined") {
  for (const href of sheets) {
    if (!document.querySelector(`link[href="${href}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }
  }
}

const typing = (el) => !!el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable);

export function Shell() {
  const t = town.value;
  const project = projectsOn.value ? currentProject.value?.path || "" : "-";   // "-": Orkline's one fixed project
  // Another project is shown: nothing of the last one stays (its Board, its tree, its git, its drawer).
  const was = useRef(null);
  if (was.current !== project) { was.current = project; resetForProject(project); resetFiles(); resetGit(); }
  // Fresh when the town says the ideas changed, and every 10 s while a model or a task runs.
  useEffect(() => { if (project) refreshShell(); }, [t.ideas_rev, project]);
  // Operations moved: Needs you holds its rows, so the Board is read again.
  useEffect(() => { if (t.ops_rev) refreshShell(); }, [t.ops_rev]);
  useEffect(() => {
    const id = setInterval(() => { if (currentProject.value && busy()) refreshShell(); }, 10000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    const key = (e) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "o") {   // Open folder…, as an IDE
        e.preventDefault();
        if (!document.querySelector("[aria-modal='true']")) openDialog("open-folder");
      } else if (e.key === "Escape" && drawerOpen.value && !typing(e.target) && !document.querySelector("[aria-modal='true']")) {
        hideDrawer();                                   // the drawer goes and keeps its tabs
      } else if (e.key === "Escape" && solo.value && !typing(e.target) && !document.querySelector("[aria-modal='true']")) {
        solo.value = "";                                // a member's work alone: everyone's again
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  if (!project) {
    return html`<div class="shell" data-start="true"><${TopBar} /><${StartScreen} /><${Dialogs} /></div>`;
  }
  return html`<div class="shell" data-drawer=${drawerOpen.value}>
    <${TopBar} />
    <${GoalTabs} />
    <div class="shell-main">
      <${Arena} />
      ${drawerOpen.value && html`<aside class="shell-drawer" aria-label="Drawer"><${Preview} /></aside>`}
    </div>
    <${Dialogs} />
  </div>`;
}
