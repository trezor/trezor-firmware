import ustruct
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_thp import (
    BROADCAST_CHANNEL_ID,
    find_allocated_channel,
    update_channel_last_used,
)
from trezor import io, utils
from trezor.loop import Timeout, race, sleep, wait

from . import (
    CHANNEL_ALLOCATION_REQ,
    CODEC_V1,
    PING,
    PacketHeader,
    ThpErrorType,
    channel_manager,
    checksum,
    control_byte,
    get_channel_allocation_response,
)
from .channel import Channel, ChannelPreemptedException
from .checksum import CHECKSUM_LENGTH

if __debug__:
    from trezor import log


if utils.USE_BLE:
    import trezorble as ble
    from trezor.workflow import idle_timer

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes
    from trezorio import WireInterface
    from typing import Awaitable, Generator, Iterable, NoReturn

_BROADCAST_PAYLOAD_LENGTH = const(12)


# Uses `yield` instead of `await` to avoid allocations.
def _timeout_after(ms: int) -> Generator[sleep, int, NoReturn]:
    yield sleep(ms)
    raise Timeout


class ThpContext:
    """
    This class handles THP receiving from multiple wire interfaces.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, *ifaces: WireInterface) -> None:
        max_packet_len = max(iface.RX_PACKET_LEN for iface in ifaces)
        self._packet_buf = bytearray(max_packet_len)
        self._packet_view = memoryview(self._packet_buf)
        self._iface_ctxs = [InterfaceContext(iface, self) for iface in ifaces]

    async def get_next_message(self, timeout_ms: int | None = None) -> Channel | None:
        """
        Reassemble a valid THP payload from any THP interface, and return its channel.

        Also handle THP channel allocation.
        """
        # wait until one of the channels becomes readable
        children = (iface_ctx._wait_for_packet() for iface_ctx in self._iface_ctxs)
        if timeout_ms is None:
            race_task = race(*children)
        else:
            race_task = race(*children, _timeout_after(timeout_ms))

        (iface_ctx, packet_len) = await race_task  # will raise on timeout
        assert packet_len == iface_ctx._iface.RX_PACKET_LEN

        # read and handle the packet using its `InterfaceContext`
        iface_ctx._iface.read(self._packet_buf, 0)
        return await iface_ctx.handle_packet(self._packet_view[:packet_len])


class InterfaceContext:
    """
    This class handles multi-packet THP payloads from a single interface.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, iface: WireInterface, thp_ctx: ThpContext) -> None:
        self._iface = iface
        self._read = wait(iface.iface_num() | io.POLL_READ)
        self._write = wait(iface.iface_num() | io.POLL_WRITE)
        self._channels: dict[int, Channel] = {}
        self.thp_ctx = thp_ctx

    def _wait_for_packet(self) -> Generator[wait, int, tuple["InterfaceContext", int]]:
        """Block until this interface is readable.

        It adapts `loop.wait`, to be used in a `race()` over multiple THP interfaces by `ThpContext.get_next_message()`.
        """
        # Uses `yield` instead of `await` to avoid allocations.
        packet_len = yield self._read
        if utils.USE_BLE and self._iface is ble.interface:
            # prevent auto-lock while handling longer workflows on Bluetooth
            idle_timer.touch()
        return self, packet_len

    async def handle_packet(self, packet: AnyBuffer) -> Channel | None:
        """
        Reassemble a valid THP payload and return its channel, if reassembly succeeds.
        Otherwise, returns `None` and should be called again (with the next packet).

        Also handle THP channel allocation.
        """
        ctrl_byte = _get_ctrl_byte(packet)
        if ctrl_byte == CODEC_V1:
            return await self._handle_codec_v1(packet)

        cid = ustruct.unpack(">BH", packet)[1]
        if cid == BROADCAST_CHANNEL_ID:
            return await self._handle_broadcast(packet)

        if (cache := find_allocated_channel(cid)) is None:
            if not control_byte.is_continuation(_get_ctrl_byte(packet)):
                await self.write_error(cid, ThpErrorType.UNALLOCATED_CHANNEL)
            return None

        if (channel := self._channels.get(cid)) is None:
            from .. import THP_BUFFERS_PROVIDER

            if (buffers := THP_BUFFERS_PROVIDER.take()) is None:
                # concurrent payload reassembly is not supported
                await self.write_error(cid, ThpErrorType.TRANSPORT_BUSY)
                raise ChannelPreemptedException  # try to preempt the caller (if stale)

            channel = self._channels[cid] = Channel(cache, self, buffers)

        if channel.reassemble(packet):
            update_channel_last_used(channel.channel_id)
            return channel

    def write_payload(self, header: PacketHeader, payload: AnyBytes) -> Awaitable[None]:
        checksum_bytes = checksum.compute(
            payload, checksum.compute_int(header.to_bytes())
        )
        return self._write_payload_chunks(header, payload, checksum_bytes)

    def _write_payload_chunks(
        self, header: PacketHeader, *chunks: AnyBytes
    ) -> Awaitable[None]:
        fragments = header.fragment_payload(self._iface.TX_PACKET_LEN, *chunks)
        return self._write_packets(fragments)

    async def _write_packets(self, fragments: Iterable[AnyBytes]) -> None:
        packet_len = self._iface.TX_PACKET_LEN
        for packet in fragments:
            assert len(packet) == packet_len

            n_written = 0
            while n_written == 0:
                await self._write
                n_written = self._iface.write(packet)

            assert n_written == packet_len

    async def _handle_codec_v1(self, packet: AnyBytes) -> None:
        # If the received packet is not an initial codec_v1 packet, do not send error message
        if packet[1:3] == b"##":
            response = bytearray(self._iface.TX_PACKET_LEN)
            # Codec_v1 magic constant:
            # "?##" + Failure message type + msg_size + msg_data (code = "Failure_InvalidProtocol")
            utils.memcpy(response, 0, b"?##\x00\x03\x00\x00\x00\x14\x08\x11", 0)
            await self._write_packets([response])

    async def _handle_broadcast(self, packet: AnyBytes) -> None:
        ctrl_byte, _, payload_length = ustruct.unpack(">BHH", packet)

        packet = packet[: PacketHeader.INIT_LENGTH + payload_length]
        if not checksum.is_valid(packet[-CHECKSUM_LENGTH:], packet[:-CHECKSUM_LENGTH]):
            if __debug__:
                log.debug(
                    __name__, "Invalid checksum: %s", utils.hexlify_if_bytes(packet)
                )
            return

        if payload_length != _BROADCAST_PAYLOAD_LENGTH:
            if __debug__:
                log.debug(
                    __name__,
                    "Invalid length in broadcast channel packet: %d",
                    payload_length,
                )
            return

        nonce = packet[PacketHeader.INIT_LENGTH : -CHECKSUM_LENGTH]

        if ctrl_byte == PING:
            response_header = PacketHeader.get_pong_header(_BROADCAST_PAYLOAD_LENGTH)
            return await self.write_payload(response_header, nonce)

        if ctrl_byte != CHANNEL_ALLOCATION_REQ:
            if __debug__:
                log.debug(
                    __name__,
                    "Unexpected ctrl_byte in a broadcast channel packet: %d",
                    ctrl_byte,
                )
            return

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
        if __debug__:
            log.error(__name__, "(cid: %04x) THP error #%d", cid, err_type)
        msg_data = err_type.to_bytes(1, "big")
        length = len(msg_data) + CHECKSUM_LENGTH
        header = PacketHeader.get_error_header(cid, length)
        return self.write_payload(header, msg_data)

    def connected_addr(self) -> bytes | None:
        """
        Return peer MAC address (if connected).

        Currently supported by BLE (used for caching THP host names).
        """
        if utils.USE_BLE:
            if self._iface is ble.interface:
                return ble.connected_addr()

        return None


def _get_ctrl_byte(packet: AnyBytes) -> int:
    return packet[0]
