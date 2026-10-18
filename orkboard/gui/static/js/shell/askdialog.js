// The questions of a spec or a goal as one form (docs/specs/35-goals-window.md §0, §11.2): a box per question, one Send
// (`ideas.answer`). A click on an "asks" item of Needs you opens it.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { ask, items } from "../board/store.js";
import { Questions } from "../board/ask.js";
import { act } from "./store.js";
import { Modal, closeDialog } from "./modals.js";

export function AskDialog({ slug, goal = false, title = "" }) {
  const [questions, setQuestions] = useState(null);
  useEffect(() => {
    let live = true;
    (async () => {
      const got = goal ? await ask("ideas.goal", { slug }) : await ask("ideas.page", { slug });
      if (!live) return;
      setQuestions(goal ? (got?.questions || []) : items(got?.sections?.find((s) => s.name === "Open questions")?.text));
    })();
    return () => { live = false; };
  }, [slug, goal]);
  const send = async (answers) => {
    const got = await act("ideas.answer", { slug, answers, ...(goal ? { goal: true } : {}) });
    if (got) closeDialog();
  };
  return html`<${Modal} title=${`Questions: ${title}`} onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Later</button>`}>
    ${questions === null ? html`<p class="ok-tone-muted">Opening…</p>`
      : questions.length ? html`<${Questions} questions=${questions} onSend=${send} />`
        : html`<p class="ok-tone-muted">No question is open any more.</p>`}
  <//>`;
}
