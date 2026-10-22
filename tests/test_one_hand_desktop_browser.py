"""One hand on the desktop (docs/specs/54-one-hand.md §2–§4, part C), in a real browser at 1 440 × 900 against the arena's stub host: the bottom row holds every
party's and Operations' stops, the most urgent in the middle, a stop of another party says its party and opens there, no count anywhere (the parties' spread
wears a dot), a way out on every stop (*Let … decide*, *Describe it instead*, *Go without it*, *Let … choose*) on the raised stop and in the to-do dialog."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost  # noqa: E402
from tests.test_shell_browser import _calls, _open, _parties, _sent, _stop  # noqa: E402

pytestmark = pytest.mark.browser

BASE = {"priority": "normal", "blocks": False}


def todo(tid, title, kind, **more):
    return {"id": tid, "title": title, "kind": kind, "why": "The plan needs it", "choices": [], "steps": [], "accept": [], "done": False, **more}


def row(kind, **more):
    return BASE | {"goal": "passkey", "idea": "", "at": "2026-10-18T09:00:00", "text": "", "title": "", **more, "kind": kind}


class OneHostOne(ArenaHost):
    """The passkey party shown, a second party (Pricing page) with a to-do and a third (Weekly report email) with a question of its own, and Operations with a
    failed operation and one at the person's check: eight stops in all."""

    def __init__(self):
        super().__init__()
        self.ops = True
        self.extra_needs = [
            row("todo", goal="pricing", idea="prices", title="Prices from the billing settings", text="Reference picture", at="2026-10-16T09:00:00",
                todo=todo("t9", "Reference picture", "file", accept=["png"])),
            row("goal", goal="weekly", title="Weekly report email", text="Which day?", at="2026-10-17T09:00:00", questions=["Which day?"],
                asked=[{"ask": "Which day?", "choices": ["Monday", "Friday"], "pick": 0, "why": "", "by": None}]),
            row("op", goal="", op="r1", title="Weekly report", text="Waits at your check", at="2026-10-17T10:00:00"),
            row("op_failed", goal="", op="r2", title="Nightly export", text="It failed", at="2026-10-19T09:00:00")]


def _hand(pg):
    return pg.locator(".arena-hc")


