# orkUI / office / signs

The eight signs: **every symbol a face draws is orkUI's** (orkBoard's spec 50 §1.6, decisions §63.10). A sign stands beside the
words it explains (a state, a stop, an order), in the colour of that text; it is never the only thing that says it, so the words
(or a `title`) stay and the sign is `aria-hidden`.

    check   a done thing (✓)                         cross   a failure (✗)
    work    at work (↻)                              night   held for tonight (a clock)
    alert   a stop that asks (!)                     flag    a goal in main (⚑)
    before  what a task waits for (←)                after   what waits for it (→)

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
§1.6 together, never in a face.
