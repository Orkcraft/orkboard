# Spec 51 — Pick one: a task makes a few variants (pictures, sounds, clips or texts), the person picks one with a note

The owner, 21 October (decisions §64). Some work is chosen by eye or by ear, not reviewed line by line: an artist's
logo, an icon, a jingle, a short clip, three taglines. Today a task's result is one change to merge or send back, so a
person who wants to choose sees one variant at a time, a round each. This spec lets a task **make two to six variants
of one kind** (pictures, sounds, clips or texts) and stop; the person sees them side by side as a **Pick one** stop in
the bottom row (decisions §62.1), picks one, adds a note if they like, and the work goes on with the one picked; or
asks for new ones with a note. The kinds are one mechanism: the host keeps the variants as files with their media type
and serves them; the faces draw each kind as a tile. **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** a new end for a task (it may leave variants instead of a change), a new task state
(*picking*), a new stop kind (*pick*), one command (`ideas.pick`), one route for the files (`/media/…`), and the faces'
tiles. The plan may ask a task for variants; nothing else in the keeper changes. **Storage keeps its shape** (Orkline
reads the same Board): the variants and their manifest live in the goal's state folder beside its plan, never in the
repository; only the one picked is committed, as the task's change.

Four parts. **A0 and A first, at once**; **B and C from both** (they need spec 50's faces merged first). This file is
the contract; the mockups are E and F of *Orkboard: one window* (`Decks.dc.html`'s *Pick one* card and drawer,
`PhoneDecks.dc.html`'s raised *Pick one*), drawn with pictures; the other kinds follow §5.

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** (orkWorks/orkUI) | §1 | `office/signs/` gains `play`, `pause`, `sound`, `film`, `text` (7 × 7, as spec 50 §1.6), `.ork-sign` their classes, the gallery, README, CHANGELOG (**0.3.2**), the versions; `tests/test_orkui.py`. Then the copy into orkBoard |
| **A. Backend** | §2–§4 | new `realm/idea_pick.py` (the manifest, its checks, the kinds, the store), `core/idea_task.py` (the variants' ask and their reading after the task), `core/idea_runner.py` (the *picking* state; the pick's commit; a new round), `realm/ideas.py` (`picking` among a task's states), `core/idea_keeper.py` (the plan's `pick` on a task), `gui/ideas.py` (`ideas.pick`; the Needs you row), new `gui/media.py` (the route's signing and serving) with `gui/server.py` and `gui/phones.py` (the route), `realm/board_map.py` (a task's `pick`), `realm/event_log.py` (`PICK_ASKED`, `PICK_ANSWERED`), `realm/board_today.py`, `gui/phone_push.py`, `realm/lexicon.py` (`pick`), `gui/ideas_args.py` (`VIA` += nothing new; `OPENED` += `pick`); new `tests/test_idea_pick.py`, new `tests/test_media_route.py`, and the tests of the files it changes |
| **B. Desktop** | §5, §6 | new `js/arena/picks.js` (the tiles, the card's and the drawer's), `js/arena/stops.js` (the kind), `js/shell/` (the drawer's *Pick one*), `arena.css`; new `tests/test_pick_desktop_browser.py` |
| **C. Phone** | §5, §7 | new `pwa/shell-picks.js`, `pwa/shell-stops.js` (the kind; the raised card), `pwa/shell-preview.js` (its own screen), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up, `SHELL`; media never cached) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_pick_browser.py` |

## 0. The words
- **Pick one** (`TERMS` `pick`, *pick / picks*): the stop and its screen. A task that waits for it is *asks you to pick*.
- *n pictures* · *n sounds* · *n clips* · *n texts* (the kind's word), *Take B*, *Take the one you pick*, *Pick, with a
  note…*, *Add a note…*, *None of them: make new ones*, *Say why, or what to change (it goes to <member>)*, *A note
  says what to change: write one first*, *Picked B*, *new ones asked*, *Play*, *Pause*, *Open it on its own screen*.
- A variant's key is a capital letter in order (*A*, *B*, …); its label is *B · <its name>* (the task's name for it,
  ≤ 24 characters).
- spec 50 §0's rules hold: the interface says *party*, *goal*, *task*; no *card*, *deck*, *hand*; every symbol is
  orkUI's (§1).

## 1. orkUI: five more signs (A0)
As spec 50 §1.6 (`office/signs/<name>.svg`, `.ork-sign.<name>`, 14/28, the text's colour):

| play | pause | sound | film | text |
|---|---|---|---|---|
| `.#.....` | `.......` | `...#...` | `#######` | `#######` |
| `.##....` | `.##.##.` | `..##.#.` | `#.#.#.#` | `.......` |
| `.###...` | `.##.##.` | `####..#` | `#######` | `#####..` |
| `.####..` | `.##.##.` | `####..#` | `#.....#` | `.......` |
| `.###...` | `.##.##.` | `####..#` | `#######` | `######.` |
| `.##....` | `.##.##.` | `..##.#.` | `#.#.#.#` | `.......` |
| `.#.....` | `.......` | `...#...` | `#######` | `####...` |

*play* and *pause* a sound's or a clip's control, *sound* a sound's tile, *film* a clip's tile, *text* a text's tile.
Gallery, README, CHANGELOG **0.3.2**, tests as spec 50 §1.5.

## 2. A task that makes variants (A)
### 2.1 The plan asks for them
- A task of the plan may carry **`pick`**: `{"n": 2–6, "kind": "image" | "audio" | "video" | "text", "ask": "<the
  question, one line>", "target": "<the repository path the picked one is written to>"}`. The Taskmaster's plan prompt
  (`core/idea_keeper.py`) says when: the goal's spec asks to choose by eye or by ear (a logo, an icon, a sound, a clip,
  a name or a tagline), at most one such task per goal at a time, never for code. A plan written before has none.
- `realm/idea_pick.py` `KINDS`: `image` (`png`, `jpeg`, `gif`, `webp`, `svg`), `audio` (`mpeg`, `ogg`, `wav`, `mp4`
  audio), `video` (`mp4`, `webm`), `text` (`plain`, `markdown`); a kind's word (§0) and its limits: a file at most
  10 MB (an image, a sound), 50 MB (a clip), 4 KB (a text); 120 MB a pick in all.

### 2.2 The task's ask and its end
- The task's prompt (`core/idea_task.py`), when its plan's task has `pick`: make **n** variants of the kind for the
  ask; write each as a file into `.orkcraft-pick/` at the worktree's root and a manifest
  `.orkcraft-pick.json`: `{"variants": [{"name": "<≤ 24 chars>", "file": "<its file name in .orkcraft-pick/>",
  "why": "<one line>"}]}`; change nothing else (as a check's findings file, `realm/idea_checks.FINDINGS_FILE`, is read
  and never committed).
- After the task, the runner reads it (`idea_pick.read(worktree, task)`): the manifest is valid JSON with n variants,
  each file inside the folder, its media type **sniffed from its bytes** (never from its name) and of the task's kind,
  within the limits. Then the files move to the goal's state folder, `<state>/ideas/<goal>/picks/<task>-r<round>/`,
  with `pick.json`: `{"id", "task", "round", "by", "kind", "ask", "target", "at", "variants": [{"key", "name", "file",
  "mime", "bytes", "w", "h", "seconds", "why"}]}` (`w`, `h` for an image or a clip when they can be read without a
  tool; `seconds` for a sound or a clip when it can; else `null`), the folder and the manifest leave the worktree, and
  the task's state is **`picking`**. Nothing is committed.
- A manifest missing, broken, of another kind or over a limit: the task **fails** with the reason in plain words (*The
  task left 3 sounds; its plan asked for 4*, *B is a picture, not a sound*, *C is 72 MB: a clip is at most 50 MB*) and
  the files are removed.

### 2.3 The person picks
- **`ideas.pick {slug, task, key, note, via}`**: `key` one of the variants' keys, or `null` for *None of them*; `note`
  at most 2 000 characters, **required when `key` is `null`** (*A note says what to change: write one first*).
- A key: the runner writes the picked file to `target` in the task's worktree, commits it (*<task title>: B · <name>*),
  and the task ends as any task with a change does (the gate's checks, then Review or a merge as the project says);
  the pick's `pick.json` gains `{"picked": "B", "note", "at"}`. The note is the task's `note` and is told to the tasks
  that wait for it (*The person picked B · anchor: "<note>"*).
- `null`: the task runs again as its next round with the note (*None of the last variants: "<note>"*); the old round's
  variants stay in the state folder (the history) and `pick.json` gains `{"picked": null, "note", "at"}`.
- A pick answered twice, or of a task not `picking`: refused (*That pick is answered already*). Stop all stops a task
  that is making variants as any; a `picking` task waits, spending nothing.

### 2.4 What the faces read
- **Needs you** gains a row of kind **`pick`**: `{kind: "pick", slug, task, title, by {slug, name, head}, ask, n,
  media: "image"|"audio"|"video"|"text", variants: [{key, name, url, mime, w, h, seconds, text?}], round, at}` (`text`:
  a text variant's words, inline, at most 4 KB; the others by `url`).
- `ideas.map`'s task gains `pick` (`{n, media, round}` while `picking`, else none) and the state `picking`; its foot on
  the faces: *asks you to pick*.
- `ideas.today`: `pick_asked` (*Pick one: <task>*, the alert tone) and `pick_answered` (*Picked B: <task>* or *New ones
  asked: <task>*).
- The push (`gui/phone_push.py`): a pick that waits is an answer that waits (*<member> asks you to pick one*).
- Events: `pick_asked` `{idea, task, n, media, round}`, `pick_answered` `{idea, task, key, note_chars, via, seconds}`
  (seconds from asked to answered); `OPENED` gains `pick`.

## 3. The files' route (A)
- **`GET /media/<goal>/<pick-id>/<file>?s=<signature>`** on the page's server and on the phones' listener
  (`gui/media.py`): the file from that pick's folder only (a name with `/` or `..` is refused), its stored media type,
  **Range** requests (206, so a sound or a clip seeks), `Cache-Control: private, max-age=31536000, immutable` (a
  round's files never change), `X-Content-Type-Options: nosniff`, and `Content-Security-Policy: sandbox;
  default-src 'none'` with `Content-Disposition: inline; filename=…` (an SVG opened on its own runs nothing).
- **The signature**: an HMAC of the path with a secret the host keeps for its life (`secrets.token_bytes(32)`); the
  host signs every `url` it sends (§2.4), so an `<img>`, `<audio>` or `<video>` loads it without a header, and nothing
  but what the paired faces were given can be fetched. No signature, a wrong one or a path of another pick: 404.
- The phone's service worker never caches `/media/` (network only).

## 4. Measured (A)
From the events: how many picks a week, the share taken at the first round against *None of them*, the time to pick,
where it was answered (`via`: *hand*, the drawer, the phone's screen), and a note's share. They feed the owner's next
call (more variants or fewer, which kinds).

## 5. The tiles (B, C)
One component per kind, the same on both faces:
- **image**: the picture *contained* on the canvas ground, never cropped, never scaled up past 2× (pixel art stays
  crisp: `image-rendering: pixelated` only when it is 64 px or less on its side), its alt the variant's label.
- **video**: the clip's first frame (`<video preload="metadata" playsinline muted>`), the `film` sign and its length
  in a corner; *Play* (the `play` sign) plays it in the tile with its sound off until the person turns it on; one
  plays at a time.
- **audio**: the `sound` sign, its length, *Play*/*Pause*, a thin bar of where it is; one plays at a time.
- **text**: its words in the tile (the `text` sign), the first lines, the rest on its own screen.
- Each tile: its label strip under it (*B · monogram*) which **picks it** (a radio of the group, `aria-checked`), the
  picked one in a double ink line with the `check` sign; playing never picks. Nothing plays by itself.

## 6. The desktop (B)
- **The stop** in the bottom row (spec 49 §6): kind *Pick one*, its gem the count (*4*), the member's head, the tiles
  small (2 × 2 in the raised card), *Take B* once one is picked on the card, and *Pick, with a note…* (*Add a note…*
  once picked) that opens the drawer.
- **The drawer's Pick one**: the ask, the tiles large (four across at 1 440, fewer when wider is needed), ← → between
  them, the note, *Take B* and *None of them: make new ones* (the note first). Sending answers `ideas.pick` with
  `via: "hand"` from the card and `"drawer"` from the drawer.
- A task `picking` on the field: its card's foot *asks you to pick* with the `alert` sign.

## 7. The phone (C)
- **The stop**: its raised card (spec 49 §10.6) holds the ask, the tiles 2 × 2 (a clip and a sound play in their tile),
  the note, *Take B* and *None of them: make new ones*, and *Open it on its own screen*: the tiles one to a screen,
  swiped (snap), the note and the same two buttons under them. `via: "hand"` or `"screen"`.
- 44 px targets; a tile's label strip and its *Play* are separate targets.

## 8. Tests
- **A0**: the five signs as spec 50 §1.5.
- **A**: `idea_pick.read` on a worktree (valid; a missing manifest; a wrong count; a file outside the folder; a kind
  sniffed from bytes that its name lies about; each limit), the move to the state folder, `pick.json`, the task's
  `picking`; `ideas.pick` with a key (the file at `target`, the commit's message, the note to the tasks after), with
  `null` (a note required; the next round; the history kept), twice (refused); the Needs you row and the map's task;
  the route (a signed URL served with its type and headers; Range; a wrong signature, no signature, `..`, another
  pick: 404; the SVG's CSP); the events, today's rows, the push.
- **B / C**: each kind's tile (an image, a clip's frame and *Play*, a sound's *Play*/*Pause* and length, a text),
  picking by the label strip and not by *Play*, one playing at a time, *Take B*'s command with its `via`, *None of them*
  asking for the note, the drawer's (the phone's own screen's) ← → or swipe, nothing playing by itself, reduced motion;
  the phone's 44 px targets; the service worker never caching `/media/`.

## 9. Not in this spec
- Mixing kinds in one pick; more than six variants; ranking or picking several; a variant edited in place.
- Variants of code (a pick is never code: two branches to compare is another spec).
- Making the files: the task's own tools make them (an image model, a synthesizer, a script); the Board gives none.

## 10. As built (notes, no change of the contract)
- **A (the host).** Built as §2–§4, with these choices. (1) *Where it lives.* The reading of the files is `realm/idea_pick.py` (the kinds, the manifest, the store, `pick.json`) over `realm/media_sniff.py` (the type from the bytes, the size and the length: PNG, JPEG, GIF, WEBP, SVG, WAV, MP3 with a Xing header, MP4; the rest null, no tool); the runner's half is `core/idea_picking.py` (`PickMixin`: `_variants` after the session, `pick`), since `idea_runner.py` was at its 600 lines; `core/idea_plan.py` holds the plan's small helpers (`_task`, `estimate`, `readiness`, `_why`), moved out of `idea_keeper.py` (which re-exports them) for the same reason; the host's half is `gui/ideas_pick.py` (`ideas.pick`, the row). The phones' listener serves the route from `gui/phone_http.py` (the listener's HTTP handler, where its other paths are), not `gui/phones.py`. (2) *A stored file is `<key>.<ext>`* (`a.png`, `b.svg`), never the name the task chose, so a name is never a path, a dot-file or a surprise in a URL; `pick.json`'s `file` is that name. A text is `text/markdown` when its name ends in `.md`/`.markdown` (the bytes cannot say), else `text/plain`; every other type is the bytes'. A variant's name is cut to 24 characters (one line), and is the file's stem when the manifest gives none; `why` is cut to 300. (3) *Change nothing else* is enforced: after the variants are stored the worktree is put back as it was cut (`git reset --hard` to the task's base and `git clean -fd`, `IdeaGit.restore`), so a script the task wrote to make them, or anything it committed, is not kept and cannot ride along with the picked file. (4) *`pick.json` after an answer*: `picked`, `note` and `at` as the spec says, `at` being the time of the answer; the time it was asked is kept as `asked_at`. The history of a task is `idea_pick.history`; a task started anew (Start again, a hold) goes on from the next round, so no folder of an earlier one is replaced (`next_round`). (5) *`ideas.pick`'s `via`* is `VIA` plus its own `hand`, `drawer`, `screen` (`gui/ideas_pick.py` `PICK_VIA`; `VIA` itself is unchanged, as the file list says): the drawer's and the phone's own screen's presses are told apart in the event as §4 asks; any other value is read as `idea`. `pick_answered` also carries `round` and `device`. (6) *The commit*: the picked file is written to `target` (a link of the project's own at that path is replaced, never followed), committed alone with `<task title>: B · <name>` (`IdeaGit.commit_file`), and the task goes on as `running` into the gate with no new turn: `_work` with `again = {"taken": True}` skips the session and runs the gate, its one fix turn, and Review or the merge. A place git ignores, a path that is outside the project, or a file that is there already (nothing would change) is a refusal in words, and the pick stays asked. `picked` (`{key, name, note}`) stays on the task and is what the tasks after it are told (`The person picked B · anchor: "<note>"`, in their prompt's *tasks before yours*); the task's `note` is the note until the merge writes its own. *None of them* needs the note, writes `picked: null` in `pick.json`, sets round + 1 and resumes the task's session with *None of the last variants: "<note>"* and the ask again; a limit that holds that round puts the task back to `held`. (7) *More than the spec names*: `drop_task` also drops a `picking` task (else a pick the person does not want would wait for ever); Start again leaves a `picking` task as it is; `ideas.map` says `waits.kind = "you"` for a goal with a task `picking` and a party member `needs` with `why: "pick"`; the Agents window does not list a `picking` task. `realm/ideas.py` names the task states (`TASK_STATES`). (8) *The row* (`kind: "pick"`) also carries `idea` (= `slug`), `goal` (its party), `short`, `idea_title`, `priority`, `blocks: true` (so it sorts among what blocks work in progress) and, on each variant, `why`; `title` is the task's. A face reads `ideas.board`'s `needs_you`; a text's words (`text`) are inline, the rest by their `url`. The map's task always has `pick` (`null` when it is not `picking`). (9) *Today*: `pick_asked` is mark `!` in the tone `alert` (words *Pick one*), `pick_answered` is `✓` `ok` *Picked B* or `↺` `muted` *New ones asked*; all three open `{kind: "pick", slug, task}`. (10) *The push* says *<member> asks you to pick one* from `phone_push.PICK_WORDS`, apart from `KIND_WORDS` (which `tests/test_phone_push.py` holds equal to the desktop's table until B adds `pick` there); a pick is counted in `needs_you`, so it is an answer that waits like any. (11) *The route*: the signature is the first 128 bits of an HMAC-SHA256 of the path (`/media/<goal>/<pick-id>/<file>`) with `secrets.token_bytes(32)` made at the process's start (an address from an earlier run is dead); the file is looked for in the open projects' state folders, the shown one first, and only if its `pick.json` lists it; a method but GET and HEAD is a 405, a range past the end a 416; a text is served `; charset=utf-8`; the page's server reads the slice into one response, the phones' listener streams it in 256 KB chunks. (12) *The plan*: a `pick` that is not good (n outside 2–6, an unknown kind, no ask, a target that is absolute, outside the project, git's or the machine's own, or a Board page) is dropped and the task is then an ordinary task; a check task never has one; *at most one such task per goal at a time* is the Taskmaster's prompt's to say, nothing enforces it. (13) *Sizes in a reason* are to the nearest MB (KB under one), with one decimal when a file is over its limit by less than the unit (*10.3 MB: a picture is at most 10 MB*).
