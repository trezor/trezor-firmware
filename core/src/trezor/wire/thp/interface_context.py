from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from storage.cache_thp import clear_sessions_with_channel_id
from trezor import config, io, loop, utils
from trezor.loop import Timeout, race, wait

from ..protocol_common import ChannelPreemptedException
from . import get_encoded_device_properties
from .channel import TREZOR_STATE_PAIRED, TREZOR_STATE_UNPAIRED, Channel
from .crypto import derive_static_key_pair

if __debug__:
    from trezor import log

if utils.USE_BLE:
    import trezorble as ble
    from trezor.workflow import idle_timer

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorio import WireInterface
    from typing import Any, Awaitable, Generator


_TRACE = const(False)

# Preempt a stale channel if another channel becomes active and we allowed enough time for the host to respond.
# It allows interrupting a "stuck" THP workflow using a different channel on the same interface.
_PREEMPT_TIMEOUT_MS = const(1_000)

# Stop retransmission if writes are blocked - e.g. due to USB flow control.
# It allows restarting the event loop to handle other THP channels.
_WRITE_TIMEOUT_MS = const(5_000)
_WRITE_TIMEOUT = loop.sleep(_WRITE_TIMEOUT_MS)

EMPTY_BUFFER = bytearray()


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
            if __debug__:
                log.error(
                    __name__,
                    f"Interrupted channel {hex(self.active_channel.channel_id)} after {last_write_ms} ms",
                )
            self.active_channel.kill(ChannelPreemptedException())

    async def close(self) -> None:
        try:
            close_tasks = (
                loop.spawn(iface_ctx.close()) for iface_ctx in self._iface_ctxs
            )
            for task in close_tasks:
                await task
        except Exception as exc:
            if __debug__:
                log.exception(__name__, exc)


