from typing import TYPE_CHECKING

from trezor.wire.protocol_common import WireError


class ThpError(WireError):
    pass


class ThpDecryptionError(ThpError):
    pass


class ThpInvalidDataError(ThpError):
    pass


class ThpUnallocatedSessionError(ThpError):
    def __init__(self, session_id: int):
        self.session_id = session_id


if TYPE_CHECKING:
    from enum import IntEnum
else:
    IntEnum = object


class ThpErrorType(IntEnum):
    TRANSPORT_BUSY = 1
    UNALLOCATED_CHANNEL = 2
    DECRYPTION_FAILED = 3
    INVALID_DATA = 4


class ChannelState(IntEnum):
    UNALLOCATED = 0
    TH1 = 1
    TH2 = 2
    TP1 = 3
    TP2 = 4
    TP3 = 5
    TP4 = 6
    TC1 = 7
    ENCRYPTED_TRANSPORT = 8


class SessionState(IntEnum):
    UNALLOCATED = 0
    ALLOCATED = 1
    MANAGEMENT = 2


class WireInterfaceType(IntEnum):
    MOCK = 0
    USB = 1
    BLE = 2


def is_channel_state_pairing(state: int) -> bool:
    if state in (
        ChannelState.TP1,
        ChannelState.TP2,
        ChannelState.TP3,
        ChannelState.TP4,
        ChannelState.TC1,
    ):
        return True
    return False


if __debug__:

    def state_to_str(state: int) -> str:
        name = {
            v: k for k, v in ChannelState.__dict__.items() if not k.startswith("__")
        }.get(state)
        if name is not None:
            return name
        return "UNKNOWN_STATE"
