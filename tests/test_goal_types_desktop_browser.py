"""Goal types and the party's deck on the desktop (docs/specs/52-goal-types.md §3, §4, §6; Tests → B), in a real browser at 1 440 × 900 against the one
window's stub host (tests/test_arena_desktop_browser.py) with a party whose leader deals the designer's types: the top bar without the parties, the left
column's top line and Parties ⌄ with the other parties' count, the leader's row on the deck, the parties' spread, the New goal pile's types, New goal by a
type (its head, the party fixed, the asks, Refs, the lens, the join line's three shapes), a plan's missing line and its answers, a stop marked once."""
from __future__ import annotations

import base64

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import goal_types  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ELF, ArenaHost, member  # noqa: E402
from tests.test_shell_browser import _calls, _drawer, _open, _parties, _sent, _show_goal, _stop, box  # noqa: E402

pytestmark = pytest.mark.browser

DESIGNER = {"slug": "product-designer", "name": "Product designer", "head": ELF}
ARTIST = {"kind": "art", "words": "pixel art", "agent": "artist", "name": "Artist", "band": "build"}
UIKIT = {"kind": "uikit", "words": "UI kit", "agent": "ui-kit", "name": "UI kit", "band": "build"}
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _alert(pg):
    return pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")


def _dealt(pg):
    pg.wait_for_function("() => document.getAnimations().every((a) => !a.effect?.target?.classList?.contains('arena-spread__card'))", timeout=WAIT_MS)


def type_doc(t, used=0, missing=()):
    """A party's goal type as `ideas.map` carries it (spec 52 §2.4), from the host's own set."""
    return {"id": t.id, "name": t.name, "sign": t.sign, "line": t.line, "lens": t.lens, "asks": [{"id": a.id, "label": a.label, "hint": a.hint} for a in t.asks],
            "refs": t.refs, "used": used, "missing": [dict(m) for m in missing]}


class TypesHost(ArenaHost):
    """The passkey party led by a designer: New screen, New icon (Artist joins a free seat), New logo (a swap), New feature (the builders all busy)."""

    def __init__(self):
        super().__init__()
        self.leader = DESIGNER
        by = {t.id: t for t in goal_types.of("product-designer")}
        swap = [{"slug": "screens", "name": "Screens", "runs": 2}, {"slug": "backend", "name": "Backend", "runs": 5}]
        self.types = [type_doc(by["icon"], 3, [ARTIST | {"free": True, "out": []}]), type_doc(by["screen"], 1),
                      type_doc(by["logo"], 0, [ARTIST | {"free": False, "out": swap}]), type_doc(by["feature"], 0, [UIKIT | {"free": False, "out": []}])]
        self.plan_missing = [ARTIST | {"free": True}]
        self.party["passkey"][0] = member("product-designer", "Product designer", ELF, "lead", "needs", "plan")

    def map_doc(self):
        doc = super().map_doc()
        for g in doc["goals"]:
            if g["slug"] == "passkey":
                g.update(leader=self.leader, types=self.types)
        return doc

    def needs_you(self):
        rows = super().needs_you()
        for r in rows:
            if r["kind"] == "plan" and self.plan_missing is not None:
                r["missing"] = [dict(m) for m in self.plan_missing]
        return rows

    def handle(self, name, a):
        if name == "ideas.add" and a.get("join") and not a.get("night"):
            got = super().handle(name, a)
            return {**got, "type": f"product-designer/{a.get('type', '')}", "joined": {"add": a["join"]["add"], "out": a["join"].get("out", "")}}
        if name == "ideas.add":
            got = super().handle(name, a)
            return {**got, "type": f"product-designer/{a['type']}" if a.get("type") else "", "joined": None}
        return super().handle(name, a)


@pytest.fixture
def typed(gui):
    pg, host, errors = _open(gui, host=TypesHost(), ready=".arena-ptop")
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _types(pg):
    pg.get_by_role("button", name="New goal: pick its type, or a blank one").click()
    deal = pg.get_by_role("dialog", name="New goal for Sign in with a passkey")
    deal.wait_for(timeout=WAIT_MS)
    _dealt(pg)
    return deal


def _form(pg, name):
    _types(pg).locator(".arena-type", has_text=name).click()
    dialog = pg.get_by_role("dialog", name="New goal", exact=True)
    dialog.wait_for(timeout=WAIT_MS)
    return dialog


