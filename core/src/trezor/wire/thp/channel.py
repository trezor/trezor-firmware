from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from storage.cache_thp import clear_sessions_with_channel_id, migrate_sessions
from trezor import loop, protobuf, utils, workflow

from apps.thp.credential_manager import decode_credential, unwrap_credential

from ..protocol_common import Message
from . import ChannelState, ThpError, memory_manager

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes
    from typing import Any

    from trezor.messages import ThpPairingCredential
    from trezor.wire import WireInterface

    from .interface_context import InterfaceContext
    from .memory_manager import ThpBuffer
    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


_TRACE = const(False)

TREZOR_STATE_UNPAIRED = const(0x00)
TREZOR_STATE_PAIRED = const(0x01)
TREZOR_STATE_PAIRED_AUTOCONNECT = const(0x02)

EMPTY_BUFFER = bytearray()


class Channel:
    """
    THP protocol encrypted communication channel.
    """

    def __init__(
        self,
        channel_id: int,
        iface_ctx: InterfaceContext,
        buffers: tuple[ThpBuffer, ThpBuffer],
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
        self.send_buffer: AnyBuffer | None = None
        # Current receive buffer, or None if not receiving a message
        self.receive_buffer: AnyBuffer | None = None

        self._info = trezorthp.channel_info(iface_ctx._iface.iface_num(), channel_id)
        self.state = {
            TREZOR_STATE_UNPAIRED: ChannelState.TP0,
            TREZOR_STATE_PAIRED: ChannelState.TC1,
            TREZOR_STATE_PAIRED_AUTOCONNECT: ChannelState.TC1,
            None: ChannelState.ENCRYPTED_TRANSPORT,
        }.get(self._info.pairing_state)

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
        except Exception as e:
            if __debug__:
                self._log(f"cannot parse credential: {e}")

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
        trezorthp.channel_close(self.iface.iface_num(), self.channel_id)
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

    # ACCESS TO CHANNEL_DATA

    def get_handshake_hash(self) -> bytes:
        assert self._info.handshake_hash is not None
        return self._info.handshake_hash

    def get_host_static_public_key(self) -> bytes:
        assert self._info.host_static_public_key is not None
        return self._info.host_static_public_key

    def get_last_write(self) -> int | None:
        """
        Return milliseconds since last write (or retransmission request).
        """
        try:
            info = trezorthp.channel_info(self.iface.iface_num(), self.channel_id)
            return info.last_write
        except IndexError:
            return None

    def get_channel_state(self) -> int:
        assert isinstance(self.state, int)
        return self.state

    def set_channel_state(self, state: ChannelState) -> None:
        if __debug__:
            self._log(f"set state {state}")
        self.state = state

    def is_channel_to_replace(self) -> bool:
        return self._info.pairing_state == TREZOR_STATE_PAIRED_AUTOCONNECT

    def end_pairing_and_replace(self) -> None:
        replaced_channel_id = trezorthp.channel_paired(
            self.iface.iface_num(), self.channel_id
        )
        if replaced_channel_id is not None:
            migrate_sessions(
                replaced_channel_id.to_bytes(2, "big"), self.channel_id_bytes()
            )
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
            session_id, message_type, message_bytes_len = trezorthp.message_out(
                self.iface.iface_num(), self.channel_id, self.receive_buffer
            )
        except Exception:
            self.expecting_message = False
            raise
        finally:
            # wake up write loop to send ACKs or DECRYPTION_FAILED
            self.iface_ctx.request_write()
        if __debug__ and _TRACE:
            self._log("message is ready")
        message = Message(
            message_type,
            self.receive_buffer[3 : message_bytes_len + 3],
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
        buffer_size = memory_manager.buffer_size(msg)
        self.send_buffer = self.send_buf_src.get(buffer_size)
        if self.send_buffer is None:
            self.send_buffer = bytearray(buffer_size)
        noise_payload_len = memory_manager.encode_into_buffer(
            self.send_buffer, msg, session_id
        )
        trezorthp.message_in(
            self.iface.iface_num(), self.channel_id, noise_payload_len, self.send_buffer
        )
        self.iface_ctx.request_write()

        try:
            # Might raise Timeout or ChannelPreemptedException.
            await self.ack_box
        finally:
            self.send_buffer = None

    def read_packet(self, packet_buffer: AnyBytes, buffer_size: int) -> None:
        """
        Called by read_loop() to process incoming packet.
        """
        iface_num = self.iface.iface_num()
        if self.receive_buffer is None or buffer_size > 0:
            self.receive_buffer = self.receive_buf_src.get(buffer_size)
        result = trezorthp.packet_in_channel(
            iface_num, self.channel_id, packet_buffer, self.receive_buffer
        )
        if __debug__ and _TRACE and result is not None:
            self._log(f"packet_in: {result}")
        if result is trezorthp.ACK or result is trezorthp.MESSAGE_READY_ACK:
            self.ack_box.put(None, replace=True)
            self.expecting_ack = False
            self.iface_ctx.recompute_timeouts()
        if result is trezorthp.MESSAGE_READY or result is trezorthp.MESSAGE_READY_ACK:
            self.incoming_box.put(None, replace=True)
            self.expecting_message = False
        elif result == trezorthp.FAILED:
            # channel is closed now
            self.kill(ThpError("Channel failed"))

    def write_packet(self, packet: AnyBuffer) -> bool:
        """
        Called by write_loop() to send outgoing packets.
        """
        try:
            # If not sending application message, provide empty buffer for ACK.
            buffer = self.send_buffer or EMPTY_BUFFER
            res = trezorthp.packet_out(
                self.iface.iface_num(), self.channel_id, buffer, packet
            )
            if self.send_buffer:
                self.expecting_ack = True
                self.iface_ctx.request_read()
            return res
        except Exception as e:
            if __debug__:
                log.exception(__name__, e)
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
