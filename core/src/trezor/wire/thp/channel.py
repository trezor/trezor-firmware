import ustruct
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_HOST_STATIC_PUBKEY,
    CHANNEL_IFACE,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
    CHANNEL_STATE,
)
from storage.cache_thp import (
    SESSION_ID_LENGTH,
    TAG_LENGTH,
    ChannelCache,
    clear_sessions_with_channel_id,
    conditionally_replace_channel,
    is_there_a_channel_to_replace,
)
from trezor import protobuf, utils, workflow
from trezor.loop import Timeout

from ..protocol_common import Message
from . import (
    ACK_MESSAGE,
    ENCRYPTED,
    ChannelState,
    PacketHeader,
    ThpDecryptionError,
    ThpError,
)
from . import alternating_bit_protocol as ABP
from . import control_byte, crypto, memory_manager
from .checksum import CHECKSUM_LENGTH, is_valid
from .writer import MESSAGE_TYPE_LENGTH

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

    from . import state_to_str

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable

    from trezor.messages import ThpPairingCredential
    from trezor.wire import WireInterface

    from .interface_context import ThpContext
    from .memory_manager import ThpBuffer
    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


_MAX_RETRANSMISSION_COUNT = const(50)
_MIN_RETRANSMISSION_COUNT = const(2)


class Reassembler:
    def __init__(self, cid: int, read_buf: ThpBuffer) -> None:
        self.cid = cid
        self.thp_read_buf = read_buf
        self.reset()

    def reset(self) -> None:
        self.bytes_read: int = 0
        self.buffer_len: int = 0
        self.message: memoryview | None = None

    def handle_packet(self, packet: memoryview) -> bool:
        """
        Process current packet, returning `True` when a valid message is reassembled.
        The parsed message can retrieved via the `message` field (if it's not `None`).
        In case of a checksum error or if the reassembly is not over, return `False`.
        """
        ctrl_byte = packet[0]
        if control_byte.is_continuation(ctrl_byte):
            if not self.bytes_read:
                # ignore unexpected continuation packets
                return False

            buffer = self.thp_read_buf.get(self.buffer_len)
            self._buffer_packet_data(buffer, packet, PacketHeader.CONT_LENGTH)
        else:
            self.reset()
            _, _, payload_length = ustruct.unpack(PacketHeader.INIT_FORMAT, packet)
            self.buffer_len = payload_length + PacketHeader.INIT_LENGTH

            if control_byte.is_ack(ctrl_byte):
                # don't allocate buffer for ACKs (since they are small)
                buffer = packet[: self.buffer_len]
                self.bytes_read = len(buffer)
            else:
                buffer = self.thp_read_buf.get(self.buffer_len)
                self._buffer_packet_data(buffer, packet, 0)

        assert len(buffer) == self.buffer_len
        if self.bytes_read < self.buffer_len:
            return False

        if self.bytes_read > self.buffer_len:
            raise ThpError("read more bytes than expected")

        if not verify_checksum(buffer):
            return False

        assert self.message is None
        self.message = buffer
        return True

    def _buffer_packet_data(
        self, payload_buffer: memoryview, packet: memoryview, offset: int
    ) -> None:
        self.bytes_read += utils.memcpy(payload_buffer, self.bytes_read, packet, offset)


def verify_checksum(buffer: memoryview) -> memoryview | None:
    """
    Return the buffer if the checksum is valid, otherwise return `None`.
    """
    if is_valid(buffer[-CHECKSUM_LENGTH:], buffer[:-CHECKSUM_LENGTH]):
        return buffer
    # ignore invalid payloads
    if __debug__:
        log.warning("Invalid payload checksum: %s", utils.hexlify_if_bytes(buffer))
    return None


