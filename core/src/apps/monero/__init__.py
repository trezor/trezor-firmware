from trezor import wire
from trezor.messages import MessageType

CURVE = "ed25519"
SLIP44_ID = 128


def boot() -> None:
    wire.add(MessageType.MoneroGetAddress, __name__, "get_address")
    wire.add(MessageType.MoneroGetWatchKey, __name__, "get_watch_only")
    wire.add(MessageType.MoneroTransactionInitRequest, __name__, "sign_tx")
    wire.add(MessageType.MoneroKeyImageExportInitRequest, __name__, "key_image_sync")
    wire.add(MessageType.MoneroGetTxKeyRequest, __name__, "get_tx_keys")
    wire.add(MessageType.MoneroLiveRefreshStartRequest, __name__, "live_refresh")

    if __debug__ and hasattr(MessageType, "DebugMoneroDiagRequest"):
        wire.add(MessageType.DebugMoneroDiagRequest, __name__, "diag")