# -- the party's deck (§3) ----------------------------------------------------------------------------------------------------------

def test_the_top_bar_has_no_parties_and_the_left_column_says_the_party_over_the_leader_on_its_deck(typed):
    pg, host = typed
    top = pg.locator(".shell-top")
    assert top.get_by_role("tablist").count() == 0 and "Sign in with a passkey" not in top.inner_text() and top.locator(".arena-ptop").count() == 0
    assert "Agents" in top.inner_text() and "Stop all" in top.inner_text() and "Orkline" in top.text_content()
    line = pg.locator(".arena-left .arena-ptop")
    assert box(pg, ".arena-left .arena-ptop")["height"] == 32 and box(pg, ".arena-ptop")["y"] < box(pg, ".arena-hero")["y"]       # over the leader's row
    assert line.locator(".arena-ptop__name").inner_text() == "Sign in with a passkey"
    assert line.locator(".arena-ptop__name").evaluate("e => getComputedStyle(e).fontSize") == "13px"
    count = line.locator(".arena-ptop__count")
    assert count.inner_text() == "2/11" and count.get_attribute("title") == "2 of 11 goals done"
    assert line.locator(".arena-ptop__work .ork-sign.work").count() == 1                                                  # at work
    deck = line.get_by_role("button", name="Parties: Sign in with a passkey shown")
    assert deck.count() == 1 and deck.locator(".ork-count").count() == 0 and box(pg, ".arena-ptop__deck")["height"] == 28   # no count
    assert pg.locator(".arena-hero .arena-hero__edge").count() == 2                                                        # two other parties: two edges
    host.extra_needs.append({"kind": "plan", "goal": "pricing", "idea": "prices", "title": "Prices", "text": "Plan ready", "priority": "normal", "blocks": False, "at": "2026-10-18T09:00:00"})
    host.bump({})
    deck = line.get_by_role("button", name="Parties: Sign in with a passkey shown, 1 stop waits in the other parties")
    deck.wait_for(timeout=WAIT_MS)
    assert deck.locator(".ork-count").count() == 0 and pg.locator(".ork-count.warning").count() == 0                       # no count of stops anywhere (spec 54 §2.4)
    assert pg.locator('.arena-hc[data-kind="plan"][data-party="pricing"]').count() == 1                                      # it lies in the one hand, marked with its party


def test_parties_deals_the_parties_a_press_picks_one_and_put_them_back_esc_and_the_keys(typed):
    pg, host = typed
    host.ops = True
    host.bump({})
    pg.locator(".arena-hero .arena-hero__edge").nth(1).wait_for(timeout=WAIT_MS)
    deal = _parties(pg)
    assert deal.locator(".arena-spread__cap").inner_text().startswith("Parties of")
    cards = deal.locator(".arena-spread__card")
    assert [c.get_attribute("data-goal") for c in cards.all()] == ["passkey", "pricing", "weekly", "@operations", ""]
    shown = deal.locator(".arena-deck__card.is-shown")
    assert shown.get_attribute("data-goal") == "passkey" and "shown" in shown.text_content() and shown.get_attribute("aria-label").endswith(", shown")
    assert shown.locator(".ork-race__head.mid").count() == 1 and shown.locator(".arena-deck__heads .ork-race__head.small").count() == 4
    assert "2/11 done" in shown.inner_text() and shown.locator(".ork-count").count() == 0 and shown.locator(".ork-sign.work").count() == 1   # no count of the party shown
    assert "Operations" in cards.nth(3).inner_text() and cards.nth(3).locator(".ork-icon").count() == 1
    assert "New party" in cards.nth(4).inner_text() and "one of yours, or from the library" in cards.nth(4).inner_text()
    assert box(pg, ".arena-spread__card")["width"] == 120 and box(pg, ".arena-spread__card")["height"] == 168
    assert pg.evaluate("document.activeElement.dataset.goal") == "passkey"                                                 # the focus starts on the party shown
    pg.keyboard.press("ArrowRight")
    assert pg.evaluate("document.activeElement.dataset.goal") == "pricing"
    pg.keyboard.press("ArrowLeft")
    pg.keyboard.press("ArrowLeft")
    assert pg.evaluate("document.activeElement.dataset.goal") == ""                                                        # around: New party
    pg.keyboard.press("Escape")
    deal.wait_for(state="detached", timeout=WAIT_MS)
    assert pg.evaluate("document.activeElement.classList.contains('arena-ptop__deck')")                                   # the focus back to Parties ⌄
    deal = _parties(pg)
    deal.get_by_role("button", name="Put them back").click()
    deal.wait_for(state="detached", timeout=WAIT_MS)
    deal = _parties(pg)
    pg.mouse.click(20, 880)                                                                                                # the scrim gathers them
    deal.wait_for(state="detached", timeout=WAIT_MS)
    deal = _parties(pg)
    pg.keyboard.press("ArrowRight")
    pg.keyboard.press("Enter")                                                                                             # Enter presses: Pricing page is shown
    pg.locator(".arena[data-goal=pricing]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena-ptop__name").inner_text() == "Pricing page"
    _show_goal(pg, "@operations")
    assert pg.locator(".arena-ops .arena-ptop__name").inner_text() == "Operations"
    _show_goal(pg, "passkey")
    _parties(pg).locator(".arena-spread__card[data-goal='']").click()
    pg.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)


