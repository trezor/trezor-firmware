import ustruct
from micropython import const
from trezorcrypto import crc
from typing import TYPE_CHECKING

from storage.cache_thp import (
    BROADCAST_CHANNEL_ID,
    ChannelCache,
    iter_allocated_channels,
    update_channel_last_used,
)
from trezor import io, loop, utils

from ..errors import WireBufferError
from . import (
    CHANNEL_ALLOCATION_REQ,
    CODEC_V1,
    PacketHeader,
    ThpError,
    ThpErrorType,
    channel_manager,
    checksum,
    control_byte,
    get_channel_allocation_response,
)
from .channel import Channel
from .checksum import CHECKSUM_LENGTH

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Awaitable, Iterable

_CID_REQ_PAYLOAD_LENGTH = const(12)


class ThpContext:
    """
    This class allows fetching multi-packet THP payloads from a given interface.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    @classmethod
    def load_from_cache(cls, iface: WireInterface) -> "ThpContext":
        ctx = cls(iface)
        for channel_cache in iter_allocated_channels(iface.iface_num()):
            ctx._load_channel(channel_cache)
        return ctx

    def _load_channel(self, cache: ChannelCache) -> Channel:
        channel_id = int.from_bytes(cache.channel_id, "big")
        assert channel_id not in self._channels
        self._channels[channel_id] = channel = Channel(cache, self)
        return channel

    def __init__(self, iface: WireInterface) -> None:
        self._iface = iface
        self._read = loop.wait(iface.iface_num() | io.POLL_READ)
        self._write = loop.wait(iface.iface_num() | io.POLL_WRITE)
        self._channels: dict[int, Channel] = {}

    async def get_next_message(self) -> Channel:
        log.debug(__name__, "waiting for new message", iface=self._iface)
        packet = bytearray(self._iface.RX_PACKET_LEN)
        while True:
            packet_len = await self._read
            assert packet_len is not None
            assert packet_len == len(packet)
            self._iface.read(packet, 0)

            if _get_ctrl_byte(packet) == CODEC_V1:
                await self._handle_codec_v1(packet)
                continue

            cid = ustruct.unpack(">BH", packet)[1]

            if cid == BROADCAST_CHANNEL_ID:
                await self._handle_broadcast(packet)
                continue

            channel = self._channels.get(cid)
            if channel is None:
                await self._handle_unallocated(cid, packet)
                continue

            try:
                if channel.reassemble(packet):
                    update_channel_last_used(channel.channel_id)
                    # The reassembled message must be handled ASAP without blocking,
                    # since it may point to the global read buffer.
                    return channel
            except WireBufferError:
                log.warning(__name__, "TRANSPORT_BUSY")
                await channel.write_error(ThpErrorType.TRANSPORT_BUSY)
                continue

    def write_payload(self, header: PacketHeader, payload: bytes) -> Awaitable[None]:
        checksum = crc.crc32(payload, crc.crc32(header.to_bytes()))
        checksum_bytes = checksum.to_bytes(CHECKSUM_LENGTH, "big")
        return self._write_payload_chunks(header, payload, checksum_bytes)

    def _write_payload_chunks(
        self, header: PacketHeader, *chunks: bytes
    ) -> Awaitable[None]:
        fragments = header.fragment_payload(self._iface.TX_PACKET_LEN, *chunks)
        return self._write_packets(fragments)

    async def _write_packets(self, fragments: Iterable[bytes]) -> None:
        packet_len = self._iface.TX_PACKET_LEN
        for packet in fragments:
            assert len(packet) == packet_len

            n_written = 0
            while n_written == 0:
                await self._write
                n_written = self._iface.write(packet)

            assert n_written == packet_len

    async def _handle_codec_v1(self, packet: bytes) -> None:
        # If the received packet is not an initial codec_v1 packet, do not send error message
        if packet[1:3] == b"##":
            response = bytearray(self._iface.TX_PACKET_LEN)
            # Codec_v1 magic constant:
            # "?##" + Failure message type + msg_size + msg_data (code = "Failure_InvalidProtocol")
            utils.memcpy(response, 0, b"?##\x00\x03\x00\x00\x00\x14\x08\x11", 0)
            await self._write_packets([response])

    async def _handle_broadcast(self, packet: bytes) -> None:
        if _get_ctrl_byte(packet) != CHANNEL_ALLOCATION_REQ:
            raise ThpError("Unexpected ctrl_byte in a broadcast channel packet")

        data = packet[: PacketHeader.INIT_LENGTH + _CID_REQ_PAYLOAD_LENGTH]
        if not checksum.is_valid(data[-CHECKSUM_LENGTH:], data[:-CHECKSUM_LENGTH]):
            raise ThpError("Checksum is not valid")

        length, nonce = ustruct.unpack(">H8s", packet[3:])
        if length != _CID_REQ_PAYLOAD_LENGTH:
            raise ThpError("Invalid length in broadcast channel packet")

        channel_cache = channel_manager.create_new_channel(self._iface)
        channel = self._load_channel(channel_cache)

        response_data = get_channel_allocation_response(
            nonce, channel.channel_id, self._iface
        )
        response_header = PacketHeader.get_channel_allocation_response_header(
            len(response_data) + CHECKSUM_LENGTH,
        )
        if __debug__:
            log.debug(
                __name__,
                "New channel allocated with id %d",
                channel.get_channel_id_int(),
                iface=self._iface,
            )
        await self.write_payload(response_header, response_data)

    async def _handle_unallocated(self, cid: int, packet: bytes) -> None:
        if control_byte.is_continuation(_get_ctrl_byte(packet)):
            return
        data = (ThpErrorType.UNALLOCATED_CHANNEL).to_bytes(1, "big")
        header = PacketHeader.get_error_header(cid, len(data) + CHECKSUM_LENGTH)
        await self.write_payload(header, data)


def _get_ctrl_byte(packet: bytes) -> int:
    return packet[0]
