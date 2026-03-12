from micropython import const

from trezor import utils

if not utils.USE_THP:
    # Traditional cache keys
    APP_COMMON_SEED = const(0)
    APP_COMMON_AUTHORIZATION_TYPE = const(1)
    APP_COMMON_AUTHORIZATION_DATA = const(2)
    APP_COMMON_NONCE = const(3)
    if not utils.BITCOIN_ONLY:
        APP_COMMON_DERIVE_CARDANO = const(4)
        APP_CARDANO_ICARUS_SECRET = const(5)
        APP_CARDANO_ICARUS_TREZOR_SECRET = const(6)
        APP_MONERO_LIVE_REFRESH = const(7)

    if utils.BITCOIN_ONLY:
        CACHE_ENCRYPTED_KEYS_CODEC = (
            APP_COMMON_SEED,
            APP_COMMON_NONCE,
        )
    else:
        CACHE_ENCRYPTED_KEYS_CODEC = (
            APP_COMMON_SEED,
            APP_COMMON_NONCE,
            APP_CARDANO_ICARUS_SECRET,
            APP_CARDANO_ICARUS_TREZOR_SECRET,
        )
