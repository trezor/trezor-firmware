import ustruct
from micropython import const
from trezorcrypto import crc
from typing import TYPE_CHECKING

from storage.cache_thp import (
    BROADCAST_CHANNEL_ID,
    find_allocated_channel,
    update_channel_last_used,
)
from trezor import io, loop, utils

from . import (
    CHANNEL_ALLOCATION_REQ,
    CODEC_V1,
    PING,
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

_BROADCAST_PAYLOAD_LENGTH = const(12)


class ThpContext:
    """
    This class allows fetching multi-packet THP payloads from a given interface.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, iface: WireInterface) -> None:
        self._iface = iface
        self._read = loop.wait(iface.iface_num() | io.POLL_READ)
        self._write = loop.wait(iface.iface_num() | io.POLL_WRITE)
        self._channels: dict[int, Channel] = {}

    async def get_next_message(self) -> Channel:
        """
        Reassemble a valid THP payload and return its channel.

        Also handle THP channel allocation.
        """
        from .. import THP_BUFFERS_PROVIDER

        packet = bytearray(self._iface.RX_PACKET_LEN)
        while True:
            packet_len = await self._read
            assert packet_len is not None
            assert packet_len == len(packet)
            self._iface.read(packet, 0)

            ctrl_byte = _get_ctrl_byte(packet)
            if ctrl_byte == CODEC_V1:
                await self._handle_codec_v1(packet)
                continue

            cid = ustruct.unpack(">BH", packet)[1]
            if cid == BROADCAST_CHANNEL_ID:
                await self._handle_broadcast(packet)
                continue

            if (cache := find_allocated_channel(cid)) is None:
                if not control_byte.is_continuation(_get_ctrl_byte(packet)):
                    await self.write_error(cid, ThpErrorType.UNALLOCATED_CHANNEL)
                continue

            if (channel := self._channels.get(cid)) is None:
                if (buffers := THP_BUFFERS_PROVIDER.take()) is None:
                    # concurrent payload reassembly is not supported
                    await self.write_error(cid, ThpErrorType.TRANSPORT_BUSY)
                    continue
                channel = self._channels[cid] = Channel(cache, self, buffers)

            if channel.reassemble(packet):
                update_channel_last_used(channel.channel_id)
                return channel

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
        ctrl_byte, _, payload_length = ustruct.unpack(">BHH", packet)

        packet = packet[: PacketHeader.INIT_LENGTH + payload_length]
        if not checksum.is_valid(packet[-CHECKSUM_LENGTH:], packet[:-CHECKSUM_LENGTH]):
            raise ThpError("Invalid checksum")

        if payload_length != _BROADCAST_PAYLOAD_LENGTH:
            raise ThpError("Invalid length in broadcast channel packet")

        nonce = packet[PacketHeader.INIT_LENGTH : -CHECKSUM_LENGTH]

        if ctrl_byte == PING:
            response_header = PacketHeader.get_pong_header(_BROADCAST_PAYLOAD_LENGTH)
            return await self.write_payload(response_header, nonce)

        if ctrl_byte != CHANNEL_ALLOCATION_REQ:
            raise ThpError("Unexpected ctrl_byte in a broadcast channel packet")

        channel_cache = channel_manager.create_new_channel(self._iface)
        response_data = get_channel_allocation_response(
            nonce, channel_cache.channel_id, self._iface
        )
        response_header = PacketHeader.get_channel_allocation_response_header(
            len(response_data) + CHECKSUM_LENGTH,
        )
        if __debug__:
            log.debug(
                __name__,
                "New channel allocated with id: %s",
                utils.hexlify_if_bytes(channel_cache.channel_id),
                iface=self._iface,
            )
        await self.write_payload(response_header, response_data)

    def write_error(self, cid: int, err_type: ThpErrorType) -> Awaitable[None]:
        msg_data = err_type.to_bytes(1, "big")
        length = len(msg_data) + CHECKSUM_LENGTH
        header = PacketHeader.get_error_header(cid, length)
        return self.write_payload(header, msg_data)


def _get_ctrl_byte(packet: bytes) -> int:
    return packet[0]
