"""The listener for phones, stage 1 of docs/design/mobile.md: pairing, device tokens, TLS pinned by its
fingerprint, and a socket that passes only what a phone may send."""
from __future__ import annotations

import asyncio
import hashlib
import http.client
import json
import os
import ssl
import stat
from pathlib import Path

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from orkboard import settings
from orkboard.gui import pairing, phone_http, phone_tls, phones
from orkboard.gui.board_host import BoardPhone, Orkboard
from orkboard.gui.server import PROTOCOL, Server


# -- pairing, without a network ----------------------------------------------------------------------

def test_a_code_pairs_once_and_the_host_keeps_only_the_tokens_hash(tmp_path):
    p = pairing.Pairing(tmp_path / "settings.json")
    code = p.new_code(now=0.0)
    assert len(code) >= 43                                          # 32 random bytes
    device_id, token, name = p.pair(code, "  My\x07 phone ", now=1.0)
    assert name == "My phone" and p.device(token)["id"] == device_id
    raw = (tmp_path / "settings.json").read_text()
    assert token not in raw and code not in raw and hashlib.sha256(token.encode()).hexdigest() in raw
    assert set(p.public()[0]) == {"id", "name", "paired", "seen"}
    with pytest.raises(pairing.PairError):
        p.pair(code, "again", now=2.0)                              # once
    assert p.device("guess") is None and p.device("") is None and p.device(token[:-1]) is None


def test_a_code_runs_out_after_two_minutes(tmp_path):
    p = pairing.Pairing(tmp_path / "settings.json")
    code = p.new_code(now=0.0)
    assert p.code_ok(code, now=119.0) and not p.code_ok(code, now=121.0)
    with pytest.raises(pairing.PairError):
        p.pair(code, "late", now=121.0)


def test_the_sixth_attempt_in_a_minute_locks_pairing_until_a_new_code(tmp_path):
    p = pairing.Pairing(tmp_path / "settings.json")
    code = p.new_code(now=0.0)
    assert all(p.attempt(now=float(i)) for i in range(5))
    assert not p.attempt(now=6.0) and p.locked
    with pytest.raises(pairing.PairError):
        p.pair(code, "right code, too late", now=7.0)               # the code went with the lock
    assert not p.attempt(now=100.0)                                 # locked until the desktop shows a new code
    fresh = p.new_code(now=101.0)
    assert p.attempt(now=101.0) and p.pair(fresh, "phone", now=102.0)


def test_forget_is_at_once_and_a_town_that_loaded_earlier_never_brings_a_phone_back(tmp_path):
    file = tmp_path / "settings.json"
    stale = settings.load(file)                                     # another town on this machine, opened before
    p = pairing.Pairing(file)
    device_id, token, _ = p.pair(p.new_code(), "phone")
    loaded = settings.load(file)
    assert [d["id"] for d in loaded.phones] == [device_id]
    settings.save(stale, file)                                      # it saves its own settings…
    assert p.device(token) is not None                              # …and the phone stays paired
    assert p.forget(device_id) and p.device(token) is None
    settings.save(loaded, file)                                     # a town that knew the phone saves…
    assert p.device(token) is None and settings.load(file).phones == []   # …and it stays forgotten


def test_broken_phone_entries_are_dropped():
    good = {"id": "0123456789abcdef", "name": "a", "hash": "a" * 64, "paired": "", "seen": ""}
    raw = {"phones": [good, {**good, "hash": "short"}, {**good, "id": "x"}, "junk", {**good}], "phone_port": 80}
    s = settings.MachineSettings.from_dict(raw)
    assert s.phones == [good] and s.phone_port == 0


def test_commands_are_limited_to_a_few_a_second():
    b = pairing.Bucket(level=pairing.CMD_BURST, at=0.0)
    assert sum(b.take(now=0.0) for _ in range(20)) == pairing.CMD_BURST
    assert not b.take(now=0.05) and b.take(now=0.3)


