// A newer Orkline on the phone (gui/board_host.py `BoardPhone`, docs/updates.md): a bar under the status says it is out,
// loudly for a critical one, plainly for a major one; a tap opens its sheet, whose Update and restart installs it on the
// computer (`update.install`). The computer restarts on it, what ran is cut off and starts again by itself, and this phone
// comes back on its own (board-app.js reconnects); then the bar says which version runs. Later hides an ordinary or a
// major update until the next version, a critical one until the app opens again. Which updates install by themselves
// is the computer's to say (Settings → Updates).
import { h, sheet } from "./util.js";
import { foot } from "./shell-forms.js";

const LATER_KEY = "orkboard.update.later";
const ASKED_KEY = "orkboard.update.asked";   // the version this phone asked the computer to install, until it runs

function read(key) { try { return localStorage.getItem(key) || ""; } catch { return ""; } }
function write(key, value) { try { if (value) localStorage.setItem(key, value); else localStorage.removeItem(key); } catch { /* kept for now */ } }

/** What the update is called: a critical one first, then a major one, else a plain newer version. */
export function updateTitle(u) {
  if (u.critical) return `Critical update: Orkline ${u.version}`;
  if (u.major) return `New version: Orkline ${u.version}`;
  return `Orkline ${u.version} is out`;
}

/** `ctx`: {send, flash}. Returns {el, sheets, render(snapshot), check()}. */
export function makeUpdate(ctx) {
  let u = null;
  let later = read(LATER_KEY);
  const bar = h("button", { class: "update-bar", type: "button", hidden: true, "data-update": "bar", onclick: () => { draw(); ask.open(); } });
  const body = h("div", { class: "update-body" });
  const go = h("button", { class: "ork-btn primary big", type: "button", "data-update": "install" }, "Update and restart");
  const wait = h("button", { class: "ork-btn big", type: "button" }, "Later");
  const ask = sheet("Update", body, foot(wait, go));

  wait.addEventListener("click", () => {
    if (u) { later = u.version; if (!u.critical) write(LATER_KEY, u.version); }
    ask.close();
    draw();
  });
  go.addEventListener("click", async () => {
    if (!u) return;
    go.disabled = true;
    const r = await ctx.send("update.install");
    go.disabled = false;
    if (!r.ok) { ctx.flash(`Not installed: ${r.error}`); return; }
    write(ASKED_KEY, u.version);
    ask.close();
    ctx.flash(`Installing Orkline ${u.version} on the computer. It restarts when it is in; this phone comes back by itself.`);
  });

  function draw() {
    const busy = u && (u.state === "installing" || u.state === "installed");
    const show = u && (busy || u.state === "failed" || later !== u.version);
    bar.hidden = !show;
    bar.classList.toggle("is-critical", Boolean(u?.critical || u?.state === "failed"));
    if (!u) return;
    bar.textContent = u.state === "installing" ? `Installing Orkline ${u.version} on the computer…`
      : u.state === "installed" ? `Orkline ${u.version} is in: the computer restarts`
        : u.state === "failed" ? `Orkline ${u.version} did not install`
          : updateTitle(u);
    ask.title(updateTitle(u));
    body.replaceChildren(...[
      h("p", { class: "muted" }, `The computer runs ${u.current}.`),
      u.critical ? h("p", { class: "warn" }, "It fixes something that can lose work or let harm in: install it now.") : null,
      u.major && !u.critical ? h("p", {}, "A major update: what is new may change how you work. Read it before you install.") : null,
      u.notes.length ? h("ul", { class: "steps" }, ...u.notes.map((n) => h("li", {}, n))) : null,
      h("p", { class: "muted" }, u.can
        ? "Orkline restarts on the computer when it is in: what runs now stops, and the tasks cut off start again by themselves. This phone comes back on its own in a few seconds."
        : `It cannot install itself on the computer: ${u.how}`),
      u.state === "failed" ? h("p", { class: "warn" }, `It did not install. The computer keeps running ${u.current}.`) : null,
      u.state === "failed" && u.error ? h("pre", { class: "update-error" }, u.error) : null].filter(Boolean));
    go.hidden = !u.can || busy;
    go.textContent = u.state === "failed" ? "Try again" : "Update and restart";
  }

  return {
    el: bar,
    sheets: [ask.el],
    render(s) {
      const asked = read(ASKED_KEY);
      if (asked && s.version === asked) {                 // the computer came back on the version this phone asked for
        write(ASKED_KEY, "");
        ctx.flash(`Updated: the computer runs Orkline ${s.version}.`);
      }
      u = s.update || null;
      draw();
    },
    /** Settings → Check for updates: the list read again on the computer now. */
    async check() {
      const r = await ctx.send("update.check");
      if (!r.ok) { ctx.flash(r.error); return; }
      if (!r.result) { ctx.flash("The computer runs the latest Orkline."); return; }
      later = "";                                         // asked for: shown again, whatever Later said (the next state brings it)
      write(LATER_KEY, "");
      draw();
    },
  };
}