def test_no_deal_under_reduced_motion(gui):
    pg, host, errors = _open(gui, host=TypesHost(), ready=".arena-ptop")
    pg.emulate_media(reduced_motion="reduce")
    pg.locator(".arena-ptop__deck").click()
    pg.get_by_role("dialog", name="Parties").wait_for(timeout=WAIT_MS)
    assert pg.evaluate("document.getAnimations().filter((a) => a.effect?.target?.classList?.contains('arena-spread__card')).length") == 0
    pg.get_by_role("button", name="New goal: pick its type, or a blank one").count()
    pg.keyboard.press("Escape")
    pg.get_by_role("button", name="New goal: pick its type, or a blank one").click()
    pg.get_by_role("dialog", name="New goal for Sign in with a passkey").wait_for(timeout=WAIT_MS)
    assert pg.evaluate("document.getAnimations().filter((a) => a.effect?.target?.classList?.contains('arena-spread__card')).length") == 0
    pg.locator(".arena-type", has_text="New screen").click()
    pg.get_by_role("dialog", name="New goal", exact=True).wait_for(timeout=WAIT_MS)                                                   # no turn: at once
    pg.close()
    assert not errors, "\n".join(errors)


# -- the New goal pile deals the types (§4.1) ---------------------------------------------------------------------------------------

def test_the_pile_deals_the_partys_types_the_most_used_first_with_what_they_need_and_the_blank_last(typed):
    pg, host = typed
    words = pg.locator(".arena-new__words")
    assert "New goal" in words.text_content() and "pick its type" in words.text_content()
    deal = _types(pg)
    assert "New goal for Sign in with a passkey" in deal.locator(".arena-spread__cap").inner_text()
    cards = deal.locator(".arena-type")
    assert [c.get_attribute("data-type") for c in cards.all()] == ["icon", "screen", "logo", "feature", ""]            # the host's order, the blank last
    icon = cards.nth(0)
    assert icon.locator(".ork-sign.picture.big").count() == 1 and "New icon" in icon.inner_text() and "An icon in the pixel style" in icon.inner_text()
    needs = icon.locator(".arena-type__needs")
    assert "needs: Artist" in needs.inner_text() and needs.locator(".ork-race__head.small").count() == 1
    assert needs.evaluate("e => getComputedStyle(e).color") != _alert(pg)                                                # muted ink: not a stop
    assert cards.nth(1).locator(".arena-type__needs").count() == 0                                                       # it misses no one
    assert "A blank goal" in cards.nth(4).inner_text()
    cards.nth(1).click()                                                                                                  # the card turns over, then New goal opens
    assert "is-turning" in (cards.nth(1).get_attribute("class") or "")
    dialog = pg.get_by_role("dialog", name="New goal", exact=True)
    dialog.wait_for(timeout=WAIT_MS)
    assert dialog.locator(".arena-typed__head").text_content().strip() == "New screen"
    assert pg.get_by_role("dialog", name="New goal for Sign in with a passkey").count() == 0
    dialog.get_by_role("button", name="Close").click()
    _types(pg).locator(".arena-type.is-blank").click()                                                                   # the blank card: the form of today
    pg.get_by_role("dialog", name="New goal", exact=True).get_by_text("A blank goal").wait_for(timeout=WAIT_MS)


