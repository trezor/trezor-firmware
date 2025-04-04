import ustruct
from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_HOST_STATIC_PUBKEY,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
)
from storage.cache_thp import (
    SESSION_ID_LENGTH,
    TAG_LENGTH,
    ChannelCache,
    clear_sessions_with_channel_id,
    conditionally_replace_channel,
    is_there_a_channel_to_replace,
)
from trezor import log, loop, protobuf, utils, workflow
from trezor.wire.errors import WireBufferError

from . import ENCRYPTED, ChannelState, PacketHeader, ThpDecryptionError, ThpError
from . import alternating_bit_protocol as ABP
from . import (
    checksum,
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
    from trezor.utils import get_bytes_as_str

    from . import state_to_str

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Awaitable

    from trezor.messages import ThpPairingCredential

    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


class Channel:
    """
    THP protocol encrypted communication channel.
    """

    def __init__(self, channel_cache: ChannelCache) -> None:
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            log.debug(__name__, "channel initialization")

        # Channel properties
        self.iface: WireInterface = interface_manager.decode_iface(channel_cache.iface)
        self.channel_cache: ChannelCache = channel_cache
        self.channel_id: bytes = channel_cache.channel_id

        # Shared variables
        self.buffer: utils.BufferType = bytearray(self.iface.TX_PACKET_LEN)
        self.fallback_decrypt: bool = False
        self.bytes_read: int = 0
        self.expected_payload_length: int = 0
        self.is_cont_packet_expected: bool = False
        self.sessions: dict[int, GenericSessionContext] = {}

        # Objects for writing a message to a wire
        self.transmission_loop: TransmissionLoop | None = None
        self.write_task_spawn: loop.spawn | None = None

        # Temporary objects
        self.handshake: crypto.Handshake | None = None
        self.credential: ThpPairingCredential | None = None
        self.connection_context: PairingContext | None = None
        self.busy_decoder: crypto.BusyDecoder | None = None
        self.temp_crc: int | None = None
        self.temp_crc_compare: bytearray | None = None
        self.temp_tag: bytearray | None = None

    def clear(self) -> None:
        clear_sessions_with_channel_id(self.channel_id)
        memory_manager.release_lock_if_owner(self.get_channel_id_int())
        self.channel_cache.clear()

    # ACCESS TO CHANNEL_DATA

    def get_channel_id_int(self) -> int:
        return int.from_bytes(self.channel_id, "big")

    def get_channel_state(self) -> int:
        state = int.from_bytes(self.channel_cache.state, "big")
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            self._log("get_channel_state: ", state_to_str(state))
        return state

    def get_handshake_hash(self) -> bytes:
        h = self.channel_cache.get(CHANNEL_HANDSHAKE_HASH)
        assert h is not None
        return h

    def set_channel_state(self, state: ChannelState) -> None:
        self.channel_cache.state = bytearray(state.to_bytes(1, "big"))
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
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
        log.debug(__name__, "Was any channel replaced? %s", str(was_any_replaced))

    def is_channel_to_replace(self) -> bool:
        return is_there_a_channel_to_replace(
            new_channel=self.channel_cache,
            required_state=ChannelState.ENCRYPTED_TRANSPORT,
            required_key=CHANNEL_HOST_STATIC_PUBKEY,
        )

    # READ and DECRYPT

    def receive_packet(self, packet: utils.BufferType) -> Awaitable[None] | None:
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            self._log("receive packet")

        self._handle_received_packet(packet)

        if self.expected_payload_length == 0:  # Reading failed TODO
            from trezor.wire.thp import ThpErrorType

            return self.write_error(ThpErrorType.TRANSPORT_BUSY)

        try:
            buffer = memory_manager.get_existing_read_buffer(self.get_channel_id_int())
        except WireBufferError:
            pass  # TODO ??
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            try:
                self._log("self.buffer: ", get_bytes_as_str(buffer))
            except Exception:
                pass  # TODO handle nicer - happens in fallback_decrypt

        if self.expected_payload_length + INIT_HEADER_LENGTH == self.bytes_read:
            self._finish_message()
            if self.fallback_decrypt:
                # TODO Check CRC and if valid, check tag, if valid update nonces
                self._finish_fallback()
                # TODO self.write() failure device is busy - use channel buffer to send this failure message!!
                return None
            return received_message_handler.handle_received_message(self, buffer)
        elif self.expected_payload_length + INIT_HEADER_LENGTH > self.bytes_read:
            self.is_cont_packet_expected = True
        else:
            raise ThpError(
                "Read more bytes than is the expected length of the message!"
            )
        return None

    def _handle_received_packet(self, packet: utils.BufferType) -> None:
        ctrl_byte = packet[0]
        if control_byte.is_continuation(ctrl_byte):
            self._handle_cont_packet(packet)
            return
        self._handle_init_packet(packet)

    def _handle_init_packet(self, packet: utils.BufferType) -> None:
        self.fallback_decrypt = False
        self.bytes_read = 0
        self.expected_payload_length = 0

        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            self._log("handle_init_packet")

        _, _, payload_length = ustruct.unpack(PacketHeader.format_str_init, packet)
        self.expected_payload_length = payload_length

        # If the channel does not "own" the buffer lock, decrypt first packet
        # TODO do it only when needed!
        # TODO FIX: If "_decrypt_single_packet_payload" is implemented, it will (possibly) break "decrypt_buffer" and nonces incrementation.
        # On the other hand, without the single packet decryption, the "advanced" buffer selection cannot be implemented
        # in "memory_manager.select_buffer", because the session id is unknown (encrypted).

        # if control_byte.is_encrypted_transport(ctrl_byte):
        #   packet_payload = self._decrypt_single_packet_payload(packet_payload)

        cid = self.get_channel_id_int()
        length = payload_length + INIT_HEADER_LENGTH
        try:
            buffer = memory_manager.get_new_read_buffer(cid, length)
        except WireBufferError:
            # TODO handle not encrypted/(short??), eg. ACK

            self.fallback_decrypt = True

            try:
                self._prepare_fallback()
            except Exception:
                self.fallback_decrypt = False
                self.expected_payload_length = 0
                self.bytes_read = 0
                if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
                    from ubinascii import hexlify

                    log.debug(
                        __name__, "FAILED TO FALLBACK: %s", hexlify(packet).decode()
                    )
                return

            to_read_len = min(len(packet) - INIT_HEADER_LENGTH, payload_length)
            buf = memoryview(self.buffer)[:to_read_len]
            utils.memcpy(buf, 0, packet, INIT_HEADER_LENGTH)

            # CRC CHECK
            self._handle_fallback_crc(buf)

            # TAG CHECK
            self._handle_fallback_decryption(buf)

            self.bytes_read += to_read_len
            return

        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            self._log("handle_init_packet - payload len: ", str(payload_length))
            self._log("handle_init_packet - buffer len: ", str(len(buffer)))

        self._buffer_packet_data(buffer, packet, 0)

    def _handle_fallback_crc(self, buf: memoryview) -> None:
        assert self.temp_crc is not None
        assert self.temp_crc_compare is not None
        if self.expected_payload_length > len(buf) + self.bytes_read + CHECKSUM_LENGTH:
            # The CRC checksum is not in this packet, compute crc over whole buffer
            self.temp_crc = checksum.compute_int(buf, self.temp_crc)
        elif self.expected_payload_length >= len(buf) + self.bytes_read:
            # At least a part of the CRC checksum is in this packet, compute CRC over
            # the first (max(0, crc_copy_len)) bytes and add the rest of the bytes
            # (max 4) as the checksum from message into temp_crc_compare
            crc_copy_len = (
                self.expected_payload_length - self.bytes_read - CHECKSUM_LENGTH
            )
            self.temp_crc = checksum.compute_int(buf[:crc_copy_len], self.temp_crc)

            crc_checksum = buf[
                self.expected_payload_length
                - CHECKSUM_LENGTH
                - len(buf)
                - self.bytes_read :
            ]
            offset = CHECKSUM_LENGTH - len(buf[-CHECKSUM_LENGTH:])
            utils.memcpy(self.temp_crc_compare, offset, crc_checksum, 0)
        else:
            raise Exception(
                f"Buffer (+bytes_read) ({len(buf)}+{self.bytes_read})should not be bigger than payload{self.expected_payload_length}"
            )

    def _handle_fallback_decryption(self, buf: memoryview) -> None:
        assert self.busy_decoder is not None
        assert self.temp_tag is not None
        if (
            self.expected_payload_length
            > len(buf) + self.bytes_read + CHECKSUM_LENGTH + TAG_LENGTH
        ):
            # The noise tag is not in this packet, decrypt the whole buffer
            self.busy_decoder.decrypt_part(buf)
        elif self.expected_payload_length >= len(buf) + self.bytes_read:
            # At least a part of the noise tag is in this packet, decrypt
            # the first (max(0, dec_len)) bytes and add the rest of the bytes
            # as the noise_tag from message into temp_tag
            dec_len = (
                self.expected_payload_length
                - self.bytes_read
                - TAG_LENGTH
                - CHECKSUM_LENGTH
            )
            self.busy_decoder.decrypt_part(buf[:dec_len])

            noise_tag = buf[
                self.expected_payload_length
                - CHECKSUM_LENGTH
                - TAG_LENGTH
                - len(buf)
                - self.bytes_read :
            ]
            offset = (
                TAG_LENGTH + CHECKSUM_LENGTH - len(buf[-CHECKSUM_LENGTH - TAG_LENGTH :])
            )
            utils.memcpy(self.temp_tag, offset, noise_tag, 0)
        else:
            raise Exception("Buffer (+bytes_read) should not be bigger than payload")

    def _handle_cont_packet(self, packet: utils.BufferType) -> None:
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            self._log("handle_cont_packet")

        if not self.is_cont_packet_expected:
            raise ThpError("Continuation packet is not expected, ignoring")

        if self.fallback_decrypt:
            to_read_len = min(
                len(packet) - CONT_HEADER_LENGTH,
                self.expected_payload_length - self.bytes_read,
            )
            buf = memoryview(self.buffer)[:to_read_len]
            utils.memcpy(buf, 0, packet, CONT_HEADER_LENGTH)

            # CRC CHECK
            self._handle_fallback_crc(buf)

            # TAG CHECK
            self._handle_fallback_decryption(buf)

            self.bytes_read += to_read_len
            return
        try:
            buffer = memory_manager.get_existing_read_buffer(self.get_channel_id_int())
        except WireBufferError:
            self.set_channel_state(ChannelState.INVALIDATED)
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

    def _finish_fallback(self) -> None:
        self.fallback_decrypt = False
        self.busy_decoder = None

    def _decrypt_single_packet_payload(
        self, payload: utils.BufferType
    ) -> utils.BufferType:
        # crypto.decrypt(b"\x00", b"\x00", payload_buffer, INIT_DATA_OFFSET, len(payload))
        return payload

    def _prepare_fallback(self) -> None:
        # prepare busy decoder
        key_receive = self.channel_cache.get(CHANNEL_KEY_RECEIVE)
        nonce_receive = self.channel_cache.get_int(CHANNEL_NONCE_RECEIVE)

        assert key_receive is not None
        assert nonce_receive is not None

        self.busy_decoder = crypto.BusyDecoder(key_receive, nonce_receive)

        # prepare temp channel values
        self.temp_crc = 0
        self.temp_crc_compare = bytearray(4)
        self.temp_tag = bytearray(16)
        # self.bytes_read = INIT_HEADER_LENGTH

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

            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
                self._log("Buffer before decryption: ", get_bytes_as_str(noise_buffer))

            is_tag_valid = crypto.dec(noise_buffer, tag, key_receive, nonce_receive)
            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
                self._log("Buffer after decryption: ", get_bytes_as_str(noise_buffer))

            self.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, nonce_receive + 1)

        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
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
    ) -> None:
        if __debug__ and utils.EMULATOR:
            self._log(f"write message: {msg.MESSAGE_NAME}\n", utils.dump_protobuf(msg))

        cid = self.get_channel_id_int()
        msg_size = protobuf.encoded_length(msg)
        payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size
        length = payload_size + CHECKSUM_LENGTH + TAG_LENGTH + INIT_HEADER_LENGTH
        try:
            buffer = memory_manager.get_new_write_buffer(cid, length)
            noise_payload_len = memory_manager.encode_into_buffer(
                buffer, msg, session_id
            )
        except WireBufferError:
            from trezor.enums import FailureType
            from trezor.messages import Failure

            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
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
        task = self._write_and_encrypt(noise_payload_len, force)
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
        self, noise_payload_len: int, force: bool = False
    ) -> Awaitable[None] | None:
        buffer = memory_manager.get_existing_write_buffer(self.get_channel_id_int())
        # if buffer is WireBufferError:
        # pass  # TODO handle deviceBUSY

        self._encrypt(buffer, noise_payload_len)
        payload_length = noise_payload_len + TAG_LENGTH

        if self.write_task_spawn is not None:
            self.write_task_spawn.close()  # UPS TODO might break something
            print("\nCLOSED\n")
        self._prepare_write()
        if force:
            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
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
        self, ctrl_byte: int, payload: bytes
    ) -> None:
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            self._log("write_encrypted_payload_loop")

        payload_len = len(payload) + CHECKSUM_LENGTH
        sync_bit = ABP.get_send_seq_bit(self.channel_cache)
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(ctrl_byte, sync_bit)
        header = PacketHeader(ctrl_byte, self.get_channel_id_int(), payload_len)
        self.transmission_loop = TransmissionLoop(self, header, payload)
        await self.transmission_loop.start()

        ABP.set_send_seq_bit_to_opposite(self.channel_cache)

        # Let the main loop be restarted and clear loop, if there is no other
        # workflow and the state is ENCRYPTED_TRANSPORT
        if self._can_clear_loop():
            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
                self._log("clearing loop from channel")

            loop.clear()

    def _encrypt(self, buffer: utils.BufferType, noise_payload_len: int) -> None:
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
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
            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
                self._log("New nonce_send: ", str((nonce_send + 1)))

        buffer[noise_payload_len : noise_payload_len + TAG_LENGTH] = tag

    def _can_clear_loop(self) -> bool:
        return (
            not workflow.tasks
        ) and self.get_channel_state() is ChannelState.ENCRYPTED_TRANSPORT

    if __debug__:

        def _log(self, text_1: str, text_2: str = "") -> None:
            log.debug(
                __name__,
                "(cid: %s) %s%s",
                get_bytes_as_str(self.channel_id),
                text_1,
                text_2,
            )
