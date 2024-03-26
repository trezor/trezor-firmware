from typing import TYPE_CHECKING  # pyright: ignore[reportShadowedImports]

if TYPE_CHECKING:
    from enum import IntEnum
else:
    IntEnum = object


class ChannelState(IntEnum):
    UNALLOCATED = 0
    UNAUTHENTICATED = 1
    TH1 = 2
    TH2 = 3
    TP1 = 4
    TP2 = 5
    TP3 = 6
    TP4 = 7
    TP5 = 8
    ENCRYPTED_TRANSPORT = 9


class SessionState(IntEnum):
    UNALLOCATED = 0


class WireInterfaceType(IntEnum):
    MOCK = 0
    USB = 1
    BLE = 2
