"""WARD key derivation and the keyed path (entry_key).

    K_path    = SLIP21(seed, [b"ward", b"K_path"]).key()
    K_ident   = SLIP21(seed, [b"ward", b"K_ident"]).key()    -- seals leaf_identity
    K_data    = SLIP21(seed, [b"ward", b"K_data"]).key()     -- seals leaf_content
    entry_key = HMAC-SHA256(K_path, "WARD PATH v1" || leaf_identity)   -- see leaf.py
    K_sig     = SLIP21(seed, [b"ward", b"K_sig"]).key()      -- Ed25519 secret
    ward_id   = ed25519.publickey(K_sig)                     -- the WM-facing handle

One global key set (docs/ward/ward-leaf.md). The entry type is in the sealed content, not in
the path or the keys: one identity has one leaf, whatever it holds.

Byte-identical to the reference implementation; its vectors in `core/tests/test_apps.ward.py`
pin the layout. All keys are passphrase-dependent, so each hidden wallet has its own space.
The retired path [b"ward", b"K_mac"] must never be reused.
"""

from typing import Sequence

ENTRY_TYPE_ADDRESS = "address"
# The value is the target's leaf_identity; a read follows it one hop (common.read_entry).
ENTRY_TYPE_POINTER = "pointer"


async def _derive_slip21(path: "Sequence[bytes]") -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    node = Slip21Node(await get_seed())
    node.derive_path(path)
    return node.key()


# wallet_id: keys local storage, never sent. K_auth: the device-to-device MAC key over transitions,
# the sole authority on state. K_sig complements it for the WM. K_ident / K_data seal the two leaf
# parts.
async def derive_k_path() -> bytes:
    return await _derive_slip21([b"ward", b"K_path"])


async def derive_wallet_id() -> bytes:
    return (await _derive_slip21([b"ward", b"wallet_id"]))[:16]


async def derive_k_sig() -> bytes:
    return await _derive_slip21([b"ward", b"K_sig"])


async def derive_ward_id() -> bytes:
    from trezor.crypto.curve import ed25519

    return ed25519.publickey(await derive_k_sig())


async def derive_k_auth() -> bytes:
    return await _derive_slip21([b"ward", b"K_auth"])


async def derive_k_ident() -> bytes:
    return await _derive_slip21([b"ward", b"K_ident"])


async def derive_k_data() -> bytes:
    return await _derive_slip21([b"ward", b"K_data"])


def _scope(app_id: str | bytes | None, key_type: str, device_id: int) -> bytes:
    """The offline store's local record name (`wallet_entry`); NOT the trie path. NUL-delimited,
    so NUL is refused in app_id and key_type (app_id is a protobuf string); otherwise two
    records could be re-split onto one name."""
    from trezor.wire import DataError

    if app_id is None:
        app_id = b""
    elif isinstance(app_id, str):
        app_id = app_id.encode()

    key_type_bytes = key_type.encode()
    if b"\x00" in app_id or b"\x00" in key_type_bytes:
        raise DataError("app_id and key_type must not contain NUL")
    if not 0 <= device_id <= 0xFF:
        raise DataError("device_id must be a single byte")

    return app_id + b"\x00" + key_type_bytes + b"\x00" + bytes([device_id])


def entry_key(
    k_path: bytes,
    app_id: str | bytes | None,
    identifier: bytes,
    device_id: int = 0,
) -> bytes:
    """The keyed 32-byte path: HMAC-SHA256(K_path, "WARD PATH v1" || leaf_identity)."""
    from trezor.crypto import hmac

    from .leaf import pack_identity

    preimage = b"WARD PATH v1" + pack_identity(identifier, app_id or b"", device_id)
    return hmac(hmac.SHA256, k_path, preimage).digest()


WALLET_ENTRY_LEN = 16


def wallet_entry(
    wallet_id: bytes,
    app_id: str | bytes | None,
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """The name a COMPACT record is found by: SHA256(wallet_id || scope || identifier)[:16]. A
    plain hash suffices: it never leaves the device, and the secret wallet_id stops offline search."""
    from trezor.crypto.hashlib import sha256

    return sha256(wallet_id + _scope(app_id, key_type, device_id) + identifier).digest()[
        :WALLET_ENTRY_LEN
    ]


async def entry_key_for(
    app_id: str | bytes | None,
    identifier: bytes,
    device_id: int = 0,
) -> bytes:
    """The keyed path under the active wallet -- the only way an entry_key is produced, so a host
    cannot aim a read or write at a slot it chose."""
    return entry_key(await derive_k_path(), app_id, identifier, device_id)
