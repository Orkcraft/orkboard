// The drawer's settings on the phone (docs/specs/41-phone-round-3.md §2): Stop all and Spend today at its head, then This project — the
// Target, Start plans by themselves, the night's hours, Push after merging, What is left — and This phone — Pair a phone, Download the
// logs, Unpair this phone. Each setting writes with today's command (`ideas.board_set`, `ideas.into`) at once.
import { h, sheet } from "./util.js";
import { foot } from "./shell-forms.js";
import { TARGETS } from "./shell-words.js";
import { makePush } from "./shell-push.js";
import { makeWeek, pushWeek } from "./shell-cards.js";

/** `core`: the board's frame; `ctx`: {send, flash, unpair}; `drawer`: the sheet these live in; `limits`: opens What is left.
 *  Returns {head, project, phone, sheets, sync(), render(snapshot)}. */
export function makeSettings(core, ctx, drawer, limits) {
  const spend = h("p", { class: "board-spend muted" });
  // This week (spec 42 §6): the Spend today row opens a sheet of the week's work. New idea is the Board's button, pressed from here.
  const week = makeWeek(core, () => { drawer.close(); document.querySelector(".fab")?.click(); });

  // Stop all: a tap asks first (the confirm is a sheet whose button sits away from this one), as the town's does.
  const stop = h("button", { class: "ork-btn danger board-stop", type: "button" }, "Stop all");
  const really = h("button", { class: "ork-btn danger", type: "button" }, "Stop every ork");
  const stopSheet = sheet("Stop all",
    h("p", {}, "Every ork at work stops now, and every idea's tasks with them: their sessions are interrupted and their processes ended."),
    really);
  stop.addEventListener("click", () => { drawer.close(); stopSheet.open(); });
  really.addEventListener("click", async () => {
    stopSheet.close();
    const r = await ctx.send("halt");
    ctx.flash(r.ok ? `Stopped: ${r.result} session(s)` : r.error);
  });

  // The analytics zip (gui/ideas.py `ideas.logs`), handed over the paired link and saved as a file on this phone.
  async function download(days) {
    const got = await core.call("ideas.logs", { days });
    if (!got?.data) return;
    const bytes = Uint8Array.from(atob(got.data), (c) => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }));
    const a = h("a", { href: url, download: got.name || "orkline-logs.zip" });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    ctx.flash("The logs are downloaded.");
  }

  // Pair a phone: a phone does not pair another one (the listener refuses `phones.*` to a phone, docs/design/mobile.md §2): this sheet says
  // where it is done and how the phone will reach the computer.
  const pairSheet = sheet("Pair a phone",
    h("p", {}, "A phone is paired from the computer, never from another phone: that keeps a lost phone from adding more."),
    h("ol", { class: "steps" },
      h("li", {}, "On the computer, open the gear → Pair a phone: it shows a QR code and says how long the code lasts."),
      h("li", {}, "Scan the code with this phone’s camera: Orkline opens in the browser and pairs.")),
    h("h3", {}, "How the phone reaches the computer"),
    h("ul", { class: "steps" },
      h("li", {}, "On the same Wi-Fi as the computer."),
      h("li", {}, "Anywhere on your tailnet, when Tailscale runs on the computer and the phone."),
      h("li", {}, "Away from home? Install Tailscale on the computer and the phone.")),
    foot(h("button", { class: "ork-btn primary big", type: "button", onclick: () => pairSheet.close() }, "Done")));

  // -- This project: the Board's settings (spec 35 §1, §5, §7, §11), written at once ------------------------------------------
  let writing = 0;                                       // settings being written: the board read in between must not put the old value back
  const write = async (name, args) => { writing += 1; try { return await core.call(name, args); } finally { writing -= 1; } };
  const picks = TARGETS.map(([id, word, line]) => {
    const input = h("input", { type: "radio", name: "target", value: id, "aria-label": word });
    input.addEventListener("change", async () => { if (await write("ideas.board_set", { target: id })) await core.refresh(); });
    return [id, input, h("label", { class: "target-pick" }, input, h("span", { class: "need-text" }, h("b", {}, word), h("small", {}, line)))];
  });
  const pushBox = h("input", { type: "checkbox", id: "push-after" });
  const autoBox = h("input", { type: "checkbox", id: "autostart" });
  const nightFrom = h("input", { class: "ork-field", type: "time", "aria-label": "Night from" });
  const nightTo = h("input", { class: "ork-field", type: "time", "aria-label": "Night to" });
  autoBox.addEventListener("change", async () => { await write("ideas.board_set", { autostart: autoBox.checked }); await core.refresh(); });
  const setNight = async () => {
    if (!nightFrom.value || !nightTo.value) return;
    if (await write("ideas.board_set", { night: `${nightFrom.value}-${nightTo.value}` })) await core.refresh();
  };
  nightFrom.addEventListener("change", setNight);
  nightTo.addEventListener("change", setNight);
  pushBox.addEventListener("change", async () => { await write("ideas.into", { push: pushBox.checked }); await core.refresh(); });

  const project = [
    h("h3", {}, "This project"),
    h("div", { class: "field target-picks", role: "radiogroup", "aria-label": "Target" }, h("span", { class: "field-label" }, "Target"), ...picks.map((p) => p[2])),
    h("label", { class: "check-line", for: "autostart" }, autoBox, h("span", {}, "Start plans by themselves")),
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Night"), h("div", { class: "row night-row" }, nightFrom, h("span", {}, "to"), nightTo)),
    h("label", { class: "check-line", for: "push-after" }, pushBox, h("span", {}, "Push after merging (sends your code to origin)")),
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => { drawer.close(); limits(); } }, "What is left")),
  ];
  const push = makePush(ctx);
  const phone = [
    h("h3", {}, "This phone"),
    push.el,
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: async () => {                 // Last week (spec 42 §7.3): its card on the Board tab
      const got = await core.call("ideas.week");
      if (!got) return;
      drawer.close();
      core.go("board");
      pushWeek(core, got, "map");
    } }, "Last week")),
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => pairSheet.open() }, "Pair a phone")),
    h("div", { class: "field" }, h("span", { class: "field-label" }, "Download the logs"),
      h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => download(1) }, "Today"),
        h("button", { class: "ork-btn", type: "button", onclick: () => download(7) }, "The last 7 days")),
      h("small", { class: "muted" }, "What you did and what the orks did, kept on the computer. Off by default.")),
    h("div", { class: "row" }, h("button", { class: "ork-btn", type: "button", onclick: () => ctx.unpair() }, "Unpair this phone")),
  ];

  return {
    head: [h("div", { class: "row" }, stop), spend],
    project,
    phone,
    sheets: [stopSheet.el, pairSheet.el, week.el],
    /** The settings' values from what the Board read last. */
    sync() {
      push.draw();
      if (writing) return;
      for (const [id, input] of picks) input.checked = id === (core.st.board?.target || "balance");
      pushBox.checked = Boolean(core.st.review?.push);
      autoBox.checked = core.st.board?.autostart !== false;
      if (document.activeElement !== nightFrom && document.activeElement !== nightTo) [nightFrom.value, nightTo.value] = String(core.st.board?.night || "01:00-07:00").split("-");
    },
    render(s) {
      const gold = s.hud?.show_gold ? s.hud.gold : "";
      spend.replaceChildren(...(gold ? [h("button", { class: "linkish board-spend__open", type: "button", "aria-label": `Spend today: ${gold}. This week’s work`,
        onclick: () => { drawer.close(); week.open(); } }, h("span", { class: "word" }, "Spend today"), " ", h("b", {}, gold))] : []));
      spend.hidden = !gold;
    },
  };
}
