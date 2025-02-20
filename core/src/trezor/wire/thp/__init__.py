import ustruct
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_thp import BROADCAST_CHANNEL_ID
from trezor import protobuf, utils
from trezor.enums import ThpPairingMethod
from trezor.messages import ThpDeviceProperties

from ..protocol_common import WireError

if TYPE_CHECKING:
    from enum import IntEnum

    from trezor.wire import WireInterface
    from typing_extensions import Self
else:
    IntEnum = object

CODEC_V1 = const(0x3F)

HANDSHAKE_INIT_REQ = const(0x00)
HANDSHAKE_INIT_RES = const(0x01)
HANDSHAKE_COMP_REQ = const(0x02)
HANDSHAKE_COMP_RES = const(0x03)
ENCRYPTED = const(0x04)

ACK_MESSAGE = const(0x20)
CHANNEL_ALLOCATION_REQ = const(0x40)
_CHANNEL_ALLOCATION_RES = const(0x41)
_ERROR = const(0x42)
CONTINUATION_PACKET = const(0x80)


class ThpError(WireError):
    pass


class ThpDecryptionError(ThpError):
    pass


class ThpInvalidDataError(ThpError):
    pass


class ThpDeviceLockedError(ThpError):
    pass


class ThpUnallocatedSessionError(ThpError):

    def __init__(self, session_id: int) -> None:
        self.session_id = session_id


class ThpErrorType(IntEnum):
    TRANSPORT_BUSY = 1
    UNALLOCATED_CHANNEL = 2
    DECRYPTION_FAILED = 3
    INVALID_DATA = 4
    DEVICE_LOCKED = 5


class ChannelState(IntEnum):
    UNALLOCATED = 0
    TH1 = 1
    TH2 = 2
    TP0 = 3
    TP1 = 4
    TP2 = 5
    TP3 = 6
    TP4 = 7
    TC1 = 8
    ENCRYPTED_TRANSPORT = 9
    INVALIDATED = 10


class SessionState(IntEnum):
    UNALLOCATED = 0
    ALLOCATED = 1
    SEEDLESS = 2


class PacketHeader:
    format_str_init = ">BHH"
    format_str_cont = ">BH"

    def __init__(self, ctrl_byte: int, cid: int, length: int) -> None:
        self.ctrl_byte = ctrl_byte
        self.cid = cid
        self.length = length

    def to_bytes(self) -> bytes:
        return ustruct.pack(self.format_str_init, self.ctrl_byte, self.cid, self.length)

    def pack_to_init_buffer(self, buffer: bytearray, buffer_offset: int = 0) -> None:
        """
        Packs header information in the form of **intial** packet
        into the provided buffer.
        """
        ustruct.pack_into(
            self.format_str_init,
            buffer,
            buffer_offset,
            self.ctrl_byte,
            self.cid,
            self.length,
        )

    def pack_to_cont_buffer(self, buffer: bytearray, buffer_offset: int = 0) -> None:
        """
        Packs header information in the form of **continuation** packet header
        into the provided buffer.
        """
        ustruct.pack_into(
            self.format_str_cont, buffer, buffer_offset, CONTINUATION_PACKET, self.cid
        )

    @classmethod
    def get_error_header(cls, cid: int, length: int) -> Self:
        """
        Returns header for protocol-level error messages.
        """
        return cls(_ERROR, cid, length)

    @classmethod
    def get_channel_allocation_response_header(cls, length: int) -> Self:
        """
        Returns header for allocation response handshake message.
        """
        return cls(_CHANNEL_ALLOCATION_RES, BROADCAST_CHANNEL_ID, length)


_DEFAULT_ENABLED_PAIRING_METHODS = [
    ThpPairingMethod.CodeEntry,
    ThpPairingMethod.QrCode,
    ThpPairingMethod.NFC,
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
    return methods


def _get_device_properties(iface: WireInterface) -> ThpDeviceProperties:
    # TODO define model variants
    return ThpDeviceProperties(
        pairing_methods=get_enabled_pairing_methods(iface),
        internal_model=utils.INTERNAL_MODEL,
        model_variant=0,
        protocol_version_major=2,
        protocol_version_minor=0,
    )


def get_encoded_device_properties(iface: WireInterface) -> bytes:
    props = _get_device_properties(iface)
    length = protobuf.encoded_length(props)
    encoded_properties = bytearray(length)
    protobuf.encode(encoded_properties, props)
    return encoded_properties


def get_channel_allocation_response(
    nonce: bytes, new_cid: bytes, iface: WireInterface
) -> bytes:
    props_msg = get_encoded_device_properties(iface)
    return nonce + new_cid + props_msg


if __debug__:

    def state_to_str(state: int) -> str:
        name = {
            v: k for k, v in ChannelState.__dict__.items() if not k.startswith("__")
        }.get(state)
        if name is not None:
            return name
        return "UNKNOWN_STATE"
