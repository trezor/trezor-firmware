from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_SEP5

CURVE = "ed25519"
SLIP44_ID = 128
PATTERN = PATTERN_SEP5


def boot() -> None:
    wire.add(MessageType.MoneroGetAddress, __name__, "get_address")
    wire.add(MessageType.MoneroGetWatchKey, __name__, "get_watch_only")
    wire.add(MessageType.MoneroTransactionInitRequest, __name__, "sign_tx")
    wire.add(MessageType.MoneroKeyImageExportInitRequest, __name__, "key_image_sync")
    wire.add(MessageType.MoneroGetTxKeyRequest, __name__, "get_tx_keys")
    wire.add(MessageType.MoneroLiveRefreshStartRequest, __name__, "live_refresh")

    if __debug__ and hasattr(MessageType, "DebugMoneroDiagRequest"):
        wire.add(MessageType.DebugMoneroDiagRequest, __name__, "diag")
