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
from trezor import loop, protobuf, utils, wire, workflow
from trezor.wire.errors import WireBufferError

from . import (
    ENCRYPTED,
    ChannelState,
    PacketHeader,
    ThpDecryptionError,
    ThpError,
    ThpTransportBusy,
)
from . import alternating_bit_protocol as ABP
from . import control_byte, crypto, interface_manager
from .checksum import CHECKSUM_LENGTH
from .memory_manager import encode_into_buffer
from .transmission_loop import TransmissionLoop
from .writer import (
    CONT_HEADER_LENGTH,
    INIT_HEADER_LENGTH,
    MESSAGE_TYPE_LENGTH,
    write_payload_to_wire_and_add_checksum,
)

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

    from . import state_to_str

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any, Awaitable

    from trezor.messages import ThpPairingCredential

    from .pairing_context import PairingContext


class ChannelBuffers:
    def __init__(self) -> None:
        self.rx = bytearray(8192)
        self.tx = bytearray(8192)

    def get_rx(self, size: int) -> memoryview:
        view = memoryview(self.rx)
        if size > len(view):
            raise WireBufferError("RX")
        return view[:size]

    def get_tx(self, size: int) -> memoryview:
        view = memoryview(self.tx)
        if size > len(view):
            raise WireBufferError("TX")
        return view[:size]


