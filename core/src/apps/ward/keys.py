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
    from .caller import WardCaller

# Default entry type. key_type is a real wire/storage field (it selects both K_ident and
# K_data); this is only the default when a caller omits it.
ENTRY_TYPE_ADDRESS = "address"


# WHO FILLS THE SCOPE. entry_key is computed ONLY by the WARD service on the Trezor. Apps
# running on the Trezor -- core apps and third-party (extapp) apps, which are untrusted --
# never touch WARD keys or storage; they go through the WARD service, which fills in app_id
# from the identity of the calling app (a WardCaller, apps.ward.caller, made by firmware --
# never a value the app or the host names) and device_id = 0x00 (another slot only for
# core apps). So no app can name, read or write another app's domain. This function is the
# raw HMAC and takes the scope as arguments: only the service calls it; everything else
# goes through entry_key_for(caller, ...). Host messages are served under the one domain
# the service fixes for host-driven labels (caller.ADDRESS_LABELS); a host that names
# another app_id, key_type or device_id is refused (caller.host_caller).
# FIXME(ward): extapps have no IPC path to the WARD service yet (apps.extapp.run is not
# implemented); caller.extapp_caller is ready for it, keyed by the verified image id.
# FIXME(ward): the offline cache still files an entry under the subscope of its leaf's
# key_type; with key_type now fixed by the service for host writes this is "address",
# but the cache should use a fixed per-domain subscope.
#
# FIXME(ward): should ward_id be in the entry_key preimage, so that all wallets share one
# database? Notes for that decision:
#  - Today every passphrase wallet has its own K_path/K_ident/K_data (all from the
#    passphrase seed), its own trie, root, counter and WM head (ward_id = its K_sig pubkey).
#    Two wallets' entries for the same (app_id, identifier) already land on different paths,
#    because the KEY differs, so ward_id in the preimage would add nothing.
#  - One shared STORE is possible without any change: entry_keys are PRF outputs under
#    different keys, so the host can keep every wallet's rows in one database, tagged by
#    ward_id, with no collisions. Only a shared TRIE (one root/counter/WM register) would
#    need entry_key to change.
#  - A shared trie needs a path key common to all wallets, and the device holds no
#    passphrase-independent secret while a hidden wallet is open (the passphrase is inside
#    the BIP-39 seed). Deriving one from the bare mnemonic would let every wallet on the
#    device compute every other wallet's paths. With such a common K_path, ward_id (or
#    another per-wallet value) MUST be in the preimage to keep wallets apart.
#  - Decrypting the identifier: if K_ident/K_data stay per wallet, a wallet can open only
#    its own leaves. Every walk over a shared trie (list_entries, cache_entry, proofs) meets
#    other wallets' leaves that fail the AEAD tag and the entry_key check, and must skip them
#    as foreign instead of aborting as it does now -- which also tells the walker how many
#    foreign entries exist and roughly where. If the sealing keys were shared instead, any
#    wallet could read any other wallet's identifiers and values.
#  - Privacy: one shared root, counter and WM register links all wallets on the seed. The WM
#    and the host would see hidden-wallet writes as activity on the same register, which
#    ends passphrase deniability. Rollback, freezing and reverts would also become
#    cross-wallet: one wallet's stuck head blocks the others.
#  - ward_id is public (sent to the WM) and tied to the K_sig derivation, so putting it in
#    the preimage would change every path whenever that derivation changes.
#  Current leaning: keep per-wallet keys and tries, and share only the host store.
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
    compute it, so a party that only STORES the trie -- the Evolu replica, the WM,
    anyone reading the host's database -- cannot forge a path or brute-force a
    low-entropy identifier from it. That does NOT hold for the host connected to an
    unlocked device: a pull lookup (WARDLookup without proof material) makes the
    device send the entry_key for any identifier the host names, with no screen, so
    that host can map identifiers it can guess (its own addresses, say) to paths.
    Values stay sealed under K_data either way. `device_id`=0 is a global entry; >0 is
    a device slot (§5). Must stay
    byte-for-byte identical to trezorlib `ward_crypto.leaf_identity_mac` and the
    host. Note the host does not need to derive this to *serve* a proof -- the MAC is
    stored alongside the leaf; K_path is for checking a stored MAC against its stored
    identity, or computing a MAC for an identity not in the store."""
    from trezor.crypto import hmac as crypto_hmac

    if app_id is None:
        app_id = b""
    elif isinstance(app_id, str):
        app_id = app_id.encode()
    kind = key_type.encode()
    if (
        len(k_path) != 32
        or len(app_id) > 255
        or len(kind) > 255
        or len(identifier) > 65535
        or not 0 <= device_id <= 255
    ):
        raise ValueError("WARD identity exceeds canonical encoding bounds")
    preimage = (
        b"WARD PATH v2"
        + bytes([len(app_id)])
        + app_id
        + bytes([len(kind)])
        + kind
        + bytes([device_id])
        + len(identifier).to_bytes(2, "big")
        + identifier
    )
    return crypto_hmac(crypto_hmac.SHA256, k_path, preimage).digest()


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
    return k_sig_pubkey(await derive_ward_key(b"K_sig"))


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
    caller: "WardCaller",
    identifier: bytes,
    key_type: str = ENTRY_TYPE_ADDRESS,
    device_id: int = 0,
) -> bytes:
    """The opaque entry_key path for `identifier` in the CALLER's domain, under the
    active wallet's K_path. The domain comes from the caller's identity and the device
    slot is checked against it (`WardCaller.device_slot`); neither is the caller's to
    name. Used by the Core gateway to build a WARDProofRequest without leaking the
    identifier to the host."""
    k_path = await derive_k_path()
    return entry_key(
        k_path, caller.app_id, identifier, key_type, caller.device_slot(device_id)
    )


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


# --- Mini WARD (the offline cache, `store`): the passphrase wallet's record scope ---

_WARD_KEY_PATH_PREFIX = [b"TREZOR", b"WARD"]


async def derive_wallet_id() -> bytes:
    """Identify the current passphrase wallet.

    Derived from the passphrase-dependent seed, so every passphrase wallet has
    its own id.
    """
    from apps.common.seed import Slip21Node, get_seed

    node = Slip21Node(await get_seed())
    node.derive_path(_WARD_KEY_PATH_PREFIX + [b"Wallet ID"])
    return node.key()
