"""Spec 42 C on the phone (docs/specs/42-coming-back.md §3.4, Tests → C): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with `Notification` and the service worker's `pushManager` stood in by an init script. Notify this phone
sends `mobile.push_on` with the endpoint and keys; on, the quiet hours and Turn off; the Home Screen line without `PushManager`;
the refusals in words; the badge set; a visit from a notification logged once."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _menu, _phone  # noqa: E402,F401

KEY = "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8"
QUIET = {"value": "23:00-08:00"}
REFUSE = {"error": ""}

FAKE = """
(() => {
  const granted = %(granted)s;
  window.__log = { asked: 0, subscribed: 0, unsubscribed: 0, badge: [] };
  class N { static get permission() { return window.__perm; } static async requestPermission() { window.__log.asked += 1; window.__perm = %(answer)s; return window.__perm; } }
  window.__perm = granted ? "granted" : "default";
  window.Notification = N;
  const sub = { endpoint: "https://push.example.com/send/abc", toJSON() { return { endpoint: this.endpoint, keys: { p256dh: "BCVxsr7N_eNgVRqvHtD0", auth: "BTBZMqHH6r4T" } }; },
                async unsubscribe() { window.__sub = null; window.__log.unsubscribed += 1; return true; } };
  window.__sub = granted ? sub : null;
  const manager = { async getSubscription() { return window.__sub; },
                    async subscribe(o) { window.__log.subscribed += 1; window.__log.key = o.applicationServerKey.length; window.__log.user = o.userVisibleOnly; window.__sub = sub; return sub; } };
  Object.defineProperty(navigator.serviceWorker, "ready", { get: () => Promise.resolve({ pushManager: manager }) });
  window.PushManager = window.PushManager || function PushManager() {};
  navigator.setAppBadge = (n) => { window.__log.badge.push(n); return Promise.resolve(); };
  navigator.clearAppBadge = () => { window.__log.badge.push(0); return Promise.resolve(); };
})();
"""


def fake(granted=False, answer="granted"):
    return FAKE % {"granted": "true" if granted else "false", "answer": f'"{answer}"'}


@pytest.fixture(autouse=True)
def _push(monkeypatch):
    QUIET["value"] = "23:00-08:00"
    REFUSE["error"] = ""
    real = Stub.commands

    def commands(self):
        def key(a):
            self.calls.append(("mobile.push_key", {}))
            if REFUSE["error"]:
                raise ValueError(REFUSE["error"])
            return {"key": KEY, "quiet": ""}

        def on(a):
            self.calls.append(("mobile.push_on", {k: a.get(k) for k in ("endpoint", "p256dh", "auth")}))
            return {"ok": True, "quiet": QUIET["value"]}

        def off(a):
            self.calls.append(("mobile.push_off", {}))
            return {"ok": True}

        def quiet(a):
            self.calls.append(("mobile.push_quiet", {"quiet": a.get("quiet")}))
            QUIET["value"] = a["quiet"]
            return {"ok": True}
        return {**real(self), "mobile.push_key": key, "mobile.push_on": on, "mobile.push_off": off, "mobile.push_quiet": quiet}
    monkeypatch.setattr(Stub, "commands", commands)


async def _row(page):
    drawer = await _menu(page)
    return drawer, drawer.get_by_label("Notifications", exact=True).first


@pytest.mark.asyncio
async def test_notify_this_phone_asks_for_permission_the_key_then_subscribes_and_tells_the_computer(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=fake()) as (stub, page):
        drawer, row = await _row(page)
        assert "When an answer waits, and once in the morning. Never in the quiet hours." in await row.inner_text()
        await row.get_by_role("button", name="Notify this phone").click()
        await row.get_by_role("button", name="Turn off").wait_for(timeout=WAIT_MS)
        log = await page.evaluate("window.__log")
        assert log["asked"] == 1 and log["subscribed"] == 1 and log["user"] is True and log["key"] == 65
        assert await _called(stub, "mobile.push_on", {"endpoint": "https://push.example.com/send/abc", "p256dh": "BCVxsr7N_eNgVRqvHtD0", "auth": "BTBZMqHH6r4T"})
        assert "On · quiet 23:00–08:00" in await row.inner_text()
        assert await row.get_by_label("Quiet from").input_value() == "23:00" and await row.get_by_label("Quiet to").input_value() == "08:00"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_on_the_quiet_hours_are_two_fields_and_turn_off_unsubscribes_then_tells_the_computer(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=fake(granted=True)) as (stub, page):
        assert await _called(stub, "mobile.push_on")                                # on every connect while on: sent again
        drawer, row = await _row(page)
        await row.get_by_role("button", name="Turn off").wait_for(timeout=WAIT_MS)
        await row.get_by_label("Quiet to").fill("07:30")
        assert await _called(stub, "mobile.push_quiet", {"quiet": "23:00-07:30"})
        await row.get_by_text("On · quiet 23:00–07:30").wait_for(timeout=WAIT_MS)
        await row.get_by_role("button", name="Turn off").click()
        await row.get_by_role("button", name="Notify this phone").wait_for(timeout=WAIT_MS)
        assert (await page.evaluate("window.__log"))["unsubscribed"] == 1 and await _called(stub, "mobile.push_off")


@pytest.mark.asyncio
async def test_the_computers_refusal_and_the_phones_are_said_in_words(fake_repo, monkeypatch):
    REFUSE["error"] = "Notifications need the cryptography package: pip install 'orkboard[gui]'"
    async with _phone(fake_repo, monkeypatch, init=fake()) as (stub, page):
        drawer, row = await _row(page)
        await row.get_by_role("button", name="Notify this phone").click()
        await row.get_by_text("Notifications need the cryptography package").wait_for(timeout=WAIT_MS)
        assert (await page.evaluate("window.__log"))["subscribed"] == 0
    async with _phone(fake_repo, monkeypatch, init=fake(answer="denied")) as (stub, page):
        drawer, row = await _row(page)
        await row.get_by_role("button", name="Notify this phone").click()
        await row.get_by_text("Notifications are off for Orkline in this phone’s settings").wait_for(timeout=WAIT_MS)
        assert not any(c[0] == "mobile.push_key" for c in stub.calls)


@pytest.mark.asyncio
async def test_without_push_an_iphone_is_told_the_home_screen_and_another_browser_that_it_cannot(fake_repo, monkeypatch):
    gone = "delete window.PushManager;"
    iphone = "Object.defineProperty(navigator, 'userAgent', {get: () => 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'});"
    async with _phone(fake_repo, monkeypatch, init=gone + iphone) as (stub, page):
        drawer, row = await _row(page)
        assert "Add Orkline to the Home Screen to get notifications here" in await row.inner_text()
        assert await row.get_by_role("button").count() == 0
    async with _phone(fake_repo, monkeypatch, init=gone) as (stub, page):
        drawer, row = await _row(page)
        assert "This browser cannot show notifications from Orkline" in await row.inner_text()


@pytest.mark.asyncio
async def test_the_badge_is_how_many_answers_wait_and_a_visit_from_a_notification_is_logged_once(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=fake()) as (stub, page):
        assert 2 in (await page.evaluate("window.__log"))["badge"]                  # the stub's snapshot: needs_you 2
        assert not any(c[0] == "ideas.log" and c[1].get("what") == "push" for c in stub.calls)
    async with _phone(fake_repo, monkeypatch, init=fake(), extra="&needs&from=push-needs") as (stub, page):
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "push", "ref": "needs", "device": "phone"})
        await page.locator(".raised").wait_for(timeout=WAIT_MS)                    # a notification's visit: the first stop of the goal that waits, popped out along the bottom
        assert await page.locator(".raised").is_visible() and await page.locator(".hc").count() >= 1
        assert "from=push" not in page.url
