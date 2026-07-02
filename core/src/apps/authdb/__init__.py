async def _get_device_id() -> bytes:
    """Derive a device-specific identifier (not passphrase-bound).

    device_id = SLIP21(no-passphrase seed, [b"AUTHDB DEVICE ID"]).key()  -- 32 bytes
    Stable across different passphrases on the same device/mnemonic.
    """
    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = seed_module._get_seed_without_passphrase()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB DEVICE ID"])
    return node.key()


async def _derive_mac_key() -> bytes:
    """Derive the 32-byte device MAC key for AuthDB tokens via SLIP-0021.

    device_key = HMAC-SHA256(SLIP21(no-passphrase, [b"AUTHDB MAC v1"]).key(), device_id)
    Unique per device (mnemonic), not passphrase-bound.
    """
    from trezor.crypto import hmac as crypto_hmac

    device_id = await _get_device_id()

    from apps.common import seed as seed_module
    from apps.common.seed import Slip21Node

    s = seed_module._get_seed_without_passphrase()
    node = Slip21Node(s)
    node.derive_path([b"AUTHDB MAC v1"])
    base_key = node.key()

    # bind the base key to the device_id
    return crypto_hmac(crypto_hmac.SHA256, base_key, device_id).digest()


def _compute_mac(key: bytes, *parts: bytes) -> bytes:
    """Compute HMAC-SHA256(key, concatenation of parts)."""
    from trezor.crypto import hmac as crypto_hmac

    h = crypto_hmac(crypto_hmac.SHA256, key)
    for p in parts:
        h.update(p)
    return h.digest()


# Keep _get_identifier as alias so existing handler imports don't break
_get_identifier = _get_device_id
