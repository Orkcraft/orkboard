"""Spec 42 C (docs/specs/42-coming-back.md §3.2, Tests → C): `web_push.seal` against RFC 8291's Appendix A byte for byte and a
round trip with a receiver key made here, the VAPID JWT, and `send` with a stubbed opener."""
from __future__ import annotations

import json
import urllib.error

import pytest

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature  # noqa: E402
from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: E402
from cryptography.hazmat.primitives.kdf.hkdf import HKDF  # noqa: E402

from orkboard.gui import web_push as w  # noqa: E402

# RFC 8291 Appendix A: the example's keys, salt and message, and the body it gives.
PLAIN = b"When I grow up, I want to be a watermelon"
AS_PRIVATE = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
AS_PUBLIC = "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8"
UA_PUBLIC = "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
AUTH = "BTBZMqHH6r4Tts7J_aSIgg"
SALT = "DGv6ra1nlYgDCS1FRnbzlw"
BODY = ("DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4M"
        "qgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN")


@pytest.fixture(autouse=True)
def _folder(tmp_path, monkeypatch):
    monkeypatch.setenv("ORKCRAFT_SETTINGS_FILE", str(tmp_path / "settings.json"))


def test_seal_gives_the_body_of_rfcs_appendix_a_byte_for_byte():
    key = ec.derive_private_key(int.from_bytes(w.unb64(AS_PRIVATE), "big"), ec.SECP256R1())
    assert w.b64(w.point(key.public_key())) == AS_PUBLIC
    assert w.b64(w.seal(PLAIN, UA_PUBLIC, AUTH, salt=w.unb64(SALT), key=key)) == BODY


def test_a_receiver_opens_what_is_sealed_to_it():
    receiver = ec.generate_private_key(ec.SECP256R1())
    auth = b"0123456789abcdef"
    body = w.seal(b'{"title":"Orkline"}', w.b64(w.point(receiver.public_key())), w.b64(auth))
    salt, size, idlen = body[:16], int.from_bytes(body[16:20], "big"), body[20]
    sender = body[21:21 + idlen]
    assert size == 4096 and idlen == 65
    ua = w.point(receiver.public_key())
    shared = receiver.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), sender))
    ikm = HKDF(hashes.SHA256(), 32, auth, b"WebPush: info\x00" + ua + sender).derive(shared)
    cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(ikm)
    assert AESGCM(cek).decrypt(nonce, body[21 + idlen:], None) == b'{"title":"Orkline"}\x02'
    assert w.seal(b"x", w.b64(ua), w.b64(auth)) != w.seal(b"x", w.b64(ua), w.b64(auth))      # a salt and a key each time


def test_the_key_is_made_once_beside_the_settings_private_and_the_jwt_verifies():
    import os
    import stat
    first = w.public_key()
    assert w.public_key() == first and len(w.unb64(first)) == 65
    assert stat.S_IMODE(os.stat(w.key_path()).st_mode) == 0o600 and w.key_path().parent == w.settings.path().parent
    header = w.vapid("https://push.example.com/send/abc", now=1_000_000)
    assert header.startswith("vapid t=") and header.endswith(f", k={first}")
    jwt = header[len("vapid t="):header.index(", k=")]
    head, claims, sig = jwt.split(".")
    assert json.loads(w.unb64(head)) == {"typ": "JWT", "alg": "ES256"}
    assert json.loads(w.unb64(claims)) == {"aud": "https://push.example.com", "exp": 1_000_000 + 12 * 3600, "sub": "https://github.com/orkWorks/orkBoard"}
    raw = w.unb64(sig)
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), w.unb64(first))
    public.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")), f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))


def _sub():
    receiver = ec.generate_private_key(ec.SECP256R1())
    return {"endpoint": "https://push.example.com/send/abc", "p256dh": w.b64(w.point(receiver.public_key())), "auth": w.b64(b"0123456789abcdef")}


def test_send_posts_the_sealed_message_with_its_headers_and_gives_the_status(monkeypatch):
    seen = []

    class Answer:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(w, "OPENER", lambda request, timeout: (seen.append((request, timeout)), Answer())[1])
    assert w.send(_sub(), {"title": "Orkline", "body": "A spec asks · Offline mode", "tag": "needs", "badge": 2, "url": "./#needs"}) == 201
    request, timeout = seen[0]
    headers = {k.lower(): v for k, v in request.header_items()}
    assert timeout == 10 and request.get_method() == "POST" and request.full_url == "https://push.example.com/send/abc"
    assert headers["content-encoding"] == "aes128gcm" and headers["content-type"] == "application/octet-stream"
    assert headers["ttl"] == "43200" and headers["urgency"] == "high" and headers["topic"] == "needs"
    assert headers["authorization"].startswith("vapid t=") and len(request.data) < 1024
    w.send(_sub(), {"title": "Orkline", "body": "x", "tag": "recap"})
    assert {k.lower(): v for k, v in seen[1][0].header_items()}["urgency"] == "normal"


def test_send_gives_the_error_status_zero_when_none_and_never_raises(monkeypatch):
    def gone(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 410, "Gone", {}, None)
    monkeypatch.setattr(w, "OPENER", gone)
    assert w.send(_sub(), {"title": "Orkline", "tag": "needs"}) == 410

    def down(request, timeout):
        raise OSError("no network")
    monkeypatch.setattr(w, "OPENER", down)
    assert w.send(_sub(), {"title": "Orkline", "tag": "needs"}) == 0
    assert w.send({"endpoint": "x"}, {"tag": "needs"}) == 0                                   # a broken subscription
    assert w.send(_sub(), {"title": "x" * 2000, "tag": "needs"}) == 0                          # over a kilobyte: not sent


def test_without_cryptography_every_push_command_says_how_to_get_it(monkeypatch):
    import builtins
    sub = _sub()
    real = builtins.__import__

    def no_crypto(name, *a, **k):
        if name.startswith("cryptography"):
            raise ImportError(name)
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", no_crypto)
    with pytest.raises(w.PushError, match=r"Notifications need the cryptography package: pip install 'orkboard\[gui\]'"):
        w.public_key()
    assert w.send(sub, {"tag": "needs"}) == 0
