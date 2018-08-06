from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.MoneroGetAddress, __name__, "get_address")
    wire.add(MessageType.MoneroGetWatchKey, __name__, "get_watch_only")
    wire.add(MessageType.MoneroTransactionInitRequest, __name__, "sign_tx")
    wire.add(MessageType.MoneroKeyImageExportInitRequest, __name__, "key_image_sync")

    if __debug__ and hasattr(MessageType, "DebugMoneroDiagRequest"):
        wire.add(MessageType.DebugMoneroDiagRequest, __name__, "diag")
