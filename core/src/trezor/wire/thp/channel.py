from micropython import const
from typing import TYPE_CHECKING

import trezorthp
from storage.cache_thp import clear_sessions_with_channel_id, migrate_sessions
from trezor import loop, protobuf, utils, workflow
from trezor.loop import Timeout, sleep
from trezor.wire.context import UnexpectedMessageException

from ..protocol_common import Message
from . import ChannelState, ThpError, memory_manager

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBuffer
    from typing import Any

    from trezor.messages import ThpPairingCredential
    from trezor.wire import WireInterface

    from .interface_context import InterfaceContext
    from .memory_manager import ThpBuffer
    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


_MAX_RETRANSMISSION_COUNT = const(50)
_MIN_RETRANSMISSION_COUNT = const(2)

# Stop retransmission if writes are blocked - e.g. due to USB flow control.
# It allows restarting the event loop to handle other THP channels.
_WRITE_TIMEOUT_MS = const(5_000)
_WRITE_TIMEOUT = sleep(_WRITE_TIMEOUT_MS)

# Preempt a stale channel if another channel becomes active and we allowed enough time for the host to respond.
# It allows interrupting a "stuck" THP workflow using a different channel on the same interface.
_PREEMPT_TIMEOUT_MS = const(1_000)

TREZOR_STATE_UNPAIRED = const(0x00)
TREZOR_STATE_PAIRED = const(0x01)
TREZOR_STATE_PAIRED_AUTOCONNECT = const(0x02)


class ChannelPreemptedException(UnexpectedMessageException):
    """Raising this exception should restart the event loop."""

    def __init__(self) -> None:
        super().__init__(msg=None)


class Channel:
    """
    THP protocol encrypted communication channel.
    """

    def __init__(
        self,
        channel_id: int,
        iface_ctx: InterfaceContext,
        buffers: tuple[ThpBuffer, ThpBuffer],
        credential: ThpPairingCredential | None = None,
    ) -> None:
        # Channel properties
        self.channel_id = channel_id
        self.iface_ctx: InterfaceContext = iface_ctx
        self.read_buf, self.write_buf = buffers

        # used by read loop to wake up context.read
        self.incoming_box: loop.mailbox[None] = loop.mailbox()
        # used by read loop to wake up context.write
        self.ack_box: loop.mailbox[None | Timeout] = loop.mailbox()

        self.send_buffer = None
        self.receive_buffer = None

        info = trezorthp.channel_info(iface_ctx._iface.iface_num(), channel_id)
        self.state = {
            TREZOR_STATE_UNPAIRED: ChannelState.TP0,
            TREZOR_STATE_PAIRED: ChannelState.TC1,
            TREZOR_STATE_PAIRED_AUTOCONNECT: ChannelState.TC1,
            None: ChannelState.ENCRYPTED_TRANSPORT,
        }.get(info.pairing_state)
        self.is_channel_to_replace = (
            info.pairing_state == TREZOR_STATE_PAIRED_AUTOCONNECT
        )

        # Shared variables
        self.sessions: dict[int, GenericSessionContext] = {}

        # Temporary objects
        self.credential: ThpPairingCredential | None = credential
        self.connection_context: PairingContext | None = None

    def channel_id_bytes(self) -> bytes:
        return self.channel_id.to_bytes(2, "big")

    @property
    def iface(self) -> WireInterface:
        return self.iface_ctx._iface

    def clear(self) -> None:
        clear_sessions_with_channel_id(self.channel_id_bytes())
        trezorthp.channel_close(self.iface.iface_num(), self.channel_id)

    # ACCESS TO CHANNEL_DATA

    def get_channel_state(self) -> int:
        assert isinstance(self.state, int)
        return self.state

    def get_handshake_hash(self) -> bytes:
        info = trezorthp.channel_info(self.iface.iface_num(), self.channel_id)
        assert info.handshake_hash is not None
        return info.handshake_hash

    def get_host_static_public_key(self) -> bytes:
        info = trezorthp.channel_info(self.iface.iface_num(), self.channel_id)
        assert info.host_static_public_key is not None
        return info.host_static_public_key

    def set_channel_state(self, state: ChannelState) -> None:
        self._log(f"set state {state}")
        self.state = state

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
        if __debug__:
            self._log(
                "Was any channel replaced? ", str(replaced_channel_id is not None)
            )

    async def read(self) -> tuple[int, Message]:
        """
        Receive, decrypt and return a `(session_id, message)` tuple.
        """
        await self.incoming_box
        assert self.receive_buffer is not None
        try:
            session_id, message_type, message_bytes_len = trezorthp.message_out(
                self.iface.iface_num(), self.channel_id, self.receive_buffer
            )
        finally:
            # wake up write loop to send ACKs or DECRYPTION_FAILED
            self.iface_ctx.request_write()
        self._log("message is ready")
        message = Message(
            message_type,
            self.receive_buffer[3:][:message_bytes_len],
        )
        self.receive_buffer = None
        return (session_id, message)

    async def write(
        self,
        msg: protobuf.MessageType,
        session_id: int = 0,
    ) -> None:
        if __debug__:
            self._log(
                f"write message: {msg.MESSAGE_NAME}",
                logger=log.info,
            )
            if utils.EMULATOR:
                log.debug(
                    __name__,
                    "message contents:\n%s",
                    utils.dump_protobuf(msg),
                    iface=self.iface,
                )

        self.send_buffer = self.write_buf.get(memory_manager.buffer_size(msg))
        noise_payload_len = memory_manager.encode_into_buffer(
            self.send_buffer, msg, session_id
        )
        trezorthp.message_in(
            self.iface.iface_num(), self.channel_id, noise_payload_len, self.send_buffer
        )

        self.iface_ctx.request_write()
        # self.iface_ctx.recompute_timeouts()

        try:
            await self.ack_box
        except Timeout:
            if __debug__:
                self._log("Exceeded retransmission limit")
            self.clear()
            raise Timeout("THP retransmission timeout")
        finally:
            self.send_buffer = None

    def read_packet(self, packet_buffer: AnyBuffer) -> None:
        iface_num = self.iface.iface_num()
        if self.receive_buffer is None:
            self.receive_buffer = self.read_buf.get(8192)
        result = trezorthp.packet_in_channel(
            iface_num, self.channel_id, packet_buffer, self.receive_buffer
        )
        self._log(f"packet_in: {result}")
        if result == trezorthp.MESSAGE_READY:
            self.incoming_box.put(None)
        elif result == trezorthp.ACK:
            self.ack_box.put(None)
            self.iface_ctx.recompute_timeouts()
        elif result == trezorthp.FAILED:
            self.clear()
            raise ThpError

    def write_packet(self, packet: AnyBuffer) -> bool:
        buffer = self.send_buffer or bytearray()
        return trezorthp.packet_out(
            self.iface.iface_num(), self.channel_id, buffer, packet
        )

    if __debug__:

        def _log(self, text_1: str, text_2: str = "", logger: Any = log.debug) -> None:
            logger(
                __name__,
                "(cid: %s) %s%s",
                hex(self.channel_id)[2:],
                text_1,
                text_2,
                iface=self.iface,
            )
