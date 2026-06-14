# DarkFi derives its spend keys with its own hierarchical-deterministic scheme
# (see crypto/hd.rs) rooted directly at the BIP-39 seed, *not* via a BIP-32
# path. The device therefore needs the raw seed, and a DarkFi account index.
DEFAULT_ACCOUNT = 0


async def account_spend_key(account: int | None) -> bytes:
    """Derive the DarkFi account spend key `sk` for `account`.

    `sk = HD_account(seed, account)` where `seed` is the device's BIP-39 seed.
    This matches `darkfi_sdk::crypto::hd::ExtendedSecretKey::account`, so the
    same mnemonic yields identical keys on the device and in the `drk` wallet.
    """
    from trezor.crypto import pallas

    from apps.common.seed import get_seed

    if account is None:
        account = DEFAULT_ACCOUNT

    seed = await get_seed()
    return pallas.hd_account(seed, account)
