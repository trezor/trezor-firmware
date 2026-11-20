from micropython import const

from trezor import utils

if utils.USE_THP:
    # Number of encrypted cache entries (see below)
    CACHE_ENCRYPTED_COUNT_THP = const(4)

    # Cache keys for THP session, encrypted ones first
    APP_COMMON_SEED = const(0)
    APP_COMMON_NONCE = const(1)
    if not utils.BITCOIN_ONLY:
        APP_CARDANO_ICARUS_SECRET = const(2)
        APP_CARDANO_ICARUS_TREZOR_SECRET = const(3)

    # non-encrypted keys
    CHANNEL_ID = const(4)
    SESSION_ID = const(5)
    SESSION_STATE = const(6)
    LAST_USAGE = const(7)
    APP_COMMON_AUTHORIZATION_TYPE = const(8)
    APP_COMMON_AUTHORIZATION_DATA = const(9)
    if not utils.BITCOIN_ONLY:
        APP_COMMON_DERIVE_CARDANO = const(10)
        APP_MONERO_LIVE_REFRESH = const(11)
        APP_EXTAPP_IDS = const(12)
