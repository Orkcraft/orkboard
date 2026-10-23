// Which dialog is open (shell/modals.js `dialog`), drawn over the shell on its dimmed backdrop.
import { html } from "../html.js";
import { dialog } from "./modals.js";
import { GoalDialog } from "./goaldialog.js";
import { IdeaDialog } from "./ideadialog.js";
import { AskDialog } from "./askdialog.js";
import { TodoDialog } from "./tododialog.js";
import { AgentDialog } from "./agentdialog.js";
import { SettingsDialog } from "./settings.js";
import { PairDialog } from "./pair.js";
import { IntoDialog, DropDialog } from "./review.js";
import { OpenFolderDialog, CloseProjectDialog } from "./projects.js";
import { LeaveDialog } from "./editor.js";
import { SwitchDialog } from "./gitpane.js";
import { OpFormDialog, OpSettingsDialog, OpRulesDialog, OpForgetDialog } from "./opdialog.js";
import { OpCheckDialog } from "./opcheck.js";
import { WeekDialog } from "../board/cards.js";

const KINDS = { goal: GoalDialog, idea: IdeaDialog, ask: AskDialog, todo: TodoDialog, agent: AgentDialog, settings: SettingsDialog, pair: PairDialog, into: IntoDialog, drop: DropDialog,
  "open-folder": OpenFolderDialog, "close-project": CloseProjectDialog, leave: LeaveDialog, "switch-branch": SwitchDialog,
  this_week: WeekDialog, opform: OpFormDialog, opcheck: OpCheckDialog, opsettings: OpSettingsDialog, oprules: OpRulesDialog, opforget: OpForgetDialog };

export function Dialogs() {
  const d = dialog.value;
  const View = d && KINDS[d.kind];
  return View ? html`<${View} key=${d.kind + (d.props.slug || d.props.op || d.props.template || d.props.assign || d.props.todo?.id || "") + (d.props.standing || "")} ...${d.props} />` : null;
}