def test_the_certificate_is_made_once_kept_private_and_named_by_its_fingerprint(tmp_path):
    cert, key = phone_tls.ensure(tmp_path)
    assert stat.S_IMODE(os.stat(key).st_mode) == 0o600 and stat.S_IMODE(os.stat(cert).st_mode) == 0o600
    fp = phone_tls.fingerprint(cert)
    assert len(fp.split(":")) == 32
    assert phone_tls.ensure(tmp_path) == (cert, key) and phone_tls.fingerprint(cert) == fp


def test_the_qr_code_carries_the_address_the_fingerprint_and_the_code():
    link = phones.pair_link("https://192.168.1.5:8765", "AB:CD", "c0de-_x")
    assert link == "orkcraft://pair?v=1&addr=https%3A%2F%2F192.168.1.5%3A8765&fp=ABCD&code=c0de-_x"
    assert phones.qr_data_uri(link).startswith("data:image/svg+xml;base64,")


def test_a_phones_stop_all_is_said_to_be_the_phones():
    assert BoardPhone.guard("halt", {}) == {"device": "phone"}      # the event log says which window stopped it (spec 33 §9)


def test_a_phone_may_not_pair_list_or_forget_phones(fake_repo):
    host = Orkboard(fake_repo)
    for name in ("phones.pair", "phones.list", "phones.forget", "phones.pair_stop", "watch", "term.attach",
                 "term.replay", "town.settings.set"):
        assert not BoardPhone.allowed(host, name, {}), name


# -- the listener, over TLS on 127.0.0.1 -----------------------------------------------------------

