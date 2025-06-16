from micropython import const

from trezor import utils

if utils.USE_THP:
    # Cache keys for THP channel
    CHANNEL_ID = const(0)
    CHANNEL_STATE = const(1)
    CHANNEL_IFACE = const(2)
    CHANNEL_SYNC = const(3)
    CHANNEL_HANDSHAKE_HASH = const(4)
    CHANNEL_KEY_RECEIVE = const(5)
    CHANNEL_KEY_SEND = const(6)
    CHANNEL_NONCE_RECEIVE = const(7)
    CHANNEL_NONCE_SEND = const(8)
    CHANNEL_HOST_STATIC_PUBKEY = const(9)

    # Cache keys for THP session
    # CHANNEL_ID = const(0)
    SESSION_ID = const(1)
    SESSION_STATE = const(2)
    APP_COMMON_SEED = const(3)
    APP_COMMON_AUTHORIZATION_TYPE = const(4)
    APP_COMMON_AUTHORIZATION_DATA = const(5)
    APP_COMMON_NONCE = const(6)
    if not utils.BITCOIN_ONLY:
        APP_COMMON_DERIVE_CARDANO = const(7)
        APP_CARDANO_ICARUS_SECRET = const(8)
        APP_CARDANO_ICARUS_TREZOR_SECRET = const(9)
        APP_MONERO_LIVE_REFRESH = const(10)
