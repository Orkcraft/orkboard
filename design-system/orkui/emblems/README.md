# orkUI / office / emblems

The library of **emblems** (orkBoard's spec 56, decisions §69): twenty-eight 7 x 7 drawings of things of the realm (a wand, a beetle, a scroll, an anvil, a key,
a chest, a torch ...), never a being. Sixteen of them are the goal types' pictures, which a face draws as signs (`../signs/`); twelve are kept for what comes next.

**An emblem is not a mask of `components.css`, and no face draws it.** There is no `.ork-emblem` class. A face that needs one asks orkUI to make it a sign
(a `signs/<name>.svg`, a `.ork-sign.<name>` class, a row in the gallery and the tests): then it is a sign, and a face draws that.

`emblems.json` lists them: `[{"name", "meaning", "tags", "sign"}]`. `name` is the file's (`<name>.svg`), `meaning` one line, `tags` words to find it by, and
`sign` the name of the sign that draws it (`wand` is the sign `feature`) or `""` when no face draws it yet. An emblem with a `sign` has that sign's pixels,
exactly.

Each is drawn as the signs are: a **7 x 7** grid of unit squares, one `path` (`M{x} {y}h1v1h-1z` for every pixel, row by row from the top), `viewBox="0 0 7 7"`,
`fill="#000"`, `shape-rendering="crispEdges"`, no colour of its own, no metadata. The gallery (`../preview.html`, *Emblems*) shows each at 14 and 28 px, in ink and
in muted ink, by a mask of its own.

    with a sign   wand (feature)  beetle (bug)  broom (tidy)  anvil (restructure)  mirror (screen)  gem (picture)  seal (logo)  arrow (target)
                  beaker (flask)  bell (horn)  menhirs (chart)  scroll (page)  fork (abtest)  signpost (landing)  letter (post)  quill (tagline)
    the library   chalice  hut  tome  ring  scarab  hammer  key  chest  shield  torch  crown  cairn