def test_the_bottom_row_holds_every_stop_of_the_project_the_most_urgent_in_the_middle(gui):
    pg, host, errors = _open(gui, host=OneHostOne(), ready=".arena[data-goal=passkey]")
    try:
        cards = _hand(pg)
        cards.first.wait_for(timeout=WAIT_MS)
        # urgency's order is the page's (the keys', a screen reader's): red first, then what holds work back, then what does not; the oldest first in a group
        assert [(c.get_attribute("data-kind"), c.get_attribute("data-party")) for c in cards.all()] == [
            ("op_failed", "@operations"), ("failed", "passkey"),
            ("todo", "pricing"), ("goal", "weekly"), ("op", "@operations"), ("plan", "passkey"), ("asks", "passkey"),
            ("proposal", "passkey")]
        # laid out from the middle: the most urgent in it, the next to its right, the next to its left, and so outward
        by_x = sorted(cards.all(), key=lambda c: c.bounding_box()["x"])
        assert [c.get_attribute("data-kind") for c in by_x] == ["asks", "op", "todo", "op_failed", "failed", "goal", "plan", "proposal"]
        middle = pg.locator(".arena-hand").bounding_box()
        first = pg.locator('.arena-hc[data-kind="op_failed"]').bounding_box()
        assert abs((first["x"] + first["width"] / 2) - (middle["x"] + middle["width"] / 2)) <= 100                 # in the middle, give or take half a card
        hand = pg.locator(".arena-hand").bounding_box()
        assert all(hand["x"] <= b["x"] + b["width"] / 2 <= hand["x"] + hand["width"] for b in (c.bounding_box() for c in cards.all()))              # all of them fit
        # the party's own stops say nothing of a party; another party's say it, with its leader's small head (Operations': its sliders)
        for c in cards.all():
            other = c.get_attribute("data-party") != "passkey"
            assert ("is-other" in c.get_attribute("class")) == other and c.locator(".arena-hc__party").count() == int(other)
        pricing = pg.locator('.arena-hc[data-kind="todo"]')
        assert pricing.locator(".arena-hc__party .ork-race__head").count() == 1
        assert pricing.locator(".arena-banner").inner_text() == "Pricing page · Prices from the billing settings"
        assert pricing.locator(".arena-hc__open").get_attribute("aria-label") == "A to-do in Pricing page: Prices from the billing settings"
        op = pg.locator('.arena-hc[data-kind="op"]')
        assert op.locator(".arena-hc__party .ork-icon").count() == 1 and op.locator(".arena-banner").inner_text() == "Operations · Weekly report"
        assert pg.locator('.arena-hc[data-kind="plan"] .arena-banner').inner_text() == "Recovery codes"           # the party shown: its goal alone
        assert pg.get_by_text("Nothing waits for you").count() == 0
        # Operations shown: the same hand, now its own and the parties' for others
        _parties(pg).locator('[data-goal="@operations"]').click()
        pg.locator(".arena-ops").wait_for(timeout=WAIT_MS)
        assert _hand(pg).count() == 8 and pg.locator(".arena-hc.is-other").count() == 6
        assert pg.locator('.arena-hc[data-kind="op"]').get_attribute("class").count("is-other") == 0
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_open_on_a_stop_of_another_party_shows_that_party_first_and_a_quick_answer_acts_in_place(gui):
    pg, host, errors = _open(gui, host=OneHostOne(), ready=".arena[data-goal=passkey]")
    try:
        item = _stop(pg, "todo")
        item.get_by_role("button", name="Open…").click()
        pg.locator(".arena[data-goal=pricing]").wait_for(timeout=WAIT_MS)                                         # that party is shown, as a pick of it
        dialog = pg.get_by_role("dialog", name="Reference picture")
        dialog.wait_for(timeout=WAIT_MS)
        assert dialog.get_by_role("button", name="Go without it: Reference picture").count() == 1
        dialog.get_by_role("button", name="Later").click()
        # a quick answer acts where it stands: the party does not change
        _parties(pg).locator('[data-goal="passkey"]').click()
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        item = _stop(pg, "goal")
        item.get_by_role("button", name="Monday").click()
        assert _sent(pg, host, ("ideas.answer", {"slug": "weekly", "answers": ["Monday"], "goal": True}))
        assert pg.locator(".arena[data-goal=passkey]").count() == 1
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_no_count_on_parties_and_a_dot_in_the_spread_red_when_one_failed(gui):
    pg, host, errors = _open(gui, host=OneHostOne(), ready=".arena[data-goal=passkey]")
    try:
        deck = pg.locator(".arena-ptop__deck")
        assert deck.locator(".ork-count").count() == 0 and pg.locator(".arena-ptop .ork-count").count() == 0
        assert deck.get_attribute("aria-label") == "Parties: Sign in with a passkey shown, 4 stops wait in the other parties"      # for a screen reader only
        spread = _parties(pg)
        assert spread.locator(".ork-count").count() == 0
        dot = lambda goal: spread.locator(f'[data-goal="{goal}"] .arena-deck__dot')                                # noqa: E731
        assert dot("passkey").count() == 0                                                                         # the party shown: its stops lie in the hand
        assert dot("pricing").count() == 1 and dot("weekly").count() == 1 and dot("@operations").count() == 1
        assert spread.locator('[data-goal="pricing"]').locator(".arena-deck__dot").evaluate("e => e.getBoundingClientRect().width") == 8
        assert "is-danger" not in dot("pricing").get_attribute("class") and "is-danger" in dot("@operations").get_attribute("class")      # a failed operation: red
        assert "color" not in (dot("pricing").get_attribute("style") or "")
        colours = {g: dot(g).evaluate("e => getComputedStyle(e).backgroundColor") for g in ("pricing", "@operations")}
        assert colours["pricing"] != colours["@operations"]
        assert spread.locator('[data-goal="pricing"]').get_attribute("aria-label") == "Pricing page, 1 of 1 goals done, 1 stop waits for you"
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


class Quiet(ArenaHost):
    """Nothing waits: no row, no failed task."""

    def __init__(self):
        super().__init__()
        self.cookie[0]["state"] = "merged"

    def needs_you(self):
        return []


def test_an_empty_hand_says_nothing_waits_for_you(gui):
    pg, host, errors = _open(gui, host=Quiet(), ready=".arena[data-goal=passkey]")
    try:
        pg.locator(".arena-hand__empty").wait_for(timeout=WAIT_MS)
        assert pg.locator(".arena-hand__empty").inner_text() == "Nothing waits for you." and _hand(pg).count() == 0
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_let_the_asker_decide_on_a_question_and_on_a_partys(gui):
    pg, host, errors = _open(gui, host=OneHostOne(), ready=".arena[data-goal=passkey]")
    try:
        item = _stop(pg, "asks")
        decide = item.get_by_role("button", name="Let Reviewer decide")                                           # the one who asked
        assert decide.count() == 1 and "quiet" in decide.get_attribute("class")
        assert item.locator(".arena-hc__quick .ork-btn").last.inner_text() == "Let Reviewer decide"             # last
        decide.click()
        assert _sent(pg, host, ("ideas.answer", {"slug": "second", "decide": True}))
        pg.locator(".ok-toast", has_text="Sent: Reviewer decides.").wait_for(timeout=WAIT_MS)
        item = _stop(pg, "goal")                                                                                    # a party's question: its leader
        item.get_by_role("button", name="Let the Taskmaster decide").click()
        assert _sent(pg, host, ("ideas.answer", {"slug": "weekly", "decide": True, "goal": True}))
        pg.locator(".ok-toast", has_text="Sent: the Taskmaster decides.").wait_for(timeout=WAIT_MS)
        assert pg.locator(".arena[data-goal=passkey]").count() == 1                                                # answered in place
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


