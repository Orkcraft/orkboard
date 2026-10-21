"""The files of a pick (docs/specs/51-pick-one.md §3, §8 A): `GET /media/<goal>/<pick-id>/<file>?s=<signature>` on the page's server and
on the phones' listener: a signed address served with its stored type and the headers of §3, Range (206), and a 404 for a wrong or
missing signature, a name with `..` or `/`, a file the pick does not list and the address of another pick."""
from __future__ import annotations

import asyncio
import http.client
import re
import threading
from pathlib import Path

import pytest

from orkboard.gui import media
from orkboard.gui.board_host import Orkboard
from orkboard.gui.server import Server
from tests import pick_files as pf
from tests.test_phones import _pair, _pinned, _serve

PNG, SVG, WAV, TEXT = pf.png(5, 4), pf.svg(), pf.wav(0.5), pf.text("Take it easy.")


@pytest.fixture
def host(fake_repo: Path):
    h = Orkboard(fake_repo)
    yield h
    h.close()


@pytest.fixture
def pick(host, tmp_path: Path) -> dict:
    """k1's first round: a picture, an SVG and a sound; k2's, in another goal, beside it."""
    state = host.ideas.state_dir
    pf.make_pick(state, tmp_path / "s2", {"a.png": pf.png(9, 9), "b.png": pf.png(8, 8)}, slug="other-goal", tid="k2")
    return pf.make_pick(state, tmp_path / "s1", {"a.png": PNG, "b.svg": SVG}, slug="dark-mode") | {"slug": "dark-mode"}


def dirs(host) -> list[Path]:
    return media.state_dirs(host)


def get(host, target: str, range_header: str = "", method: str = "GET") -> media.Reply:
    return media.serve(method, target, range_header, dirs(host))


def headers(reply: media.Reply) -> dict[str, str]:
    return {k.lower(): v for k, v in reply.headers}


# -- the signature ------------------------------------------------------------------------------------------------------

def test_an_address_is_signed_with_a_secret_of_the_process_and_only_its_own_path_is_proved():
    u = media.url("dark-mode", "k1-r1", "a.png")
    path, sig = u.split("?s=")
    assert path == "/media/dark-mode/k1-r1/a.png" and re.fullmatch(r"[0-9a-f]{32}", sig)
    assert media.check(path, sig) and not media.check(path, sig[:-1] + ("0" if sig[-1] != "0" else "1"))
    assert not media.check("/media/dark-mode/k1-r1/b.png", sig) and not media.check(path, "") and not media.check(path, "x")
    assert media.url("dark-mode", "k1-r1", "a.png") == u                                          # the same path, the same proof
    assert media.sign(path) != media.sign(path + "x") and media._SECRET and len(media._SECRET) == 32


@pytest.mark.parametrize("target", ["/media/dark-mode/k1-r1", "/media/dark-mode/k1-r1/a.png/more", "/media//k1-r1/a.png", "/media/dark-mode/k1-r1/",
                                    "/media/../k1-r1/a.png", "/media/dark-mode/../a.png", "/media/dark-mode/k1-r1/..", "/media/dark-mode/k1-r1/%2e%2e",
                                    "/media/dark-mode/k1-r1/a%2Fb.png", "/media/dark-mode/k1-r1/.hidden", "/media/Dark/k1-r1/a.png",
                                    "/media/dark-mode/k1/a.png", "/media/dark-mode/k1-r1/a b.png", "/static/dark-mode/k1-r1/a.png"])
def test_a_path_that_is_not_one_plain_file_of_a_pick_is_no_address_at_all(target):
    assert media.parse(target) is None


# -- serving ------------------------------------------------------------------------------------------------------------

def test_a_signed_address_is_served_with_its_stored_type_and_the_headers_of_the_spec(host, pick):
    reply = get(host, media.url("dark-mode", "k1-r1", "a.png"))
    h = headers(reply)
    assert reply.status == 200 and reply.read() == PNG
    assert h["content-type"] == "image/png" and h["content-length"] == str(len(PNG)) and h["accept-ranges"] == "bytes"
    assert h["cache-control"] == "private, max-age=31536000, immutable" and h["x-content-type-options"] == "nosniff"
    assert h["content-security-policy"] == "sandbox; default-src 'none'"
    assert h["content-disposition"].startswith("inline; filename=") and "a.png" in h["content-disposition"]
    svg = get(host, media.url("dark-mode", "k1-r1", "b.svg"))                                      # an SVG on its own screen runs nothing
    assert headers(svg)["content-type"] == "image/svg+xml" and headers(svg)["content-security-policy"] == "sandbox; default-src 'none'"
    assert svg.read() == SVG


