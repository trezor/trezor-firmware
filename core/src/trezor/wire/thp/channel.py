import ustruct
from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
)
from storage.cache_thp import TAG_LENGTH, ChannelCache, clear_sessions_with_channel_id
from trezor import log, loop, protobuf, utils, workflow
from trezor.wire.thp.transmission_loop import TransmissionLoop

from . import ChannelState, ThpDecryptionError, ThpError
from . import alternating_bit_protocol as ABP
from . import (
    control_byte,
    crypto,
    interface_manager,
    memory_manager,
    received_message_handler,
    session_manager,
)
from .checksum import CHECKSUM_LENGTH
from .thp_messages import ENCRYPTED_TRANSPORT, PacketHeader
from .writer import (
    CONT_HEADER_LENGTH,
    INIT_HEADER_LENGTH,
    write_payload_to_wire_and_add_checksum,
)

if __debug__:
    from ubinascii import hexlify

    from . import state_to_str

if TYPE_CHECKING:
    from trezorio import WireInterface

    from .pairing_context import PairingContext
    from .session_context import GenericSessionContext


class Channel:
    def __init__(self, channel_cache: ChannelCache) -> None:
        if __debug__:
            log.debug(__name__, "channel initialization")
        self.iface: WireInterface = interface_manager.decode_iface(channel_cache.iface)
        self.channel_cache: ChannelCache = channel_cache
        self.is_cont_packet_expected: bool = False
        self.expected_payload_length: int = 0
        self.bytes_read: int = 0
        self.buffer: utils.BufferType
        self.channel_id: bytes = channel_cache.channel_id
        self.selected_pairing_methods = []
        self.sessions: dict[int, GenericSessionContext] = {}
        self.write_task_spawn: loop.spawn | None = None
        self.connection_context: PairingContext | None = None
        self.transmission_loop: TransmissionLoop | None = None
        self.handshake: crypto.Handshake | None = None

        self._create_management_session()

    def clear(self):
        clear_sessions_with_channel_id(self.channel_id)
        self.channel_cache.clear()

    # ACCESS TO CHANNEL_DATA
    def get_channel_id_int(self) -> int:
        return int.from_bytes(self.channel_id, "big")

    def get_channel_state(self) -> int:
        state = int.from_bytes(self.channel_cache.state, "big")
        if __debug__:
            log.debug(__name__, "get_channel_state: %s", state_to_str(state))
        return state

    def get_handshake_hash(self) -> bytes:
        h = self.channel_cache.get(CHANNEL_HANDSHAKE_HASH)
        assert h is not None
        return h

    def set_channel_state(self, state: ChannelState) -> None:
        self.channel_cache.state = bytearray(state.to_bytes(1, "big"))
        if __debug__:
            log.debug(__name__, "set_channel_state: %s", state_to_str(state))

    def set_buffer(self, buffer: utils.BufferType) -> None:
        self.buffer = buffer
        if __debug__:
            log.debug(__name__, "set_buffer: %s", type(self.buffer))

    def _create_management_session(self) -> None:
        session = session_manager.create_new_management_session(self)
        self.sessions[session.session_id] = session
        loop.schedule(session.handle())

    # CALLED BY THP_MAIN_LOOP

    async def receive_packet(self, packet: utils.BufferType):
        if __debug__:
            log.debug(__name__, "receive_packet")

        await self._handle_received_packet(packet)

        if __debug__:
            log.debug(__name__, "self.buffer: %s", utils.get_bytes_as_str(self.buffer))

        if self.expected_payload_length + INIT_HEADER_LENGTH == self.bytes_read:
            self._finish_message()
            await received_message_handler.handle_received_message(self, self.buffer)
        elif self.expected_payload_length + INIT_HEADER_LENGTH > self.bytes_read:
            self.is_cont_packet_expected = True
        else:
            raise ThpError(
                "Read more bytes than is the expected length of the message!"
            )

    async def _handle_received_packet(self, packet: utils.BufferType) -> None:
        ctrl_byte = packet[0]
        if control_byte.is_continuation(ctrl_byte):
            await self._handle_cont_packet(packet)
        else:
            await self._handle_init_packet(packet)

    async def _handle_init_packet(self, packet: utils.BufferType) -> None:
        if __debug__:
            log.debug(__name__, "handle_init_packet")
        # ctrl_byte, _, payload_length = ustruct.unpack(">BHH", packet) # TODO use this with single packet decryption
        _, _, payload_length = ustruct.unpack(">BHH", packet)
        self.expected_payload_length = payload_length
        packet_payload = memoryview(packet)[INIT_HEADER_LENGTH:]

        # If the channel does not "own" the buffer lock, decrypt first packet
        # TODO do it only when needed!
        # TODO FIX: If "_decrypt_single_packet_payload" is implemented, it will (possibly) break "decrypt_buffer" and nonces incrementation.
        # On the other hand, without the single packet decryption, the "advanced" buffer selection cannot be implemented
        # in "memory_manager.select_buffer", because the session id is unknown (encrypted).

        # if control_byte.is_encrypted_transport(ctrl_byte):
        #   packet_payload = self._decrypt_single_packet_payload(packet_payload)

        self.buffer = memory_manager.select_buffer(
            self.get_channel_state(),
            self.buffer,
            packet_payload,
            payload_length,
        )
        await self._buffer_packet_data(self.buffer, packet, 0)

        if __debug__:
            log.debug(__name__, "handle_init_packet - payload len: %d", payload_length)
            log.debug(__name__, "handle_init_packet - buffer len: %d", len(self.buffer))

    async def _handle_cont_packet(self, packet: utils.BufferType) -> None:
        if __debug__:
            log.debug(__name__, "handle_cont_packet")
        if not self.is_cont_packet_expected:
            raise ThpError("Continuation packet is not expected, ignoring")
        await self._buffer_packet_data(self.buffer, packet, CONT_HEADER_LENGTH)

    def _decrypt_single_packet_payload(
        self, payload: utils.BufferType
    ) -> utils.BufferType:
        # crypto.decrypt(b"\x00", b"\x00", payload_buffer, INIT_DATA_OFFSET, len(payload))
        return payload

    def decrypt_buffer(
        self, message_length: int, offset: int = INIT_HEADER_LENGTH
    ) -> None:
        noise_buffer = memoryview(self.buffer)[
            offset : message_length - CHECKSUM_LENGTH - TAG_LENGTH
        ]
        tag = self.buffer[
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

            print("Buffer before decryption:", hexlify(noise_buffer))
            is_tag_valid = crypto.dec(
                noise_buffer, tag, key_receive, nonce_receive, b""
            )
            print("Buffer after decryption:", hexlify(noise_buffer))

            self.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, nonce_receive + 1)

        if __debug__:
            log.debug(__name__, "Is decrypted tag valid? %s", str(is_tag_valid))
            log.debug(__name__, "Received tag: %s", (hexlify(tag).decode()))
            log.debug(__name__, "New nonce_receive: %i", nonce_receive + 1)

        if not is_tag_valid:
            raise ThpDecryptionError()

    def _encrypt(self, buffer: utils.BufferType, noise_payload_len: int) -> None:
        if __debug__:
            log.debug(__name__, "encrypt")
        assert len(buffer) >= noise_payload_len + TAG_LENGTH + CHECKSUM_LENGTH

        noise_buffer = memoryview(buffer)[0:noise_payload_len]

        if utils.DISABLE_ENCRYPTION:
            tag = crypto.DUMMY_TAG
        else:
            key_send = self.channel_cache.get(CHANNEL_KEY_SEND)
            nonce_send = self.channel_cache.get_int(CHANNEL_NONCE_SEND)

            assert key_send is not None
            assert nonce_send is not None

            tag = crypto.enc(noise_buffer, key_send, nonce_send, b"")

            self.channel_cache.set_int(CHANNEL_NONCE_SEND, nonce_send + 1)
            if __debug__:
                log.debug(__name__, "New nonce_send: %i", nonce_send + 1)

        buffer[noise_payload_len : noise_payload_len + TAG_LENGTH] = tag

    async def _buffer_packet_data(
        self, payload_buffer: utils.BufferType, packet: utils.BufferType, offset: int
    ):
        self.bytes_read += utils.memcpy(payload_buffer, self.bytes_read, packet, offset)

    def _finish_message(self):
        self.bytes_read = 0
        self.expected_payload_length = 0
        self.is_cont_packet_expected = False

    # CALLED BY WORKFLOW / SESSION CONTEXT

    async def write(self, msg: protobuf.MessageType, session_id: int = 0) -> None:
        if __debug__ and utils.EMULATOR:
            log.debug(
                __name__,
                "write message: %s\n%s",
                msg.MESSAGE_NAME,
                utils.dump_protobuf(msg),
            )

        self.buffer = memory_manager.get_write_buffer(self.buffer, msg)
        noise_payload_len = memory_manager.encode_into_buffer(
            self.buffer, msg, session_id
        )
        await self.write_and_encrypt(self.buffer[:noise_payload_len])

    async def write_error(self, err_type: int):
        msg_data = err_type.to_bytes(1, "big")
        length = len(msg_data) + CHECKSUM_LENGTH
        header = PacketHeader.get_error_header(self.get_channel_id_int(), length)
        await write_payload_to_wire_and_add_checksum(self.iface, header, msg_data)

    async def write_and_encrypt(self, payload: bytes) -> None:
        payload_length = len(payload)

        if not isinstance(self.buffer, bytearray):
            self.buffer = bytearray(self.buffer)
        self._encrypt(self.buffer, payload_length)
        payload_length = payload_length + TAG_LENGTH

        if self.write_task_spawn is not None:
            self.write_task_spawn.close()  # UPS TODO might break something
            print("\nCLOSED\n")
        self._prepare_write()
        self.write_task_spawn = loop.spawn(
            self._write_encrypted_payload_loop(
                ENCRYPTED_TRANSPORT, memoryview(self.buffer[:payload_length])
            )
        )

    async def write_handshake_message(self, ctrl_byte: int, payload: bytes) -> None:
        self._prepare_write()
        self.write_task_spawn = loop.spawn(
            self._write_encrypted_payload_loop(ctrl_byte, payload)
        )

    def _prepare_write(self) -> None:
        # TODO add condition that disallows to write when can_send_message is false
        ABP.set_sending_allowed(self.channel_cache, False)

    async def _write_encrypted_payload_loop(
        self, ctrl_byte: int, payload: bytes
    ) -> None:
        if __debug__:
            log.debug(__name__, "write_encrypted_payload_loop")
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
            if __debug__:
                log.debug(__name__, "clearing loop from channel")
            loop.clear()

    def _can_clear_loop(self) -> bool:
        return (
            not workflow.tasks
        ) and self.get_channel_state() is ChannelState.ENCRYPTED_TRANSPORT
