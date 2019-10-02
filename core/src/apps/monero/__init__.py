from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "ed25519"
_LIVE_REFRESH_TOKEN = None  # live-refresh permission token


def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 128]]
    wire.add(MessageType.MoneroGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.MoneroGetWatchKey, __name__, "get_watch_only", ns)
    wire.add(MessageType.MoneroTransactionInitRequest, __name__, "sign_tx", ns)
    wire.add(
        MessageType.MoneroKeyImageExportInitRequest, __name__, "key_image_sync", ns
    )
    wire.add(MessageType.MoneroGetTxKeyRequest, __name__, "get_tx_keys", ns)
    wire.add(MessageType.MoneroLiveRefreshStartRequest, __name__, "live_refresh", ns)

    if __debug__ and hasattr(MessageType, "DebugMoneroDiagRequest"):
        wire.add(MessageType.DebugMoneroDiagRequest, __name__, "diag")


def live_refresh_token(token: bytes = None) -> None:
    global _LIVE_REFRESH_TOKEN
    if token is None:
        return _LIVE_REFRESH_TOKEN
    else:
        _LIVE_REFRESH_TOKEN = token