class Todos(ArenaHost):
    """One to-do of each kind of the passkey party."""

    def __init__(self):
        super().__init__()
        self.extra_needs = [
            row("todo", idea="register", title="WebAuthn register", text="Reference picture", todo=todo("f", "Reference picture", "file")),
            row("todo", idea="register", title="WebAuthn register", text="Which tone", todo=todo("c", "Which tone", "choice", choices=["warm", "cold"])),
            row("todo", idea="register", title="WebAuthn register", text="API_KEY", todo=todo("s", "API_KEY", "secret")),
            row("todo", idea="register", title="WebAuthn register", text="Billing on", todo=todo("k", "Billing on", "confirm")),
            row("todo", idea="register", title="WebAuthn register", text="Create the account", todo=todo("i", "Create the account", "instructions", steps=["Open it"]))]


def test_a_to_do_goes_on_without_it_or_with_words_from_the_raised_stop(gui):
    pg, host, errors = _open(gui, host=Todos(), ready=".arena[data-goal=passkey]")
    try:
        cards = pg.locator('.arena-hc[data-kind="todo"]')
        cards.first.wait_for(timeout=WAIT_MS)
        card = lambda title: pg.locator(f'.arena-hc[data-kind="todo"][data-key$="/{title}"]')                        # noqa: E731
        assert cards.count() == 5

        def raise_(title):
            item = card(title)
            item.locator(".arena-hc__open").focus()
            pg.wait_for_function("(el) => getComputedStyle(el).transform === 'matrix(1, 0, 0, 1, 0, -184)'", arg=item.element_handle(), timeout=WAIT_MS)
            return item

        item = raise_("f")                                                                                           # a file: describe it, or go without it
        assert item.get_by_role("button", name="Describe it instead: Reference picture").count() == 1
        item.get_by_role("button", name="Describe it instead: Reference picture").click()
        field = item.get_by_placeholder("What should it look like?")
        assert item.get_by_role("button", name="Send: Reference picture").is_disabled()                              # not empty
        field.fill("  A warm button, round  ")
        item.get_by_role("button", name="Send: Reference picture").click()
        assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "f", "done": True, "words": "A warm button, round"}))
        pg.locator(".ok-toast", has_text="Sent: the words go to the Taskmaster.").wait_for(timeout=WAIT_MS)
        item = raise_("f")
        item.get_by_role("button", name="Go without it: Reference picture").click()
        assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "f", "skip": True}))
        pg.locator(".ok-toast", has_text="Done: the Taskmaster’s plan goes on without it.").wait_for(timeout=WAIT_MS)

        item = raise_("c")                                                                                           # a choice: the leader chooses
        item.get_by_role("button", name="Let the Taskmaster choose: Which tone").click()
        assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "c", "skip": True}))

        for tid, title in (("s", "API_KEY"), ("k", "Billing on"), ("i", "Create the account")):                    # the rest: go without it
            item = raise_(tid)
            go = item.get_by_role("button", name=f"Go without it: {title}")
            assert go.get_attribute("title") == "Its tasks run without it, and say so if they cannot" and "quiet" in go.get_attribute("class")
            go.click()
            assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": tid, "skip": True}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_to_do_dialog_has_the_same_ways_out(gui):
    pg, host, errors = _open(gui, host=Todos(), ready=".arena[data-goal=passkey]")
    try:
        def dialog_of(tid, title):
            item = pg.locator(f'.arena-hc[data-kind="todo"][data-key$="/{tid}"]')
            item.locator(".arena-hc__open").focus()
            pg.wait_for_function("(el) => getComputedStyle(el).transform === 'matrix(1, 0, 0, 1, 0, -184)'", arg=item.element_handle(), timeout=WAIT_MS)
            item.get_by_role("button", name="Open…").click()
            d = pg.get_by_role("dialog", name=title)
            d.wait_for(timeout=WAIT_MS)
            return d

        d = dialog_of("f", "Reference picture")                                                                      # a file
        d.get_by_role("button", name="Describe it instead: Reference picture").click()
        d.get_by_placeholder("What should it look like?").fill("Round, warm")
        d.get_by_role("button", name="Send: Reference picture").click()
        assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "f", "done": True, "words": "Round, warm"}))
        d.wait_for(state="detached", timeout=WAIT_MS)
        d = dialog_of("f", "Reference picture")
        d.get_by_role("button", name="Go without it: Reference picture").click()
        assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "f", "skip": True}))
        d.wait_for(state="detached", timeout=WAIT_MS)
        d = dialog_of("c", "Which tone")                                                                              # a choice
        d.get_by_role("button", name="Let the Taskmaster choose: Which tone").click()
        assert _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "c", "skip": True}))
        d.wait_for(state="detached", timeout=WAIT_MS)
        d = dialog_of("s", "API_KEY")                                                                                 # a secret: still its own input
        assert d.get_by_label("Value of API_KEY").count() == 1
        d.get_by_role("button", name="Go without it: API_KEY").click()
        assert len(_calls(pg, host, "ideas.todo", 4)) >= 4 and _sent(pg, host, ("ideas.todo", {"idea": "register", "id": "s", "skip": True}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
