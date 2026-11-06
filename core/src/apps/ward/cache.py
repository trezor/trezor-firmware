"""WARD entries held in the offline cache (Mini WARD's per-app store).

A copy of a WARD trie entry, kept on the device so it is available without a host.
Each lives in the store of the app its domain belongs to, under a FIXED subscope
(`_SUBSCOPE`), so the host can never choose where it lands:

    key    = len8(key_type) || key_type || device_id(1B) || identifier
    value  = version(1B) || flags(1B) || C_leaf(4B BE) || value

`flags` bit 0 is STICKY -- a device-only decision the user confirms, never part of the
leaf: the entry may be used while NO proof can be had (the host answers a proof request
`unavailable`, e.g. no or failing wardd), shown marked cached, not proven. Every verified
answer still updates the copy, or removes it when WARD proves it absent, sticky or not,
and this device's own committed writes update it directly. C_leaf is the leaf counter
the copy was taken at.

THREAT MODEL (accepted, known DoS from the host/Suite side): a host can always claim to
be unavailable and so keep a sticky entry in use after another device deleted it in
WARD; the label is marked cached. The host learns which entries are cached
(validate_cache pulls one proof per cached entry), but cannot make one sticky, nor bring
a deleted one back from a backup (import is checked against WARD).
KNOWN: the offline store is small and shared by every app and passphrase wallet, and
nothing is evicted, so a host can fill it with plain copies.

A backup is one sealed blob per record, under a key only this wallet (seed and
passphrase) can derive, so the host carrying it can neither read nor forge it:

    blob = nonce(12B) || ChaCha20-Poly1305(K_backup, aad, plaintext) || tag(16B)
    plaintext = len8(domain) || domain || len16(key) || key || value

A blob can be replayed, so it is never trusted for content: import stores only what a
proof against the device's root shows WARD still holds.
"""

from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import WardStore

_SUBSCOPE = b"WARD"
_VERSION = const(1)
FLAG_STICKY = const(0x01)
_BACKUP_AAD = b"WARD CACHE BACKUP v1"


def record_key(key_type: str, device_id: int, identifier: bytes) -> bytes:
    kt = key_type.encode()
    return bytes([len(kt)]) + kt + bytes([device_id]) + identifier


def parse_key(key: bytes) -> tuple[str, int, bytes]:
    """(key_type, device_id, identifier) of a record key."""
    n = key[0]
    return bytes(key[1 : 1 + n]).decode(), key[1 + n], bytes(key[2 + n :])


def record_value(flags: int, c_leaf: int, value: bytes) -> bytes:
    return bytes([_VERSION, flags]) + c_leaf.to_bytes(4, "big") + value


def parse_value(raw: bytes) -> tuple[int, int, bytes]:
    """(flags, C_leaf, value) of a record value."""
    if len(raw) < 6 or raw[0] != _VERSION:
        raise ValueError("unknown WARD cache record")
    return raw[1], int.from_bytes(raw[2:6], "big"), bytes(raw[6:])


async def store_for(domain: bytes) -> WardStore:
    """The cache store for entries of `domain`; DataError for a domain with none."""
    from trezor.wire import DataError

    from . import app_for_domain, open_ward

    app = app_for_domain(domain)
    if app is None:
        raise DataError("WARD cache: no offline store for this domain")
    return (await open_ward(app)).subscope(_SUBSCOPE)


async def records() -> list:
    """Every cached WARD entry of the active wallet, as (domain, key, value) -- read
    in full first, since the store must not change while it is iterated."""
    from . import _DOMAIN_APPS, open_ward

    out = []
    for domain, app in _DOMAIN_APPS.items():
        store = (await open_ward(app)).subscope(_SUBSCOPE)
        async for key, value in store.entries():
            out.append((domain, key, value))
    return out


async def _backup_key() -> bytes:
    from .keys import derive_ward_key

    return await derive_ward_key(b"K_cache_backup")


async def seal(domain: bytes, key: bytes, value: bytes) -> bytes:
    from trezor.crypto import chacha20poly1305_encrypt, random

    nonce = random.bytes(12)
    cipher = chacha20poly1305_encrypt(await _backup_key(), nonce)
    cipher.auth(_BACKUP_AAD)
    plaintext = (
        bytes([len(domain)]) + domain + len(key).to_bytes(2, "big") + key + value
    )
    ct = cipher.encrypt(plaintext)
    return nonce + ct + cipher.finish()


async def open_blob(blob: bytes) -> tuple[bytes, bytes, bytes]:
    """(domain, key, value) of a backup blob; DataError unless it was sealed by this
    wallet and is well formed."""
    from trezor.crypto import AuthenticationError, chacha20poly1305_decrypt
    from trezor.wire import DataError

    if len(blob) < 12 + 16 + 4:
        raise DataError("WARD cache backup: malformed entry")
    cipher = chacha20poly1305_decrypt(await _backup_key(), blob[:12])
    cipher.auth(_BACKUP_AAD)
    pt = cipher.decrypt(blob[12:-16])
    try:
        cipher.finish(blob[-16:])
    except AuthenticationError:
        raise DataError("WARD cache backup: not sealed by this wallet")
    n = pt[0]
    domain = bytes(pt[1 : 1 + n])
    off = 1 + n
    klen = int.from_bytes(pt[off : off + 2], "big")
    key = bytes(pt[off + 2 : off + 2 + klen])
    value = bytes(pt[off + 2 + klen :])
    try:
        parse_key(key)
        parse_value(value)
    except (ValueError, IndexError):
        raise DataError("WARD cache backup: malformed entry")
    return domain, key, value
