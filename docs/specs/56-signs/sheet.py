"""Spec 56 part G: check the fantasy-sign candidates and write sheet.html.

    python docs/specs/56-signs/sheet.py             check candidates.json, write sheet.html
    python docs/specs/56-signs/sheet.py --selftest  check that the checks reject a bad grid and a copy of `cross`

Stdlib only. The reserved signs and the elements are read from design-system/orkui/ (spec 56 §2.3); the colours
from its tokens.css. Exit status is non-zero, naming each candidate, when a check fails.
"""

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORKUI = HERE.parents[2] / "design-system" / "orkui"
CANDIDATES = HERE / "candidates.json"
SHEET = HERE / "sheet.html"

TYPE_IDS = {
    "feature": "a new thing people can do",
    "bug": "something that goes wrong",
    "tidy": "the same behaviour in simpler code",
    "restructure": "modules split or moved",
    "screen": "a screen",
    "icon": "a picture or an icon",
    "logo": "a mark for the product",
    "pain": "a pain of someone's",
    "experiment": "a change shown to some, measured",
    "launch": "the words people read when it ships",
    "metric": "a number counted from events",
    "report": "numbers that answer a question",
    "abtest": "two versions, one decided by a number",
    "landing": "a page that says the product",
    "post": "a post for one channel",
    "tagline": "one line that says the product",
}
# the sign each type wears today (spec 52 §1, as spec 56 §2.3 gives it)
CURRENT = {
    "feature": "feature", "bug": "bug", "tidy": "tidy", "restructure": "tidy", "screen": "screen",
    "icon": "picture", "logo": "logo", "pain": "target", "experiment": "flask", "launch": "horn",
    "metric": "chart", "report": "page", "abtest": "flask", "landing": "page", "post": "horn",
    "tagline": "text",
}
RESERVED_SIGNS = ["check", "cross", "work", "night", "alert", "flag", "before", "after", "play", "pause",
                  "sound", "film", "text"]
ELEMENTS = ["meadow", "ice", "dust", "void", "lava"]
MIN_PER_TYPE = 3
MIN_LIBRARY = 12
NEAR = 8  # a candidate within this many differing cells of another sign fails (spec 56 §2.3)
SIZE = 7
PATH_RE = re.compile(r"M(\d+) (\d+)h1v1h-1z")


def read_drawing(path):
    """The unit squares of an orkUI sign or element file, as a set of (x, y) and its viewBox size."""
    text = path.read_text(encoding="utf-8")
    box = re.search(r'viewBox="0 0 (\d+) (\d+)"', text)
    if not box:
        raise ValueError(f"{path}: no viewBox")
    cells = {(int(x), int(y)) for x, y in PATH_RE.findall(text)}
    return cells, int(box.group(1)), int(box.group(2)), text


def to_grid(cells, w=SIZE, h=SIZE):
    return ["".join("#" if (x, y) in cells else "." for x in range(w)) for y in range(h)]


def grid_cells(grid):
    return {(x, y) for y, row in enumerate(grid) for x, c in enumerate(row) if c == "#"}


def distance(a, b):
    """Differing cells of two 7 x 7 grids (cell sets)."""
    return len(a ^ b)


def load_reference():
    """The reserved signs and the elements, as {name: (cells, kind)}, from orkUI's copy."""
    ref = {}
    for name in RESERVED_SIGNS:
        cells, w, h, _ = read_drawing(ORKUI / "signs" / f"{name}.svg")
        if (w, h) == (SIZE, SIZE):
            ref[name] = (cells, "sign")
    for name in ELEMENTS:
        cells, w, h, _ = read_drawing(ORKUI / "elements" / f"{name}.svg")
        if (w, h) == (SIZE, SIZE):
            ref[name] = (cells, "element")
    return ref


