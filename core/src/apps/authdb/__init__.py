async def _get_wallet_id() -> bytes:
    """Derive the wallet identifier (specific mnemonic + passphrase combination).

    wallet_id = SLIP21(seed_with_passphrase, [b"AUTHDB WALLET ID"]).key()  -- 32 bytes

    Uses the passphrase-including seed, so distinct passphrases on the same
    mnemonic (distinct hidden wallets) get distinct wallet_ids and therefore
    distinct Merkle trees.
    """
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB WALLET ID"])
    return node.key()


async def _derive_mac_key(domain: bytes) -> bytes:
    """Derive the 32-byte wallet MAC key for AuthDB tokens via SLIP-0021.

    mac_key = HMAC-SHA256(SLIP21(seed_with_passphrase, [b"AUTHDB MAC v1", domain]).key(), wallet_id)

    `domain` (currently only b"root_mac") is a purpose label folded into the
    SLIP-21 path itself, so each purpose gets a distinct base key -- a MAC
    minted for one purpose must not validate for another.

    Scoped to wallet_id (not device_id): a MAC computed for one hidden
    wallet on this device must not validate against a different hidden
    wallet's tree on the same physical unit. Unique per (mnemonic,
    passphrase); no longer device-only.
    """
    from trezor.crypto import hmac as crypto_hmac

    wallet_id = await _get_wallet_id()

    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB MAC v1", domain])
    base_key = node.key()

    # bind the base key to the wallet_id
    return crypto_hmac(crypto_hmac.SHA256, base_key, wallet_id).digest()


def _compute_mac(key: bytes, *parts: bytes) -> bytes:
    """Compute HMAC-SHA256(key, concatenation of parts)."""
    from trezor.crypto import hmac as crypto_hmac

    h = crypto_hmac(crypto_hmac.SHA256, key)
    for p in parts:
        h.update(p)
    return h.digest()
