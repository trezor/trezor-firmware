"""WARD key derivation and the keyed path (entry_key, a.k.a. LeafIdentityMAC).

    K_path    = SLIP21(seed, [b"ward", b"K_path"]).key()
    scope     = app_id || 0x00 || key_type || 0x00 || device_id(1B)
    entry_key = HMAC-SHA256(K_path, scope || identifier)

Byte-for-byte identical to the reference implementation, so its published vectors pin
this code -- see `core/tests/test_apps.ward.py`. Do not "improve" the layout without
changing those vectors and the TS host together.

K_path is derived from the passphrase-dependent seed, so each hidden wallet has its own
key space: the same identifier maps to a different path under a different passphrase.

    K_sig     = SLIP21(seed, [b"ward", b"K_sig"]).key()      -- Ed25519 secret
    ward_id   = ed25519.publickey(K_sig)                     -- the WM-facing handle

Siblings reserved under the same [b"ward"] root, for later phases: K_ident(key_type) and
K_data(key_type) at [b"ward", b"K_ident"/b"K_data", key_type], which seal the two leaf
parts once leaves stop being plaintext.
"""

from typing import Sequence

ENTRY_TYPE_ADDRESS = "address"


async def _derive_slip21(path: "Sequence[bytes]") -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    node = Slip21Node(await get_seed())
    node.derive_path(path)
    return node.key()


async def derive_k_path() -> bytes:
    """K_path = SLIP21(seed, [b"ward", b"K_path"]).key()."""
    return await _derive_slip21([b"ward", b"K_path"])


async def derive_wallet_id() -> bytes:
    """A 16-byte handle for the active hidden wallet, from the same seed as K_path.

    Passphrase-dependent, so it distinguishes wallets, and it is a SLIP-21 leaf rather
    than anything derived from a root or an identifier -- so it names the wallet without
    revealing what the wallet contains. Used only to key this device's own storage; it is
    never sent anywhere.

    Callers always get the whole 16 bytes. The OFFLINE STORE keeps only the first 7 of them in each
    record, which is `storage.ward`'s business rather than this function's -- the root slots keep all
    16. See `storage.ward._STORE_WALLET_ID_LEN` for why 56 bits is enough there.
    """
    return (await _derive_slip21([b"ward", b"wallet_id"]))[:16]


async def derive_k_sig() -> bytes:
    """K_sig = SLIP21(seed, [b"ward", b"K_sig"]).key() -- an Ed25519 secret.

    COMPLEMENTARY to K_auth, never a replacement. K_auth's HMAC is what a DEVICE of this
    wallet verifies, and it stays the authority on authenticity; K_sig exists so a party
    holding no secret -- the WM -- can also check that a transition came from a real device
    of this wallet, which is what lets it arbitrate ordering without being trusted for
    anything but freshness. See `cas.sig_commit`.
    """
    return await _derive_slip21([b"ward", b"K_sig"])


async def derive_ward_id() -> bytes:
    """The 32-byte handle the WM knows this wallet by: the PUBLIC KEY of K_sig.

    Being a key rather than an opaque label is what makes it useful to the WM -- the
    identifier a transition is attributed to IS the key that verifies it, so there is no
    second per-wallet value to keep in step and no enrolment step that can bind the wrong
    pair. It is still passphrase-dependent, since K_sig is, so it distinguishes hidden
    wallets and tells a WM nothing beyond "these requests concern one wallet", which it must
    know to keep a counter at all.

    Both this and the reference's RIPEMD160(SHA256(secp256k1 master pubkey)) are public keys
    of seed-derived secrets; this one avoids dragging a BIP-32 key in for the purpose.
    """
    from trezor.crypto.curve import ed25519

    return ed25519.publickey(await derive_k_sig())


async def derive_k_mac() -> bytes:
    """K_mac, which MACs the root the WM attests. Never leaves the device.

    Its whole purpose is that the WM cannot compute one: it can sign a mac, so it can
    replay a state this wallet reached, but it can never fabricate one.
    """
    return await _derive_slip21([b"ward", b"K_mac"])


