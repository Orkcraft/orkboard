// A file's patch, as Review shows a result's code (docs/specs/33-v1-shell.md §6): the lines coloured, each file folded.
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";

export function Patch({ patch }) {
  return html`<pre class="shell-patch">${patch.split("\n").map((ln, n) => html`<span key=${n}
    class=${cls("shell-patch__line", { "is-add": ln.startsWith("+") && !ln.startsWith("+++"), "is-del": ln.startsWith("-") && !ln.startsWith("---"),
      "is-hunk": ln.startsWith("@@") })}>${ln}\n</span>`)}</pre>`;
}

export function File({ f, open: opened = false }) {
  const [open, setOpen] = useState(opened);       // the lines are drawn when it opens: a big diff stays light
  return html`<details class="shell-file" open=${opened} onToggle=${(e) => setOpen(e.currentTarget.open)}>
    <summary><code>${f.path}</code><span class="shell-file__n"><span class="is-add">+${f.added}</span> <span class="is-del">−${f.removed}</span></span></summary>
    ${open && (f.patch == null ? html`<p class="ok-tone-muted">Too large to show.</p>` : html`<${Patch} patch=${f.patch} />`)}
  </details>`;
}
