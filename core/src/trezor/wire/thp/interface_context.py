from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from storage.cache_thp import PREEMPTING_PACKET, clear_sessions_without_channel
from trezor import config, io, loop, utils
from trezor.loop import Timeout, race, wait

from ..protocol_common import ChannelPreemptedException
from . import get_encoded_device_properties
from .channel import TREZOR_STATE_PAIRED, TREZOR_STATE_UNPAIRED, Channel
from .crypto import get_trezor_static_private_key

if __debug__:
    from trezor import log

if utils.USE_BLE:
    import trezorble as ble
    from trezor.workflow import idle_timer

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorio import WireInterface
    from typing import Any, Generator

    from .. import Provider
    from .memory_manager import ThpBuffer


_TRACE = const(False)

# Preempt a stale channel if another channel becomes active and we allowed enough time for the host to respond.
# It allows interrupting a "stuck" THP workflow using a different channel on the same interface.
_PREEMPT_TIMEOUT_MS = const(1_000)

# Stop retransmission if writes are blocked - e.g. due to USB flow control.
# It allows restarting the event loop to handle other THP channels.
_WRITE_TIMEOUT_MS = const(5_000)

_KEY_REQUIRED_VALS = (trezorthp.KEY_REQUIRED, trezorthp.KEY_REQUIRED_UNLOCK)

EMPTY_BUFFER = bytearray()


class ThpContext:
    """
    This class handles THP receiving from multiple wire interfaces.
    It also handles and responds to low-level single packet THP messages, creating new channels if needed.
    """

    def __init__(self, *ifaces: WireInterface) -> None:
        from .. import buffers_provider_for

        self._iface_ctxs = [
            InterfaceContext(iface, self, buffers_provider_for(iface)) for iface in ifaces
        ]
        self.channel_ready_box: loop.mailbox[None] = loop.mailbox()
        # THE CHANNEL WHOSE MESSAGES THE MAIN LOOP DISPATCHES, on whichever interface it arrived --
        # this is what `get_dispatch_channel` hands to `handle_session_thp`. NOT "the foreground
        # channel": which channel gets dispatched is decided by which one received a packet first,
        # so any interface's channel can hold this, and a channel that is not dispatched can still
        # be alive and carrying traffic driven by a workflow running on another one.
        #
        # Distinct from `InterfaceContext.active_channel`, which is PER INTERFACE and is what that
        # interface's write loop drains. A channel must be its interface's `active_channel` to be
        # writable at all; being `dispatch_channel` is a separate question about whose messages the
        # main loop reads.
        self.dispatch_channel: Channel | None = None

    # Blocks until a channel in pairing/credential/transport phase starts receiving data.
    async def get_dispatch_channel(self) -> Channel:
        """
        Reassemble a valid THP payload from any THP interface, and return its channel.

        Also handle THP channel allocation.
        """
        await self.channel_ready_box
        assert self.dispatch_channel is not None
        return self.dispatch_channel

    def preempt_dispatch_channel_if_stale(
        self, iface_num: int, cid_hint: int, packet_buffer: AnyBytes
    ) -> bool:
        """
        If the dispatched channel is idle for more than _PREEMPT_TIMEOUT_MS, kill
        it and save the packet passed as an argument to be processed as if it
        was received when the next loop session is started.

        Returns True on success, False if the caller should send TRANSPORT_BUSY.
        """
        if not self.dispatch_channel:
            return False
        last_write_ms = self.dispatch_channel.get_last_write()
        if last_write_ms is None or last_write_ms > _PREEMPT_TIMEOUT_MS:
            self.dispatch_channel.kill(ChannelPreemptedException())
            saved = PREEMPTING_PACKET.set(iface_num, cid_hint, packet_buffer)
            if __debug__:
                log.error(
                    __name__,
                    f"Interrupted channel {hex(self.dispatch_channel.channel_id)} after {last_write_ms} ms",
                )
                log.debug(
                    __name__, f"Packet will be processed in next session: {saved}"
                )
            return saved
        return False

    def attach_existing_channel(self, iface_num: int, channel_id: int) -> Channel:
        """Make an already-open channel writable again on the interface it belongs to.

        The Rust side keeps a channel across MicroPython session restarts, but the `Channel`
        object does not survive them -- and a channel that is not its interface's
        `active_channel` cannot be written at all: `Channel.write` only pokes the write loop,
        which drains `active_channel` and nothing else. So a caller holding a channel id from
        persisted state has to reattach before it can send anything.

        THREE THINGS ARE CHECKED, and none of them is a formality:

          the channel still exists -- Rust may have closed it since the id was recorded, and a
          `Channel` for a dead id would fail later and further away;

          it is on the interface the caller named -- `packet_out_channel` looks a channel up by
          id ALONE and fragments into a buffer the caller then writes to its OWN interface, so
          attaching to the wrong one puts a host's encrypted traffic on another host's wire.
          `Channel.__init__` enforces this too; naming the interface here is what lets the
          caller be told which of the two is wrong;

          the interface is not already serving a different channel -- reattaching must never
          displace one, because the displaced object is what some other task is awaiting.

        Reattaching a channel that is already attached returns the existing object rather than
        building a second one: two `Channel`s for one id would each hold half the state (one
        has the mailbox being awaited, the other the buffers being filled).
        """
        from ..errors import DataError

        for iface_ctx in self._iface_ctxs:
            if iface_ctx._iface.iface_num() == iface_num:
                break
        else:
            raise DataError("no such THP interface")

        existing = iface_ctx.active_channel
        if existing is not None:
            if existing.channel_id != channel_id:
                raise DataError("THP interface is busy with another channel")
            return existing

        buffers = iface_ctx._buffers_provider.take()
        if buffers is None:
            # The pool is held by a channel this interface no longer tracks. Refusing is the only
            # safe answer: the buffers are still referenced by whatever took them.
            raise DataError("no THP buffers left for this interface")

        try:
            channel = Channel(channel_id, iface_ctx, buffers=buffers)
        except trezorthp.ThpError:
            # Closed since the id was recorded -- report it as unavailable rather than letting a
            # Rust-level error escape into a workflow.
            raise DataError("THP channel is no longer open")

        iface_ctx.active_channel = channel
        return channel

    async def close(self) -> None:
        for iface_ctx in self._iface_ctxs:
            try:
                await iface_ctx.close()
            except Exception as exc:
                if __debug__:
                    log.exception(__name__, exc)