async def derive_k_auth() -> bytes:
    """K_auth, which authorises a transition from one root to the next.

    Seed-derived, so every device of the wallet holds it -- which is the point: a
    transition needs to be verifiable by the other devices that share this tree, and by
    nobody else. See `cas.py` for why a MAC rather than a signature.
    """
    return await _derive_slip21([b"ward", b"K_auth"])


async def derive_k_ident(key_type: str) -> bytes:
    """K_ident(key_type) = SLIP21(seed, [b"ward", b"K_ident", key_type]).key().

    Seals the identity part. Keyed per key_type, which is why key_type must travel in the
    clear -- it selects the key needed to open the part that would otherwise name it.
    """
    return await _derive_slip21([b"ward", b"K_ident", key_type.encode()])


async def derive_k_data(key_type: str) -> bytes:
    """K_data(key_type) = SLIP21(seed, [b"ward", b"K_data", key_type]).key().

    Seals the content part. Separate from K_ident so a future export of one part's key
    cannot expose the other.
    """
    return await _derive_slip21([b"ward", b"K_data", key_type.encode()])


def _scope(app_id: str | bytes | None, key_type: str, device_id: int) -> bytes:
    """scope = app_id || 0x00 || key_type || 0x00 || device_id(1B).

    The fields are 0x00-DELIMITED rather than length-prefixed, which is only unambiguous
    while neither app_id nor key_type can contain 0x00 -- otherwise the same bytes could
    be re-split into a different (app_id, key_type, device_id, identifier) tuple and two
    distinct entries would share one entry_key. For example

        app_id="x", key_type="address",     device_id=0,    identifier=b"\\x00foo"
        app_id="x", key_type="address\\0\\0", device_id=0x66, identifier=b"oo"

    both encode to b"x\\x00address\\x00\\x00\\x00foo". app_id arrives from the host as a
    protobuf string and 0x00 is valid UTF-8, so this is reachable input, not a
    hypothetical. Hence the checks below.

    `identifier` is exempt: it is the terminal field, so it may contain 0x00 freely.

    FIXME(ward): length-prefixing both fields behind a version byte would make this
    injective by construction rather than by validation. That is a wire break shared with
    the TS host, so it waits for a deliberate compatibility bump.
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
    """The 16-byte name a COMPACT record is found by: SHA256(wallet_id || scope || identifier)[:16].

    NOT AN HMAC, and that is the point of it. `entry_key` is HMAC under K_path because the HOST keeps
    it and must not be able to learn an identifier from it. This one never leaves the device and
    nobody else verifies it -- it exists so a record can be recognised without storing the identity
    it was made from -- so a plain hash is enough. `wallet_id` sits inside it and is the secret that
    stops anyone computing candidates offline.

    Reuses `_scope`, so it is domain-separated exactly as the keyed path is: app_id and key_type are
    NUL-terminated and cannot be slid past each other. Note the device_id byte comes along with the
    scope; a compact record is therefore per device slot as well, which matches what the identity it
    replaces carried.

    SIXTEEN BYTES. Two records colliding would be two entries sharing one value, so the length has to
    be enough that it never happens by accident (2^-128 territory for the twenty records a store
    holds) -- and an attacker cannot search for a collision at all without wallet_id, which is
    seed-derived and never sent anywhere.
    """
    from trezor.crypto.hashlib import sha256

    return sha256(wallet_id + _scope(app_id, key_type, device_id) + identifier).digest()[
        :WALLET_ENTRY_LEN
    ]


async def wallet_entry_for(
    app_id: str | bytes | None,
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """`wallet_entry` under the active wallet."""
    return wallet_entry(
        await derive_wallet_id(), app_id, identifier, key_type, device_id
    )


async def entry_key_for(
    app_id: str | bytes | None,
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """Derive the keyed path for (app_id, identifier) under the active wallet's K_path.

    This is the only way an entry_key is ever produced. Nothing accepts one from the
    host, so the host cannot aim a read or a write at a slot of its choosing.
    """
    return entry_key(await derive_k_path(), app_id, identifier, key_type, device_id)
