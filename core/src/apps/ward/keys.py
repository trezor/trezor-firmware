"""WARD key derivation, and the keyed path an identifier maps to.

Everything secret in WARD descends from the seed through SLIP-21, and nothing here
ever leaves the device except by an explicit, user-confirmed export:

    K_path          resolves an identifier to its trie path -- see `entry_key`
    K_ident(kt)     seals the identity part of a leaf
    K_data(kt)      seals the content part
    K_mac, K_auth   authenticate a root and a transition
    K_sig           signs to the WM; `ward_id` IS its public key

The three leaf-facing keys are INDEPENDENT CAPABILITIES, which is why they are derived
separately rather than sliced out of one secret: a party given K_path can resolve
identifiers to paths and nothing else, and one given K_data can read values without
being able to link them to identifiers.

`key_type` is a derivation input for K_ident and K_data, so entries of different types
are sealed under different keys even at the same path prefix.

Split out of `service` so the trust anchor's wire logic and its key schedule can be
read, and changed, apart. The trie (`trie`) and the leaf codec (`leaf`) take their keys
as ARGUMENTS and import nothing from here -- that is what keeps them testable against
published vectors with no wallet in play.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Default entry type. key_type is a real wire/storage field (it selects both K_ident and
# K_data); this is only the default when a caller omits it.
ENTRY_TYPE_ADDRESS = "address"


def entry_key(
    k_path: bytes,
    app_id,
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """Keyed 32-byte trie path, a.k.a. LeafIdentityMAC (ward-design.md §1/§3):

        scope     = app_id || 0x00 || key_type || 0x00 || device_id(1B)
        entry_key = HMAC-SHA256(K_path, scope || identifier)

    A PRF-derived path, NOT an authenticator (§2.5): only a holder of K_path can
    compute it, so the host cannot forge a path or brute-force a low-entropy
    identifier. `device_id`=0 is a global entry; >0 is a device slot (§5). Must stay
    byte-for-byte identical to trezorlib `ward_crypto.leaf_identity_mac` and the
    host. Note the host does not need to derive this to *serve* a proof -- the MAC is
    stored alongside the leaf; K_path is for checking a stored MAC against its stored
    identity, or computing a MAC for an identity not in the store."""
    from trezor.crypto import hmac as crypto_hmac

    if app_id is None:
        app_id = b""
    elif isinstance(app_id, str):
        app_id = app_id.encode()
    scope = app_id + b"\x00" + key_type.encode() + b"\x00" + bytes([device_id & 0xFF])
    return crypto_hmac(crypto_hmac.SHA256, k_path, scope + identifier).digest()


# ---------------------------------------------------------------------------
# Wallet identity + MAC derivation (formerly apps.authdb.__init__).
# ---------------------------------------------------------------------------


async def get_wallet_id() -> bytes:
    """wallet_id = RIPEMD160(SHA256(compressed master public key)) -- 20 bytes.

    The BIP32 identifier (Hash160) of the wallet's master xpub, derived from the
    passphrase-including seed, so distinct hidden wallets get distinct trees.
    """
    from trezor.crypto import bip32
    from trezor.crypto.scripts import sha256_ripemd160
    from apps.common import seed as seed_module

    s = await seed_module.get_seed()
    node = bip32.from_seed(s, "secp256k1")
    return sha256_ripemd160(node.public_key()).digest()


async def get_ward_id() -> bytes:
    """ward_id = SLIP21(seed, [b"TREZOR", b"WARDID", b"wallet_id", wallet_id]).key()
    -- 32 bytes.

    The WM-facing anti-rollback / anti-fork anchor (spec §5). Distinct from the
    20-byte local `wallet_id`: it is what the WM signs over in every ATTEST/FINAL
    preimage, is derived from the seed (so it is wallet-stable and independent of
    the mutable Evolu `ownerId`), and is verifiable by the device. The device
    derives it and forwards it to the host; the host MUST NOT invent or substitute
    it.
    """
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    wallet_id = await get_wallet_id()
    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"TREZOR", b"WARDID", b"wallet_id", wallet_id])
    return node.key()


async def derive_mac_key(domain: bytes) -> bytes:
    """mac_key = HMAC-SHA256(SLIP21(seed, [b"AUTHDB MAC v1", domain]).key(), wallet_id).

    `domain` (currently only b"root_mac") is folded into the SLIP-21 path so each
    purpose gets a distinct base key; bound to wallet_id so a MAC minted for one
    hidden wallet never validates against another's tree.
    """
    from trezor.crypto import hmac as crypto_hmac

    wallet_id = await get_wallet_id()

    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB MAC v1", domain])
    base_key = node.key()

    return crypto_hmac(crypto_hmac.SHA256, base_key, wallet_id).digest()


async def _derive_slip21(path: list) -> bytes:
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path(path)
    return node.key()


async def derive_k_path() -> bytes:
    """K_path = SLIP21(seed, [b"ward", b"K_path"]).key() -- the HMAC key that derives
    every entry_key (LeafIdentityMAC) path (§1). Seed-scoped and shared across the
    wallet's devices; the per-device axis lives in the entry_key scope, not the key."""
    return await _derive_slip21([b"ward", b"K_path"])


async def derive_k_ident(key_type: str) -> bytes:
    """K_ident(key_type) = SLIP21(seed, [b"ward", b"K_ident", key_type]).key() -- the
    AEAD key sealing the LeafIdentity part. Separate from K_data so identities and
    values are independently discloseable. Must match ward_crypto.derive_k_ident."""
    return await _derive_slip21([b"ward", b"K_ident", key_type.encode()])


async def derive_k_data(key_type: str) -> bytes:
    """K_data(key_type) = SLIP21(seed, [b"ward", b"K_data", key_type]).key() -- the
    AEAD key sealing the LeafContent part, per entry type (§1), so a PUSH export can
    hand a host only the types it may decrypt. Must match ward_crypto.derive_k_data."""
    return await _derive_slip21([b"ward", b"K_data", key_type.encode()])


async def entry_key_for(
    app_id, identifier: bytes, key_type: str = ENTRY_TYPE_ADDRESS, device_id: int = 0
) -> bytes:
    """Compute the opaque entry_key path for (app_id, identifier) under the active
    wallet's K_path. Used by the Core gateway to build a WARDProofRequest without
    leaking the identifier to the host."""
    k_path = await derive_k_path()
    return entry_key(k_path, app_id, identifier, key_type, device_id)


async def derive_ward_key(leaf: bytes) -> bytes:
    """SLIP21(seed, [b"ward", leaf]).key() -- the shared m/"ward" key family
    (K_head/K_auth/K_sig). Seed-scoped; the wallet binding is ward_id inside each
    preimage. Mirrors `derive_k_path`/`derive_k_data`."""
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"ward", leaf])
    return node.key()


def k_sig_pubkey(k_sig_secret: bytes) -> bytes:
    from trezor.crypto.curve import ed25519

    return ed25519.publickey(k_sig_secret)


def compute_mac(key: bytes, *parts: bytes) -> bytes:
    """HMAC-SHA256(key, concatenation of parts)."""
    from trezor.crypto import hmac as crypto_hmac

    h = crypto_hmac(crypto_hmac.SHA256, key)
    for p in parts:
        h.update(p)
    return h.digest()