def test_a_map_with_no_types_opens_the_blank_form(typed):
    pg, host = typed
    host.types = []
    host.bump({})
    pg.wait_for_function("() => !document.querySelector('.arena-new__pile[aria-haspopup]')", timeout=WAIT_MS)
    pg.get_by_role("button", name="New goal: pick its type, or a blank one").click()
    dialog = pg.get_by_role("dialog", name="New goal", exact=True)
    dialog.wait_for(timeout=WAIT_MS)
    assert "A blank goal" in dialog.text_content() and dialog.get_by_label("Party").count() == 1


# -- New goal by its type (§4.2, §4.3) ----------------------------------------------------------------------------------------------

def test_new_goal_by_a_type_has_its_head_the_party_fixed_its_asks_refs_and_sends_them(typed):
    pg, host = typed
    host.lens = {"lenses": [{"id": "text", "by": ""}, {"id": "screen", "by": "Product designer"}, {"id": "pain", "by": "Product manager"}], "default": "pain", "segments": [], "screens": []}
    dialog = _form(pg, "New logo")
    head = dialog.locator(".arena-typed__head")
    assert head.locator(".ork-sign.logo.big").count() == 1 and head.text_content().strip() == "New logo"
    assert dialog.locator(".arena-typed__for").inner_text() == "for Sign in with a passkey · Product designer reads it next"
    assert dialog.get_by_label("Party").count() == 0                                                                      # fixed: said, not a select
    assert dialog.get_by_text("A blank goal").count() == 0
    labels = dialog.locator(".shell-field > .ok-font-label").all_text_contents()
    assert labels[:3] == ["Its title", "What it is for", "What it should say"] and "Refs" in labels
    ask = dialog.get_by_label("What it should say")
    assert ask.get_attribute("placeholder") == "three words"
    assert dialog.get_by_role("radio", name="Text").get_attribute("aria-checked") == "true"                             # the type's lens first (text), not the leader's (pain)
    dialog.get_by_label("Its title").fill("A mark for the app")
    dialog.get_by_label("What it is for").fill("The store page and the icon")
    ask.fill("  calm,   quick,  sure ")
    dialog.get_by_label("Links").fill("https://example.com/likes")
    dialog.locator("input[type=file]").set_input_files({"name": "like.png", "mimeType": "image/png", "buffer": PNG})
    dialog.locator(".arena-refs__pic").first.wait_for(timeout=WAIT_MS)
    pg.evaluate("""(b64) => { const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
        const dt = new DataTransfer(); dt.items.add(new File([u], 'pasted.png', { type: 'image/png' }));
        const e = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }); document.querySelector('.arena-typed').dispatchEvent(e); }""",
                base64.b64encode(PNG).decode())
    pg.wait_for_function("() => document.querySelectorAll('.arena-refs__pic').length === 2", timeout=WAIT_MS)
    dialog.get_by_role("button", name="Remove picture 2").click()
    assert dialog.locator(".arena-refs__pic").count() == 1
    dialog.get_by_label("Who leaves").select_option("backend")
    dialog.get_by_role("button", name="Add the goal").click()
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["type"] == "logo" and sent["track"] == "passkey" and sent["text"] == "A mark for the app\n\nThe store page and the icon"
    assert sent["asks"] == {"says": "calm,   quick,  sure", "refs": "https://example.com/likes"}
    assert len(sent["photos"]) == 1 and base64.b64decode(sent["photos"][0]["data"])[:3] == b"\xff\xd8\xff"           # a JPEG
    assert sent["join"] == {"add": "artist", "out": "backend"}
    pg.get_by_text("Added: Artist joined the party; Product designer drafts it now.").first.wait_for(timeout=WAIT_MS)