def test_a_text_is_served_as_utf8_and_a_sound_by_its_stored_type(host, tmp_path):
    state = host.ideas.state_dir
    pf.make_pick(state, tmp_path / "t", {"a.txt": TEXT, "b.md": pf.text("# Hi")}, slug="words", kind="text")
    assert headers(get(host, media.url("words", "k1-r1", "a.txt")))["content-type"] == "text/plain; charset=utf-8"
    assert headers(get(host, media.url("words", "k1-r1", "b.md")))["content-type"] == "text/markdown; charset=utf-8"
    pf.make_pick(state, tmp_path / "w", {"a.wav": WAV, "b.mp3": pf.mp3()}, slug="jingle", kind="audio")
    assert headers(get(host, media.url("jingle", "k1-r1", "a.wav")))["content-type"] == "audio/wav"
    assert headers(get(host, media.url("jingle", "k1-r1", "b.mp3")))["content-type"] == "audio/mpeg"


@pytest.mark.parametrize("asked, status, first, last", [
    ("bytes=0-9", 206, 0, 9), ("bytes=10-", 206, 10, None), ("bytes=-12", 206, None, None), ("bytes=5-5", 206, 5, 5),
    ("bytes=0-99999999", 206, 0, None), ("bytes=-99999999", 206, 0, None),
])
def test_a_range_is_a_206_with_its_bytes_so_a_sound_or_a_clip_seeks(host, tmp_path, asked, status, first, last):
    pf.make_pick(host.ideas.state_dir, tmp_path / "w", {"a.wav": pf.wav(1.0), "b.wav": pf.wav(0.5)}, slug="jingle", kind="audio")
    whole = pf.wav(1.0)
    reply = get(host, media.url("jingle", "k1-r1", "a.wav"), asked)
    size = len(whole)
    if first is None:                                                    # a suffix
        first, last = size - 12, size - 1
    last = size - 1 if last is None else min(last, size - 1)
    h = headers(reply)
    assert reply.status == status and h["content-range"] == f"bytes {first}-{last}/{size}"
    assert h["content-length"] == str(last - first + 1) and h["content-type"] == "audio/wav" and h["accept-ranges"] == "bytes"
    assert reply.read() == whole[first:last + 1]


def test_a_range_past_the_end_is_416_and_a_range_that_is_not_one_is_the_whole_file(host, pick):
    u = media.url("dark-mode", "k1-r1", "a.png")
    gone = get(host, u, f"bytes={len(PNG)}-")
    assert gone.status == 416 and headers(gone)["content-range"] == f"bytes */{len(PNG)}" and gone.read() == b""
    assert get(host, u, "bytes=-0").status == 416
    for odd in ("lines=0-3", "bytes=5-2", "bytes=a-b", "bytes=0-1,4-5", "", "bytes=-"):
        reply = get(host, u, odd)
        assert reply.status == 200 and reply.read() == PNG, odd


def test_head_has_the_headers_of_get_and_no_body_and_other_methods_are_refused(host, pick):
    u = media.url("dark-mode", "k1-r1", "a.png")
    head = get(host, u, method="HEAD")
    assert head.status == 200 and head.read() == b"" and headers(head)["content-length"] == str(len(PNG))
    assert get(host, u, "bytes=0-3", method="HEAD").status == 206
    for method in ("POST", "PUT", "DELETE"):
        assert get(host, u, method=method).status == 405


def test_no_signature_a_wrong_one_or_the_signature_of_another_path_is_a_404(host, pick):
    path = "/media/dark-mode/k1-r1/a.png"
    other = media.url("other-goal", "k2-r1", "a.png")
    for target in (path, path + "?s=", path + "?s=deadbeef", path + "?t=" + media.sign(path), path + "?s=" + media.sign(path)[::-1],
                   path + "?s=" + other.split("?s=")[1],                                               # another pick's proof on this path
                   "/media/dark-mode/k1-r1/b.svg?s=" + media.sign(path)):
        reply = get(host, target)
        assert reply.status == 404 and reply.read() == b"Not found", target
        assert "private" not in headers(reply).get("cache-control", "")