class Channel:
    """
    THP protocol encrypted communication channel.
    """

    def __init__(self, channel_cache: ChannelCache) -> None:

        # Channel properties
        self.channel_id: bytes = channel_cache.channel_id
        channel_iface = channel_cache.get(CHANNEL_IFACE)
        assert channel_iface is not None
        self.iface: WireInterface = interface_manager.decode_iface(channel_iface)
        if __debug__:
            self._log("channel initialization")
        self.channel_cache: ChannelCache = channel_cache
        self._buffers: ChannelBuffers | None = None

        # Shared variables
        self.buffer: utils.BufferType = bytearray(self.iface.TX_PACKET_LEN)
        self.bytes_read: int = 0
        self.rx_buffer: memoryview = memoryview(b"")
        self.is_cont_packet_expected: bool = False

        # Objects for writing a message to a wire
        self.transmission_loop: TransmissionLoop | None = None
        self.write_task_spawn: loop.spawn | None = None

        # Temporary objects
        self.handshake: crypto.Handshake | None = None
        self.credential: ThpPairingCredential | None = None
        self.connection_context: PairingContext | None = None

        if __debug__:
            self.should_show_pairing_dialog: bool = True

    def get_buffers(self) -> ChannelBuffers:
        """Try to acquire buffers (in case it's the first message being handled)."""
        self._buffers = self._buffers or wire.THP_BUFFERS_PROVIDER.take()
        if not self._buffers:
            raise ThpTransportBusy(self.get_channel_id_int())
        return self._buffers

    def clear(self) -> None:
        clear_sessions_with_channel_id(self.channel_id)
        self.rx_buffer = memoryview(b"")
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

    def receive_packet(self, packet: utils.BufferType) -> bool:
        if __debug__:
            self._log("receive packet")

        self._handle_received_packet(packet)

        if len(self.rx_buffer) == self.bytes_read:
            self.bytes_read = 0
            self.is_cont_packet_expected = False
            # FIXME: if any message is received before `rx_buffer` is decoded, it will be overwritten :(
            return True

        elif len(self.rx_buffer) > self.bytes_read:
            self.is_cont_packet_expected = True
            return False
        else:
            raise ThpError(
                "Read more bytes than is the expected length of the message!"
            )

    def _handle_received_packet(self, packet: utils.BufferType) -> None:
        ctrl_byte = packet[0]
        if control_byte.is_continuation(ctrl_byte):
            self._handle_cont_packet(packet)
        else:
            self._handle_init_packet(packet)

    def _handle_init_packet(self, packet: utils.BufferType) -> None:
        self.bytes_read = 0

        _, _, payload_length = ustruct.unpack(PacketHeader.format_str_init, packet)
        self.rx_buffer = self.get_buffers().get_rx(INIT_HEADER_LENGTH + payload_length)
        self._buffer_packet_data(self.rx_buffer, packet, 0)

    def _handle_cont_packet(self, packet: utils.BufferType) -> None:
        if __debug__:
            self._log("handle_cont_packet")

        if not self.is_cont_packet_expected:
            raise ThpError("Continuation packet is not expected, ignoring")

        self._buffer_packet_data(self.rx_buffer, packet, CONT_HEADER_LENGTH)

    def _buffer_packet_data(
        self, payload_buffer: utils.BufferType, packet: utils.BufferType, offset: int
    ) -> None:
        self.bytes_read += utils.memcpy(payload_buffer, self.bytes_read, packet, offset)

    def decrypt_buffer(
        self, message: memoryview, offset: int = INIT_HEADER_LENGTH
    ) -> None:
        noise_buffer = message[offset : len(message) - CHECKSUM_LENGTH - TAG_LENGTH]
        tag = message[
            len(message) - CHECKSUM_LENGTH - TAG_LENGTH : len(message) - CHECKSUM_LENGTH
        ]

        if utils.DISABLE_ENCRYPTION:
            is_tag_valid = tag == crypto.DUMMY_TAG
        else:
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
        force: bool = False,
    ) -> None:
        raise NotImplementedError
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
        length = payload_size + CHECKSUM_LENGTH + TAG_LENGTH + INIT_HEADER_LENGTH

        buffer = self.get_buffers().get_tx(length)
        noise_payload_len = encode_into_buffer(buffer, msg, session_id)

        task = self._write_and_encrypt(
            buffer=buffer, noise_payload_len=noise_payload_len, force=force
        )
        if task is not None:
            await task

    def write_error(self, err_type: int) -> Awaitable[None]:
        msg_data = err_type.to_bytes(1, "big")
        length = len(msg_data) + CHECKSUM_LENGTH
        header = PacketHeader.get_error_header(self.get_channel_id_int(), length)
        return write_payload_to_wire_and_add_checksum(self.iface, header, msg_data)

    def write_handshake_message(self, ctrl_byte: int, payload: bytes) -> None:
        self._prepare_write()
        self.write_task_spawn = loop.spawn(
            self._write_encrypted_payload_loop(ctrl_byte, payload)
        )

    def send_payload(self, ctrl_byte: int, payload: bytes) -> Awaitable[None]:
        """Send payload with ABP bit - don't wait for an ACK."""
        payload_len = len(payload) + CHECKSUM_LENGTH
        seq_bit = ABP.get_send_seq_bit(self.channel_cache)
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(ctrl_byte, seq_bit)
        header = PacketHeader(ctrl_byte, self.get_channel_id_int(), payload_len)
        self._prepare_write()  # stop sending after this write, until receiving an ACK
        return write_payload_to_wire_and_add_checksum(self.iface, header, payload)

    def send_message(
        self, msg: protobuf.MessageType, session_id: int = 0
    ) -> Awaitable[None]:
        """Encode, encrypt and send payload with ABP bit - don't wait for an ACK."""
        msg_size = protobuf.encoded_length(msg)
        payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size
        length = payload_size + CHECKSUM_LENGTH + TAG_LENGTH + INIT_HEADER_LENGTH

        buffer = self.get_buffers().get_tx(length)
        noise_payload_len = encode_into_buffer(buffer, msg, session_id)
        self._encrypt(buffer, noise_payload_len)

        payload_length = noise_payload_len + TAG_LENGTH
        return self.send_payload(ENCRYPTED, buffer[:payload_length])

    def _write_and_encrypt(
        self,
        buffer: memoryview,
        noise_payload_len: int,
        force: bool = False,
    ) -> Awaitable[None] | None:
        self._encrypt(buffer, noise_payload_len)
        payload_length = noise_payload_len + TAG_LENGTH

        if self.write_task_spawn is not None:
            self.write_task_spawn.close()  # TODO might break something
            if __debug__:
                self._log("Closed write task", logger=log.warning)
        self._prepare_write()
        if force:
            if __debug__:
                self._log("Writing FORCE message (without async or retransmission).")

            return self._write_encrypted_payload_loop(
                ENCRYPTED, memoryview(buffer[:payload_length])
            )
        self.write_task_spawn = loop.spawn(
            self._write_encrypted_payload_loop(
                ENCRYPTED, memoryview(buffer[:payload_length])
            )
        )
        return None

    def _prepare_write(self) -> None:
        # TODO add condition that disallows to write when can_send_message is false
        ABP.set_sending_allowed(self.channel_cache, False)

    async def _write_encrypted_payload_loop(
        self, ctrl_byte: int, payload: bytes, only_once: bool = False
    ) -> None:
        if __debug__:
            self._log("write_encrypted_payload_loop")

        payload_len = len(payload) + CHECKSUM_LENGTH
        sync_bit = ABP.get_send_seq_bit(self.channel_cache)
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(ctrl_byte, sync_bit)
        header = PacketHeader(ctrl_byte, self.get_channel_id_int(), payload_len)
        self.transmission_loop = TransmissionLoop(self, header, payload)
        if only_once:
            if __debug__:
                self._log('Starting transmission loop "only once"')
            await self.transmission_loop.start(max_retransmission_count=1)
        else:
            if __debug__:
                self._log("Starting transmission loop")
            await self.transmission_loop.start()

        ABP.set_send_seq_bit_to_opposite(self.channel_cache)

        # Let the main loop be restarted and clear loop, if there is no other
        # workflow and the state is ENCRYPTED_TRANSPORT
        # TODO only once is there to not clear when FALLBACK
        # TODO missing transmission loop is active -> do not clear
        if not only_once and self._can_clear_loop():
            if __debug__:
                self._log("clearing loop from channel")

    def _encrypt(self, buffer: utils.BufferType, noise_payload_len: int) -> None:
        if __debug__:
            self._log("encrypt")

        assert len(buffer) >= noise_payload_len + TAG_LENGTH + CHECKSUM_LENGTH

        noise_buffer = memoryview(buffer)[0:noise_payload_len]

        if utils.DISABLE_ENCRYPTION:
            tag = crypto.DUMMY_TAG
        else:
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