def test_the_join_line_free_seat_unticked_says_the_grunt_and_a_full_band_has_no_box(typed):
    pg, host = typed
    dialog = _form(pg, "New icon")
    join = dialog.locator(".arena-join[data-agent=artist]")
    box_ = join.get_by_role("checkbox")
    assert box_.is_checked() and "Artist joins the party" in join.inner_text() and join.locator(".ork-race__head.small").count() == 1
    price = join.locator("[title='at API prices, not your bill']")
    assert price.inner_text().startswith("≈$") and price.inner_text().endswith(" a run")
    box_.uncheck()
    assert "Without Artist, its pixel art goes to the Grunt." in join.inner_text()
    dialog.get_by_label("Its title").fill("A sync icon")
    dialog.get_by_role("button", name="Add the goal").click()
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["type"] == "icon" and "join" not in sent
    dialog = _form(pg, "New icon")
    dialog.get_by_label("Its title").fill("A second icon")
    dialog.get_by_role("button", name="Add the goal").click()
    assert _calls(pg, host, "ideas.add")[-1]["join"] == {"add": "artist"}
    pg.get_by_text("Added: Artist joined the party; Product designer drafts it now.").first.wait_for(timeout=WAIT_MS)
    dialog = _form(pg, "New feature")
    full = dialog.locator(".arena-join.is-full")
    assert full.get_by_role("checkbox").count() == 0
    assert full.inner_text() == ("The party's builders all have work open: UI kit can join from Edit the party when one is done. "
                                 "Till then its UI kit goes to the Grunt.")
    swap = _form_swap(pg, dialog)
    assert "Swap: Screens leaves, Artist joins" in swap.inner_text()
    who = swap.get_by_label("Who leaves")
    assert [o.inner_text() for o in who.locator("option").all()] == ["Screens · 2 runs this week", "Backend · 5 runs this week"]


def _form_swap(pg, open_dialog):
    open_dialog.get_by_role("button", name="Close").click()
    return _form(pg, "New logo").locator(".arena-join[data-shape=swap]")


def test_put_it_back_with_words_keeps_the_type_and_asks_and_sends_no_join(typed):
    pg, host = typed
    dialog = _form(pg, "New icon")
    dialog.get_by_label("Its title").fill("An icon for tonight")
    dialog.get_by_label("Where it shows").fill("the tab bar, 24 px")
    dialog.get_by_role("button", name="Put it back").click()
    pg.wait_for_function("() => !document.querySelector('.shell-modal')", timeout=WAIT_MS)
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["night"] is True and sent["type"] == "icon" and sent["asks"] == {"where": "the tab bar, 24 px"} and "join" not in sent


# -- a plan's missing line (§4.4) ----------------------------------------------------------------------------------------------------

def test_a_plan_that_misses_someone_says_so_and_add_and_start_sends_the_join(typed):
    pg, host = typed
    stop = _stop(pg, "plan")
    assert "No one in the party does pixel art: Artist would." in stop.locator(".arena-hc__miss").inner_text()
    add = stop.get_by_role("button", name="Add and start")
    assert add.get_attribute("title") == "Artist joins the party, then the work starts"
    assert [b.inner_text() for b in stop.locator(".arena-hc__quick").get_by_role("button").all()] == ["Add and start", "Start without"]
    add.click()
    assert _sent(pg, host, ("ideas.start", {"slug": "recovery", "join": {"add": "artist"}, "via": "hand"}))
    pg.get_by_text("Artist joined the party; the work started.").first.wait_for(timeout=WAIT_MS)
    stop = _stop(pg, "plan")
    stop.get_by_role("button", name="Start without").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "recovery", "via": "hand"}))


def test_a_plan_that_misses_someone_with_no_free_seat_offers_edit_the_party_and_says_more(typed):
    pg, host = typed
    host.plan_missing = [ARTIST | {"free": False}, UIKIT | {"free": False}]
    host.bump({})
    pg.wait_for_function("() => (document.querySelector('.arena-hc[data-kind=plan] .arena-hc__miss') || {}).textContent?.includes('more')", timeout=WAIT_MS)
    stop = _stop(pg, "plan")
    assert stop.locator(".arena-hc__miss").inner_text() == "No one in the party does pixel art: Artist would. and 1 more"
    assert [b.inner_text() for b in stop.locator(".arena-hc__quick").get_by_role("button").all()] == ["Start without", "Edit the party"]
    stop.get_by_role("button", name="Edit the party").click()
    pg.get_by_role("dialog", name="Edit the party").wait_for(timeout=WAIT_MS)


# -- a stop marked once; a goal's type sign (§4.5, §4.6) -----------------------------------------------------------------------------

