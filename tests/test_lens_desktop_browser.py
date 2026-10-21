"""The lens of New goal on the desktop (js/shell/lens.js, lensscreen.js; realm/idea_lens.py), as the phone's: the goal's party's
lenses, its leader's open first; a product manager's pain, an engineer's parts of the repository, a designer's screen with areas
marked; the text alone always enough; the spec says what the goal pointed at. The host is the stub (tests/test_shell_browser.py)."""
from __future__ import annotations

import base64
import os

from tests.browser_kit import WAIT_MS, gui  # noqa: F401  (fixture)
from tests.test_pwa_idea_field_browser import _png
from tests.test_pwa_lens_browser import PARTS, PARTY
from tests.test_shell_browser import SHOTS, StubHost, _calls, _new_goal, _open, _open_goal, _show_goal


def test_the_leader_s_lens_is_open_first_each_lens_points_its_way_and_the_spec_says_what_was_pointed_at(gui):
    host = StubHost()
    host.lens, host.parts = PARTY, PARTS
    host.screen_png = base64.b64encode(_png(600, 400)).decode()
    pg, host, errors = _open(gui, host=host)
    try:
        _show_goal(pg)
        dlg = _new_goal(pg)
        bar = dlg.get_by_role("radiogroup", name="Lens")
        bar.wait_for(timeout=WAIT_MS)
        assert bar.get_by_role("radio", name="Pain").get_attribute("aria-checked") == "true"             # the leader's
        assert [r.get_attribute("aria-label") for r in bar.get_by_role("radio").all()] == [
            "Text", "Code · Architect", "Screen · UI kit designer", "Pain · Product manager"]
        dlg.get_by_label("Your goal").fill("Orders are never lost")
        dlg.get_by_role("group", name="Kept segments").get_by_role("button", name="Shop owners").click()
        dlg.get_by_role("group", name="Their pains").get_by_role("button", name="Orders get lost").click()
        bar.get_by_role("radio", name="Code").click()
        dlg.get_by_role("button", name="Pick: app/core").click()
        assert "is-near" in dlg.get_by_role("button", name="Pick: app", exact=True).get_attribute("class")
        dlg.get_by_label("What to change there").fill("Keep each order until the till has it")
        bar.get_by_role("radio", name="Screen").click()
        dlg.get_by_role("group", name="The project's screens").get_by_role("button", name="Orders").click()
        shot = dlg.locator(".shell-lens-shot")
        shot.wait_for(timeout=WAIT_MS)
        pg.wait_for_timeout(100)
        shot.scroll_into_view_if_needed()
        box = shot.bounding_box()
        pg.mouse.move(box["x"] + box["width"] * 0.1, box["y"] + box["height"] * 0.2)
        pg.mouse.down()
        pg.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.4, steps=4)
        pg.mouse.up()
        dlg.get_by_label("Mark 1: what to change").fill("Say which orders wait")
        if os.environ.get("ORKCRAFT_SHOTS"):
            SHOTS.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(SHOTS / "desktop-lens-screen-1440x900.png"))
        bar.get_by_role("radio", name="Pain").click()                                                    # switching loses nothing
        assert dlg.get_by_label("For whom").input_value() == "Shop owners"
        if os.environ.get("ORKCRAFT_SHOTS"):
            pg.screenshot(path=str(SHOTS / "desktop-lens-pain-1440x900.png"))
        dlg.get_by_role("button", name="Add the goal").click()
        sent = _calls(pg, host, "ideas.add")[-1]
        assert [x["kind"] for x in sent["lens"]] == ["pain", "code", "screen"]
        assert sent["lens"][0] == {"kind": "pain", "segment": "Shop owners", "pain": "Orders get lost"}
        assert sent["lens"][1] == {"kind": "code", "paths": ["app/core"], "note": "Keep each order until the till has it"}
        mark = sent["lens"][2]["marks"][0]
        assert sent["lens"][2]["screen"] == "abc123" and mark["note"] == "Say which orders wait" and abs(mark["x"] - 0.1) < 0.03
        host.ideas["dark"]["lens"] = [{"kind": "pain", "segment": "Shop owners", "pain": "Orders get lost"},
                                      {"kind": "screen", "screen": "abc123", "name": "Orders", "marks": [{"x": 0.1, "y": 0.2, "w": 0.4, "h": 0.2, "note": "Say which orders wait"}]}]
        host.bump({})
        _open_goal(pg, "Dark mode")
        pointed = pg.locator(".shell-preview").get_by_role("list", name="Pointed at")
        pointed.wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in pointed.get_by_role("listitem").all_inner_texts()] == [
            "Pain · Shop owners Orders get lost", "Screen · Orders 1) Say which orders wait"]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_with_no_lens_in_the_party_the_dialog_is_the_text_alone(gui):
    pg, host, errors = _open(gui)
    try:
        _show_goal(pg)
        dlg = _new_goal(pg)
        dlg.get_by_label("Your goal").fill("Dark mode please")
        assert dlg.get_by_role("radiogroup", name="Lens").count() == 0
        dlg.get_by_role("button", name="Add the goal").click()
        assert _calls(pg, host, "ideas.add")[-1] == {"text": "Dark mode please", "track": "ship-sync", "priority": "normal"}
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
