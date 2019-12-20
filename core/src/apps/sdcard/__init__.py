from trezor import wire
from trezor.messages import MessageType


def boot() -> None:
    wire.add(MessageType.SdProtect, __name__, "sd_protect")