def test_a_stop_is_marked_once_by_its_sign_and_a_goal_of_a_type_shows_its_sign(typed):
    pg, host = typed
    host.node_of("recovery")["type"] = {"id": "icon", "name": "New icon", "sign": "picture"}
    host.bump({})
    row = pg.locator(".arena-goal[data-slug=recovery]")
    row.locator(".arena-goal__type .ork-sign.picture").wait_for(timeout=WAIT_MS)
    assert row.locator(".arena-goal__type").evaluate("e => getComputedStyle(e).color") != _alert(pg)
    assert row.locator(".arena-goal__mark .ork-sign.alert").count() == 1
    assert row.locator(".arena-goal__main").evaluate("e => getComputedStyle(e).boxShadow") == "none"                    # no alert edge
    assert row.locator(".arena-goal__line").evaluate("e => getComputedStyle(e).color") != _alert(pg)                    # no alert words
    assert pg.locator(".arena-goal[data-slug=register] .arena-goal__type").count() == 0                                  # a goal with no type: none
    failed = pg.locator(".arena-task[data-task=f1]")
    assert failed.evaluate("e => getComputedStyle(e).borderTopColor") == pg.evaluate(
        "(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-danger)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    assert pg.locator(".arena-hero .ork-count.warning, .arena-goals .ork-count.warning, .arena-field .ork-count.warning").count() == 0   # no count of the shown party's stops


def test_two_join_lines_one_ticked_at_a_time_since_one_joins_with_the_goal(typed):
    pg, host = typed
    host.types[1]["missing"] = [ARTIST | {"free": True, "out": []}, UIKIT | {"free": True, "out": []}]
    host.bump({})
    deal = _types(pg)
    deal.locator(".arena-type[data-type=screen] .arena-type__needs", has_text="UI kit").wait_for(timeout=WAIT_MS)     # the map read again
    deal.locator(".arena-type[data-type=screen]").click()
    dialog = pg.get_by_role("dialog", name="New goal", exact=True)
    dialog.wait_for(timeout=WAIT_MS)
    art, kit = dialog.locator(".arena-join[data-agent=artist] input[type=checkbox]"), dialog.locator(".arena-join[data-agent=ui-kit] input[type=checkbox]")
    assert art.is_checked() and not kit.is_checked()
    assert "Without UI kit, its UI kit goes to the Grunt." in dialog.locator(".arena-join[data-agent=ui-kit]").inner_text()
    kit.check()
    assert kit.is_checked() and not art.is_checked()
    dialog.get_by_label("Its title").fill("A settings screen")
    dialog.get_by_role("button", name="Add the goal").click()
    assert _calls(pg, host, "ideas.add")[-1]["join"] == {"add": "ui-kit"}


def test_a_task_card_shows_its_goals_type_sign_before_its_name_and_a_planning_card_says_its_type(typed):
    """Spec 53 §3 (C): a task's card has its goal's type's sign before the goal's name, its label names the type after the goal; a Planning goal's card says its
    type's name with the sign (*Fix a bug*), and a goal with no type keeps the word *Planning* and no sign."""
    pg, host = typed
    bug = {"id": "bug", "name": "Fix a bug", "sign": "bug"}
    host.node_of("register")["type"] = bug
    host.node_of("recovery")["type"] = bug
    host.bump({})
    card = pg.locator(".arena-task[data-idea=register]").first
    goal = card.locator(".arena-task__goal")
    goal.locator(".arena-task__type .ork-sign.bug").wait_for(timeout=WAIT_MS)
    assert goal.evaluate("e => e.firstElementChild.classList.contains('arena-task__type') && e.textContent === 'WebAuthn register'")   # the sign before the name
    assert goal.locator(".ork-sign").evaluate("e => e.getBoundingClientRect().width") == 14
    assert "WebAuthn register, Fix a bug" in card.get_attribute("aria-label") and "(WebAuthn register, Fix a bug)" in card.get_attribute("title")
    plain = pg.locator(".arena-task[data-idea=cookie] .arena-task__goal").first
    assert plain.locator(".arena-task__type").count() == 0 and plain.inner_text() != ""                                    # a goal with no type: the name alone
    pg.locator(".arena-hero .arena-member").click()                                                                       # the leader's solo: its Planning goals
    lead = pg.locator(".arena-solo[data-agent=product-designer]")
    planned = lead.locator(".arena-task[data-slug=recovery]")
    planned.locator(".arena-task__goal .arena-task__type .ork-sign.bug").wait_for(timeout=WAIT_MS)
    assert planned.locator(".arena-task__goal").inner_text() == "Fix a bug" and "Recovery codes, Fix a bug" in planned.get_attribute("aria-label")
    untyped = lead.locator(".arena-task:not([data-slug=recovery])").first
    assert untyped.locator(".arena-task__goal").inner_text() == "Planning" and untyped.locator(".arena-task__type").count() == 0
    pg.keyboard.press("Escape")