def _pinned() -> ssl.SSLContext:
    """As a phone does: no CA, the certificate's fingerprint checked after the handshake."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    return ctx


def _fp(der: bytes) -> str:
    return ":".join(f"{b:02X}" for b in hashlib.sha256(der).digest())


def _https(address: str, method: str, path: str, body: dict | None = None, headers: dict | None = None,
           raw: bytes | None = None) -> tuple[int, dict, str]:
    host, port = address.removeprefix("https://").rsplit(":", 1)
    conn = http.client.HTTPSConnection(host, int(port), context=_pinned(), timeout=5)
    try:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        hdrs = {"Content-Type": "application/json"} if data is not None else {}
        conn.request(method, path, body=data, headers={**hdrs, **(headers or {})})
        fp = _fp(conn.sock.getpeercert(binary_form=True))
        r = conn.getresponse()
        text = r.read().decode()
        try:
            out = json.loads(text)
        except ValueError:
            out = {}
        return r.status, out, fp
    finally:
        conn.close()


async def _serve(repo: Path):
    server = Server(Orkboard(repo))
    server.phones.bind = "127.0.0.1"
    task = asyncio.create_task(server.run())
    for _ in range(200):
        if server.ready.is_set():
            break
        await asyncio.sleep(0.02)
    return server, task


async def _listening(server: Server) -> None:
    for _ in range(200):
        if server.phones.server is not None and not isinstance(server.phones.server, phones._Pending):
            return
        await asyncio.sleep(0.02)
    raise AssertionError("the listener did not come up")


async def _pair(server: Server, name: str = "Test phone") -> tuple[str, str]:
    offer = server.host.command("phones.pair")
    await _listening(server)
    status, body, fp = await asyncio.to_thread(_https, offer["address"], "POST", "/api/pair",
                                               {"code": offer["code"], "name": name})
    assert status == 200 and fp == offer["fingerprint"], body
    assert offer["link"].endswith("code=" + offer["code"]) and offer["qr"]
    return body["id"], body["token"]


def _ws_url(server: Server) -> str:
    return server.phones.address.replace("https://", "wss://") + "/ws"


@pytest.mark.asyncio
async def test_no_phone_paired_no_port_on_the_lan(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        assert not server.phones.listening and server.host.command("phones.list")["phones"] == []
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_a_paired_phone_reads_the_compact_town_and_sends_only_what_a_phone_may(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        device_id, token = await _pair(server)
        auth = {"Authorization": f"Bearer {token}"}
        status, body, _ = await asyncio.to_thread(_https, server.phones.address, "GET", "/api/version", None, auth)
        assert status == 200 and body["protocol"] == PROTOCOL and body["api"] == phones.API
        status, _, _ = await asyncio.to_thread(_https, server.phones.address, "GET", "/api/version")
        assert status == 403
        assert (await asyncio.to_thread(_https, server.phones.address, "GET", "/", None, auth))[0] == 404

        async with connect(_ws_url(server), ssl=_pinned(), additional_headers=auth) as ws:
            first = json.loads(await asyncio.wait_for(ws.recv(), 5))
            assert first["t"] == "state" and first["state"]["v"] == phones.API and "projects" not in first["state"]

            async def cmd(i, name, args=None):
                await ws.send(json.dumps({"t": "cmd", "id": i, "name": name, "args": args or {}}))
                while True:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if msg["t"] == "reply" and msg["id"] == i:
                        return msg

            hello = await cmd(1, "mobile.hello")
            assert hello["ok"] and hello["result"]["api"] == phones.API
            same = await cmd(2, "mobile.snapshot", {"since": first["state"]["rev"]})
            assert same["result"]["same"] is True
            for i, name in enumerate(("term.input", "town.build", "watch", "term.attach", "phones.pair",
                                      "town.settings.set"), start=10):
                refused = await cmd(i, name, {"key": "x", "data": "rm -rf /\r"})
                assert not refused["ok"] and refused["error"] == f"Not from a phone: {name}"
            answered = await cmd(20, "ideas.board")                  # the Board's commands are a phone's
            assert answered["ok"] and "tracks" in answered["result"]
            halted = await cmd(21, "halt")
            assert halted["ok"] and isinstance(halted["result"], int)
        seen = server.host.command("phones.list")["phones"]
        assert [p["id"] for p in seen] == [device_id]
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_without_a_device_token_there_is_no_socket(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        await _pair(server)
        for headers in ({}, {"Authorization": "Bearer guess"}, {"Authorization": f"Bearer {server.token}"}):
            with pytest.raises(InvalidStatus) as e:
                async with connect(_ws_url(server), ssl=_pinned(), additional_headers=headers):
                    pass
            assert e.value.response.status_code == 403
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_forget_closes_the_phones_socket_at_once_and_its_token_is_dead(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        device_id, token = await _pair(server)
        await _pair(server, "Second phone")                          # another stays: the listener keeps listening
        auth = {"Authorization": f"Bearer {token}"}
        async with connect(_ws_url(server), ssl=_pinned(), additional_headers=auth) as ws:
            await asyncio.wait_for(ws.recv(), 5)
            left = server.host.command("phones.forget", {"id": device_id})
            assert [p["name"] for p in left["phones"]] == ["Second phone"] and left["listening"]
            with pytest.raises(ConnectionClosed) as e:
                await asyncio.wait_for(ws.recv(), 5)
            assert e.value.rcvd.code == 1008
        with pytest.raises(InvalidStatus):
            async with connect(_ws_url(server), ssl=_pinned(), additional_headers=auth):
                pass
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_the_last_phone_forgotten_the_listener_stops(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        device_id, _ = await _pair(server)
        assert server.phones.listening
        assert not server.host.command("phones.forget", {"id": device_id})["listening"]
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_pairing_locks_after_five_wrong_codes_and_says_so_on_the_desktop(fake_repo):
    server, task = await _serve(fake_repo)
    toasts = []
    server.host.on_toast = toasts.append
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        address = offer["address"]
        for _ in range(5):
            status, body, _ = await asyncio.to_thread(_https, address, "POST", "/api/pair", {"code": "guess", "name": "x"})
            assert status == 403
        status, body, _ = await asyncio.to_thread(_https, address, "POST", "/api/pair", {"code": offer["code"], "name": "x"})
        assert status == 429 and "locked" in body["error"]
        assert any("Too many pairing attempts" in t["message"] for t in toasts)
        fresh = server.host.command("phones.pair")
        status, _, _ = await asyncio.to_thread(_https, address, "POST", "/api/pair", {"code": fresh["code"], "name": "x"})
        assert status == 200
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_a_pairing_request_must_be_json_and_small(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        address = offer["address"]
        status, _, _ = await asyncio.to_thread(_https, address, "POST", "/api/pair", None,
                                               {"Content-Type": "text/plain"}, json.dumps({"code": offer["code"]}).encode())
        assert status == 415                                         # a browser's simple POST cannot pair
        status, _, _ = await asyncio.to_thread(_https, address, "POST", "/api/pair", None, None, b"x" * 5000)
        assert status == 413
        status, _, _ = await asyncio.to_thread(_https, address, "GET", "/api/pair")
        assert status == 405
        # The code is still good: none of those tried it.
        status, _, _ = await asyncio.to_thread(_https, address, "POST", "/api/pair", {"code": offer["code"], "name": "x"})
        assert status == 200
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_a_town_with_a_paired_phone_listens_from_the_start_and_the_version_takes_the_code(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        status, body, _ = await asyncio.to_thread(_https, offer["address"], "GET", "/api/version", None,
                                                  {"Authorization": f"Bearer {offer['code']}"})
        assert status == 200 and body["api"] == phones.API          # a phone checks the version before it pairs
        await asyncio.to_thread(_https, offer["address"], "POST", "/api/pair", {"code": offer["code"], "name": "p"})
        port = settings.load().phone_port
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)
    server, task = await _serve(fake_repo)
    try:
        await _listening(server)
        assert server.phones.address.endswith(f":{port}")            # the same port: the phone finds it again
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_a_phone_that_floods_is_told_to_wait(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        _, token = await _pair(server)
        async with connect(_ws_url(server), ssl=_pinned(), additional_headers={"Authorization": f"Bearer {token}"}) as ws:
            await asyncio.wait_for(ws.recv(), 5)
            for i in range(30):
                await ws.send(json.dumps({"t": "cmd", "id": i, "name": "mobile.snapshot", "args": {"since": "x"}}))
            replies = []
            while len(replies) < 30:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 5))
                if msg["t"] == "reply":
                    replies.append(msg)
            assert any(not r["ok"] and "Too many" in r["error"] for r in replies)
            assert sum(r["ok"] for r in replies) >= pairing.CMD_BURST
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_halt_from_a_phone_says_on_the_desktop_which_phone(fake_repo):
    server, task = await _serve(fake_repo)
    toasts = []
    try:
        _, token = await _pair(server, "Pocket")
        server.host.on_toast = toasts.append
        async with connect(_ws_url(server), ssl=_pinned(), additional_headers={"Authorization": f"Bearer {token}"}) as ws:
            await asyncio.wait_for(ws.recv(), 5)
            await ws.send(json.dumps({"t": "cmd", "id": 1, "name": "halt", "args": {}}))
            while json.loads(await asyncio.wait_for(ws.recv(), 5))["t"] != "reply":
                pass
        assert any("Pocket" in t["message"] for t in toasts)
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_a_listener_stopped_while_it_comes_up_never_comes_back_by_itself(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        server.host.command("phones.pair")
        assert not server.host.command("phones.pair_stop")["listening"]       # stopped before it came up
        offer = server.host.command("phones.pair")                           # and started anew at once
        await _listening(server)
        await asyncio.sleep(0.1)
        status, _, _ = await asyncio.to_thread(_https, offer["address"], "POST", "/api/pair",
                                               {"code": offer["code"], "name": "p"})
        assert status == 200
        server.host.command("phones.forget", {"id": server.host.command("phones.list")["phones"][0]["id"]})
        await asyncio.sleep(0.1)
        assert not server.phones.listening
        with pytest.raises(OSError):
            await asyncio.to_thread(_https, offer["address"], "GET", "/api/version")
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


def test_a_paired_phone_is_offered_keeping_the_computer_awake_once(fake_repo):
    """Spec 47 §3: `awake_offer` is the machine's word until `awake.offer` answers it."""
    host = Orkboard(fake_repo)
    listener = phones.Listener(host)
    assert listener.read()["awake_offer"] == ""                                  # no phone paired yet
    listener.pairing.pair(listener.pairing.new_code(), "Vadim's phone")
    assert listener.read()["awake_offer"] == "computer"                          # the fake Awake says Linux
    host.command("awake.offer", {"yes": False})
    assert listener.read()["awake_offer"] == "" and host.machine.keep_awake == "carts"