class InterfaceContext:
    """
    This class shuffles packets between an interface and non-blocking rust/trezor-thp code.
    """

    def __init__(self, iface: WireInterface, thp_ctx: ThpContext) -> None:
        self._iface = iface
        self._read = wait(iface.iface_num() | io.POLL_READ)
        self._write = wait(iface.iface_num() | io.POLL_WRITE)
        # Currently only one active channel is allowed in a session. Without session restart
        # this might become a dict[int, Channel].
        self.active_channel: Channel | None = None
        self.thp_ctx = thp_ctx

        self._read_loop: loop.spawn = loop.spawn(self.read_loop())
        self._write_loop: loop.spawn = loop.spawn(self.write_loop())
        self._retrans_loop: loop.spawn = loop.spawn(self.retransmission_loop())
        self._handshake_key_task: loop.spawn | None = None

        # Mailboxes used to wake up each loop.
        self._read_box: loop.mailbox[None] = loop.mailbox()
        self._write_box: loop.mailbox[None] = loop.mailbox()
        self._retrans_box: loop.mailbox[None] = loop.mailbox()
        # Whether the write loop should exit after completing the current iteration.
        self._write_loop_exit: bool = False

        self._rx_packet_buf = bytearray(iface.RX_PACKET_LEN)
        self._tx_packet_buf = bytearray(iface.TX_PACKET_LEN)

        # IDs hannels that would like to become active but will get error instead.
        self.inactive_channels: list[int] = []

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
        # This should not take forever thanks to _WRITE_TIMEOUT.
        await self._write_loop
        self._write_loop.close()

    def read_loop(self) -> Generator[Any, Any, None]:
        """
        Waits for incoming packets and stuffs them into rust/trezor-thp for processing.
        Passes packets to corresponding Channel object if needed. Spawns storage
        unlocking task if needed for a handshake.
        The loop is not trying to read packets all the time and may have to be woken up
        using `request_read()` - please see the documentation for `should_read()`.

        The loop should only ever await the interface or _read_box, any other blocking
        processing should happen in a different task.
        """
        iface = self._iface
        iface_num = iface.iface_num()
        verify_fn = self.verify_credential
        packet_buffer = self._rx_packet_buf

        while True:
            while not self.should_read():
                if __debug__ and _TRACE:
                    log.debug(__name__, "read loop paused", iface=iface)
                yield self._read_box

            packet_len = yield self._read
            if utils.USE_BLE and self._iface is ble.interface:
                # prevent auto-lock while handling longer workflows on Bluetooth
                idle_timer.touch()

            assert packet_len == self._iface.RX_PACKET_LEN

            self._iface.read(packet_buffer, 0)
            if __debug__ and _TRACE:
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

            if __debug__ and _TRACE and result is not None:
                log.debug(__name__, f"packet_in: {result}", iface=iface)
            if (
                result == trezorthp.KEY_REQUIRED  # pylint: disable=consider-using-in
                or result == trezorthp.KEY_REQUIRED_UNLOCK
            ):
                self.handle_handshake_key(result == trezorthp.KEY_REQUIRED_UNLOCK)

            # maybe we got ACK, recompute next retransmission timeout
            self.recompute_timeouts()
            # wake up write loop in case broadcast/handshake channels have outgoing data
            self.request_write()

    def should_read(self) -> bool:
        """
        We want to avoid thefollowing sequence of events:
        - workflow triggered by a message has finished,
        - next message is reassembled before session.py restarts,
        - session is restarted, receive buffer is lost,
        - host has to resend message after a delay.
          - NOTE: trezorlib doesn't resend ChannelAllocationRequest
        To avoid unnecessarry delay, interface is only awaited when:
        - there is no active channel,
        - a session called `read()` and is expecting a message,
        - a session called `write()` and is expecting an ACK.
        We can get rid of this logic if we ever get rid of loop restarts.
        """
        waiting_for_channel = self.thp_ctx.active_channel is None
        expecting_message = False
        expecting_ack = False
        for ifctx in self.thp_ctx._iface_ctxs:
            if ifctx.active_channel:
                expecting_message |= ifctx.active_channel.expecting_message
                expecting_ack |= ifctx.active_channel.expecting_ack
        if __debug__ and _TRACE:
            log.debug(
                __name__,
                f"should_read: waiting_for_channel:{waiting_for_channel} expecting_message:{expecting_message} expecting_ack:{expecting_ack}",
                iface=self._iface,
            )
        return waiting_for_channel or expecting_message or expecting_ack

    def read_packet_for_channel(self, result: int, packet_buffer: AnyBytes) -> None:
        channel_id = result & 0xFFFF
        buffer_size = (result >> 16) * 8

        if self.active_channel is None:
            from .. import THP_BUFFERS_PROVIDER

            if buffers := THP_BUFFERS_PROVIDER.take():
                self.active_channel = Channel(channel_id, self, buffers=buffers)
                if self.thp_ctx.active_channel is None:
                    self.thp_ctx.active_channel = self.active_channel
                    self.thp_ctx.channel_ready_box.put(None, replace=True)

        if self.active_channel is None or self.active_channel.channel_id != channel_id:
            trezorthp.send_transport_busy(self._iface.iface_num(), channel_id)
            self.inactive_channels.append(channel_id)
            self.request_write()
            self.thp_ctx.preempt_active_channel_if_stale()
            return

        try:
            self.active_channel.read_packet(packet_buffer, buffer_size)
        except Exception as exc:
            if __debug__:
                log.exception(__name__, exc)
            self.active_channel.kill(exc)
            self.active_channel = None

    def write_loop(self) -> Generator[Any, Any, None]:
        """
        Loop that queries rust/trezor-thp for outgoing packets and writes them to
        an interface. When there are no more packets to be sent, awaits _write_box
        and needs to be poked (using `request_write()`) after more packets are
        available.
        The loop should only ever await the interface or _write_box, any other
        blocking processing should happen in a different task.
        """
        iface = self._iface

        while True:
            yield self._write_box
            if __debug__ and _TRACE:
                log.debug(__name__, "write requested", iface=iface)
            result = yield race(self.write_all_packets(), _WRITE_TIMEOUT)
            if isinstance(result, int):
                if self.active_channel:
                    self.active_channel.kill(Timeout("THP write is blocked"))
                    # FIXME #6138 mark as delivered?
            self.clear_closed_sessions()
            self.recompute_timeouts()
            if __debug__ and _TRACE:
                log.debug(__name__, "write done", iface=iface)
            if self._write_loop_exit:
                break

    async def write_all_packets(self) -> None:
        packet_buffer = self._tx_packet_buf
        iface_num = self._iface.iface_num()
        # broadcast and channels doing handshake
        while trezorthp.packet_out(iface_num, None, EMPTY_BUFFER, packet_buffer):
            await self.write_packet(packet_buffer)
        # active channel
        if self.active_channel:
            while self.active_channel.write_packet(packet_buffer):
                await self.write_packet(packet_buffer)
        # transport_busy for currently inactive channels
        for cid in self.inactive_channels:
            while trezorthp.packet_out(iface_num, cid, EMPTY_BUFFER, packet_buffer):
                await self.write_packet(packet_buffer)
        self.inactive_channels.clear()

    def write_packet(self, packet_buffer: AnyBytes) -> Awaitable[None]:  # type: ignore [awaitable-return-type]
        if __debug__ and _TRACE:
            log.debug(
                __name__,
                f"write: {utils.hexlify_if_bytes(packet_buffer)}",
                iface=self._iface,
            )
        n_written = 0
        while n_written == 0:
            yield self._write  # type: ignore [awaitable-return-type]
            n_written = self._iface.write(packet_buffer)

        assert n_written == self._iface.TX_PACKET_LEN

    async def retransmission_loop(self) -> None:
        """
        Loop for handling THP message retransmission.
        If an event related to retransmission happens, i.e. message packets are written
        or an ACK is received, the loop needs to be waken up using recompute_timeouts()
        to adjust to the new state.
        """
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
                        if __debug__:
                            log.warning(
                                __name__,
                                "(cid: %04x) retransmitting message after %s ms",
                                channel_id,
                                timeout_ms,
                                iface=self._iface,
                            )
                        self.request_write()
                    elif (
                        self.active_channel
                        and self.active_channel.channel_id == channel_id
                    ):
                        if __debug__:
                            log.error(
                                __name__,
                                "(cid: %0rx) retransmission timeout",
                                channel_id,
                                iface=self._iface,
                            )
                        self.active_channel.kill(Timeout("THP retransmission timeout"))
                        # FIXME #6138 mark as delivered?
                    else:
                        if __debug__:
                            log.error(
                                __name__,
                                "(cid: %04x) retransmission timeout, channel closed",
                                channel_id,
                                iface=self._iface,
                            )
                        self.clear_closed_sessions()

            res = trezorthp.next_timeout(iface_num)
            channel_id, timeout_ms = res or (None, None)

    def recompute_timeouts(self) -> None:
        """
        Wake up retransmission loop to recompute earliest timeout. Needs to be
        called after message is written to interface, or an ACK is received.
        Safe to call even when not necessarry.
        """
        self._retrans_box.put(None, replace=True)

    def request_write(self, exit_afterwards: bool = False) -> None:
        """
        Wake up write loop after new packets become ready to be written. Safe to
        call even when no packets are ready to be written.
        """
        if exit_afterwards:
            self._write_loop_exit = True
        self._write_box.put(None, replace=True)

    def request_read(self) -> None:
        """
        Wake up read loop when session expects a message or an ACK. The variables
        that influence the result of `should_read()` need to be modified beforehand.

        Read loop is woken up on all interfaces to facilitate channel preemption.
        """
        for ifctx in self.thp_ctx._iface_ctxs:
            ifctx._read_box.put(None, replace=True)

    def handle_handshake_key(self, try_to_unlock: bool) -> None:
        if config.is_unlocked():
            trezor_static_privkey, _trezor_static_pubkey = derive_static_key_pair()
            trezorthp.handshake_key(self._iface.iface_num(), trezor_static_privkey)
        elif not try_to_unlock:
            trezorthp.handshake_key(self._iface.iface_num(), None)
        elif self._handshake_key_task is None:
            if __debug__:
                log.debug(
                    __name__,
                    "Static key needed but device is locked, spawning unlock dialog",
                    iface=self._iface,
                )
            self._handshake_key_task = loop.spawn(self.handshake_unlock())
        elif __debug__:
            log.debug(__name__, "Unlock task already running", iface=self._iface)

    async def handshake_unlock(self) -> None:
        try:
            from trezor import workflow

            from apps.common.lock_manager import unlock_device

            # Register the unlock prompt with the workflow management system
            # (in order to avoid immediately respawning the lockscreen task)
            await workflow.spawn(unlock_device())
            trezor_static_privkey, _trezor_static_pubkey = derive_static_key_pair()
        except Exception as e:
            if __debug__:
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
        """
        Credential verification callback invoked from rust code.
        Please note calling most trezorthp.* functions will fail because the lock on
        global state is already held.
        """
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
        except Exception as e:
            if __debug__:
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
