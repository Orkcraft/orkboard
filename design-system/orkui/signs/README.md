# orkUI / office / signs

The twenty-nine signs: **every symbol a face draws is orkUI's** (orkBoard's spec 50 §1.6, spec 51 §1 and spec 52 §1 and spec 56 §6, decisions §63.10 and §69). A sign stands beside the
words it explains (a state, a stop, an order), in the colour of that text; it is never the only thing that says it, so the words
(or a `title`) stay and the sign is `aria-hidden`.

    check   a done thing (✓)                         cross   a failure (✗)
    work    at work (↻)                              night   held for tonight (a clock)
    alert   a stop that asks (!)                     flag    a goal in main (⚑)
    before  what a task waits for (←)                after   what waits for it (→)
    play    a sound's or a clip's control (▶)        pause   a sound's or a clip's control (‖)
    sound   a sound's tile (a loudspeaker)           film    a clip's tile (a film strip)
    text    a text's tile (lines of text)

A goal type's mark (spec 52 §1 and spec 56, decisions §65.4 and §69: a type is told by its sign, never by a colour; every type has its own sign, a thing of the realm,
never a being; the thing drawn in brackets):

    feature      a new thing people can do (a wand)
    bug          a thing that goes wrong (a beetle)
    tidy         the same behaviour in simpler code (a broom)
    restructure  modules split or moved (an anvil)
    screen       a screen (a mirror)
    picture      a picture or an icon (a gem)
    logo         a mark for the product (a seal)
    target       a pain of someone's (an arrow)
    flask        an experiment (a beaker)
    horn         a launch (a bell)
    chart        a number (standing stones)
    page         a report (a scroll)
    abtest       two versions, one decided by a number (a fork)
    landing      a page that says the product (a signpost)
    post         a post for one channel (a letter)
    tagline      one line that says the product (a quill)

The sixteen pictures are also in `../emblems/` (the library), with twelve more that no face draws.

*night* is a clock: a crescent is the *void* element (`../elements/`), so a moon would say two things. The close (×), the plus (+)
and the chevrons (›, ⌄) are not here: they are orkUI's icons already (`../icons/icons.svg`).

Each is a **7 x 7** grid of unit squares, one `path` (`M{x} {y}h1v1h-1z` for every pixel, row by row from the top), `viewBox="0 0
7 7"`, `fill="#000"`, `shape-rendering="crispEdges"`: no colour of its own, no metadata. They are **drawn as masks**:
`.ork-sign` in `components.css` fills a 14 x 14 box (`.big` 28 x 28, two or four pixels a cell, whole pixels) with
`background: currentColor` through `mask-image: url(signs/<name>.svg)`, so a sign takes the colour of the text it stands in and the
file's black is only the shape. `vertical-align: -3px` sets the 14 px box on the baseline of a 16 px line.

    <span class="ork-sign check" aria-hidden="true"></span> done           14 x 14, in the text's colour
    <span class="ork-sign alert big" aria-hidden="true"></span>            28 x 28
    <span style="color: var(--ork-danger)"><span class="ork-sign cross" aria-hidden="true"></span> failed</span>

A sign takes the signal colour of its text (success, danger, alert) or the muted ink, never a colour of its own: colour is a
signal, and the sign does not add one. A shape is changed here, in the table of `tests/test_orkui.py` and in orkBoard's spec 50
§1.6 (spec 51 §1 for the media signs, spec 52 §1 and spec 56 §6 for the goal types') together, never in a face.
