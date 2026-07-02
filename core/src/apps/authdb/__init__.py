async def _derive_mac_key() -> bytes:
    """Derive the 32-byte HMAC key for AuthDB MAC tokens via SLIP-0021.

    Path: [b"AUTHDB MAC v1"]  — unique per seed+passphrase.
    """
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = seed_module._get_seed_without_passphrase()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB MAC v1"])
    return node.key()


def _compute_mac(key: bytes, *parts: bytes) -> bytes:
    """Compute HMAC-SHA256(key, concatenation of parts)."""
    from trezor.crypto import hmac as crypto_hmac

    h = crypto_hmac(crypto_hmac.SHA256, key)
    for p in parts:
        h.update(p)
    return h.digest()


async def _get_identifier() -> bytes:
    """Derive the AuthDB identity identifier for the current seed/passphrase.

    identifier = SHA-256(public_key at m/44'/0'/0'/0/0)

    Unique per seed/passphrase combination.
    """
    from apps.common import seed as seed_module
    from apps.common.paths import HARDENED
    from trezor.crypto import bip32
    from trezor.crypto.hashlib import sha256

    #FIXME(petr) s = await seed_module.get_seed()
    s = seed_module._get_seed_without_passphrase()
    node = bip32.from_seed(s, "secp256k1")
    node.derive_path([44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0, 0])
    return sha256(node.public_key()).digest()
