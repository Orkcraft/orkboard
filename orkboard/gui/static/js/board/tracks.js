// The party this computer showed last in the project (docs/specs/35-goals-window.md §11.1, docs/specs/50-parties-and-goals.md §3.1): the party tabs (arena/goaltabs.js)
// keep it per project, so the window opens on the party the person last looked at. The code's goal is a party.
import { currentProject } from "../shell/projects.js";

const GOAL_KEPT = "orkboard.goal";                    // {project: party slug}
const projectKey = () => currentProject.value?.path || "";
export const keptGoal = () => { try { return (JSON.parse(localStorage.getItem(GOAL_KEPT)) || {})[projectKey()] || ""; } catch { return ""; } };
export function keepGoal(slug) {
  try { localStorage.setItem(GOAL_KEPT, JSON.stringify({ ...(JSON.parse(localStorage.getItem(GOAL_KEPT)) || {}), [projectKey()]: slug })); } catch { /* this run only */ }
}