def test_a_name_with_dots_or_slashes_is_a_404_even_when_it_is_signed(host, pick):
    for goal, pid, name in (("dark-mode", "k1-r1", "../k1-r1/a.png"), ("dark-mode", "../dark-mode/k1-r1", "a.png"), ("..", "k1-r1", "a.png"),
                            ("dark-mode", "k1-r1", "%2e%2e/a.png"), ("dark-mode", "k1-r1", "a.png/")):
        path = f"/media/{goal}/{pid}/{name}"
        assert get(host, f"{path}?s={media.sign(path)}").status == 404, path


def test_the_address_of_another_pick_serves_that_picks_file_only_and_a_file_it_does_not_list_is_a_404(host, pick):
    mine, theirs = media.url("dark-mode", "k1-r1", "a.png"), media.url("other-goal", "k2-r1", "a.png")
    assert get(host, mine).read() == PNG and get(host, theirs).read() == pf.png(9, 9)                   # each its own
    assert get(host, media.url("dark-mode", "k2-r1", "a.png")).status == 404                            # k2's round is in another goal
    assert get(host, media.url("dark-mode", "k1-r2", "a.png")).status == 404                            # a round that was never made
    assert get(host, media.url("dark-mode", "k1-r1", "c.png")).status == 404                            # a name the pick does not list
    assert get(host, media.url("dark-mode", "k1-r1", "pick.json")).status == 404                        # … its own manifest too
    assert get(host, media.url("no-such-goal", "k1-r1", "a.png")).status == 404
    folder = host.ideas.state_dir / "ideas" / "dark-mode" / "picks" / "k1-r1"
    (folder / "extra.png").write_bytes(PNG)                                                             # a file there that the pick never listed
    assert get(host, media.url("dark-mode", "k1-r1", "extra.png")).status == 404
    (folder / "a.png").unlink()
    (folder / "a.png").symlink_to(host.ideas.state_dir.parent / "README.md")                            # a link out of its folder
    assert get(host, mine).status == 404


def test_a_secret_of_another_run_is_dead(host, pick, monkeypatch):
    old = media.url("dark-mode", "k1-r1", "a.png")
    monkeypatch.setattr(media, "_SECRET", b"x" * 32)
    assert get(host, old).status == 404 and get(host, media.url("dark-mode", "k1-r1", "a.png")).status == 200


def test_the_open_projects_are_looked_in_the_shown_one_first(host, pick, tmp_path):
    other = tmp_path / "second"
    other.mkdir()
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=other, check=True)
    host.command("projects.open", {"path": str(other)})
    shown = host.ideas.state_dir                                      # the second project is shown now
    assert shown != host.projects.open_ones[0].ideas.state_dir and len(media.state_dirs(host)) == 2
    assert media.state_dirs(host)[0] == shown
    assert get(host, media.url("dark-mode", "k1-r1", "a.png")).read() == PNG                 # found in the first project, shown or not


# -- over HTTP --------------------------------------------------------------------------------------------------------------

def _fetch(origin: str, target: str, headers: dict | None = None, method: str = "GET") -> tuple[int, dict, bytes]:
    host, port = origin.removeprefix("http://").rsplit(":", 1)
    conn = http.client.HTTPConnection(host, int(port), timeout=5)
    try:
        conn.request(method, target, headers=headers or {})
        r = conn.getresponse()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
    finally:
        conn.close()


def test_the_pages_server_serves_a_signed_address_without_its_token_and_a_range(host, pick):
    server = Server(host)
    thread = server.start_thread()
    try:
        status, h, body = _fetch(server.origin, media.url("dark-mode", "k1-r1", "a.png"))
        assert (status, body, h["content-type"]) == (200, PNG, "image/png")
        assert h["cache-control"] == "private, max-age=31536000, immutable" and h["x-content-type-options"] == "nosniff"
        assert h["content-security-policy"] == "sandbox; default-src 'none'" and h["accept-ranges"] == "bytes"
        status, h, body = _fetch(server.origin, media.url("dark-mode", "k1-r1", "a.png"), {"Range": "bytes=4-9"})
        assert (status, body, h["content-range"]) == (206, PNG[4:10], f"bytes 4-9/{len(PNG)}")
        assert _fetch(server.origin, "/media/dark-mode/k1-r1/a.png")[0] == 404
        assert _fetch(server.origin, "/media/dark-mode/k1-r1/a.png?s=nope")[0] == 404
        assert _fetch(server.origin, "/media/dark-mode/k1-r1/..%2fa.png?s=" + media.sign("/media/dark-mode/k1-r1/..%2fa.png"))[0] == 404
        assert _fetch(server.origin, media.url("dark-mode", "k1-r1", "a.png"), method="HEAD")[2] == b""
        assert _fetch(server.origin, "/api/version")[0] == 403                                  # the rest of the server is as it was
    finally:
        server.stop()
        thread.join(10)


