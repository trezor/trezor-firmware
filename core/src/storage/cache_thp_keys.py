from micropython import const

from trezor import utils

if utils.USE_THP:
    # Cache keys for THP session
    CHANNEL_ID = const(0)
    SESSION_ID = const(1)
    SESSION_STATE = const(2)
    LAST_USAGE = const(3)
    APP_COMMON_SEED = const(4)
    APP_COMMON_AUTHORIZATION_TYPE = const(5)
    APP_COMMON_AUTHORIZATION_DATA = const(6)
    APP_COMMON_NONCE = const(7)
    if not utils.BITCOIN_ONLY:
        APP_COMMON_DERIVE_CARDANO = const(8)
        APP_CARDANO_ICARUS_SECRET = const(9)
        APP_CARDANO_ICARUS_TREZOR_SECRET = const(10)
        APP_MONERO_LIVE_REFRESH = const(11)
