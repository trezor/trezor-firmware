import ustruct
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_thp import BROADCAST_CHANNEL_ID, SESSION_ID_LENGTH, TAG_LENGTH
from trezor import io, loop, utils
from trezor.wire.protocol_common import Message

from . import (
    CHANNEL_ALLOCATION_REQ,
    CODEC_V1,
    ChannelState,
    PacketHeader,
    ThpError,
    ThpErrorType,
    channel_manager,
    checksum,
    control_byte,
    get_channel_allocation_response,
    writer,
)
from .channel import Channel
from .checksum import CHECKSUM_LENGTH
from .received_message_handler import handle_checksum_and_acks, handle_received_message
from .writer import (
    INIT_HEADER_LENGTH,
    MAX_PAYLOAD_LEN,
    MESSAGE_TYPE_LENGTH,
    write_payload_to_wire_and_add_checksum,
)

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import WireInterface

_CID_REQ_PAYLOAD_LENGTH = const(12)
_CHANNELS: dict[int, Channel] = {}


async def thp_main_loop(iface: WireInterface) -> None:
    global _CHANNELS
    channel_manager.load_cached_channels(_CHANNELS, iface)

    log.info(__name__, "start thp_main_loop()", iface=iface)
    try:
        ctx = await ThpContext.accept(iface)
        await handle_received_message(ctx)
        log.info(__name__, "close thp_main_loop()", iface=iface)
    finally:
        channel_manager.CHANNELS_LOADED = False


class ThpContext:
    def __init__(self, channel: Channel) -> None:
        self.channel = channel
        self.msg: memoryview | None = channel.rx_buffer

    async def read(self) -> memoryview:
        if self.msg is None:
            channel = await _read_next_message(self.channel.iface)
            assert channel is self.channel
            self.msg = channel.rx_buffer

        msg = self.msg
        self.msg = None
        return msg

    async def decrypt(self) -> tuple[int, Message]:
        buf = await self.read()
        self.channel.decrypt_buffer(buf)

        session_id, message_type = ustruct.unpack(">BH", buf[INIT_HEADER_LENGTH:])
        message = Message(
            message_type,
            buf[
                INIT_HEADER_LENGTH
                + MESSAGE_TYPE_LENGTH
                + SESSION_ID_LENGTH : len(buf)
                - CHECKSUM_LENGTH
                - TAG_LENGTH
            ],
        )
        return (session_id, message)

    @classmethod
    async def accept(cls, iface: WireInterface) -> "ThpContext":
        return cls(await _read_next_message(iface))


async def _read_next_message(iface: WireInterface) -> Channel:
    read = loop.wait(iface.iface_num() | io.POLL_READ)
    packet = bytearray(iface.RX_PACKET_LEN)
    while True:
        packet_len = await read
        assert packet_len == len(packet)
        iface.read(packet, 0)

        if _get_ctrl_byte(packet) == CODEC_V1:
            await _handle_codec_v1(iface, packet)
            continue

        cid = ustruct.unpack(">BH", packet)[1]

        if cid == BROADCAST_CHANNEL_ID:
            await _handle_broadcast(iface, packet)
            continue

        channel = _CHANNELS.get(cid)
        if channel is None:
            await _handle_unallocated(iface, cid, packet)
            continue

        if not await _handle_allocated(iface, channel, packet):
            continue

        if await handle_checksum_and_acks(channel):
            # channel.rx_buffer contains a valid & acknowledged message
            return channel


async def _handle_codec_v1(iface: WireInterface, packet: bytes) -> None:
    # If the received packet is not an initial codec_v1 packet, do not send error message
    if not packet[1:3] == b"##":
        return
    if __debug__:
        log.debug(__name__, "Received codec_v1 message, returning error", iface=iface)
    error_message = _get_codec_v1_error_message()
    await writer.write_packet_to_wire(iface, error_message)


async def _handle_broadcast(iface: WireInterface, packet: utils.BufferType) -> None:
    if _get_ctrl_byte(packet) != CHANNEL_ALLOCATION_REQ:
        raise ThpError("Unexpected ctrl_byte in a broadcast channel packet")
    if __debug__:
        log.debug(
            __name__, "Received valid message on the broadcast channel", iface=iface
        )

    length, nonce = ustruct.unpack(">H8s", packet[3:])
    payload = _get_buffer_for_payload(length, packet[5:], _CID_REQ_PAYLOAD_LENGTH)
    if not checksum.is_valid(
        payload[-4:],
        packet[: _CID_REQ_PAYLOAD_LENGTH + INIT_HEADER_LENGTH - CHECKSUM_LENGTH],
    ):
        raise ThpError("Checksum is not valid")

    new_channel: Channel = channel_manager.create_new_channel(iface)
    cid = int.from_bytes(new_channel.channel_id, "big")
    _CHANNELS[cid] = new_channel

    response_data = get_channel_allocation_response(
        nonce, new_channel.channel_id, iface
    )
    response_header = PacketHeader.get_channel_allocation_response_header(
        len(response_data) + CHECKSUM_LENGTH,
    )
    if __debug__:
        log.debug(__name__, "New channel allocated with id %d", cid, iface=iface)

    await write_payload_to_wire_and_add_checksum(iface, response_header, response_data)


async def _handle_allocated(
    iface: WireInterface, channel: Channel, packet: utils.BufferType
) -> bool:
    if channel.iface is not iface:
        # TODO send error message to wire
        raise ThpError("Channel has different WireInterface")

    assert channel.get_channel_state() != ChannelState.UNALLOCATED
    return channel.receive_packet(packet)


async def _handle_unallocated(iface: WireInterface, cid: int, packet: bytes) -> None:
    if control_byte.is_continuation(_get_ctrl_byte(packet)):
        return
    data = (ThpErrorType.UNALLOCATED_CHANNEL).to_bytes(1, "big")
    header = PacketHeader.get_error_header(cid, len(data) + CHECKSUM_LENGTH)
    await write_payload_to_wire_and_add_checksum(iface, header, data)


def _get_buffer_for_payload(
    payload_length: int,
    existing_buffer: utils.BufferType,
    max_length: int = MAX_PAYLOAD_LEN,
) -> utils.BufferType:
    if payload_length > max_length:
        raise ThpError("Message too large")
    if payload_length > len(existing_buffer):
        try:
            new_buffer = bytearray(payload_length)
        except MemoryError:
            raise ThpError("Message too large")
        return new_buffer
    return _reuse_existing_buffer(payload_length, existing_buffer)


def _reuse_existing_buffer(
    payload_length: int, existing_buffer: utils.BufferType
) -> utils.BufferType:
    return memoryview(existing_buffer)[:payload_length]


def _get_ctrl_byte(packet: bytes) -> int:
    return packet[0]


def _get_codec_v1_error_message() -> bytes:
    # Codec_v1 magic constant "?##" + Failure message type + msg_size
    # + msg_data (code = "Failure_InvalidProtocol") + padding to 64 B
    ERROR_MSG = b"\x3f\x23\x23\x00\x03\x00\x00\x00\x14\x08\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    return ERROR_MSG
