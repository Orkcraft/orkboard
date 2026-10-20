"""Spec 45 part B on the desktop (docs/specs/45-sign-in.md §5, §8, "Tests → B"): in a real browser against a stub host that serves the
snapshot's `sign_in` and the three commands. A tool `needed` with `auto` is asked to sign in once when the person is at the page
(visible and focused), not while it is hidden or unfocused, on its next focus or press; one tool at a time; the toasts of a sign-in
that is open (in the browser, in a terminal, no terminal), done with what goes on, failed, and a browser that did not open; **Sign
in** on the first screen's Check row, on an error line and on the need; *waits: Claude Code's sign-in* on a row and a stop. The
phone's side is in tests/test_pwa_shell_browser.py."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_map_desktop_browser import MapHost, node  # noqa: E402
from tests.test_map_desktop_browser import _open as _open_map  # noqa: E402
from tests.test_shell_browser import StubHost, _calls, _needs, _open, _sent, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

LINE = "Claude Code is not signed in, or its sign-in has expired. Sign in opens Claude Code's sign-in. In a terminal: claude, then /login."
# the page's focus is the test's to give or take: `document.hasFocus()` is what the page asks (spec 45 §5)
AT_PAGE = "window.__at = true; document.hasFocus = () => window.__at;"
AWAY = "window.__at = false; document.hasFocus = () => window.__at;"


def entry(harness="claude", tool="Claude Code", state="needed", by="browser", auto=True, **more):
    """One tool of the snapshot's `sign_in` (core/sign_ins.py)."""
    return {"harness": harness, "tool": tool, "mark": "✱", "state": state, "by": by, "auto": auto, "since": 1700000000.0, "where": "task",
            "why": "", "command": "", "waiting": 0, **more}


def _page(gui, host, init=AT_PAGE, **kw):
    """The page opened with the focus given (or taken) by `init`, the Board's first goal shown."""
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    pg.add_init_script(init)
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.wait_for_selector(kw.get("ready", ".shell-card"), timeout=WAIT_MS)
    return pg, errors


def _toast(pg, text):
    t = pg.locator(".gui-toast", has_text=text)
    t.first.wait_for(timeout=WAIT_MS)
    return t.first


def _opened(host):
    return [a for n, a in host.log if n == "tools.sign_in"]


