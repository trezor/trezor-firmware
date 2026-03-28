from typing import TYPE_CHECKING

from trezor import protobuf, utils
from trezor.enums import ThpPairingMethod
from trezor.messages import ThpDeviceProperties

from ..protocol_common import WireError

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from enum import IntEnum

    from trezor.wire import WireInterface
else:
    IntEnum = object


class ThpError(WireError):
    pass


class ThpUnallocatedSessionError(ThpError):

    def __init__(self, session_id: int) -> None:
        self.session_id = session_id


# Only a subset, handshake states are not visible to python
class ChannelState(IntEnum):
    TP0 = 3
    TP1 = 4
    TP2 = 5
    TP3 = 6
    TP4 = 7
    TC1 = 8
    ENCRYPTED_TRANSPORT = 9


class SessionState(IntEnum):
    UNALLOCATED = 0
    ALLOCATED = 1
    SEEDLESS = 2


_DEFAULT_ENABLED_PAIRING_METHODS = [
    # TODO: Add pairing methods https://github.com/trezor/trezor-firmware/issues/6036
    ThpPairingMethod.CodeEntry
]


def get_enabled_pairing_methods(
    iface: WireInterface | None = None,
) -> list[ThpPairingMethod]:
    """
    Returns pairing methods that are currently allowed by the device
    with respect to the wire interface the host communicates on.
    """
    methods = _DEFAULT_ENABLED_PAIRING_METHODS.copy()
    if __debug__:
        methods.append(ThpPairingMethod.SkipPairing)
        methods.append(  # Used only in tests, TODO: https://github.com/trezor/trezor-firmware/issues/6037
            ThpPairingMethod.NFC
        )
        methods.append(  # Used only in tests, TODO: https://github.com/trezor/trezor-firmware/issues/6038
            ThpPairingMethod.QrCode
        )

    return methods


def _get_device_properties(iface: WireInterface) -> ThpDeviceProperties:
    model_variant = (
        (utils.unit_color() or 0)
        | (int(utils.unit_btconly() or False) << 8)
        | ((utils.unit_packaging() or 0) << 16)
    )
    return ThpDeviceProperties(
        pairing_methods=get_enabled_pairing_methods(iface),
        internal_model=utils.INTERNAL_MODEL,
        model_variant=model_variant,
        protocol_version_major=2,
        protocol_version_minor=0,  # TODO ack piggybacking
    )


# NOTE: make sure the result never exceeds MAX_DEVICE_PROPERTIES_LEN in embed/rust/src/thp/mod.rs
def get_encoded_device_properties(iface: WireInterface) -> AnyBytes:
    props = _get_device_properties(iface)
    length = protobuf.encoded_length(props)
    encoded_properties = bytearray(length)
    protobuf.encode(encoded_properties, props)
    return encoded_properties
