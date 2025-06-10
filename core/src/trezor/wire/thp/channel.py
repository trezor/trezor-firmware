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
from trezor.wire.thp.fallback import Fallback

from . import ENCRYPTED, ChannelState, PacketHeader, ThpDecryptionError, ThpError
from . import alternating_bit_protocol as ABP
from . import (
    control_byte,
    crypto,
    interface_manager,
    memory_manager,
    received_message_handler,
)
from .checksum import CHECKSUM_LENGTH
from .transmission_loop import TransmissionLoop
from .writer import (
    CONT_HEADER_LENGTH,
    INIT_HEADER_LENGTH,
    MESSAGE_TYPE_LENGTH,
    write_payload_to_wire_and_add_checksum,
)

if __debug__:
    from trezor import log
    from trezor.utils import get_bytes_as_str

    from . import state_to_str

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Any, Awaitable

    from trezor.messages import ThpPairingCredential

    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


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

        # Shared variables
        self.buffer: utils.BufferType = bytearray(self.iface.TX_PACKET_LEN)
        self.bytes_read: int = 0
        self.expected_payload_length: int = 0
        self.is_cont_packet_expected: bool = False
        self.sessions: dict[int, GenericSessionContext] = {}

        # Objects for writing a message to a wire
        self.transmission_loop: TransmissionLoop | None = None
        self.write_task_spawn: loop.spawn | None = None

        # Temporary objects
        self._fallback: Fallback | None = None
        self.handshake: crypto.Handshake | None = None
        self.credential: ThpPairingCredential | None = None
        self.connection_context: PairingContext | None = None

        if __debug__:
            self.should_show_pairing_dialog: bool = True

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

    def replace_old_channels_with_the_same_host_pubkey(self) -> None:
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

    def receive_packet(self, packet: utils.BufferType) -> Awaitable[None] | None:
        if __debug__:
            self._log("receive packet")

        task = self._handle_received_packet(packet)
        if task is not None:
            return task

        if self.expected_payload_length == 0:  # Reading failed TODO
            from trezor.wire.thp import ThpErrorType

            return self.write_error(ThpErrorType.TRANSPORT_BUSY)

        try:
            buffer = memory_manager.get_existing_read_buffer(self.get_channel_id_int())
            if __debug__:
                self._log("self.buffer: ", get_bytes_as_str(buffer))
        except WireBufferError:
            if __debug__:
                self._log(
                    "getting read buffer failed - ",
                    str(WireBufferError.__name__),
                    logger=log.warning,
                )
            pass  # TODO ??
        if (
            self._fallback is not None
            and self.expected_payload_length == self.bytes_read
        ):

            self._fallback.finish()
            if not self._fallback.is_crc_checksum_valid():
                if __debug__:
                    self._log("INVALID FALLBACK CRC", logger=log.warning)
                return None

            # Check ABP seq bit
            seq_bit = control_byte.get_seq_bit(self._fallback.ctrl_byte)
            if not ABP.has_msg_correct_seq_bit(self.channel_cache, seq_bit):
                if __debug__:
                    self._log(
                        "Received message with an unexpected sequential bit!",
                        logger=log.warning,
                    )
                return received_message_handler._send_ack(self, ack_bit=seq_bit)

            # Check noise tag
            if not self._fallback.is_noise_tag_valid():
                if __debug__:
                    self._log("Invalid fallback noise tag", logger=log.warning)
                raise ThpDecryptionError()

            # Update nonces and seq bit
            nonce_receive = self.channel_cache.get_int(CHANNEL_NONCE_RECEIVE)
            assert nonce_receive is not None
            self.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, nonce_receive + 1)
            ABP.set_expected_receive_seq_bit(self.channel_cache, 1 - seq_bit)

            self._finish_message()
            sid = self._fallback.session_id or 0
            self._clear_fallback()

            from trezor.enums import FailureType
            from trezor.messages import Failure

            return self.write(
                Failure(code=FailureType.Busy, message="FALLBACK!"),
                session_id=sid,
                fallback=True,
            )

        if (
            self._fallback is None
            and self.expected_payload_length + INIT_HEADER_LENGTH == self.bytes_read
        ):
            self._finish_message()
            return received_message_handler.handle_received_message(self, buffer)
        elif self.expected_payload_length + INIT_HEADER_LENGTH > self.bytes_read:
            self.is_cont_packet_expected = True
            if __debug__:
                self._log(
                    "CONT EXPECTED - read/expected:",
                    str(self.bytes_read)
                    + "/"
                    + str(self.expected_payload_length + INIT_HEADER_LENGTH),
                )
        else:
            raise ThpError(
                "Read more bytes than is the expected length of the message!"
            )
        return None

    def _handle_received_packet(
        self, packet: utils.BufferType
    ) -> Awaitable[None] | None:
        ctrl_byte = packet[0]
        if control_byte.is_continuation(ctrl_byte):
            self._handle_cont_packet(packet)
            return None
        return self._handle_init_packet(packet)

    def _handle_init_packet(self, packet: utils.BufferType) -> Awaitable[None] | None:
        self._fallback = None
        self.bytes_read = 0
        self.expected_payload_length = 0

        if __debug__:
            self._log("handle_init_packet")

        _, _, payload_length = ustruct.unpack(PacketHeader.format_str_init, packet)
        self.expected_payload_length = payload_length

        # If the channel does not "own" the buffer lock, decrypt the first packet

        cid = self.get_channel_id_int()
        length = payload_length + INIT_HEADER_LENGTH
        try:
            buffer = memory_manager.get_new_read_buffer(cid, length)
        except WireBufferError:
            # Channel does not "own" the buffer lock, decrypt the first packet

            try:
                if not self._can_fallback():
                    if __debug__:
                        self._log(
                            "Channel is in a state that does not support fallback.",
                            logger=log.error,
                        )
                    raise Exception(
                        "Channel is in a state that does not support fallback."
                    )
                if __debug__:
                    self._log("Started fallback read")
                self._fallback = Fallback(self, memoryview(packet))

            except Exception:
                self._fallback = None
                self.expected_payload_length = 0
                self.bytes_read = 0
                if __debug__:
                    from ubinascii import hexlify

                    self._log(
                        "FAILED TO FALLBACK: ",
                        hexlify(packet).decode(),
                        logger=log.error,
                    )
                return None

            to_read_len = min(len(packet) - INIT_HEADER_LENGTH, payload_length)
            buf = memoryview(self.buffer)[:to_read_len]
            utils.memcpy(buf, 0, packet, INIT_HEADER_LENGTH)

            # Fallback
            fallback_task = self._fallback.read_init_packet(buf)
            self.bytes_read += to_read_len
            return fallback_task

        if __debug__:
            self._log("handle_init_packet - payload len: ", str(payload_length))
            self._log("handle_init_packet - buffer len: ", str(len(buffer)))

        self._buffer_packet_data(buffer, packet, 0)
        return None

    def _handle_cont_packet(self, packet: utils.BufferType) -> None:
        if __debug__:
            self._log("handle_cont_packet")

        if not self.is_cont_packet_expected:
            raise ThpError("Continuation packet is not expected, ignoring")

        if self._fallback is not None:
            to_read_len = min(
                len(packet) - CONT_HEADER_LENGTH,
                self.expected_payload_length - self.bytes_read,
            )
            buf = memoryview(self.buffer)[:to_read_len]
            utils.memcpy(buf, 0, packet, CONT_HEADER_LENGTH)

            self._fallback.read_cont_packet(buf)

            self.bytes_read += to_read_len
            return
        try:
            buffer = memory_manager.get_existing_read_buffer(self.get_channel_id_int())
        except WireBufferError:
            self.set_channel_state(ChannelState.INVALIDATED)
            # TODO ? self.clear() or raise Decryption error?
            pass  # TODO handle device busy, channel kaput
        self._buffer_packet_data(buffer, packet, CONT_HEADER_LENGTH)

    def _buffer_packet_data(
        self, payload_buffer: utils.BufferType, packet: utils.BufferType, offset: int
    ) -> None:
        self.bytes_read += utils.memcpy(payload_buffer, self.bytes_read, packet, offset)

    def _finish_message(self) -> None:
        self.bytes_read = 0
        self.expected_payload_length = 0
        self.is_cont_packet_expected = False

    def _clear_fallback(self) -> None:
        self._fallback = None
        if __debug__:
            self._log("Finish fallback")

    def decrypt_buffer(
        self, message_length: int, offset: int = INIT_HEADER_LENGTH
    ) -> None:
        buffer = memory_manager.get_existing_read_buffer(self.get_channel_id_int())
        # if buffer is WireBufferError:
        # pass  # TODO handle deviceBUSY
        noise_buffer = memoryview(buffer)[
            offset : message_length - CHECKSUM_LENGTH - TAG_LENGTH
        ]
        tag = buffer[
            message_length
            - CHECKSUM_LENGTH
            - TAG_LENGTH : message_length
            - CHECKSUM_LENGTH
        ]

        if utils.DISABLE_ENCRYPTION:
            is_tag_valid = tag == crypto.DUMMY_TAG
        else:
            key_receive = self.channel_cache.get(CHANNEL_KEY_RECEIVE)
            nonce_receive = self.channel_cache.get_int(CHANNEL_NONCE_RECEIVE)

            assert key_receive is not None
            assert nonce_receive is not None

            if __debug__:
                self._log("Buffer before decryption: ", get_bytes_as_str(noise_buffer))

            is_tag_valid = crypto.dec(noise_buffer, tag, key_receive, nonce_receive)
            if __debug__:
                self._log("Buffer after decryption: ", get_bytes_as_str(noise_buffer))

            self.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, nonce_receive + 1)

        if __debug__:
            self._log("Is decrypted tag valid? ", str(is_tag_valid))
            self._log("Received tag: ", get_bytes_as_str(tag))
            self._log("New nonce_receive: ", str((nonce_receive + 1)))

        if not is_tag_valid:
            raise ThpDecryptionError()

    # WRITE and ENCRYPT

    async def write(
        self,
        msg: protobuf.MessageType,
        session_id: int = 0,
        force: bool = False,
        fallback: bool = False,
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
        length = payload_size + CHECKSUM_LENGTH + TAG_LENGTH + INIT_HEADER_LENGTH
        try:
            if fallback:
                buffer = self.buffer
            else:
                buffer = memory_manager.get_new_write_buffer(cid, length)
            noise_payload_len = memory_manager.encode_into_buffer(
                buffer, msg, session_id
            )
        except WireBufferError:
            from trezor.enums import FailureType
            from trezor.messages import Failure

            if length <= len(self.buffer):
                # Fallback write - Write buffer is locked, using backup buffer instead
                noise_payload_len = memory_manager.encode_into_buffer(
                    self.buffer, msg, session_id
                )
                task = self._write_and_encrypt(noise_payload_len, fallback=True)
                if task is not None:
                    await task
                return

            # Message cannot be written - not even in fallback mode, killing channel
            if __debug__:
                self._log("Failed to get write buffer, killing channel.")

            noise_payload_len = memory_manager.encode_into_buffer(
                self.buffer,
                Failure(
                    code=FailureType.FirmwareError,
                    message="Failed to obtain write buffer.",
                ),
                session_id,
            )
            self.set_channel_state(ChannelState.INVALIDATED)
        task = self._write_and_encrypt(
            noise_payload_len=noise_payload_len, force=force, fallback=fallback
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

    def _write_and_encrypt(
        self,
        noise_payload_len: int,
        force: bool = False,
        fallback: bool = False,
    ) -> Awaitable[None] | None:
        if fallback:
            buffer = self.buffer
        else:
            buffer = memory_manager.get_existing_write_buffer(self.get_channel_id_int())
        # if buffer is WireBufferError:
        # pass  # TODO handle deviceBUSY

        self._encrypt(buffer, noise_payload_len)
        payload_length = noise_payload_len + TAG_LENGTH

        if self.write_task_spawn is not None:
            self.write_task_spawn.close()  # TODO might break something
            if __debug__:
                self._log("Closed write task", logger=log.warning)
        self._prepare_write()
        if fallback:
            if __debug__:
                self._log(
                    "Writing FALLBACK message (written only once without async or retransmission)."
                )

            return self._write_encrypted_payload_loop(
                ctrl_byte=ENCRYPTED,
                payload=memoryview(buffer[:payload_length]),
                only_once=True,
            )

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
            loop.clear()

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

    def _can_fallback(self) -> bool:
        state = self.get_channel_state()
        return state not in [
            ChannelState.TH1,
            ChannelState.TH2,
            ChannelState.UNALLOCATED,
        ]

    if __debug__:

        def _log(self, text_1: str, text_2: str = "", logger: Any = log.debug) -> None:
            logger(
                __name__,
                "(cid: %s) %s%s",
                get_bytes_as_str(self.channel_id),
                text_1,
                text_2,
                iface=self.iface,
            )