class InterfaceContext:
    """
    This class shuffles packets between an interface and non-blocking rust/trezor-thp code.
    """

    def __init__(
        self,
        iface: WireInterface,
        thp_ctx: ThpContext,
        buffers_provider: Provider[tuple[ThpBuffer, ThpBuffer]],
    ) -> None:
        self._iface = iface
        # WHERE THIS INTERFACE GETS ITS CHANNEL BUFFERS, passed in rather than looked up, because
        # WHICH provider an interface draws from is the whole question. A provider hands out its
        # pair ONCE, so interfaces that share one can only ever have a channel one at a time --
        # which is deliberate for USB and BLE, and is exactly what an interface hosting a service
        # channel alongside a live wallet channel must not do.
        self._buffers_provider = buffers_provider
        self._read = wait(iface.iface_num() | io.POLL_READ)
        self._write = wait(
            iface.iface_num() | io.POLL_WRITE, timeout_ms=_WRITE_TIMEOUT_MS
        )
        # This interface's channel: the one its read loop feeds and its write loop drains. Only one
        # per interface for now; without session restart this might become a dict[int, Channel].
        #
        # Separate from `ThpContext.dispatch_channel` -- see there. Several interfaces may each hold
        # one of these at the same time while only one of them is being dispatched.
        self.active_channel: Channel | None = None
        self.thp_ctx = thp_ctx

        # Whether this interface dispatches its own inbound messages instead of handing them to
        # the session's single dispatcher. True for the WARD service interface, whose daemon is not
        # the session's host and must not have to wait for it.
        from .. import is_ward_interface

        self._serves_own_dispatch: bool = is_ward_interface(iface)
        self._dispatch_box: loop.mailbox[None] = loop.mailbox()
        # Set by a handler that has taken ownership of the conversation -- see `release_dispatch`.
        self._dispatch_released: bool = False

        self._read_loop: loop.spawn = loop.spawn(self.read_loop())
        self._write_loop: loop.spawn = loop.spawn(self.write_loop())
        self._retrans_loop: loop.spawn = loop.spawn(self.retransmission_loop())
        self._handshake_key_task: loop.spawn | None = None

        # A DISPATCHER OF ITS OWN, for the service interface only. `ThpContext.dispatch_channel`
        # holds exactly one channel -- whichever received a packet first -- because a wallet host's
        # conversation IS the session, and the session restarts around it. A wallet channel is
        # normally live and holding that slot, so a message arriving on the service interface would
        # be reassembled and then never read by anyone: the symptom is a daemon that hangs rather
        # than an error.
        #
        # Serving it here rather than teaching the main loop to multiplex keeps the two
        # conversations independent, which is the reason the interface is separate at all.
        self._dispatch_loop: loop.spawn | None = None
        if self._serves_own_dispatch:
            self._dispatch_loop = loop.spawn(self.dispatch_loop())

        # Mailboxes used to wake up each loop.
        self._read_box: loop.mailbox[None] = loop.mailbox()
        self._write_box: loop.mailbox[None] = loop.mailbox()
        self._retrans_box: loop.mailbox[None] = loop.mailbox()
        # Whether the write loop should exit after completing the current iteration.
        self._write_loop_exit: bool = False

        self._rx_packet_buf = bytearray(iface.RX_PACKET_LEN)
        self._tx_packet_buf = bytearray(iface.TX_PACKET_LEN)

        # IDs of channels that would like to become active but will get error instead.
        self.inactive_channels: set[int] = set()

        trezorthp.init(
            iface.iface_num(),
            get_encoded_device_properties(iface),
        )

    async def close(self) -> None:
        """
        Shut down THP processing on this interface. Try waiting for the write loop
        to finish in case it is sending an error to host.
        """
        if self._handshake_key_task:
            self._handshake_key_task.close()
        if self._dispatch_loop:
            self._dispatch_loop.close()
        self._retrans_loop.close()
        self._read_loop.close()

        self.request_write(exit_afterwards=True)
        try:
            # This should not take forever thanks to _WRITE_TIMEOUT.
            await self._write_loop
        finally:
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

        if (pep := PREEMPTING_PACKET.get(iface_num)) is not None:
            if __debug__:
                log.debug(__name__, "got packet from previous session", iface=iface)
            cid_hint, buf = pep
            self.read_packet_for_channel(cid_hint, buf)

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
                continue

            if __debug__ and _TRACE and result is not None:
                log.debug(__name__, f"packet_in: {result}", iface=iface)
            if result in _KEY_REQUIRED_VALS:
                self.handle_handshake_key(result == trezorthp.KEY_REQUIRED_UNLOCK)

            # maybe we got ACK, recompute next retransmission timeout
            self.recompute_timeouts()
            # wake up write loop in case broadcast/handshake channels have outgoing data
            self.request_write()

    def release_dispatch(self) -> None:
        """Stop dispatching this interface: a handler has taken over the conversation.

        WHAT IT PREVENTS IS TWO READERS. A channel has ONE incoming mailbox, so a dispatcher
        parked in `Channel.read` and a workflow reading its own reply would race for the same
        message -- and which one won would depend on scheduling. Handing the channel over
        removes the race rather than arbitrating it.

        Reset when a channel is next allocated here, because that is a new conversation.
        """
        self._dispatch_released = True

    async def dispatch_loop(self) -> None:
        """Handle host-initiated messages on this interface's own channel, until handed over.

        ONE MESSAGE IN PRACTICE. `WardServiceOpen` is the last thing the daemon initiates;
        afterwards the device asks and the daemon answers, and those replies are read by the
        workflow that asked. So this loop stops as soon as that handler says so, and is a
        bootstrap path rather than a second general dispatcher.
        """
        from . import received_message_handler

        while True:
            await self._dispatch_box
            channel = self.active_channel
            while channel is not None and channel is self.active_channel:
                try:
                    await received_message_handler.handle_received_message(channel)
                except Exception as exc:
                    # The channel died, or a handler failed in a way `handle_received_message`
                    # does not convert into a Failure. Either way this loop is not the place to
                    # decide what that means -- go back to waiting for a channel rather than
                    # retrying, which on a dead channel would spin.
                    #
                    # A channel that SURVIVES a failure here is therefore not served again until
                    # a channel is next allocated on this interface. That is acceptable only
                    # because the daemon initiates exactly one message: it reconnects, which
                    # allocates a channel, which re-arms this loop.
                    if __debug__:
                        # `iface` so the line is tagged as WARD's like the rest of this
                        # conversation: a dispatcher dying is one of the few ways the daemon's
                        # channel stops being served without anything else saying so.
                        log.exception(__name__, exc, iface=self._iface)
                    break
                if self._dispatch_released:
                    break

    def should_read(self) -> bool:
        """
        We want to avoid the following sequence of events:
        - workflow triggered by a message has finished,
        - next message is reassembled before session.py restarts,
        - session is restarted, receive buffer is lost,
        - host has to resend message after a delay.
          - NOTE: trezorlib doesn't resend ChannelAllocationRequest

        To avoid unnecessary delay, interface is only awaited when:
        - there is no active channel,
        - a session called `read()` and is expecting a message,
        - a session called `write()` and is expecting an ACK.

        We can get rid of this logic if we ever get rid of loop restarts.
        """
        waiting_for_channel = self.thp_ctx.dispatch_channel is None
        expecting_message = False
        expecting_ack = False
        for ifctx in self.thp_ctx._iface_ctxs:
            if ifctx.active_channel:
                expecting_message = (
                    expecting_message or ifctx.active_channel.expecting_message
                )
                expecting_ack = expecting_ack or ifctx.active_channel.expecting_ack
        if __debug__ and _TRACE:
            log.debug(
                __name__,
                f"should_read: waiting_for_channel:{waiting_for_channel} expecting_message:{expecting_message} expecting_ack:{expecting_ack}",
                iface=self._iface,
            )
        if self._serves_own_dispatch:
            # ALWAYS LISTENING. The conditions below describe a channel whose traffic the session
            # drives: the session is between messages, or a workflow is waiting for one. The
            # service interface fits none of them -- the daemon may announce itself at any moment,
            # with no workflow waiting and no restart pending -- and the buffer-loss race this
            # guards against is handled for it by reattaching the channel instead.
            return True

        return waiting_for_channel or expecting_message or expecting_ack

    def _retire_displaced_channel(self, channel_id: int) -> None:
        """Give a newcomer the slot an incumbent is occupying, unless the incumbent is in use.

        WHY THIS EXISTS AT ALL. An interface tracks one channel, and the machinery that lets a
        newcomer displace an incumbent is `preempt_dispatch_channel_if_stale` -- which can only
        preempt `ThpContext.dispatch_channel`. That is a WIRE channel by construction: an interface
        that serves its own dispatch never installs one there. So on the service interface an
        incumbent is never let go of, and the symptom is not an error but a LOCK-OUT -- the
        newcomer's packets are answered with TRANSPORT_BUSY forever, its host retransmits, and
        nothing on the device notices anything is wrong.

        It was survivable by accident. A wallet channel that happened to be the dispatch channel and
        happened to be idle got preempted instead, forcing a loop restart that rebuilt this object --
        so a daemon reconnect cost a second and a half and an unrelated host's channel. With no
        wallet workflow in flight there is nothing to preempt, and the interface stays locked until
        the device reboots.

        THE RULE IS THE SAME ONE THE WIRE INTERFACE ALREADY USES: an incumbent the device has
        written to within `_PREEMPT_TIMEOUT_MS` is in use and is kept; anything else is displaced.
        Applied here rather than borrowed, because the object it has to protect is this interface's
        own channel and not the dispatch one.

        WHY NOT "ONLY IF IT IS CLOSED", which was the first shape this took. A daemon that goes away
        does not close anything -- a host process dying, or a socket dropped, is invisible to the
        device -- so "closed" describes almost none of the cases that matter, and the interface would
        stay locked for exactly the reason it needed unlocking.

        WHY IT IS SAFE THAT AN IDLE BOUND CHANNEL CAN BE DISPLACED. The pin is untouched by any of
        this: a newcomer still has to be the daemon this device bound before it can answer for the
        replica, so what an interloper gains is not the role but the interruption. And it gains
        nothing it did not already have -- a host that can open a channel here can hold the interface
        by being first. Meanwhile the last write is exactly the right thing to measure: a workflow
        parked in `service._rpc` has just written its request, so a genuine in-flight RPC is inside
        the window and protected, and a real daemon knocked off while idle simply reconnects.

        The buffers move across rather than being taken again: `wire.Provider` hands out its pool
        once, so a slot reclaimed through the provider would come back empty.
        """
        channel = self.active_channel
        if channel is None or channel.channel_id == channel_id:
            return

        last_write_ms = channel.get_last_write()
        if last_write_ms is not None and last_write_ms <= _PREEMPT_TIMEOUT_MS:
            # In use. The newcomer is told the interface is busy and retransmits; if the incumbent
            # really is gone, the next attempt is past the window and gets in.
            if __debug__:
                log.debug(
                    __name__,
                    f"keeping channel {hex(channel.channel_id)}, written {last_write_ms} ms ago; {hex(channel_id)} gets TRANSPORT_BUSY",
                    iface=self._iface,
                )
            return

        try:
            # BUILT BEFORE THE INCUMBENT IS RETIRED, so a newcomer that has already gone away costs
            # nothing: `Channel.__init__` refuses a closed id, and until it succeeds nothing here has
            # changed. It only keeps references to the buffers, so sharing them across these two
            # statements is safe.
            replacement = Channel(
                channel_id,
                self,
                buffers=(channel.receive_buf_src, channel.send_buf_src),
            )
        except trezorthp.ThpError:
            return

        # CLOSED, NOT MERELY FORGOTTEN, so a host that is still there finds out rather than holding
        # a channel nothing will ever answer for. `clear` also drops its sessions, which is what
        # `end_pairing_and_replace` does for a service reconnect and for the same reason: a session
        # that outlived its transport would keep a readiness it can no longer vouch for.
        channel.clear(trezorthp.ThpError("displaced on the service interface"))

        if __debug__:
            # A DAEMON RECONNECT AS THE DEVICE SEES IT. It is the one event on this interface that
            # destroys a channel without anything having gone wrong, and the binding it invalidates
            # is read much later, on the wallet channel -- so this is where the two are still next
            # to each other.
            log.info(
                __name__,
                f"displaced channel {hex(channel.channel_id)} with {hex(channel_id)}",
                iface=self._iface,
            )

        self.active_channel = replacement

        # A NEW CONVERSATION, so this interface listens again -- the released flag belonged to the
        # channel that has just gone.
        self._dispatch_released = False
        self._dispatch_box.put(None, replace=True)

    def read_packet_for_channel(self, result: int, packet_buffer: AnyBytes) -> None:
        channel_id = result & 0xFFFF
        buffer_size = (result >> 16) * 8

        if self._serves_own_dispatch:
            # Only here. The wire interface has the preemption path above and session migration
            # around it, and neither wants a second way to lose a channel.
            self._retire_displaced_channel(channel_id)

        if self.active_channel is None:
            if buffers := self._buffers_provider.take():
                self.active_channel = Channel(channel_id, self, buffers=buffers)
                if self._serves_own_dispatch:
                    self._dispatch_released = False
                    self._dispatch_box.put(None, replace=True)
                elif self.thp_ctx.dispatch_channel is None:
                    self.thp_ctx.dispatch_channel = self.active_channel
                    self.thp_ctx.channel_ready_box.put(None, replace=True)

        if self.active_channel is None or self.active_channel.channel_id != channel_id:
            preempted = self.thp_ctx.preempt_dispatch_channel_if_stale(
                self._iface.iface_num(), result, packet_buffer
            )
            if not preempted:
                trezorthp.send_transport_busy(channel_id)
                self.inactive_channels.add(channel_id)
                self.request_write()
            return

        try:
            self.active_channel.read_packet(packet_buffer, buffer_size)
        except Exception as exc:
            if __debug__:
                log.exception(__name__, exc)
            self.active_channel.kill(exc)
            self.active_channel = None
        self.clear_closed_sessions()

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
            try:
                yield from self.write_all_packets()
            except Timeout:
                if __debug__:
                    log.error(
                        __name__,
                        f"write blocked for {_WRITE_TIMEOUT_MS} ms",
                        iface=iface,
                    )
                if self.active_channel:
                    self.active_channel.kill(trezorthp.ThpError("Write is blocked"))
            self.clear_closed_sessions()
            self.recompute_timeouts()
            if __debug__ and _TRACE:
                log.debug(__name__, "write done", iface=iface)
            if self._write_loop_exit:
                break

    def write_all_packets(self) -> Generator[Any, Any, None]:
        packet_buffer = self._tx_packet_buf
        iface_num = self._iface.iface_num()
        # broadcast and channels doing handshake
        while trezorthp.packet_out(iface_num, packet_buffer):
            yield from self.write_packet(packet_buffer)
        # active channel
        if self.active_channel:
            while self.active_channel.write_packet(packet_buffer):
                yield from self.write_packet(packet_buffer)
        # transport_busy for currently inactive channels
        while self.inactive_channels:
            cid = self.inactive_channels.pop()
            while trezorthp.packet_out_channel(cid, EMPTY_BUFFER, packet_buffer):
                yield from self.write_packet(packet_buffer)
        self.inactive_channels.clear()

    def write_packet(self, packet_buffer: AnyBytes) -> Generator[Any, Any, None]:
        if __debug__ and _TRACE:
            log.debug(
                __name__,
                f"write: {utils.hexlify_if_bytes(packet_buffer)}",
                iface=self._iface,
            )
        n_written = 0
        while n_written == 0:
            yield self._write
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
                    ok = trezorthp.message_retransmit(channel_id)
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
                    else:
                        if __debug__:
                            log.error(
                                __name__,
                                "(cid: %04x) retransmission timeout",
                                channel_id,
                                iface=self._iface,
                            )
                        if (
                            self.active_channel
                            and self.active_channel.channel_id == channel_id
                        ):
                            self.active_channel.kill(
                                trezorthp.ThpError("Retransmission timeout")
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
            trezor_static_privkey = get_trezor_static_private_key()
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
            trezor_static_privkey = get_trezor_static_private_key()
        except Exception as e:
            if __debug__:
                log.exception(__name__, e)
            trezorthp.handshake_key(self._iface.iface_num(), None)
        else:
            trezorthp.handshake_key(self._iface.iface_num(), trezor_static_privkey)
        finally:
            self.request_write()
            self._handshake_key_task = None

    def verify_credential(self, host_static_public_key: bytes, payload: bytes) -> int:
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
        if not trezorthp.channel_was_closed():
            return
        clear_sessions_without_channel()
