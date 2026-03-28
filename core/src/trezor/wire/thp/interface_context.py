from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from storage.cache_thp import clear_sessions_with_channel_id
from trezor import config, io, loop, utils
from trezor.loop import Timeout, race, wait

from ..protocol_common import ChannelPreemptedException
from . import get_encoded_device_properties
from .channel import TREZOR_STATE_PAIRED, TREZOR_STATE_UNPAIRED, Channel

if __debug__:
    from trezor import log

if utils.USE_BLE:
    import trezorble as ble
    from trezor.workflow import idle_timer

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes
    from trezorio import WireInterface

    from typing_extensions import Self

# Preempt a stale channel if another channel becomes active and we allowed enough time for the host to respond.
# It allows interrupting a "stuck" THP workflow using a different channel on the same interface.
_PREEMPT_TIMEOUT_MS = const(1_000)

# TODO
_LAST_WRITE_TIMEOUT_MS = const(400)

EMPTY_BUFFER = bytearray()
CHANNEL_PREEMPTED = ChannelPreemptedException()


class ThpContext:
    """
    This class handles THP receiving from multiple wire interfaces.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, *ifaces: WireInterface) -> None:
        self._iface_ctxs = [InterfaceContext(iface, self) for iface in ifaces]
        self.channel_ready_box: loop.mailbox[None] = loop.mailbox()
        self.active_channel: Channel | None = None

    # Blocks until a channel in pairing/credential/transport phase starts receiving data.
    async def get_active_channel(self) -> Channel:
        """
        Reassemble a valid THP payload from any THP interface, and return its channel.

        Also handle THP channel allocation.
        """
        await self.channel_ready_box
        assert self.active_channel is not None
        return self.active_channel

    def preempt_active_channel_if_stale(self) -> None:
        if not self.active_channel:
            return
        last_write_ms = self.active_channel.get_last_write()
        # TODO does not work well if we're stuck in retransmit loop
        if last_write_ms is None or last_write_ms > _PREEMPT_TIMEOUT_MS:
            log.error(
                __name__,
                f"Interrupting channel {hex(self.active_channel.channel_id)} after {last_write_ms} ms",
            )
            self.active_channel.clear()
            self.active_channel.incoming_box.put(CHANNEL_PREEMPTED, replace=True)
            self.active_channel.ack_box.put(CHANNEL_PREEMPTED, replace=True)

    async def close(self) -> None:
        try:
            close_tasks = (
                loop.spawn(iface_ctx.close()) for iface_ctx in self._iface_ctxs
            )
            for task in close_tasks:
                await task
        except Exception as exc:
            log.exception(__name__, exc)


class InterfaceContext:
    """
    This class handles multi-packet THP payloads from a single interface.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed. FIXME
    """

    def __init__(self, iface: WireInterface, thp_ctx: ThpContext) -> None:
        self._iface = iface
        self._read = wait(iface.iface_num() | io.POLL_READ)
        self._write = wait(iface.iface_num() | io.POLL_WRITE)
        self._channels: dict[int, Channel] = {}
        self.thp_ctx = thp_ctx

        self._read_box: loop.mailbox[None] = loop.mailbox()
        self._write_box: loop.mailbox[bool] = loop.mailbox()
        self._retrans_box: loop.mailbox[None] = loop.mailbox()

        self._read_loop: loop.spawn = loop.spawn(self.read_loop())
        self._write_loop: loop.spawn = loop.spawn(self.write_loop())
        self._retrans_loop: loop.spawn = loop.spawn(self.retransmission_loop())
        self._handshake_key_task: loop.spawn | None = None

        self._packet_buf = bytearray(iface.RX_PACKET_LEN)
        self._packet_view = memoryview(self._packet_buf)

        self.write_error_cids = []

        trezorthp.init(
            iface.iface_num(),
            get_encoded_device_properties(iface),
        )

    async def close(self) -> None:
        if self._handshake_key_task:
            self._handshake_key_task.close()
        self._retrans_loop.close()
        self._read_loop.close()

        self.request_write(exit_afterwards=True)
        await race(self._write_loop, loop.sleep(_LAST_WRITE_TIMEOUT_MS))
        self._write_loop.close()

    def read_packet_for_channel(self, result: int, packet_buffer: AnyBytes) -> None:
        channel_id = result & 0xFFFF
        buffer_size = (result >> 16) * 8
        if channel_id not in self._channels:
            from .. import THP_BUFFERS_PROVIDER

            if (buffers := THP_BUFFERS_PROVIDER.take()) is None:
                trezorthp.send_transport_busy(self._iface.iface_num(), channel_id)
                self.write_error_cids.append(channel_id)
                self.request_write()
                self.thp_ctx.preempt_active_channel_if_stale()  # XXX what if handshake/unlock
                return
            self._channels[channel_id] = Channel(
                channel_id,
                self,
                buffers=buffers,
            )
        channel = self._channels[channel_id]
        # TODO catch exceptions and remove channel
        channel.read_packet(packet_buffer, buffer_size)
        if self.thp_ctx.active_channel is None:
            self.thp_ctx.active_channel = channel
        self.thp_ctx.channel_ready_box.put(None, replace=True)

    def should_read(self) -> bool:
        # TODO ALL interfaces
        waiting_for_channel = self.thp_ctx.active_channel is None
        expecting_message = any(ch.expecting_message for ch in self._channels.values())
        expecting_ack = any(ch.expecting_ack for ch in self._channels.values())
        # log.debug(__name__, f"should_read: {waiting_for_channel} {expecting_message} {expecting_ack}", iface=self._iface)
        return waiting_for_channel or expecting_message or expecting_ack

    async def read_loop(self) -> None:
        iface = self._iface
        iface_num = iface.iface_num()
        verify_fn = self.verify_credential

        while True:
            while not self.should_read():
                log.debug(__name__, "read loop paused", iface=iface)
                await self._read_box

            packet_len = await self._read
            if utils.USE_BLE and self._iface is ble.interface:
                # prevent auto-lock while handling longer workflows on Bluetooth
                idle_timer.touch()

            assert packet_len == self._iface.RX_PACKET_LEN

            self._iface.read(self._packet_buf, 0)
            packet_buffer = self._packet_view[:packet_len]
            log.debug(
                __name__,
                f"read: {utils.hexlify_if_bytes(packet_buffer)}",
                iface=iface,
            )
            result = trezorthp.packet_in(iface_num, packet_buffer, verify_fn)

            if isinstance(result, int):
                self.read_packet_for_channel(result, packet_buffer)
                self.clear_closed_sessions()
                continue

            log.debug(__name__, f"packet_in: {result}", iface=iface)
            if result in (trezorthp.KEY_REQUIRED, trezorthp.KEY_REQUIRED_UNLOCK):
                if self._handshake_key_task is None:
                    # TODO don't spawn a task if the device is unlocked
                    self._handshake_key_task = loop.spawn(
                        self.handshake_unlock(result == trezorthp.KEY_REQUIRED_UNLOCK)
                    )

            # maybe we got ACK, recompute next retransmission timeout
            # TODO request_write calls it too, maybe remove from here?
            self.recompute_timeouts()
            # wake up write loop in case broadcast/handshake channels have outgoing data
            self.request_write()

    async def write_loop(self) -> None:
        iface = self._iface
        packet_len = iface.TX_PACKET_LEN
        packet = bytearray(packet_len)

        while True:
            exit_afterwards = await self._write_box
            log.debug(__name__, "write requested", iface=iface)
            await self.write_all_packets(self, packet)
            for channel in self._channels.values():
                await self.write_all_packets(channel, packet)
            self.clear_closed_sessions()
            self.recompute_timeouts()
            log.debug(__name__, "write done", iface=iface)
            if exit_afterwards:
                break

    async def write_all_packets(
        self, channel: Channel | Self, packet: AnyBuffer
    ) -> None:
        while channel.write_packet(packet):
            log.debug(
                __name__,
                f"write: {utils.hexlify_if_bytes(packet)}",
                iface=self._iface,
            )
            n_written = 0
            while n_written == 0:
                await self._write
                n_written = self._iface.write(packet)

            assert n_written == self._iface.TX_PACKET_LEN

    def write_packet(self, packet: AnyBuffer) -> bool:
        if self.write_error_cids:
            channel_id = self.write_error_cids.pop(0)
            if trezorthp.packet_out(
                self._iface.iface_num(), channel_id, EMPTY_BUFFER, packet
            ):
                return True
        return trezorthp.packet_out(self._iface.iface_num(), None, EMPTY_BUFFER, packet)

    async def retransmission_loop(self) -> None:
        channel_id = None
        timeout_ms = None
        iface_num = self._iface.iface_num()

        while True:
            if timeout_ms is None or channel_id is None:
                await self._retrans_box
            else:
                res = await race(self._retrans_box, loop.sleep(timeout_ms))
                if isinstance(res, int):
                    ok = trezorthp.message_retransmit(iface_num, channel_id)
                    if ok:
                        log.warning(
                            __name__,
                            f"({hex(channel_id)}) retransmitting message after {timeout_ms} ms",
                            iface=self._iface,
                        )
                        self.request_write()
                    elif channel_id in self._channels:
                        self._channels[channel_id].ack_box.put(
                            Timeout("THP retransmission timeout")
                        )
                    else:
                        log.error(
                            __name__,
                            f"({hex(channel_id)}) retransmission timeout, channel closed",
                            iface=self._iface,
                        )
                        self.clear_closed_sessions()

            res = trezorthp.next_timeout(iface_num)
            channel_id, timeout_ms = res or (None, None)

    def recompute_timeouts(self) -> None:
        self._retrans_box.put(None, replace=True)

    def request_write(self, exit_afterwards: bool = False) -> None:
        self._write_box.put(exit_afterwards, replace=True)

    def request_read(self) -> None:
        # TODO ALL interfaces
        self._read_box.put(None, replace=True)

    async def handshake_unlock(self, try_to_unlock: bool) -> None:
        try:
            if not config.is_unlocked() and try_to_unlock:
                from trezor import workflow

                from apps.common.lock_manager import unlock_device

                log.debug(
                    __name__,
                    "Static key needed but device is locked, spawning unlock dialog",
                    iface=self._iface,
                )
                # Register the unlock prompt with the workflow management system
                # (in order to avoid immediately respawning the lockscreen task)
                await workflow.spawn(unlock_device())
            trezor_static_privkey, _trezor_static_pubkey = _derive_static_key_pair()
        except Exception as e:
            log.exception(__name__, e)
            trezorthp.handshake_key(self._iface.iface_num(), None)
        else:
            trezorthp.handshake_key(self._iface.iface_num(), trezor_static_privkey)
        finally:
            self.request_write()
            self._handshake_key_task = None

    def verify_credential(
        self, channel_id: int, host_static_public_key: bytes, payload: bytes
    ) -> int:
        from apps.thp.credential_manager import (
            decode_credential,
            unwrap_credential,
            validate_credential,
        )

        try:
            encoded_credential = unwrap_credential(payload)
            if not encoded_credential:
                return TREZOR_STATE_UNPAIRED
            credential = decode_credential(encoded_credential)
            paired = validate_credential(
                credential,
                host_static_public_key,
            )
            if paired:
                from trezor.wire.thp.paired_cache import cache_host_info

                cache_host_info(
                    mac_addr=self.connected_addr(),
                    host_name=credential.cred_metadata.host_name,
                    app_name=credential.cred_metadata.app_name,
                )
                return TREZOR_STATE_PAIRED
            else:
                return TREZOR_STATE_UNPAIRED
        except Exception as e:
            log.exception(__name__, e, iface=self._iface)
        return TREZOR_STATE_UNPAIRED

    def connected_addr(self) -> AnyBytes | None:
        """
        Return peer MAC address (if connected).

        Currently supported by BLE (used for caching THP host names).
        """
        if utils.USE_BLE:
            if self._iface is ble.interface:
                return ble.connected_addr()

        return None

    def clear_closed_sessions(self) -> None:
        channels = trezorthp.channel_get_closed(self._iface.iface_num())
        if channels is None:
            return
        for cid in channels:
            clear_sessions_with_channel_id(cid.to_bytes(2, "big"))


def _derive_static_key_pair() -> tuple[bytes, bytes]:
    from trezorcrypto import bip32

    from storage import device

    HARDENED = const(0x8000_0000)

    node_int = HARDENED | int.from_bytes(b"\x00THP", "big")
    node = bip32.from_seed(device.get_device_secret(), "curve25519")
    node.derive(node_int)

    trezor_static_private_key = node.private_key()
    trezor_static_public_key = node.public_key()[1:33]
    # Note: the first byte (\x01) of the public key is removed, as it
    # only indicates the type of the elliptic curve used

    return trezor_static_private_key, trezor_static_public_key