def test_a_tool_that_needs_a_sign_in_is_asked_to_open_it_once_when_the_page_is_visible_and_focused(gui):
    host = StubHost()
    host.sign_in = [entry()]
    pg, errors = _page(gui, host)
    try:
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude", "auto": True}]
        toast = _toast(pg, "Sign in to Claude Code")                      # open, in the browser: a toast that stays, with Cancel
        assert "Its sign-in opened in your browser. Sign in there: the work that waits for it goes on by itself." in toast.inner_text()
        assert [b.inner_text() for b in toast.locator(".ork-btn").all()] == ["Cancel"]
        pg.wait_for_timeout(600)
        assert len(_opened(host)) == 1                                    # once
        toast.get_by_role("button", name="Cancel").click()
        assert _sent(pg, host, ("tools.sign_in_cancel", {"harness": "claude"}))
        pg.wait_for_timeout(600)
        assert len(_opened(host)) == 1                                    # a cancelled sign-in is not opened again by itself
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_nothing_opens_while_the_page_is_hidden_or_not_focused_it_opens_on_the_next_focus(gui):
    host = StubHost()
    host.sign_in = [entry()]
    pg, errors = _page(gui, host, AWAY)
    try:
        pg.wait_for_timeout(800)
        assert _opened(host) == []                                        # not at 3 a.m. into a browser no one answers
        pg.evaluate("() => { window.__at = true; window.dispatchEvent(new Event('focus')); }")
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude", "auto": True}]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_hidden_page_opens_nothing_and_a_press_on_it_once_it_is_back_opens_it(gui):
    host = StubHost()
    host.sign_in = [entry()]
    hidden = AT_PAGE + "Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => window.__hide ? 'hidden' : 'visible'}); window.__hide = true;"
    pg, errors = _page(gui, host, hidden)
    try:
        pg.wait_for_timeout(800)
        assert _opened(host) == []
        pg.evaluate("() => { window.__hide = false; }")
        pg.mouse.click(4, 4)                                              # a press
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude", "auto": True}]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_two_tools_open_one_at_a_time_the_next_once_the_first_is_no_longer_open(gui):
    host = StubHost()
    host.sign_in = [entry(), entry("codex", "Codex")]
    pg, errors = _page(gui, host)
    try:
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude", "auto": True}]
        pg.wait_for_timeout(800)
        assert _opened(host) == [{"harness": "claude", "auto": True}]     # Codex waits for Claude Code's
        host.handle("tools.sign_in_cancel", {"harness": "claude"})        # Claude Code's is no longer open
        assert _calls(pg, host, "tools.sign_in", at_least=2) == [{"harness": "claude", "auto": True}, {"harness": "codex", "auto": True}]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_terminal_sign_in_says_to_type_what_the_entry_names(gui):
    host = StubHost()
    host.sign_in = [entry("claude", "Claude Code", "open", "terminal", auto=False, type="/login now")]
    pg, errors = _page(gui, host)
    try:
        assert "Type /login now there." in _toast(pg, "Sign in to Claude Code").inner_text()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_sign_in_in_a_terminal_says_where_and_has_copy_done_and_cancel(gui):
    host = StubHost()
    host.sign_in = [entry("pi", "pi", "open", "terminal", auto=False)]
    pg, errors = _page(gui, host)
    try:
        toast = _toast(pg, "Sign in to pi")
        assert "pi signs in in its own window: a terminal opened with pi. Type /login there." in toast.inner_text()
        assert [b.inner_text() for b in toast.locator(".ork-btn").all()] == ["Copy", "Done", "Cancel"]
        toast.locator(".ork-btn", has_text="Copy").click()
        _toast(pg, "Sign in to pi")                                       # Copy keeps it up
        _toast(pg, "Sign in to pi").get_by_role("button", name="Done").click()
        assert _sent(pg, host, ("tools.sign_in_done", {"harness": "pi"}))
        assert _opened(host) == []                                        # it was open already: nothing asked
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_no_terminal_says_the_words_to_type_with_copy(gui):
    host = StubHost()
    host.sign_in = [entry("pi", "pi", "none", "terminal", auto=False, command="pi  (then /login)")]
    pg, errors = _page(gui, host)
    try:
        toast = _toast(pg, "No terminal was found")
        assert " ".join(toast.inner_text().split()).count("Open one and run: pi (then /login)") == 1
        assert [b.inner_text() for b in toast.locator(".ork-btn").all()] == ["Copy"]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_sign_in_done_says_the_tool_is_signed_in_and_how_many_tasks_go_on(gui):
    host = StubHost()
    host.sign_in = [entry(state="open", auto=False, waiting=3)]
    pg, errors = _page(gui, host)
    try:
        _toast(pg, "Sign in to Claude Code")
        host.sign_in = []                                                 # signed in: the tool is no longer in the snapshot
        host.bump({})
        _toast(pg, "Claude Code is signed in. 3 tasks go on.")
        assert pg.locator(".gui-toast", has_text="Its sign-in opened in your browser").count() == 0       # the open one is gone
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_sign_in_that_did_not_finish_says_why_and_offers_sign_in_again_and_details(gui):
    host = StubHost()
    host.sign_in = [entry(state="open", auto=False)]
    pg, errors = _page(gui, host)
    try:
        _toast(pg, "Sign in to Claude Code")
        host.sign_in[0].update(state="failed", why="timeout")
        host.bump({})
        toast = _toast(pg, "Claude Code's sign-in did not finish.")
        assert [b.inner_text() for b in toast.locator(".ork-btn").all()] == ["Sign in again", "Details"]
        toast.get_by_role("button", name="Details").click()
        _toast(pg, "it took too long")
        host.sign_in[0].update(state="open")                              # again, and again it did not finish
        host.bump({})
        _toast(pg, "Sign in to Claude Code")
        host.sign_in[0].update(state="failed", why="refused")
        host.bump({})
        _toast(pg, "Claude Code's sign-in did not finish.").get_by_role("button", name="Sign in again").click()
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude"}]                  # the person's own: not `auto`
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_browser_that_did_not_open_offers_the_terminal(gui):
    host = StubHost()
    host.sign_in = [entry(state="open", auto=False)]
    pg, errors = _page(gui, host)
    try:
        _toast(pg, "Sign in to Claude Code")
        host.sign_in[0].update(state="failed", why="no_browser")
        host.bump({})
        toast = _toast(pg, "The browser did not open.")
        assert [b.inner_text() for b in toast.locator(".ork-btn").all()] == ["Sign in in a terminal"]
        toast.get_by_role("button", name="Sign in in a terminal").click()
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude", "by": "terminal"}]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_cancelled_sign_in_says_nothing(gui):
    host = StubHost()
    host.sign_in = [entry(state="open", auto=False)]
    pg, errors = _page(gui, host)
    try:
        _toast(pg, "Sign in to Claude Code")
        host.sign_in[0].update(state="failed", why="cancelled")
        host.bump({})
        pg.wait_for_function("() => !document.querySelector('.gui-toast')", timeout=WAIT_MS)
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