@pytest.mark.asyncio
async def test_two_get_requests_on_one_connection_both_answered_keep_alive(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        def run():
            host, port = offer["address"].removeprefix("https://").rsplit(":", 1)
            conn = http.client.HTTPSConnection(host, int(port), context=_pinned(), timeout=5)
            try:
                conn.request("GET", "/app/")
                r1 = conn.getresponse()
                assert r1.status == 200
                assert r1.getheader("Connection", "").lower() == "keep-alive"
                body1 = r1.read()
                assert b"Orkline" in body1

                conn.request("GET", "/app/board-app.js")
                r2 = conn.getresponse()
                assert r2.status == 200
                assert r2.getheader("Connection", "").lower() == "keep-alive"
                body2 = r2.read()
                assert len(body2) > 0
            finally:
                conn.close()
        await asyncio.to_thread(run)
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_connection_close_request_ends_the_connection(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        def run():
            host, port = offer["address"].removeprefix("https://").rsplit(":", 1)
            conn = http.client.HTTPSConnection(host, int(port), context=_pinned(), timeout=5)
            try:
                conn.request("GET", "/app/", headers={"Connection": "close"})
                r = conn.getresponse()
                assert r.status == 200
                assert r.getheader("Connection", "").lower() == "close"
                assert r.will_close is True
                assert conn.sock is None  # Connection: close ended the connection
                body = r.read()
                assert b"Orkline" in body
                assert r.isclosed()
            finally:
                conn.close()
        await asyncio.to_thread(run)
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_idle_timeout_closes_connection(fake_repo, monkeypatch):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        monkeypatch.setattr(phone_http, "IDLE_S", 0.2)
        def run():
            import time
            host, port = offer["address"].removeprefix("https://").rsplit(":", 1)
            conn = http.client.HTTPSConnection(host, int(port), context=_pinned(), timeout=5)
            try:
                conn.request("GET", "/app/")
                r = conn.getresponse()
                assert r.status == 200
                r.read()
                time.sleep(0.35)
                with pytest.raises((http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError, OSError)):
                    conn.request("GET", "/app/")
                    conn.getresponse()
            finally:
                conn.close()
        await asyncio.to_thread(run)
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


def _raw_exchange(address: str, data: bytes) -> bytes:
    """Send `data` on one TLS connection and read until the listener closes it: all it answered."""
    import socket
    host, port = address.removeprefix("https://").rsplit(":", 1)
    with socket.create_connection((host, int(port)), timeout=5) as raw, _pinned().wrap_socket(raw) as tls:
        tls.sendall(data)
        out = b""
        while chunk := tls.recv(65536):           # b"": the listener closed the connection
            out += chunk
    return out


@pytest.mark.asyncio
async def test_a_post_with_a_body_then_a_get_on_one_connection_gets_one_answer_and_the_close(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        body = json.dumps({"code": "guess", "name": "x"}).encode()
        data = (b"POST /api/pair HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
                + f"Content-Length: {len(body)}\r\n\r\n".encode() + body
                + b"GET /app/ HTTP/1.1\r\nHost: x\r\n\r\n")
        got = await asyncio.to_thread(_raw_exchange, offer["address"], data)
        assert got.count(b"HTTP/1.1 ") == 1                 # one answer: the GET behind it is never read
        head = got.split(b"\r\n\r\n", 1)[0].decode("latin-1")
        assert "Connection: close" in head and "keep-alive" not in head
        assert b"Orkline" not in got
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_an_http_1_0_request_without_keep_alive_is_answered_with_the_close(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        data = b"GET /app/ HTTP/1.0\r\nHost: x\r\n\r\nGET /app/board-app.js HTTP/1.0\r\nHost: x\r\n\r\n"
        got = await asyncio.to_thread(_raw_exchange, offer["address"], data)
        assert got.count(b"HTTP/1.1 200") == 1
        head = got.split(b"\r\n\r\n", 1)[0].decode("latin-1")
        assert "Connection: close" in head and "keep-alive" not in head
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_the_connection_header_is_a_list_of_options(fake_repo):
    """"keep-alive, Upgrade" asks for keep-alive (an HTTP/1.0 request is kept open); "close, x" asks to close."""
    server, task = await _serve(fake_repo)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        kept = (b"GET /app/ HTTP/1.0\r\nHost: x\r\nConnection: Keep-Alive, Upgrade\r\n\r\n"
                b"GET /app/board-app.js HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        got = await asyncio.to_thread(_raw_exchange, offer["address"], kept)
        assert got.count(b"HTTP/1.1 200") == 2
        assert b"Connection: keep-alive" in got.split(b"\r\n\r\n", 1)[0]
        closed = b"GET /app/ HTTP/1.1\r\nHost: x\r\nConnection: close, foo\r\n\r\nGET /app/board-app.js HTTP/1.1\r\nHost: x\r\n\r\n"
        got = await asyncio.to_thread(_raw_exchange, offer["address"], closed)
        assert got.count(b"HTTP/1.1 200") == 1
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


# -- spec 42 C: a phone's Web Push subscription ---------------------------------------------------------------

_PUSH = {"endpoint": "https://push.example.com/send/abc", "p256dh": "BCVxsr7N_eNgVRqvHtD0", "auth": "BTBZMqHH6r4T", "at": "2026-10-01T10:00:00",
         "morning": "2026-10-19"}


def _device(**more):
    return {"id": "0123456789abcdef", "name": "Pixel", "hash": "a" * 64, "paired": "", "seen": "", **more}


def test_clean_phones_keeps_a_good_push_and_drops_a_bad_one_and_anything_else_in_it():
    (good,) = settings.clean_phones([_device(push={**_PUSH, "extra": "gone"})])
    assert good["push"] == _PUSH
    for bad in ({**_PUSH, "endpoint": "http://insecure"}, {**_PUSH, "endpoint": "https://x/" + "a" * 1100}, {**_PUSH, "p256dh": "no spaces allowed"},
                {**_PUSH, "auth": ""}, {**_PUSH, "morning": "yesterday"}, "text", None):
        (kept,) = settings.clean_phones([_device(push=bad)])
        assert "push" not in kept and kept["id"] == "0123456789abcdef"             # the phone stays paired, the subscription goes


def test_a_subscription_is_kept_with_the_device_and_forgotten_with_it(tmp_path):
    p = pairing.Pairing(tmp_path / "settings.json")
    device_id, _token, _name = p.add("Pixel")
    assert p.set_push(device_id, _PUSH) and p.get(device_id)["push"] == _PUSH
    assert "push" not in p.public()[0] and not p.set_push(device_id, {**_PUSH, "endpoint": "nope"}) and p.set_push(device_id, None)
    assert "push" not in p.get(device_id)
    p.set_push(device_id, _PUSH)
    assert p.forget(device_id) and p.get(device_id) is None and not p.set_push(device_id, _PUSH)


@pytest.mark.asyncio
async def test_a_phone_with_its_socket_open_is_known_and_its_push_commands_carry_its_own_id(fake_repo):
    server, task = await _serve(fake_repo)
    try:
        device_id, token = await _pair(server)
        auth = {"Authorization": f"Bearer {token}"}
        assert server.phones.open_ids() == set()
        async with connect(_ws_url(server), ssl=_pinned(), additional_headers=auth) as ws:
            await asyncio.wait_for(ws.recv(), 5)
            assert server.phones.open_ids() == {device_id}

            async def cmd(i, name, args=None):
                await ws.send(json.dumps({"t": "cmd", "id": i, "name": name, "args": args or {}}))
                while True:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if msg["t"] == "reply" and msg["id"] == i:
                        return msg
            got = await cmd(1, "mobile.push_on", {"endpoint": _PUSH["endpoint"], "p256dh": _PUSH["p256dh"], "auth": _PUSH["auth"], "device_id": "someone-else"})
            assert got["ok"] and got["result"]["ok"]
            assert server.phones.pairing.get(device_id)["push"]["endpoint"] == _PUSH["endpoint"]            # its own, not the one it named
            assert (await cmd(2, "mobile.push_off"))["ok"] and "push" not in server.phones.pairing.get(device_id)
        await asyncio.sleep(0.2)
        assert server.phones.open_ids() == set()
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)