class Channel:
    """
    THP protocol encrypted communication channel.
    """

    def __init__(
        self,
        channel_cache: ChannelCache,
        ctx: ThpContext,
        buffers: tuple[ThpBuffer, ThpBuffer],
    ) -> None:
        assert ctx._iface.iface_num() == channel_cache.get_int(CHANNEL_IFACE)

        # Channel properties
        self.channel_id: bytes = channel_cache.channel_id
        self.ctx: ThpContext = ctx
        self.read_buf, self.write_buf = buffers
        if __debug__:
            self._log("channel initialization")
        self.channel_cache: ChannelCache = channel_cache

        # Shared variables
        self.sessions: dict[int, GenericSessionContext] = {}
        self.reassembler = Reassembler(self.get_channel_id_int(), self.read_buf)

        # Temporary objects
        self.credential: ThpPairingCredential | None = None
        self.connection_context: PairingContext | None = None

        if __debug__:
            self.should_show_pairing_dialog: bool = True

    @property
    def iface(self) -> WireInterface:
        return self.ctx._iface

    def clear(self) -> None:
        clear_sessions_with_channel_id(self.channel_id)
        self.channel_cache.clear()

    # ACCESS TO CHANNEL_DATA

    def get_channel_id_int(self) -> int:
        return int.from_bytes(self.channel_id, "big")

    def get_channel_state(self) -> int:
        state = self.channel_cache.get_int(
            CHANNEL_STATE, default=ChannelState.UNALLOCATED
        )
        assert isinstance(state, int)
        if __debug__:
            self._log("get_channel_state: ", state_to_str(state))
        return state

    def get_handshake_hash(self) -> bytes:
        h = self.channel_cache.get(CHANNEL_HANDSHAKE_HASH)
        assert h is not None
        return h

    def set_channel_state(self, state: ChannelState) -> None:
        self.channel_cache.set_int(CHANNEL_STATE, state)
        if __debug__:
            self._log("set_channel_state: ", state_to_str(state))

    def replace_old_channels_with_the_same_host_public_key(self) -> None:
        was_any_replaced = conditionally_replace_channel(
            new_channel=self.channel_cache,
            required_state=ChannelState.ENCRYPTED_TRANSPORT,
            required_key=CHANNEL_HOST_STATIC_PUBKEY,
        )
        if was_any_replaced:
            # In case a channel was replaced, close all running workflows
            workflow.close_others()
        if __debug__:
            self._log("Was any channel replaced? ", str(was_any_replaced))

    def is_channel_to_replace(self) -> bool:
        return is_there_a_channel_to_replace(
            new_channel=self.channel_cache,
            required_state=ChannelState.ENCRYPTED_TRANSPORT,
            required_key=CHANNEL_HOST_STATIC_PUBKEY,
        )

    # READ and DECRYPT

    async def recv_payload(
        self,
        expected_ctrl_byte: Callable[[int], bool] | None,
        timeout_ms: int | None = None,
    ) -> memoryview:
        """
        Receive and return a valid THP payload from this channel & its control byte.
        Also handle ACKs while waiting for the payload.

        Raise if the received control byte is an unexpected one.

        If `expected_ctrl_byte` is `None`, returns after the first received ACK.
        """

        while True:
            # Handle an existing message (if already reassembled).
            # Otherwise, receive and reassemble a new one.
            msg = await self._get_reassembled_message(timeout_ms=timeout_ms)

            # Synchronization process
            ctrl_byte = msg[0]
            payload = msg[PacketHeader.INIT_LENGTH : -CHECKSUM_LENGTH]
            seq_bit = control_byte.get_seq_bit(ctrl_byte)

            # 1: Handle ACKs
            if control_byte.is_ack(ctrl_byte):
                handle_ack(self, control_byte.get_ack_bit(ctrl_byte))
                if expected_ctrl_byte is None:
                    return payload
                continue

            if expected_ctrl_byte is None or not expected_ctrl_byte(ctrl_byte):
                if __debug__:
                    self._log("Unexpected control byte: ", utils.hexlify_if_bytes(msg))
                raise ThpError("Unexpected control byte")

            # 2: Handle message with unexpected sequential bit
            if seq_bit != ABP.get_expected_receive_seq_bit(self.channel_cache):
                if __debug__:
                    self._log(
                        "Received message with an unexpected sequential bit",
                    )
                await send_ack(self, ack_bit=seq_bit)
                raise ThpError("Received message with an unexpected sequential bit")

            # 3: Send ACK in response
            await send_ack(self, ack_bit=seq_bit)

            ABP.set_expected_receive_seq_bit(self.channel_cache, 1 - seq_bit)

            return payload

    async def _get_reassembled_message(
        self, timeout_ms: int | None = None
    ) -> memoryview:
        """Doesn't block if a message has been already reassembled."""
        while self.reassembler.message is None:
            # receive and reassemble a new message from this channel
            channel = await self.ctx.get_next_message(timeout_ms=timeout_ms)
            if channel is self:
                break

            # currently only single-channel sessions are supported during a single event loop run
            self._log(
                "Ignoring unexpected channel: ",
                utils.hexlify_if_bytes(channel.channel_id),
                logger=log.warning,
            )

        msg = self.reassembler.message
        self.reassembler.reset()  # next call will reassemble a new message
        assert msg is not None
        return msg

    def reassemble(self, packet: utils.BufferType) -> bool:
        """
        Process current packet, returning `True` when a valid message is reassembled.
        The parsed message can retrieved via the `message` field (if it's not `None`).
        In case of a checksum error or if the reassembly is not over, return `False`.
        """
        if self.get_channel_state() == ChannelState.UNALLOCATED:
            return False
        return self.reassembler.handle_packet(memoryview(packet))

    async def decrypt_message(self) -> tuple[int, Message]:
        """
        Receive, decrypt and return a `(session_id, message)` tuple.
        Also handle ACKs while waiting for the message.
        """
        payload = await self.recv_payload(control_byte.is_encrypted_transport)
        self._decrypt_buffer(payload)
        session_id, message_type = ustruct.unpack(">BH", payload)
        message = Message(
            message_type,
            payload[SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH : -TAG_LENGTH],
        )
        return (session_id, message)

    def _decrypt_buffer(self, payload: memoryview) -> None:
        noise_buffer = payload[:-TAG_LENGTH]
        tag = payload[-TAG_LENGTH:]

        key_receive = self.channel_cache.get(CHANNEL_KEY_RECEIVE)
        nonce_receive = self.channel_cache.get_int(CHANNEL_NONCE_RECEIVE)

        assert key_receive is not None
        assert nonce_receive is not None

        if __debug__:
            self._log("Buffer before decryption: ", hexlify_if_bytes(noise_buffer))

        is_tag_valid = crypto.dec(noise_buffer, tag, key_receive, nonce_receive)
        if __debug__:
            self._log("Buffer after decryption: ", hexlify_if_bytes(noise_buffer))

        self.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, nonce_receive + 1)

        if __debug__:
            self._log("Is decrypted tag valid? ", str(is_tag_valid))
            self._log("Received tag: ", hexlify_if_bytes(tag))
            self._log("New nonce_receive: ", str((nonce_receive + 1)))

        if not is_tag_valid:
            raise ThpDecryptionError()

    # WRITE and ENCRYPT

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

        msg_size = protobuf.encoded_length(msg)
        payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size
        length = payload_size + CHECKSUM_LENGTH + TAG_LENGTH + PacketHeader.INIT_LENGTH

        buffer = self.write_buf.get(length)
        noise_payload_len = memory_manager.encode_into_buffer(buffer, msg, session_id)

        self._encrypt(buffer, noise_payload_len)
        payload_length = noise_payload_len + TAG_LENGTH

        return await self.write_encrypted_payload(ENCRYPTED, buffer[:payload_length])

    def write_handshake_message(
        self, ctrl_byte: int, payload: bytes
    ) -> Awaitable[None]:
        return self.write_encrypted_payload(ctrl_byte, payload)

    async def write_encrypted_payload(self, ctrl_byte: int, payload: bytes) -> None:
        if __debug__:
            self._log("write_encrypted_payload_loop")

        assert ABP.is_sending_allowed(self.channel_cache)

        payload_len = len(payload) + CHECKSUM_LENGTH
        sync_bit = ABP.get_send_seq_bit(self.channel_cache)
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(ctrl_byte, sync_bit)
        header = PacketHeader(ctrl_byte, self.get_channel_id_int(), payload_len)

        # ACK is needed before sending more data
        ABP.set_sending_allowed(self.channel_cache, False)

        for i in range(_MAX_RETRANSMISSION_COUNT):
            await self.ctx.write_payload(header, payload)
            # starting from 100ms till ~3.42s
            timeout_ms = round(10200 - 1010000 / (100 + i))
            try:
                # wait and return after receiving an ACK, or raise in case of an unexpected message.
                await self.recv_payload(expected_ctrl_byte=None, timeout_ms=timeout_ms)
            except Timeout:
                if __debug__:
                    log.warning(__name__, "Retransmit after %d ms", timeout_ms)
                continue
            # `ABP.set_sending_allowed()` will be called after a valid ACK
            if ABP.is_sending_allowed(self.channel_cache):
                ABP.set_send_seq_bit_to_opposite(self.channel_cache)
                return

        raise ThpError("Retransmission timeout")

    def _encrypt(self, buffer: utils.BufferType, noise_payload_len: int) -> None:
        if __debug__:
            self._log("encrypt")

        assert len(buffer) >= noise_payload_len + TAG_LENGTH + CHECKSUM_LENGTH

        noise_buffer = memoryview(buffer)[0:noise_payload_len]

        key_send = self.channel_cache.get(CHANNEL_KEY_SEND)
        nonce_send = self.channel_cache.get_int(CHANNEL_NONCE_SEND)

        assert key_send is not None
        assert nonce_send is not None

        tag = crypto.enc(noise_buffer, key_send, nonce_send)

        self.channel_cache.set_int(CHANNEL_NONCE_SEND, nonce_send + 1)
        if __debug__:
            self._log("New nonce_send: ", str((nonce_send + 1)))

        buffer[noise_payload_len : noise_payload_len + TAG_LENGTH] = tag

    if __debug__:

        def _log(self, text_1: str, text_2: str = "", logger: Any = log.debug) -> None:
            logger(
                __name__,
                "(cid: %s) %s%s",
                hexlify_if_bytes(self.channel_id),
                text_1,
                text_2,
                iface=self.iface,
            )


def send_ack(channel: Channel, ack_bit: int) -> Awaitable[None]:
    ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(ACK_MESSAGE, ack_bit)
    header = PacketHeader(ctrl_byte, channel.get_channel_id_int(), CHECKSUM_LENGTH)
    if __debug__:
        log.debug(
            __name__,
            "Writing ACK message to a channel with cid: %s, ack_bit: %d",
            hexlify_if_bytes(channel.channel_id),
            ack_bit,
            iface=channel.iface,
        )
    return channel.ctx.write_payload(header, b"")


def handle_ack(ctx: Channel, ack_bit: int) -> None:
    if not ABP.is_ack_valid(ctx.channel_cache, ack_bit):
        return
    # ACK is expected and it has correct sync bit
    if __debug__:
        log.debug(
            __name__,
            "Received ACK message with correct ack bit",
            iface=ctx.iface,
        )
    ABP.set_sending_allowed(ctx.channel_cache, True)
