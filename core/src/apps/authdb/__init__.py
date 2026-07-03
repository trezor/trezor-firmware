async def _get_device_id() -> bytes:
    """Derive the physical-device identifier (independent of seed/passphrase).

    device_id = SHA-256(unhex(storage.device.get_device_id()))  -- 32 bytes

    storage.device.get_device_id() is a random value generated once and
    explicitly preserved across wipe_device (see core/src/storage/__init__.py
    reset()), so this identifies the physical hardware unit, not the
    currently loaded wallet. It is already exposed to hosts via
    Features.device_id, so it carries no additional secrecy here -- it is
    only ever used as a public attribution/scoping value, never as MAC
    key material by itself.
    """
    import storage.device as storage_device
    from trezor.crypto.hashlib import sha256
    from ubinascii import unhexlify

    raw = unhexlify(storage_device.get_device_id())
    return sha256(raw).digest()


async def _get_wallet_id() -> bytes:
    """Derive the wallet identifier (specific mnemonic + passphrase combination).

    wallet_id = SLIP21(seed_with_passphrase, [b"AUTHDB WALLET ID"]).key()  -- 32 bytes

    Uses the passphrase-including seed, so distinct passphrases on the same
    mnemonic (distinct hidden wallets) get distinct wallet_ids and therefore
    distinct Merkle trees. In debug builds a flash override (set via
    AuthDbSetDeviceId) takes precedence, for deterministic testing.
    """
    if __debug__:
        import storage.authdb as authdb
        override = authdb.get_device_id_override()
        if override is not None:
            return override

    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = await seed_module.get_seed()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB WALLET ID"])
    return node.key()


async def _derive_mac_key() -> bytes:
    """Derive the 32-byte wallet MAC key for AuthDB tokens via SLIP-0021.

    mac_key = HMAC-SHA256(SLIP21(seed_with_passphrase, [b"AUTHDB MAC v1"]).key(), wallet_id)

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
    node.derive_path([b"AUTHDB MAC v1"])
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