def _phone_get(address: str, target: str, headers: dict | None = None, method: str = "GET") -> tuple[int, dict, bytes]:
    import http.client as hc
    host, port = address.removeprefix("https://").rsplit(":", 1)
    conn = hc.HTTPSConnection(host, int(port), context=_pinned(), timeout=5)
    try:
        conn.request(method, target, headers=headers or {})
        r = conn.getresponse()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_the_phones_listener_serves_it_too_with_a_range_and_two_requests_on_one_connection(fake_repo, tmp_path):
    server, task = await _serve(fake_repo)
    try:
        await _pair(server)
        state = server.host.ideas.state_dir
        pf.make_pick(state, tmp_path / "s", {"a.png": PNG, "b.svg": SVG}, slug="dark-mode")
        pf.make_pick(state, tmp_path / "w", {"a.wav": pf.wav(1.0), "b.wav": pf.wav(0.5)}, slug="jingle", kind="audio")
        addr = server.phones.address
        status, h, body = await asyncio.to_thread(_phone_get, addr, media.url("dark-mode", "k1-r1", "a.png"))
        assert (status, body, h["content-type"]) == (200, PNG, "image/png")
        assert h["cache-control"] == "private, max-age=31536000, immutable" and h["x-content-type-options"] == "nosniff"
        assert h["content-security-policy"] == "sandbox; default-src 'none'" and h["accept-ranges"] == "bytes"
        status, h, body = await asyncio.to_thread(_phone_get, addr, media.url("jingle", "k1-r1", "a.wav"), {"Range": "bytes=100-199"})
        assert (status, len(body), h["content-range"]) == (206, 100, f"bytes 100-199/{len(pf.wav(1.0))}")
        assert body == pf.wav(1.0)[100:200]
        status, h, body = await asyncio.to_thread(_phone_get, addr, media.url("dark-mode", "k1-r1", "b.svg"))
        assert (status, h["content-type"], body) == (200, "image/svg+xml", SVG) and "sandbox" in h["content-security-policy"]
        for target in ("/media/dark-mode/k1-r1/a.png", "/media/dark-mode/k1-r1/a.png?s=0", "/media/dark-mode/k1-r2/a.png?s=0",
                       "/media/dark-mode/k1-r1/%2e%2e%2fa.png?s=0"):
            assert (await asyncio.to_thread(_phone_get, addr, target))[0] == 404, target
        assert (await asyncio.to_thread(_phone_get, addr, media.url("dark-mode", "k1-r1", "a.png"), None, "HEAD"))[2] == b""
        raw = await asyncio.to_thread(_phone_keepalive, server, [media.url("dark-mode", "k1-r1", "a.png"), media.url("dark-mode", "k1-r1", "b.svg")])
        assert raw.count(b"HTTP/1.1 200 OK") == 2 and PNG in raw and SVG in raw
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)


def _phone_keepalive(server, targets: list[str]) -> bytes:
    """GETs on one connection, the last one asking to close it: every one answered, in order."""
    import socket
    host, port = server.phones.address.removeprefix("https://").rsplit(":", 1)
    raw = b""
    with socket.create_connection((host, int(port)), timeout=5) as sock, _pinned().wrap_socket(sock, server_hostname=host) as tls:
        for n, target in enumerate(targets):
            last = n == len(targets) - 1
            tls.sendall((f"GET {target} HTTP/1.1\r\nHost: x\r\n" + ("Connection: close\r\n" if last else "") + "\r\n").encode())
            if last:
                while chunk := tls.recv(65536):
                    raw += chunk
                continue
            got = b""
            while b"\r\n\r\n" not in got:
                got += tls.recv(65536)
            head, _, rest = got.partition(b"\r\n\r\n")
            assert b"Connection: keep-alive" in head, head
            length = int(re.search(rb"Content-Length: (\d+)", head).group(1))
            while len(rest) < length:
                rest += tls.recv(65536)
            raw += head + b"\r\n\r\n" + rest
    return raw
