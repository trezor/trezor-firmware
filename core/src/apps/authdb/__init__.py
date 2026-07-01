async def _get_identifier() -> bytes:
    """Derive the AuthDB identity identifier for the current seed/passphrase.

    identifier = SHA-256(public_key at m/44'/0'/0'/0/0)

    Unique per seed/passphrase combination.  The seed is cached after the user
    enters their PIN/passphrase, so this is fast and silent on repeated calls.
    """
    from apps.common import seed as seed_module
    from apps.common.paths import HARDENED
    from trezor.crypto import bip32
    from trezor.crypto.hashlib import sha256

    s = await seed_module.get_seed()
    node = bip32.from_seed(s, "secp256k1")
    node.derive_path([44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0, 0])
    return sha256(node.public_key()).digest()
