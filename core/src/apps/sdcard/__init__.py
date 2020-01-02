from trezor import wire
from trezor.messages import MessageType


def boot() -> None:
    wire.add(MessageType.SdProtect, __name__, "sd_protect")
    wire.add(MessageType.SdAppDataGet, __name__, "sd_appdata_get")
    wire.add(MessageType.SdAppDataSet, __name__, "sd_appdata_set")
    wire.add(MessageType.SdAppDataDelete, __name__, "sd_appdata_delete")