def check_shape(c):
    """Errors for one candidate's own fields and grid (not its neighbours)."""
    errors = []
    name = c.get("name")
    label = name if isinstance(name, str) and name else "(no name)"
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        errors.append(f"{label}: the name is not a slug (lowercase letters, digits, dashes)")
    if not isinstance(c.get("meaning"), str) or not c.get("meaning"):
        errors.append(f"{label}: no meaning")
    grid = c.get("grid")
    if (not isinstance(grid, list) or len(grid) != SIZE
            or any(not isinstance(r, str) or len(r) != SIZE or set(r) - {".", "#"} for r in grid)):
        errors.append(f"{label}: the grid is not {SIZE} rows of {SIZE} '.' or '#'")
        return errors
    rows_empty = [all(ch == "." for ch in r) for r in grid]
    cols = ["".join(r[x] for r in grid) for x in range(SIZE)]
    cols_empty = [all(ch == "." for ch in col) for col in cols]
    lead_r = next((i for i, e in enumerate(rows_empty) if not e), SIZE)
    trail_r = next((i for i, e in enumerate(reversed(rows_empty)) if not e), SIZE)
    lead_c = next((i for i, e in enumerate(cols_empty) if not e), SIZE)
    trail_c = next((i for i, e in enumerate(reversed(cols_empty)) if not e), SIZE)
    if lead_r == SIZE:
        errors.append(f"{label}: the grid is empty")
    if lead_r > 1 or trail_r > 1:
        errors.append(f"{label}: more than one empty row at an edge (spec 56 §1.3)")
    if lead_c > 1 or trail_c > 1:
        errors.append(f"{label}: more than one empty column at an edge (spec 56 §1.3)")
    return errors


def validate(cands, ref):
    """Every error, as strings naming the candidate. An empty list means the sheet can be written."""
    errors = []
    names = set()
    for c in cands:
        errors += check_shape(c)
        name = c.get("name")
        if name in names:
            errors.append(f"{name}: a duplicate name")
        names.add(name)
        if c.get("for") not in TYPE_IDS and c.get("for") != "":
            errors.append(f"{name}: for {c.get('for')!r} is not a type id or \"\"")
    if errors:
        return errors
    # the counts (spec 56 §2.2)
    for t in TYPE_IDS:
        n = sum(1 for c in cands if c["for"] == t)
        if n < MIN_PER_TYPE:
            errors.append(f"type {t}: {n} candidates, at least {MIN_PER_TYPE} needed")
    lib = sum(1 for c in cands if c["for"] == "")
    if lib < MIN_LIBRARY:
        errors.append(f"the library: {lib} candidates, at least {MIN_LIBRARY} needed")
    cells = {c["name"]: grid_cells(c["grid"]) for c in cands}
    # against the reserved signs and the elements (spec 56 §1.4, §2.3)
    for c in cands:
        for rname, (rcells, kind) in ref.items():
            d = distance(cells[c["name"]], rcells)
            if d < NEAR:
                errors.append(f"{c['name']}: {d} cells from the {kind} {rname}; more than {NEAR} needed")
    # against each other: two drawings for different types, and two library drawings (spec 56 §1.5, §2.3)
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            if a["for"] == b["for"] and a["for"] != "":
                continue
            d = distance(cells[a["name"]], cells[b["name"]])
            if d < NEAR:
                where = f"drawn for {b['for']}" if b["for"] else "a library drawing"
                errors.append(f"{a['name']}: {d} cells from {b['name']} ({where}); more than {NEAR} needed")
    return errors


# ---- the sheet -------------------------------------------------------------

def read_tokens():
    text = (ORKUI / "tokens.css").read_text(encoding="utf-8")
    values = dict(re.findall(r"(--ork-[a-z0-9-]+):\s*([^;]+);", text))
    need = ["--ork-canvas", "--ork-panel", "--ork-raised", "--ork-frame", "--ork-edge", "--ork-ink",
            "--ork-ink-muted", "--ork-ink-faint", "--ork-font-pixel", "--ork-font-text"]
    need += [f"--ork-elem-{e}" for e in ELEMENTS]
    missing = [n for n in need if n not in values]
    if missing:
        raise ValueError(f"tokens.css lacks {missing}")
    return {n: values[n].strip() for n in need}


