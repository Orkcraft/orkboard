"""Orkboard drawn in orkUI (docs/specs/40-design-system.md): design-system/orkui is orkUI's office look as orkUI made it, the
roles map onto its tokens, the page and the phone load it and nothing of the old Camp sheets, and Orkboard's own sheets carry
no colour, no font and no corner of their own."""
from __future__ import annotations

import re

from orkboard.design import orkui, tokens
from orkboard.gui import server

STATIC = server.STATIC
SHEETS = [STATIC / "page.css", STATIC / "js" / "shell" / "shell.css", STATIC / "js" / "board" / "board.css",
          STATIC / "js" / "arena" / "arena.css", STATIC / "pwa" / "app.css"]


def test_the_copy_is_orkuis_office_look_as_stamped():
    assert orkui.problems() == []
    stamp = orkui.stamp()
    assert stamp["from"] == "https://github.com/orkWorks/orkUI" and stamp["look"] == "office" and stamp["version"]
    for name in ("tokens.css", "components.css", "fonts.css", "tokens.json", "LICENSE", "NOTICE", "icons/icons.svg",
                 "races/peon-laborer.png", "races/elf-elder@2x.png", "races/goblin-warrior.png", "races/gnome-laborer.png"):
        assert name in stamp["files"], name
    assert ".ork-race__head" in (orkui.ROOT / "components.css").read_text(encoding="utf-8")


def test_a_hand_edit_of_the_copy_is_caught(tmp_path, monkeypatch):
    copy = tmp_path / "orkui"
    copy.mkdir()
    (copy / "a.css").write_text("x", encoding="utf-8")
    monkeypatch.setattr(orkui, "ROOT", copy)
    monkeypatch.setattr(orkui, "STAMP", copy / "ORKUI.json")
    assert orkui.problems() and "missing" in orkui.problems()[0]
    (copy / "ORKUI.json").write_text('{"files": {"a.css": "0"}}', encoding="utf-8")
    assert orkui.problems() == ["a.css: changed by hand"]


def test_the_roles_wear_orkuis_type_and_colours():
    assert tokens.problems() == []
    css = tokens.roles_css()
    assert ".ok-font-heading { font: var(--ork-type-heading)" in css and ".ok-tone-error { color: var(--ork-danger); }" in css
    declared = set(re.findall(r"^\s*(--[\w-]+):", (tokens.ORKUI / "tokens.css").read_text(encoding="utf-8"), re.M))
    assert set(re.findall(r"var\((--[\w-]+)\)", css)) <= declared


def test_the_page_loads_orkui_and_no_camp_sheet():
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'<link rel="stylesheet" href="([^"]+)">', page)
    assert links[:3] == ["/ds/orkui/fonts.css", "/ds/orkui/tokens.css", "/ds/orkui/components.css"]
    assert 'data-look="office"' in page and "data-theme" not in page
    for href in links:
        assert href == "/roles.css" or server.resolve(href) is not None, href
    for gone in ("layout", "lake", "town", "camp", "yards", "cover", "office", "onboarding", "bench", "lastlook", "inside", "kit"):
        assert not (STATIC / f"{gone}.css").exists(), gone


def test_orkboards_own_sheets_carry_no_colour_no_font_and_no_corner_of_their_own():
    for path in SHEETS:
        css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        drawn = re.sub(r"mask-image:[^;}]*", "", css)                       # a mask's black is its shape, not a colour
        assert not re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", drawn), path.name
        assert not re.findall(r"border-radius", css), path.name
        assert all(f.startswith("var(--ork-font-") for f in re.findall(r"font-family:\s*([^;}]+)", css)), path.name
        assert "[data-look=\"camp\"]" not in css and "[data-theme" not in css, path.name
        legacy = set(re.findall(r"var\((--(?!ork-)[\w-]+)", css)) - {"--agents-h", "--sec", "--role", "--tabs",
                                                                   "--rot", "--dy", "--z", "--ov", "--cols"}   # spec 49: a fan's turn, rise, order and overlap; the columns
        assert not legacy, (path.name, legacy)


def test_every_crafts_head_is_in_the_copy_and_the_pages_words_are_the_glossarys():
    from orkboard.realm import lexicon, roles

    for craft, race in roles.RACES.items():
        assert lexicon.term(f"race.{race}") and lexicon.term(f"craft.{craft}") == roles.CRAFT_LABELS[craft]
        for tier in roles.TIERS:
            for big in (False, True):
                assert (orkui.ROOT / orkui.race_png(race, tier, big)).is_file(), (race, tier, big)
    words = {"TIER_WORDS": {t: lexicon.term(f"tier.{t}") for t in roles.TIERS},
             "RACE_WORDS": {r: lexicon.term(f"race.{r}") for r in roles.RACES.values()},
             "CRAFT_WORDS": {c: lexicon.term(f"craft.{c}") for c in roles.CRAFTS}}
    for path in (STATIC / "js" / "orkui.js", STATIC / "pwa" / "shell-who.js"):
        js = path.read_text(encoding="utf-8")
        for name, want in words.items():
            got = dict(re.findall(r'(\w+): "([^"]+)"', re.search(rf"const {name} = \{{([^}}]*)\}}", js).group(1)))
            assert got == want, (path.name, name)
