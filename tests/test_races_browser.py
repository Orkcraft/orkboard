"""Who does a task, as orkUI draws it (decisions §53, docs/specs/40-design-system.md §6): on Agents each agent wears the head of
its craft's race (an ork engineers, an elf designs, a goblin minds the data, a gnome markets) in its tier's gear, each chip the
head of who runs it, small: a head is an accent, not a picture; the agent's dialog picks the craft and shows the head it will wear; the Agents tab is an ork. The desktop
at 1 440 × 900 and 800 wide, the phone at 390 × 844, against the stubs of the shell's tests with the host's heads
(realm/roles.py `head`). Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import roles  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_36_browser import Stub36  # noqa: E402
from tests.test_shell_browser import SHOTS, _open  # noqa: E402

pytestmark = pytest.mark.browser

MINE = {"layout": {"slug": "layout", "name": "Layout", "model": "elder", "max_parallel": 1, "instruction": "", "builtin": False, "craft": "design"},
        "seer": {"slug": "seer", "name": "Seer", "model": "", "max_parallel": 2, "instruction": "", "builtin": False, "craft": "data"},
        "herald": {"slug": "herald", "name": "Herald", "model": "laborer", "max_parallel": 1, "instruction": "", "builtin": False, "craft": "marketing"}}
BUILTIN = {"taskmaster": {"model": "elder", "craft": "engineering"}, "grunt": {"model": "", "craft": "engineering"}}


def _crafts(target="balance"):
    models = ["", *roles.TIERS]
    return [{"craft": c, "label": roles.CRAFT_LABELS[c], "race": roles.RACES[c], "heads": {m: roles.head_tier(m, target) for m in models}}
            for c in roles.CRAFTS]


def _heads(name, got, all_roles, a=None):
    """What the host adds to a stub's answer: each role's head and craft, each chip's head, the crafts (realm/roles.py)."""
    def role_of(slug):
        return {**BUILTIN.get(slug, {}), **all_roles.get(slug, {})} or BUILTIN["grunt"]
    if name == "ideas.agents":
        for b in got["roles"]:
            b["head"] = roles.head(role_of(b["role"]), "balance")
            for c in b.get("chips") or []:
                if "task" in c:
                    c["head"] = roles.head(role_of(c.get("role") or b["role"]), "balance", c.get("tier") or "warrior")
    if name == "ideas.roles":
        for r in got["roles"]:
            r["craft"] = role_of(r["slug"]).get("craft", "engineering")
            r["head"] = roles.head(role_of(r["slug"]), "balance")
        got["crafts"] = _crafts()
    if name == "ideas.role_save" and a and a.get("craft"):
        all_roles[got["slug"]]["craft"] = a["craft"]
    return got


class StubRaces(Stub36):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.roles.update({k: dict(v) for k, v in MINE.items()})
        self.kinds["research"] = "seer"

    def handle(self, name, a):
        return _heads(name, super().handle(name, a), self.roles, a)


def _src(locator):
    return locator.get_attribute("src")


def _drawn(pg, selector):
    return pg.evaluate(f"[...document.querySelectorAll({selector!r})].every((i) => i.complete && i.naturalWidth > 0)")


@pytest.fixture
def races(gui):
    pg, host, errors = _open(gui, host=StubRaces())
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def test_each_agent_wears_its_crafts_race_in_its_tiers_gear_and_each_chip_the_head_of_who_runs_it(races):
    pg, host = races
    agents = pg.locator(".shell-agents")
    agents.locator(".shell-role[data-slug=layout]").wait_for(timeout=WAIT_MS)
    head = lambda slug: agents.locator(f".shell-role[data-slug={slug}] .shell-role__head > img.ork-race__head")       # noqa: E731
    assert _src(head("layout")).endswith("/ds/orkui/races/elf-elder.png")             # design, on the elder tier: a hooded elf
    assert _src(head("seer")).endswith("/ds/orkui/races/goblin-warrior.png")          # data, By Target in balance: a goblin in iron
    assert _src(head("herald")).endswith("/ds/orkui/races/gnome-laborer.png")         # marketing, a novice: a bare gnome
    assert _src(head("grunt")).endswith("/ds/orkui/races/peon-warrior.png")           # the Grunts: orks
    assert _src(agents.locator(".shell-role[data-role=taskmaster] img.ork-race__head")).endswith("/ds/orkui/races/peon-elder.png")
    assert head("layout").get_attribute("title") == "Veteran elf · Design"
    facts = agents.locator(".shell-role[data-slug=seer] .shell-role__facts").inner_text()
    assert facts.startswith("Data · By Target, now Seasoned")
    chip = agents.locator(".shell-role[data-role=grunt] .shell-chip[data-state=running]").first
    assert _src(chip.locator("img.ork-race__head")).endswith("/ds/orkui/races/peon-warrior.png")
    assert head("layout").get_attribute("srcset").endswith("elf-elder@2x.png 2x")              # sharp on a sharp screen
    assert _drawn(pg, ".shell-agents img.ork-race__head")                              # every head is served and drawn
    box, small = head("layout").bounding_box(), chip.locator("img.ork-race__head").bounding_box()
    assert (box["width"], box["height"]) == (24, 22) and (small["width"], small["height"]) == (12, 11)   # an accent: a cell a pixel in a chip
    if __import__("os").environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-agents-races-1440x900.png"))


def test_the_agents_dialog_picks_the_craft_and_shows_the_head_it_will_wear(races):
    pg, host = races
    pg.locator(".shell-agents").get_by_role("button", name="+ Add agent").click()
    dialog = pg.get_by_role("dialog", name="Add agent")
    craft = dialog.get_by_label("Craft")
    assert [" ".join(o.text_content().split()) for o in craft.locator("option").all()] == [
        "Engineering: an ork", "Design: an elf", "Data: a goblin", "Marketing: a gnome"]
    who = dialog.locator(".shell-agent__who img.ork-race__head")
    assert _src(who).endswith("races/peon-warrior.png")                             # a new agent: an ork, By Target
    craft.select_option("design")
    dialog.get_by_label("Model").select_option("elder")
    assert _src(who).endswith("races/elf-elder.png") and "Veteran" in dialog.locator(".shell-agent__who").inner_text()
    dialog.get_by_label("Name").fill("Painter")
    dialog.get_by_role("button", name="Save agent").click()
    pg.locator(".shell-role[data-slug=painter]").wait_for(timeout=WAIT_MS)
    assert next(a for n, a in host.log if n == "ideas.role_save")["craft"] == "design"
    pg.locator(".shell-role[data-slug=grunt]").get_by_role("button", name="Edit Grunts").click()
    dialog = pg.get_by_role("dialog", name="Edit agent")
    assert dialog.get_by_label("Craft").is_disabled() and "orks" in dialog.inner_text()   # Taskmaster and Grunt are orks


def test_below_1024_the_agents_tab_is_an_ork(gui):
    pg, host, errors = _open(gui, viewport={"width": 800, "height": 900}, host=StubRaces(), ready=".shell-tabs")
    try:
        tab = pg.get_by_role("tab", name="Agents")
        assert _src(tab.locator("img.ork-race__head")).endswith("/ds/orkui/races/peon-laborer.png")
        assert pg.get_by_role("tab", name="Board").locator("svg.ork-icon use").get_attribute("href").endswith("#list-box")
        assert _drawn(pg, ".shell-tabs img")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