def write_sheet(cands, ref):
    tokens = read_tokens()
    symbols = {}  # id -> path data
    def sym(sid, cells):
        if sid not in symbols:
            symbols[sid] = "".join(f"M{x} {y}h1v1h-1z" for y in range(SIZE) for x in range(SIZE)
                                   if (x, y) in cells)
        return sid
    current = {}
    for t, f in CURRENT.items():
        cells, _, _, _ = read_drawing(ORKUI / "signs" / f"{f}.svg")
        current[t] = sym(f"n-{f}", cells)
    for name in ELEMENTS:
        sym(f"e-{name}", ref[name][0])
    for name in RESERVED_SIGNS:
        sym(f"n-{name}", ref[name][0])

    def svg(sid, size, css_color):
        return (f'<svg class="g" width="{size}" height="{size}" viewBox="0 0 {SIZE} {SIZE}" '
                f'shape-rendering="crispEdges" style="color:{css_color}" aria-hidden="true">'
                f'<use href="#{sid}" fill="currentColor"/></svg>')

    def card(name, tag, meaning, sid, cells):
        sym(sid, cells)
        swatches = "".join(
            f'<span class="sw">{svg(sid, 14, f"var(--ork-elem-{e})")}<i>{e}</i></span>' for e in ELEMENTS)
        return (
            f'<figure class="card{" now" if tag == "now" else ""}">'
            f'<figcaption class="tag">{html.escape(tag)}</figcaption>'
            f'<div class="big">{svg(sid, 28, "var(--ork-ink)")}</div>'
            f'<div class="small">{svg(sid, 14, "var(--ork-ink)")}'
            f'<span class="sw">{svg(sid, 14, "var(--ork-ink-muted)")}<i>muted</i></span></div>'
            f'<div class="elems">{swatches}</div>'
            f'<div class="name">{html.escape(name)}</div>'
            f'<div class="meaning">{html.escape(meaning)}</div>'
            f'</figure>')

    out = []
    out.append('<!doctype html><html lang="en"><head><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width, initial-scale=1">'
               '<title>Fantasy signs: candidates</title><style>')
    out.append(f""":root {{
  --ork-canvas: {tokens['--ork-canvas']}; --ork-panel: {tokens['--ork-panel']};
  --ork-raised: {tokens['--ork-raised']}; --ork-frame: {tokens['--ork-frame']};
  --ork-edge: {tokens['--ork-edge']}; --ork-ink: {tokens['--ork-ink']};
  --ork-ink-muted: {tokens['--ork-ink-muted']}; --ork-ink-faint: {tokens['--ork-ink-faint']};
  --ork-font-pixel: {tokens['--ork-font-pixel']}; --ork-font-text: {tokens['--ork-font-text']};
}}
body {{ margin: 0; padding: 16px; background: var(--ork-canvas); color: var(--ork-ink);
  font: 12px/18px var(--ork-font-text); }}
h1 {{ font: 500 16px/20px var(--ork-font-pixel); letter-spacing: .04em; text-transform: uppercase; margin: 0 0 6px; }}
h2 {{ font: 500 14px/16px var(--ork-font-pixel); letter-spacing: .04em; text-transform: uppercase;
  margin: 0 0 8px; }}
p.lede {{ color: var(--ork-ink-muted); margin: 0 0 20px; max-width: 70ch; }}
section {{ margin: 0 0 26px; }}
.row {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.type {{ color: var(--ork-ink-muted); margin: 0 0 6px; }}
.card {{ margin: 0; width: 176px; box-sizing: border-box; background: var(--ork-panel);
  border: 1px solid var(--ork-frame); padding: 8px; }}
.card.now {{ border-color: var(--ork-edge); }}
.tag {{ font: 500 11px/14px var(--ork-font-pixel); text-transform: uppercase; letter-spacing: .06em;
  color: var(--ork-ink-muted); margin-bottom: 6px; }}
.big, .small, .elems {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
.sw {{ display: inline-flex; flex-direction: column; align-items: center; gap: 2px; }}
.sw i {{ font-style: normal; font-size: 9px; color: var(--ork-ink-faint); }}
.elems {{ flex-wrap: wrap; gap: 6px; }}
.name {{ font-family: var(--ork-font-text); color: var(--ork-ink); }}
.meaning {{ color: var(--ork-ink-muted); font-size: 11px; line-height: 15px; }}
svg.g {{ display: block; flex: none; }}
""")
    out.append("</style></head><body>")
    out.append('<h1>Fantasy signs: the candidates</h1>')
    out.append('<p class="lede">Each goal type\'s sign, drawn as a thing of the realm (spec 56 §2). The sign a type wears '
               'today is first, then its candidates, each at 28 and 14 px, in ink, in muted ink and in the five element '
               'colours. The library and the reserved signs follow.</p>')
    for t, meaning in TYPE_IDS.items():
        cs = [c for c in cands if c["for"] == t]
        out.append(f'<section><h2>{t}</h2><p class="type">{html.escape(meaning)}</p><div class="row">')
        now_cells = read_drawing(ORKUI / "signs" / f"{CURRENT[t]}.svg")[0]
        out.append(card(CURRENT[t], "now", f"today's sign: {CURRENT[t]}", current[t], now_cells))
        for c in cs:
            out.append(card(c["name"], c["name"], c["meaning"], f"s-{c['name']}", grid_cells(c["grid"])))
        out.append("</div></section>")
    lib = [c for c in cands if c["for"] == ""]
    out.append('<section><h2>library</h2><p class="type">Things orkUI\'s faces are likely to need. Not for a type.</p>'
               '<div class="row">')
    for c in lib:
        out.append(card(c["name"], c["name"], c["meaning"], f"s-{c['name']}", grid_cells(c["grid"])))
    out.append("</div></section>")
    out.append('<section><h2>reserved</h2><p class="type">Taken: a candidate stays this far off (more than 8 cells). '
               'At 14 px.</p><div class="row">')
    for name in RESERVED_SIGNS:
        out.append(f'<figure class="card"><div class="small">{svg(f"n-{name}", 14, "var(--ork-ink)")}</div>'
                   f'<div class="name">{name}</div></figure>')
    for name in ELEMENTS:
        out.append(f'<figure class="card"><div class="small">{svg(f"e-{name}", 14, f"var(--ork-elem-{name})")}</div>'
                   f'<div class="name">{name} (element)</div></figure>')
    out.append("</div></section>")
    # the shared symbols, once, hidden
    defs = "".join(f'<symbol id="{sid}" viewBox="0 0 {SIZE} {SIZE}"><path d="{d}"/></symbol>'
                   for sid, d in symbols.items())
    out.insert(1, f'<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>{defs}</defs></svg>')
    out.append("</body></html>\n")
    SHEET.write_text("".join(out), encoding="utf-8")


