from micropython import const

from trezor import utils

if not utils.USE_THP:
    # Number of encrypted cache entries (see below)
    CACHE_ENCRYPTED_COUNT_CODEC = const(4)

    # Traditional cache keys, encrypted ones first
    APP_COMMON_SEED = const(0)
    APP_COMMON_NONCE = const(1)
    if not utils.BITCOIN_ONLY:
        APP_CARDANO_ICARUS_SECRET = const(2)
        APP_CARDANO_ICARUS_TREZOR_SECRET = const(3)

    # non-encrypted keys
    APP_COMMON_AUTHORIZATION_TYPE = const(4)
    APP_COMMON_AUTHORIZATION_DATA = const(5)
    if not utils.BITCOIN_ONLY:
        APP_COMMON_DERIVE_CARDANO = const(6)
        APP_MONERO_LIVE_REFRESH = const(7)
        APP_EXTAPP_IDS = const(8)
