"""📍 Places, stage 1 of docs/design/phone-places.md: what a paired phone may say of a place (a name and how freely its
news is acted on), the report checked before anything hears it, the history kept on this machine, and the phone
listener on the tailnet. What the town does with a report (the External listeners, its roads, Shortcuts' own token)
is Orkline's."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import subprocess
import time
from pathlib import Path

import pytest

from orkboard.gui import phones, tailnet
from orkboard.gui.board_host import Orkboard
from orkboard.realm import places

from tests.test_phones import _https


# -- the rules, without a town ------------------------------------------------------------------------

def test_a_place_is_a_name_and_how_freely_its_news_is_acted_on():
    got = places.parse({"places": ["Home", {"name": "office", "autonomy": "free", "shelf_h": 99, "say": " Go "},
                                   "home", {"name": "!!"}, "gym autonomy=bold shelf=3 say=Go  now"]})
    assert [p.name for p in got] == ["home", "office", "gym"]
    assert got[0].autonomy == "chains" and got[1].autonomy == "free" and got[2].autonomy == "chains"
    assert got[1].shelf_h == places.SHELF_MAX_H and got[1].say == "Go"
    assert got[0].text("arrived") == places.SAY["arrived"]
    assert got[2].shelf_h == 3 and got[2].say == "Go now" and got[2].line() == "gym shelf=3 say=Go now"
    assert places.place_of(got[1].line()) == got[1]
    assert places.keep_days({}) == 7 and places.keep_days({"places_keep_days": 9999}) == 365


def test_a_report_is_checked_before_anything_hears_it():
    now = dt.datetime(2026, 10, 8, 19, 0)
    ok = places.check({"id": "abcdef12", "place": "Home", "change": "left", "at": "2026-10-08T18:59:00"},
                      ["home"], "Ann's phone", "0123456789abcdef", now)
    assert ok == places.Report("abcdef12", "home", "left", "2026-10-08T18:59:00", "Ann's phone", "0123456789abcdef")
    bad = [({"id": "x", "place": "home", "change": "left"}, "id is"),
           ({"id": "abcdef12", "place": "gym", "change": "left"}, "No place named 'gym'"),
           ({"id": "abcdef12", "place": "home", "change": "came"}, "arrived or left"),
           ({"id": "abcdef12", "place": "home", "change": "left", "at": "soon"}, "not a time"),
           ({"id": "abcdef12", "place": "home", "change": "left", "at": "2026-10-08T20:00:00"}, "future"),
           ("home", "Not a place report")]
    for body, says in bad:
        with pytest.raises(places.PlaceError, match=says):
            places.check(body, ["home"], now=now)


def test_a_report_in_another_zone_is_read_as_local_time():
    now = dt.datetime.now()
    utc = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    r = places.check({"id": "abcdef12", "place": "home", "change": "left", "at": utc}, ["home"], now=now)
    assert abs((dt.datetime.fromisoformat(r.at) - now).total_seconds()) < 5


def test_the_history_lives_beside_the_machine_settings_never_in_the_project(fake_repo, tmp_path):
    f = places.history_file(fake_repo)
    assert tmp_path in f.parents and fake_repo not in f.parents
    h = places.History(f, keep=7)
    now = dt.datetime(2026, 10, 8, 12, 0)
    old = places.Report("old00001", "home", "left", "2026-09-01T08:00:00", "p", "d1")
    h.add(old, "sent", now - dt.timedelta(days=30))
    h.add(places.Report("new00001", "home", "arrived", "2026-10-08T11:59:00", "p", "d1"), "asked", now)
    assert [x.id for x in h.all()] == ["new00001"]                      # what was older than a week went
    h.add(places.Report("other001", "home", "arrived", "2026-10-08T11:59:00", "q", "d2"), "sent", now)
    assert h.seen("other001") and places.forget_device("d1", f.parent) == 1
    assert [x.id for x in h.all()] == ["other001"]
    h.clear()
    assert not f.exists()


# -- Tailscale ---------------------------------------------------------------------------------------------

def _ran(stdout: str = "", code: int = 0, then=None):
    def run(argv, **kw):
        if then:
            then(argv)
        return subprocess.CompletedProcess(argv, code, stdout, "")
    return run


def test_tailscale_is_found_when_it_runs_and_logged_in():
    status = {"BackendState": "Running", "Self": {"TailscaleIPs": ["100.64.0.7", "fd7a::7"], "DNSName": "Town.tail12.ts.net."}}
    assert tailnet.find(_ran(json.dumps(status))) == tailnet.Tail("100.64.0.7", "town.tail12.ts.net")
    assert tailnet.find(_ran(json.dumps({**status, "BackendState": "NeedsLogin"}))) is None
    assert tailnet.find(_ran("", 1)) is None


def test_tailscale_is_left_alone_when_told(monkeypatch):
    monkeypatch.setenv("ORKCRAFT_TAILSCALE", "off")
    assert tailnet.find(_ran(json.dumps({"BackendState": "Running", "Self": {"TailscaleIPs": ["100.64.0.7"]}}))) is None


def test_the_tailnet_certificate_is_asked_once_a_month(tmp_path):
    tail, asked = tailnet.Tail("100.64.0.7", "town.tail12.ts.net"), []

    def make(argv):
        asked.append(argv)
        Path(argv[argv.index("--cert-file") + 1]).write_text("c")
        Path(argv[argv.index("--key-file") + 1]).write_text("k")
    crt, key = tailnet.cert(tail, tmp_path, _ran(then=make))
    assert asked[0][-1] == "town.tail12.ts.net" and oct(key.stat().st_mode & 0o777) == "0o600"
    assert tailnet.cert(tail, tmp_path, _ran(then=make)) == (crt, key) and len(asked) == 1
    tailnet.cert(tail, tmp_path, _ran(then=make), now=time.time() + 31 * 86400)
    assert len(asked) == 2
    assert tailnet.cert(tailnet.Tail("100.64.0.7", ""), tmp_path, _ran(then=make)) is None   # no MagicDNS


@pytest.mark.asyncio
async def test_the_listener_listens_on_the_tailnet_too_and_the_qr_code_says_so(fake_repo, monkeypatch):
    host = Orkboard(fake_repo)
    listener = phones.Listener(host)
    monkeypatch.setattr(phones, "lan_ip", lambda: None)                      # no Wi-Fi: the tailnet alone
    listener.tail_find = lambda: tailnet.Tail("127.0.0.1", "")
    try:
        offer = listener.pair()
        for _ in range(200):
            if listener.tail_server is not None and not isinstance(listener.tail_server, phones._Pending):
                break
            await asyncio.sleep(0.02)
        assert listener.tail_address.startswith("https://127.0.0.1:") and not listener.tail_trusted
        assert offer["link"].startswith("orkcraft://pair?v=1&addr=https%3A%2F%2F127.0.0.1")
        status, _, fp = await asyncio.to_thread(_https, listener.tail_address, "GET", "/api/version", None,
                                                   {"Authorization": f"Bearer {offer['code']}"})
        assert status == 200 and fp == offer["fingerprint"]
    finally:
        listener.stop()
    assert not listener.listening and listener.tail_address == ""
