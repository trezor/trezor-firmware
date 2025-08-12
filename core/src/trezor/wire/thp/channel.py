import ustruct
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
from trezor import loop, protobuf, utils, workflow
from trezor.wire.errors import WireBufferError

from ..protocol_common import Message
from . import ENCRYPTED, ChannelState, PacketHeader, ThpDecryptionError, ThpError
from . import alternating_bit_protocol as ABP
from . import control_byte, crypto, memory_manager
from .checksum import CHECKSUM_LENGTH, is_valid
from .received_message_handler import (
    _send_ack,
    _should_have_ctrl_byte_encrypted_transport,
    handle_ack,
)
from .writer import MESSAGE_TYPE_LENGTH

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

    from . import state_to_str

if TYPE_CHECKING:
    from typing import Any, Awaitable

    from trezor.messages import ThpPairingCredential
    from trezor.wire import WireInterface

    from .interface_context import ThpContext
    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


class Reassembler:
    def __init__(self, cid: int) -> None:
        self.cid = cid
        self.reset()

    def reset(self) -> None:
        self.bytes_read: int = 0
        self.buffer_len: int = 0
        self.message: memoryview | None = None

    def handle_packet(self, packet: memoryview) -> bool:
        """
        Process current packet, returning `True` on success.
        In case of checksum error or if reasembly is not over, `False` is returned.

        May raise `WireBufferError` if there is a concurrent payload reassembly in progress.
        """
        ctrl_byte = packet[0]
        if control_byte.is_continuation(ctrl_byte):
            if not self.bytes_read:
                # ignore unexpected continuation packets
                return False

            # may raise WireBufferError
            buffer = memory_manager.get_existing_read_buffer(self.cid)
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
                # may raise WireBufferError
                buffer = memory_manager.get_new_read_buffer(self.cid, self.buffer_len)
                self._buffer_packet_data(buffer, packet, 0)

        assert len(buffer) == self.buffer_len
        if self.bytes_read < self.buffer_len:
            return False
        elif self.bytes_read == self.buffer_len:
            if not verify_checksum(buffer):
                return False
            self.message = buffer
            return True
        else:
            raise ThpError("read more bytes than expected")

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

    def __init__(self, channel_cache: ChannelCache, ctx: ThpContext) -> None:
        assert ctx._iface.iface_num() == channel_cache.get_int(CHANNEL_IFACE)

        # Channel properties
        self.channel_id: bytes = channel_cache.channel_id
        self.ctx: ThpContext = ctx
        if __debug__:
            self._log("channel initialization")
        self.channel_cache: ChannelCache = channel_cache

        # Shared variables
        self.sessions: dict[int, GenericSessionContext] = {}
        self.reassembler = Reassembler(self.get_channel_id_int())

        # Temporary objects
        self.handshake: crypto.Handshake | None = None
        self.credential: ThpPairingCredential | None = None
        self.connection_context: PairingContext | None = None

        if __debug__:
            self.should_show_pairing_dialog: bool = True

    @property
    def iface(self) -> WireInterface:
        return self.ctx._iface

    def clear(self) -> None:
        clear_sessions_with_channel_id(self.channel_id)
        memory_manager.release_lock_if_owner(self.get_channel_id_int())
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

    def reassemble(self, packet: utils.BufferType) -> bool:
        """
        Process current packet, returning `True` on success.
        In case of checksum error or if reassembly is not over, `False` is returned.

        May raise `WireBufferError` if there is a concurrent payload reassembly in progress.
        """
        if self.get_channel_state() == ChannelState.UNALLOCATED:
            return False
        try:
            return self.reassembler.handle_packet(memoryview(packet))
        except WireBufferError:
            self.reassembler.reset()
            raise

    def _decrypt_buffer(
        self, buffer: memoryview, offset: int = PacketHeader.INIT_LENGTH
    ) -> None:
        message_length = len(buffer)
        noise_buffer = buffer[offset : message_length - CHECKSUM_LENGTH - TAG_LENGTH]
        tag = buffer[
            message_length
            - CHECKSUM_LENGTH
            - TAG_LENGTH : message_length
            - CHECKSUM_LENGTH
        ]

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

        cid = self.get_channel_id_int()
        msg_size = protobuf.encoded_length(msg)
        payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size
        length = payload_size + CHECKSUM_LENGTH + TAG_LENGTH + PacketHeader.INIT_LENGTH

        buffer = memory_manager.get_new_write_buffer(cid, length)
        noise_payload_len = memory_manager.encode_into_buffer(buffer, msg, session_id)

        self._encrypt(buffer, noise_payload_len)
        payload_length = noise_payload_len + TAG_LENGTH

        return await self._write_encrypted_payload_loop(
            ENCRYPTED, buffer[:payload_length]
        )

    def write_error(self, err_type: int) -> Awaitable[None]:
        msg_data = err_type.to_bytes(1, "big")
        length = len(msg_data) + CHECKSUM_LENGTH
        header = PacketHeader.get_error_header(self.get_channel_id_int(), length)
        return self.ctx.write_payload(header, msg_data)

    def write_handshake_message(
        self, ctrl_byte: int, payload: bytes
    ) -> Awaitable[None]:
        return self._write_encrypted_payload_loop(ctrl_byte, payload)

    async def _get_reassembled_message(self) -> memoryview:
        while self.reassembler.message is None:
            # receive and reassemble a new message from this channel
            channel = await self.ctx.get_next_message()
            if channel is self:
                break

            # TODO: if this channel is inactive, allow switching to other channels
            channel._log(
                "Ignored message from unexpected channel: ",
                utils.hexlify_if_bytes(channel.reassembler.message or "N/A"),
            )

        msg = self.reassembler.message
        self.reassembler.reset()  # next call will reassemble a new message
        assert msg is not None
        return msg

    async def decrypt_message(self) -> tuple[int, Message]:
        """
        Receive decrypt and return a (session_id, message) together with handling ACKs.
        """
        buffer = await self.recv_message()
        self._decrypt_buffer(buffer)
        session_id, message_type = ustruct.unpack(
            ">BH", buffer[PacketHeader.INIT_LENGTH :]
        )
        message = Message(
            message_type,
            buffer[
                PacketHeader.INIT_LENGTH
                + MESSAGE_TYPE_LENGTH
                + SESSION_ID_LENGTH : len(buffer)
                - CHECKSUM_LENGTH
                - TAG_LENGTH
            ],
        )
        return (session_id, message)

    async def recv_message(self, _return_on_ack: bool = False) -> memoryview:
        """
        Receive and return a valid message, together with handling ACKs.
        Message content is not decrypted.

        If `return_on_ack` is set, return when a valid ACK is received.
        """
        while True:
            # Handle an existing message (if already reassembled).
            # Otherwise, receive and reassemble a new one.
            msg = await self._get_reassembled_message()

            # Synchronization process
            ctrl_byte = msg[0]
            seq_bit = control_byte.get_seq_bit(ctrl_byte)

            # 1: Handle ACKs
            if control_byte.is_ack(ctrl_byte):
                handle_ack(self, control_byte.get_ack_bit(ctrl_byte))
                if _return_on_ack:
                    return msg
                else:
                    continue

            if _should_have_ctrl_byte_encrypted_transport(
                self
            ) and not control_byte.is_encrypted_transport(ctrl_byte):
                raise ThpError("Message is not encrypted. Ignoring")

            # 2: Handle message with unexpected sequential bit
            if seq_bit != ABP.get_expected_receive_seq_bit(self.channel_cache):
                if __debug__:
                    self._log(
                        "Received message with an unexpected sequential bit",
                    )
                await _send_ack(self, ack_bit=seq_bit)
                raise ThpError("Received message with an unexpected sequential bit")

            # 3: Send ACK in response
            await _send_ack(self, ack_bit=seq_bit)

            ABP.set_expected_receive_seq_bit(self.channel_cache, 1 - seq_bit)

            return msg

    async def _write_encrypted_payload_loop(
        self, ctrl_byte: int, payload: bytes
    ) -> None:
        if __debug__:
            self._log("write_encrypted_payload_loop")

        assert ABP.is_sending_allowed(self.channel_cache)

        payload_len = len(payload) + CHECKSUM_LENGTH
        sync_bit = ABP.get_send_seq_bit(self.channel_cache)
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(ctrl_byte, sync_bit)

        header = PacketHeader(ctrl_byte, self.get_channel_id_int(), payload_len)
        await self.ctx.write_payload(header, payload)
        # TODO: re-transmit if no ACK is received
        # TODO: there may be multiple ACKs due to host-side retransmissions

        # ACK is needed before sending more data
        ABP.set_sending_allowed(self.channel_cache, False)
        while True:
            # a valid ACK will result in calling `ABP.set_sending_allowed()`
            self._log("waiting for ACK after send")
            msg = await self.recv_message(_return_on_ack=True)
            if ABP.is_sending_allowed(self.channel_cache):
                break
            if __debug__:
                # the host should send an ACK before sending other messages
                self._log("Ignored non-ACK message: ", utils.hexlify_if_bytes(msg))

        self._log("got ACK after send")
        ABP.set_send_seq_bit_to_opposite(self.channel_cache)

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

    def _can_clear_loop(self) -> bool:
        return (
            not workflow.tasks
        ) and self.get_channel_state() is ChannelState.ENCRYPTED_TRANSPORT

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
