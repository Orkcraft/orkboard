"""Web Push from this computer to a paired phone (docs/specs/42-coming-back.md §3.2): no server of ours, no app store. The
phone's browser gives a subscription (an endpoint of its push service and two keys); the computer seals a short JSON message to
it (RFC 8291, `aes128gcm` of RFC 8188, one record), signs the request as itself (VAPID, RFC 8292) and POSTs it.

    web_push.public_key()                      # this computer's key, base64url: what a phone subscribes against
    web_push.send(sub, {"title", "body", "tag", "badge", "url"})     # the HTTP status, 0 when none; never raises

`cryptography` (the `[gui]` extra pairing a phone already needs) is imported when it is used, as gui/phone_tls.py does.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from orkboard import settings
from orkboard.gui import phone_tls

SUBJECT = "https://github.com/orkWorks/orkBoard"
RECORD = 4096
MAX_MESSAGE = 1024
URGENCY = {"needs": "high"}
NEED = "Notifications need the cryptography package: pip install 'orkboard[gui]'"
OPENER = urllib.request.urlopen                  # a test stands in for the network


class PushError(Exception):
    """Notifications cannot be made here; its text is shown to the person."""


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _crypto():
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    except ImportError:
        raise PushError(NEED) from None
    return hashes, serialization, ec, decode_dss_signature, AESGCM, HKDF


def key_path(folder: Path | None = None) -> Path:
    return (folder or settings.path().parent) / "push.key"


def private_key(folder: Path | None = None):
    """This computer's P-256 key, made once beside `phone.key` (0600)."""
    _hashes, serialization, ec, *_ = _crypto()
    path = key_path(folder)
    if not path.is_file():
        key = ec.generate_private_key(ec.SECP256R1())
        phone_tls._write_private(path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                         serialization.NoEncryption()))
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def point(public) -> bytes:
    _hashes, serialization, *_ = _crypto()
    return public.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def public_key(folder: Path | None = None) -> str:
    """The uncompressed point of this computer's key, base64url without padding."""
    return b64(point(private_key(folder).public_key()))


def seal(payload: bytes, p256dh: str, auth: str, salt: bytes | None = None, key=None) -> bytes:
    """`payload` sealed to a subscription (RFC 8291 §3.4): the body of the POST. `salt` and `key` (the sender's ephemeral key)
    are given only by the tests."""
    hashes, _ser, ec, _dss, AESGCM, HKDF = _crypto()
    ua_public, secret = unb64(p256dh), unb64(auth)
    sender = key or ec.generate_private_key(ec.SECP256R1())
    as_public = point(sender.public_key())
    shared = sender.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = HKDF(hashes.SHA256(), 32, secret, b"WebPush: info\x00" + ua_public + as_public).derive(shared)
    salt = salt or os.urandom(16)
    cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(ikm)
    sealed = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)          # the one record is the last: delimiter 2
    return salt + RECORD.to_bytes(4, "big") + bytes([len(as_public)]) + as_public + sealed


def vapid(endpoint: str, now: float | None = None, folder: Path | None = None) -> str:
    """The `Authorization` header (RFC 8292): an ES256 JWT for the endpoint's origin, 12 hours, and the key it is signed by."""
    hashes, _ser, ec, decode_dss, *_ = _crypto()
    url = urllib.parse.urlsplit(endpoint)
    claims = {"aud": f"{url.scheme}://{url.netloc}", "exp": int((time.time() if now is None else now) + 12 * 3600), "sub": SUBJECT}
    part = lambda obj: b64(json.dumps(obj, separators=(",", ":")).encode())          # noqa: E731
    signing = f"{part({'typ': 'JWT', 'alg': 'ES256'})}.{part(claims)}"
    key = private_key(folder)
    r, s = decode_dss(key.sign(signing.encode("ascii"), ec.ECDSA(hashes.SHA256())))
    token = f"{signing}.{b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    return f"vapid t={token}, k={b64(point(key.public_key()))}"


def send(sub: dict, message: dict, folder: Path | None = None) -> int:
    """One message to one subscription; the push service's HTTP status, 0 when it never gave one. Never raises."""
    try:
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(body) > MAX_MESSAGE:
            return 0
        endpoint = str(sub["endpoint"])
        request = urllib.request.Request(endpoint, data=seal(body, sub["p256dh"], sub["auth"]), method="POST", headers={
            "Authorization": vapid(endpoint, folder=folder), "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
            "TTL": "43200", "Urgency": URGENCY.get(str(message.get("tag")), "normal"), "Topic": str(message.get("tag") or "orkline")})
        with OPENER(request, timeout=10) as answer:
            return int(answer.status)
    except urllib.error.HTTPError as e:
        return int(e.code)
    except Exception:
        return 0