# -- Sign in beside every failure that a sign-in helps ---------------------------------------------------------------------------

def test_the_first_screens_check_row_says_not_signed_in_with_sign_in_beside_its_line(gui):
    row = {"id": "claude", "title": "Claude Code", "mark": "✱", "enabled": True, "billing": "subscription", "version": "2.1",
           "logged_in": False, "login": "claude  (then /login)", "risk": "",
           "check": {"state": "failed", "kind": "login", "line": "Claude Code is not signed in, or its sign-in has expired.",
                     "action": "Sign in opens Claude Code's sign-in. In a terminal: claude, then /login.", "detail": "Not logged in", "sign_in": True}}
    onboarding = {"step": "tools", "steps": ["tools"], "n": 0, "again": False, "raising": None, "classes": [], "only_kin": "",
                  "tools": {"ready": True, "warder": True, "warder_agy": "", "cli": [], "others": [], "missing": [], "recommended": [], "rows": [row]}}
    host = StubHost(onboarding=onboarding)
    host.sign_in = [entry(auto=False, where="check")]
    pg, errors = _page(gui, host, ready=".gui-onb__card")
    try:
        text = pg.locator(".gui-onb__table").inner_text()
        assert "not signed in" in text and "logged in" not in text.replace("signed in", "")
        pg.get_by_role("button", name="Sign in to Claude Code").click()
        assert _sent(pg, host, ("tools.sign_in", {"harness": "claude"}))
        _toast(pg, "Sign in to Claude Code")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_first_screen_says_signed_in_for_a_tool_that_is_and_a_failed_check_opens_its_sign_in_at_once(gui):
    row = {"id": "claude", "title": "Claude Code", "mark": "✱", "enabled": True, "billing": "subscription", "version": "2.1",
           "logged_in": True, "login": "", "risk": "", "check": None}
    onboarding = {"step": "tools", "steps": ["tools"], "n": 0, "again": False, "raising": None, "classes": [], "only_kin": "",
                  "tools": {"ready": True, "warder": True, "warder_agy": "", "cli": [], "others": [], "missing": [], "recommended": [], "rows": [row]}}
    host = StubHost(onboarding=onboarding)
    pg, errors = _page(gui, host, ready=".gui-onb__card")
    try:
        assert "✓ signed in" in pg.locator(".gui-onb__table").inner_text()
        host.sign_in = [entry(where="check")]                             # the person pressed Check: it failed for its sign-in
        host.bump({})
        assert _calls(pg, host, "tools.sign_in") == [{"harness": "claude", "auto": True}]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_an_error_line_that_says_a_tool_is_not_signed_in_has_sign_in(gui):
    host = StubHost()
    host.sign_in = [entry(auto=False)]
    host.ideas["dark"]["state_error"] = LINE
    pg, errors = _page(gui, host)
    try:
        _show_goal(pg)
        pg.locator(".board-card", has_text="Dark mode").click()
        line = pg.locator(".shell-error", has_text="is not signed in")
        line.first.wait_for(timeout=WAIT_MS)
        line.get_by_role("button", name="Sign in to Claude Code").click()
        assert _sent(pg, host, ("tools.sign_in", {"harness": "claude"}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_an_error_line_of_another_failure_has_no_sign_in(gui):
    host = StubHost()
    host.sign_in = [entry(auto=False)]
    host.ideas["dark"]["state_error"] = "Codex hit an error: the model is not available."
    pg, errors = _page(gui, host)
    try:
        _show_goal(pg)
        pg.locator(".board-card", has_text="Dark mode").click()
        pg.locator(".shell-error", has_text="the model is not available").first.wait_for(timeout=WAIT_MS)
        assert pg.locator(".shell-error").get_by_role("button", name="Sign in to Claude Code").count() == 0
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_need_on_today_is_a_sign_in_row_with_sign_in(gui):
    host = StubHost()
    host.sign_in = [entry(auto=False, waiting=2)]
    host.sign_in_needs = [{"kind": "sign_in", "harness": "claude", "tool": "Claude Code", "title": "Claude Code", "blocks": True, "priority": "normal",
                           "at": "2026-10-20T01:00:00", "text": LINE, "waiting": 2}]
    pg, errors = _page(gui, host)
    try:
        _needs(pg)
        row = pg.locator(".board-need-row", has=pg.locator('[data-kind="sign_in"]'))
        row.wait_for(timeout=WAIT_MS)
        text = " ".join(row.inner_text().split())
        assert "Claude Code" in text and "Sign-in" in text and "is not signed in, or its sign-in has expired" in text and "2 tasks wait for it" in text
        row.get_by_role("button", name="Sign in to Claude Code").click()
        assert _sent(pg, host, ("tools.sign_in", {"harness": "claude"}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


# -- a row or a stop held by it ---------------------------------------------------------------------------------------------------

WAIT = {"kind": "sign_in", "ref": "claude", "title": "Claude Code", "tool": "Claude Code", "until": "2026-10-21T10:00:00"}


def test_a_row_held_for_the_sign_in_says_so_and_not_limits(gui):
    host = StubHost()
    host.ideas["offline"].update(waits=WAIT, held_until="2026-10-21T10:00:00")     # a hold has `held_until` for both: the sign-in's words win
    host.ideas["sync"].update(waits=WAIT)
    pg, errors = _page(gui, host)
    try:
        _show_goal(pg)
        off = pg.locator(".board-card-row", has_text="Offline mode")
        off.wait_for(timeout=WAIT_MS)
        assert "waits: Claude Code's sign-in" in off.inner_text() and "limits" not in off.inner_text()
        work = pg.locator(".board-card-row", has_text="Sync ideas")
        assert "waits: Claude Code's sign-in" in work.inner_text()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_stop_of_the_map_held_for_the_sign_in_says_so(gui):
    host = MapHost()
    host.nodes[1] = node("offline", "ship-sync", "Offline mode", "raw", 1, queue="night", held_until="2026-10-21T10:00:00", waits=WAIT)
    host.ideas["offline"].update(waits=WAIT, held_until="2026-10-21T10:00:00")
    pg, host, errors = _open_map(gui, host=host)
    try:
        card = pg.locator(".map-card", has_text="Offline mode")
        card.wait_for(timeout=WAIT_MS)
        said = card.get_attribute("aria-label")
        assert "waits: Claude Code's sign-in" in said and "limits" not in said
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
