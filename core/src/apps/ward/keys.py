"""WARD key derivation and the keyed path (entry_key).

    K_path    = SLIP21(seed, [b"ward", b"K_path"]).key()
    scope     = app_id || 0x00 || key_type || 0x00 || device_id(1B)
    entry_key = HMAC-SHA256(K_path, scope || identifier)
    K_sig     = SLIP21(seed, [b"ward", b"K_sig"]).key()      -- Ed25519 secret
    ward_id   = ed25519.publickey(K_sig)                     -- the WM-facing handle

Byte-identical to the reference implementation; its vectors in `core/tests/test_apps.ward.py`
pin the layout. All keys are passphrase-dependent, so each hidden wallet has its own space.
The retired path [b"ward", b"K_mac"] must never be reused.
"""

from typing import Sequence

ENTRY_TYPE_ADDRESS = "address"


async def _derive_slip21(path: "Sequence[bytes]") -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    node = Slip21Node(await get_seed())
    node.derive_path(path)
    return node.key()


async def derive_k_path() -> bytes:
    return await _derive_slip21([b"ward", b"K_path"])


async def derive_wallet_id() -> bytes:
    """16-byte handle for the active hidden wallet; keys local storage, never sent anywhere."""
    return (await _derive_slip21([b"ward", b"wallet_id"]))[:16]


async def derive_k_sig() -> bytes:
    """Ed25519 secret the WM verifies transitions under; complements K_auth, never replaces it."""
    return await _derive_slip21([b"ward", b"K_sig"])


async def derive_ward_id() -> bytes:
    """The 32-byte handle the WM knows this wallet by: the public key of K_sig."""
    from trezor.crypto.curve import ed25519

    return ed25519.publickey(await derive_k_sig())


async def derive_k_auth() -> bytes:
    """K_auth: the device-to-device MAC key over transitions, the sole authority on state."""
    return await _derive_slip21([b"ward", b"K_auth"])


async def derive_k_ident(key_type: str) -> bytes:
    """Seals the identity part; per key_type, which therefore travels in the clear."""
    return await _derive_slip21([b"ward", b"K_ident", key_type.encode()])


async def derive_k_data(key_type: str) -> bytes:
    """Seals the content part; separate from K_ident."""
    return await _derive_slip21([b"ward", b"K_data", key_type.encode()])


def _scope(app_id: str | bytes | None, key_type: str, device_id: int) -> bytes:
    """scope = app_id || 0x00 || key_type || 0x00 || device_id(1B).

    NUL-delimited, so NUL is refused in app_id and key_type (reachable: app_id is a protobuf
    string); otherwise two entries could be re-split onto one entry_key.
    """
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
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """The keyed 32-byte path for one entry: HMAC-SHA256(K_path, scope || identifier)."""
    from trezor.crypto import hmac

    return hmac(
        hmac.SHA256, k_path, _scope(app_id, key_type, device_id) + identifier
    ).digest()


WALLET_ENTRY_LEN = 16


def wallet_entry(
    wallet_id: bytes,
    app_id: str | bytes | None,
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """The name a COMPACT record is found by: SHA256(wallet_id || scope || identifier)[:16].

    A plain hash suffices: it never leaves the device, and the secret wallet_id stops offline
    candidate search.
    """
    from trezor.crypto.hashlib import sha256

    return sha256(wallet_id + _scope(app_id, key_type, device_id) + identifier).digest()[
        :WALLET_ENTRY_LEN
    ]


async def entry_key_for(
    app_id: str | bytes | None,
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """The keyed path under the active wallet -- the only way an entry_key is produced.

    Nothing accepts one from the host, so it cannot aim a read or write at a slot it chose.
    """
    return entry_key(await derive_k_path(), app_id, identifier, key_type, device_id)