# ---- self-test -------------------------------------------------------------

def selftest():
    ref = load_reference()
    ok = True
    six_rows = ["..###..", ".#...#.", ".#...#.", ".#...#.", "..###..", "...#..."]
    bad = [{"name": "six-rows", "for": "bug", "meaning": "x", "grid": six_rows}]
    errs = validate(bad, ref)
    hit = [e for e in errs if e.startswith("six-rows:") and "7 rows" in e]
    print("six-row grid rejected:", "yes" if hit else "NO")
    ok &= bool(hit)
    cross_copy = to_grid(ref_cross_cells())
    copy = [{"name": "cross-copy", "for": "logo", "meaning": "x", "grid": cross_copy}]
    errs = validate(copy, ref)
    hit = [e for e in errs if e.startswith("cross-copy:") and "sign cross" in e]
    print("copy of cross rejected:", "yes" if hit else "NO")
    ok &= bool(hit)
    return 0 if ok else 1


def ref_cross_cells():
    cells, _, _, _ = read_drawing(ORKUI / "signs" / "cross.svg")
    return cells


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ref = load_reference()
    cands = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    errors = validate(cands, ref)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"{len(errors)} error(s); sheet.html not written", file=sys.stderr)
        return 1
    write_sheet(cands, ref)
    print(f"{len(cands)} candidates pass; wrote {SHEET}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
