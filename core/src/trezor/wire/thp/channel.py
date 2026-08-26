from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from storage.cache_thp import clear_sessions_with_channel_id, migrate_sessions
from trezor import loop, protobuf, utils, workflow

from apps.thp.credential_manager import decode_credential, unwrap_credential

from ..errors import DataError, FirmwareError
from ..protocol_common import Message
from . import ChannelState, memory_manager

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes
    from typing import Any

    from trezor.messages import ThpPairingCredential
    from trezor.wire import WireInterface

    from .interface_context import InterfaceContext
    from ..buffers import BufferSource
    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


_TRACE = const(False)

TREZOR_STATE_UNPAIRED = const(0x00)
TREZOR_STATE_PAIRED = const(0x01)
TREZOR_STATE_PAIRED_AUTOCONNECT = const(0x02)

EMPTY_BUFFER = memoryview(b"")


class Channel:
    """
    THP protocol encrypted communication channel.
    """

    def __init__(
        self,
        channel_id: int,
        iface_ctx: InterfaceContext,
        buffers: tuple[BufferSource, BufferSource],
    ) -> None:
        # Channel properties
        self.channel_id = channel_id
        self.iface_ctx: InterfaceContext = iface_ctx
        self.receive_buf_src, self.send_buf_src = buffers

        # Used by read loop to wake up context.read()
        self.incoming_box: loop.mailbox[None | Exception] = loop.mailbox()
        # Used by read loop to wake up context.write()
        self.ack_box: loop.mailbox[None | Exception] = loop.mailbox()

        # Conditions used to pause read_loop
        self.expecting_message = False
        self.expecting_ack = False

        # Current send buffer, or None if not sending a message
        self.send_buffer: memoryview | None = None
        # Current receive buffer, or None if not receiving a message
        self.receive_buffer: memoryview | None = None

        self._info = trezorthp.channel_info(channel_id)

        # A CHANNEL BELONGS TO ONE INTERFACE, and this refuses to build one that disagrees.
        #
        # Not defensive tidiness: `trezorthp.packet_out_channel` looks a channel up by id alone --
        # the lookup is global across interfaces and the binding is discarded -- and fragments into
        # a buffer that `write_all_packets` then writes to whichever interface OWNS THIS OBJECT. So
        # a channel paired with the wrong `InterfaceContext` puts one host's encrypted traffic on
        # another host's wire, and every layer below here would consider that well-formed.
        #
        # Checked in the constructor so the invariant holds for every channel however it was made,
        # rather than only where a caller remembered to look. NOT an assert: those are stripped
        # under `pyopt`, which is exactly the build where this matters.
        if self._info.iface_num != iface_ctx._iface.iface_num():
            raise FirmwareError("THP channel does not belong to this interface")

        self.state = {
            TREZOR_STATE_UNPAIRED: ChannelState.TP0,
            TREZOR_STATE_PAIRED: ChannelState.TC1,
            TREZOR_STATE_PAIRED_AUTOCONNECT: ChannelState.TC1,
            None: ChannelState.ENCRYPTED_TRANSPORT,
        }[self._info.pairing_state]

        # Shared variables
        self.sessions: dict[int, GenericSessionContext] = {}

        # Temporary objects
        self.connection_context: PairingContext | None = None
        self.credential: ThpPairingCredential | None = None
        try:
            if self._info.credential and (
                inner := unwrap_credential(self._info.credential)
            ):
                self.credential = decode_credential(inner)
        except DataError as exc:
            if __debug__:
                log.exception(__name__, exc, iface=self.iface)

    def channel_id_bytes(self) -> bytes:
        return self.channel_id.to_bytes(2, "big")

    @property
    def iface(self) -> WireInterface:
        return self.iface_ctx._iface

    def clear(self, exc: Exception | None = None) -> None:
        """
        Close a channel, delete associated sessions, optionally kill task.
        """
        if __debug__:
            self._log("closing channel")
        clear_sessions_with_channel_id(self.channel_id_bytes())
        trezorthp.channel_close(self.channel_id)
        self.release_buffers()
        if exc is not None:
            self.kill(exc)

    def kill(self, exc: Exception) -> None:
        """
        Inject an exception into task waiting on read()/write().
        """
        if __debug__:
            self._log(f"killing task (exception: {exc.__class__.__name__})")
        self.expecting_message = False
        self.expecting_ack = False
        self.incoming_box.put(exc, replace=True)
        self.ack_box.put(exc, replace=True)
        self.release_buffers()

    def release_buffers(self) -> None:
        """Give back any shared buffer this channel's in-flight message was holding.

        THE ONE LEAK PATH WITH NO OTHER OWNER. Every ordinary release happens where the message
        ends -- after the ACK for a send, after the decode for a receive -- but a channel that is
        torn down mid-message never reaches either, and the shared buffer would then be stranded
        for the rest of the session with nothing to hand it back.

        Safe to call on a channel holding nothing, and safe when another channel has since taken
        the buffer: a source only ever releases a lease it actually holds.
        """
        self.receive_buffer = None
        self.send_buffer = None
        self.receive_buf_src.release()
        self.send_buf_src.release()

    # ACCESS TO CHANNEL_DATA

    def get_handshake_hash(self) -> bytes:
        assert self._info.handshake_hash is not None
        return self._info.handshake_hash

    def get_host_static_public_key(self) -> bytes:
        assert self._info.host_static_public_key is not None
        return self._info.host_static_public_key

    def get_last_write(self) -> int | None:
        """
        Return milliseconds since channel started sending last message.
        """
        try:
            info = trezorthp.channel_info(self.channel_id)
            return info.last_write
        except IndexError:
            return None

    def get_channel_state(self) -> int:
        return self.state

    def set_channel_state(self, state: ChannelState) -> None:
        if __debug__:
            self._log(f"set state {state}")
        self.state = state

    def is_autoconnected(self) -> bool:
        return self._info.pairing_state == TREZOR_STATE_PAIRED_AUTOCONNECT

    def end_pairing_and_replace(self) -> None:
        replaced_channel_id = trezorthp.channel_paired(self.channel_id)
        if replaced_channel_id is not None:
            from .. import is_ward_interface

            replaced_cid = replaced_channel_id.to_bytes(2, "big")

            if utils.USE_WARD_SERVICE_THP and is_ward_interface(self.iface):
                # A SERVICE RECONNECT, NOT A HOST TAKING OVER, and the two need opposite handling.
                #
                # Do not close other workflows. Replacement fires whenever a host reconnects with
                # the same static key, which for a daemon holding a persistent identity is an
                # ordinary restart. The workflows running at that moment belong to a WALLET host on
                # a different interface and have nothing to do with this channel; killing them
                # would let a service restart cancel a signing flow, which is most of the reason
                # the service has an interface of its own.
                #
                # Do not migrate the sessions either. `migrate_sessions` only repoints CHANNEL_ID,
                # so a migrated service session would keep its readiness state while the transport
                # under it has been replaced -- a service claiming to be synced across a
                # reconnection it cannot vouch for. Clearing it means the new channel starts by
                # proving freshness again, which is the correct reading of "the transport changed".
                clear_sessions_with_channel_id(replaced_cid)
            else:
                migrate_sessions(replaced_cid, self.channel_id_bytes())
                # In case a channel was replaced, close all running workflows
                workflow.close_others()
        self.credential = None
        if __debug__ and _TRACE:
            self._log(
                "Was any channel replaced? ", str(replaced_channel_id is not None)
            )

    async def read(self) -> tuple[int, Message]:
        """
        Wait for reassembled message, decrypt it, and return a `(session_id, message)` tuple.
        """
        self.expecting_message = True
        self.iface_ctx.request_read()
        await self.incoming_box
        assert self.receive_buffer is not None
        try:
            session_id, message_type, message_bytes = trezorthp.message_out(
                self.channel_id, self.receive_buffer
            )
        except Exception:
            self.expecting_message = False
            raise
        finally:
            # wake up write loop to send ACKs or DECRYPTION_FAILED
            self.iface_ctx.request_write()
        if __debug__ and _TRACE:
            self._log("message is ready")
        # THE LEASE GOES WITH THE MESSAGE, not with this call. `message_bytes` is a view into the
        # receive buffer rather than a copy, so the buffer is still being read after we return --
        # by whoever decodes the protobuf, which is the last consumer and therefore the one that
        # releases it.
        message = Message(
            message_type,
            message_bytes,
            self.receive_buf_src,
        )
        self.receive_buffer = None
        return (session_id, message)

    async def write(
        self,
        msg: protobuf.MessageType,
        session_id: int = 0,
    ) -> None:
        """
        Encrypt a message, wait until it is send, wait until ACK is received.
        """
        if __debug__:
            self._log(
                f"write message: {msg.MESSAGE_NAME}",
                logger=log.info,
            )
            if utils.EMULATOR and _TRACE:
                log.debug(
                    __name__,
                    "message contents:\n%s",
                    utils.dump_protobuf(msg),
                    iface=self.iface,
                )

        self.expecting_message = False

        try:
            buffer_size = memory_manager.buffer_size(msg)
            # WAITS RATHER THAN FAILS if the shared buffer is busy. By the time we are here the
            # device has decided to send this message, so refusing would turn another channel's
            # large message into this host's Failure. There is no timeout of our own: this whole
            # call is already under the interface's write timeout, and a second one would decide
            # the same thing twice, further from where it can be reported.
            self.send_buffer = await self.send_buf_src.get_when_available(buffer_size)
            noise_payload_len = memory_manager.encode_into_buffer(
                self.send_buffer, msg, session_id
            )
            trezorthp.message_in(self.channel_id, noise_payload_len, self.send_buffer)
            self.iface_ctx.request_write()
            # Might raise Timeout or ChannelPreemptedException.
            await self.ack_box
        finally:
            # HELD UNTIL THE ACK, not until the last packet goes out. `message_retransmit` only
            # resets the fragmenter and re-reads the ciphertext still sitting here, so releasing
            # any earlier would let another channel overwrite a message we may have to resend.
            self.send_buffer = None
            self.send_buf_src.release()

    def read_packet(self, packet_buffer: AnyBytes, buffer_hint: int) -> bool:
        """
        Called by read_loop() to process incoming packet.

        Returns False when this packet needs a buffer another channel currently holds. The caller
        answers TRANSPORT_BUSY and the host retransmits -- nothing has been handed to the THP state
        machine yet, so the packet is simply as though it had not arrived. Only ever the first
        packet of a message: a continuation reuses the buffer the message already has.
        """
        if self.receive_buffer is None or buffer_hint > len(self.receive_buffer):
            receive_buffer = self.receive_buf_src.try_get(buffer_hint)
            if receive_buffer is None:
                if __debug__:
                    self._log(
                        f"no shared buffer for a {buffer_hint} byte message; reporting busy",
                        logger=log.warning,
                    )
                return False
            self.receive_buffer = receive_buffer
        result = trezorthp.packet_in_channel(
            self.channel_id, packet_buffer, self.receive_buffer
        )
        if __debug__ and _TRACE and result is not None:
            self._log(f"packet_in: {result}")
        if result is trezorthp.ACK or result is trezorthp.MESSAGE_READY_ACK:
            assert self.expecting_ack
            self.ack_box.put(None, replace=True)
            self.expecting_ack = False
            self.iface_ctx.recompute_timeouts()
        if result is trezorthp.MESSAGE_READY or result is trezorthp.MESSAGE_READY_ACK:
            self.incoming_box.put(None, replace=True)
            self.expecting_message = False
        elif result == trezorthp.FAILED:
            # channel is closed now
            self.kill(trezorthp.ThpError("Channel failed"))
        return True

    def write_packet(self, packet: AnyBuffer) -> bool:
        """
        Called by write_loop() to send outgoing packets.
        """
        try:
            # If not sending application message, provide empty buffer for ACK.
            buffer = self.send_buffer or EMPTY_BUFFER
            res = trezorthp.packet_out_channel(self.channel_id, buffer, packet)
            if self.send_buffer:
                self.expecting_ack = True
                self.iface_ctx.request_read()
            return res
        except Exception as e:
            if __debug__:
                log.exception(__name__, e, iface=self.iface)
            self.kill(e)
            return False

    if __debug__:

        def _log(self, text_1: str, text_2: str = "", logger: Any = log.debug) -> None:
            logger(
                __name__,
                "(cid: %04x) %s%s",
                self.channel_id,
                text_1,
                text_2,
                iface=self.iface,
            )
