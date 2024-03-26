import ustruct  # pyright: ignore[reportMissingModuleSource]
from micropython import const  # pyright: ignore[reportMissingModuleSource]
from typing import (  # pyright:ignore[reportShadowedImports]
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
)

import usb
from storage import cache_thp
from storage.cache_thp import KEY_LENGTH, TAG_LENGTH, ChannelCache
from trezor import loop, protobuf, utils

from ..protocol_common import Context
from . import ChannelState, SessionState, checksum
from . import thp_session as THP
from .checksum import CHECKSUM_LENGTH

# from . import thp_session
from .thp_messages import (
    ACK_MESSAGE,
    CONTINUATION_PACKET,
    ENCRYPTED_TRANSPORT,
    HANDSHAKE_INIT,
)
from .thp_session import ThpError

# from .thp_session import SessionState, ThpError

if TYPE_CHECKING:
    from trezorio import WireInterface  # type:ignore

    Handler = Callable[
        [bytes, Any, Any, Any], Coroutine
    ]  # TODO Adjust parameters to be more restrictive


_INIT_DATA_OFFSET = const(5)
_CONT_DATA_OFFSET = const(3)
_INIT_DATA_OFFSET = const(5)
_REPORT_CONT_DATA_OFFSET = const(3)

_WIRE_INTERFACE_USB = b"\x01"
_MOCK_INTERFACE_HID = b"\x00"

_PUBKEY_LENGTH = const(32)

_REPORT_LENGTH = const(64)
_MAX_PAYLOAD_LEN = const(60000)


class ChannelContext(Context):
    def __init__(self, channel_cache: ChannelCache) -> None:
        iface = _decode_iface(channel_cache.iface)
        super().__init__(iface, channel_cache.channel_id)
        self.channel_cache = channel_cache
        self.buffer: utils.BufferType
        self.waiting_for_ack_timeout: loop.Task | None
        self.is_cont_packet_expected: bool = False
        self.expected_payload_length: int = 0
        self.bytes_read = 0
        from trezor.wire.thp.session_context import load_cached_sessions

        self.sessions = load_cached_sessions(self)

    @classmethod
    def create_new_channel(cls, iface: WireInterface) -> "ChannelContext":
        channel_cache = cache_thp.get_new_unauthenticated_channel(_encode_iface(iface))
        return cls(channel_cache)

    # ACCESS TO CHANNEL_DATA

    def get_channel_state(self) -> ChannelState:
        state = int.from_bytes(self.channel_cache.state, "big")
        return ChannelState(state)

    def set_channel_state(self, state: ChannelState) -> None:
        self.channel_cache.state = bytearray(state.value.to_bytes(1, "big"))

    # CALLED BY THP_MAIN_LOOP

    async def receive_packet(self, packet: utils.BufferType):
        ctrl_byte = packet[0]
        if _is_ctrl_byte_continuation(ctrl_byte):
            await self._handle_cont_packet(packet)
        else:
            await self._handle_init_packet(packet)

        if self.expected_payload_length == self.bytes_read:
            self._finish_message()
            await self._handle_completed_message()

    async def _handle_init_packet(self, packet):
        ctrl_byte, _, payload_length = ustruct.unpack(">BHH", packet)
        packet_payload = packet[5:]

        # If the channel does not "own" the buffer lock, decrypt first packet
        # TODO do it only when needed!
        if _is_ctrl_byte_encrypted_transport(ctrl_byte):
            packet_payload = self._decrypt(packet_payload)

        state = self.get_channel_state()

        if state is ChannelState.ENCRYPTED_TRANSPORT:
            session_id = packet_payload[0]
            if session_id == 0:
                pass
                # TODO use small buffer
            else:
                pass
                # TODO use big buffer but only if the channel owns the buffer lock.
                # Otherwise send BUSY message and return
        else:
            pass
            # TODO use small buffer

        # TODO for now, we create a new big buffer every time. It should be changed
        self.buffer = _get_buffer_for_payload(payload_length, self.buffer)

        await self._buffer_packet_data(self.buffer, packet, 0)

    async def _handle_cont_packet(self, packet):
        if not self.is_cont_packet_expected:
            return  # Continuation packet is not expected, ignoring
        await self._buffer_packet_data(self.buffer, packet, _CONT_DATA_OFFSET)

    async def _handle_completed_message(self):
        ctrl_byte, _, payload_length = ustruct.unpack(">BHH", self.buffer)
        msg_len = payload_length + _INIT_DATA_OFFSET
        if not checksum.is_valid(
            checksum=self.buffer[msg_len - CHECKSUM_LENGTH : msg_len],
            data=self.buffer[: msg_len - CHECKSUM_LENGTH],
        ):
            # checksum is not valid -> ignore message
            self._todo_clear_buffer()
            return

        sync_bit = (ctrl_byte & 0x10) >> 4
        if _is_ctrl_byte_ack(ctrl_byte):
            self._handle_received_ACK(sync_bit)
            self._todo_clear_buffer()
            return

        state = self.get_channel_state()

        if state is ChannelState.TH1:
            if not _is_ctrl_byte_handshake_init:
                raise ThpError("Message received is not a handshake init request!")
            if not payload_length == _PUBKEY_LENGTH + CHECKSUM_LENGTH:
                raise ThpError(
                    "Message received is not a valid handshake init request!"
                )
            host_ephemeral_key = bytearray(
                self.buffer[_INIT_DATA_OFFSET : msg_len - CHECKSUM_LENGTH]
            )
            cache_thp.set_channel_host_ephemeral_key(
                self.channel_cache, host_ephemeral_key
            )
            # TODO send ack in response
            # TODO send handshake init response message
            self.set_channel_state(ChannelState.TH2)
            return

        if not _is_ctrl_byte_encrypted_transport(ctrl_byte):
            # TODO ignore message
            self._todo_clear_buffer()
            return

        if state is ChannelState.ENCRYPTED_TRANSPORT:
            self._decrypt_buffer()
            session_id, message_type = ustruct.unpack(
                ">BH", self.buffer[_INIT_DATA_OFFSET:]
            )
            if session_id not in self.sessions:
                raise Exception("Unalloacted session")

            session_state = self.sessions[session_id].get_session_state()
            if session_state is SessionState.UNALLOCATED:
                raise Exception("Unalloacted session")

            await self.sessions[session_id].receive_message(
                message_type,
                self.buffer[_INIT_DATA_OFFSET + 3 : msg_len - CHECKSUM_LENGTH],
            )

        if state is ChannelState.TH2:
            host_encrypted_static_pubkey = self.buffer[
                _INIT_DATA_OFFSET : _INIT_DATA_OFFSET + KEY_LENGTH + TAG_LENGTH
            ]
            handshake_completion_request_noise_payload = self.buffer[
                _INIT_DATA_OFFSET + KEY_LENGTH + TAG_LENGTH : msg_len - CHECKSUM_LENGTH
            ]
            print(
                host_encrypted_static_pubkey,
                handshake_completion_request_noise_payload,
            )  # TODO remove
            # TODO send ack in response
            # TODO send hanshake completion response
            self.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)

    def _decrypt(self, payload) -> bytes:
        return payload  # TODO add decryption process

    def _decrypt_buffer(self) -> None:
        pass
        # TODO decode buffer in place

    async def _buffer_packet_data(
        self, payload_buffer, packet: utils.BufferType, offset
    ):
        self.bytes_read += utils.memcpy(payload_buffer, self.bytes_read, packet, offset)

    def _finish_message(self):
        self.bytes_read = 0
        self.expected_payload_length = 0
        self.is_cont_packet_expected = False

    def _get_handler(self) -> Handler:
        state = self.get_channel_state()
        if state is ChannelState.UNAUTHENTICATED:
            return self._handler_unauthenticated
        if state is ChannelState.ENCRYPTED_TRANSPORT:
            return self._handler_encrypted_transport
        raise Exception("Unimplemented situation")

    # Handlers for init packets
    # TODO adjust
    async def _handler_encrypted_transport(
        self, ctrl_byte: bytes, payload_length: int, packet_payload: bytes, packet
    ) -> None:
        self.expected_payload_length = payload_length
        self.bytes_read = 0

        await self._buffer_packet_data(self.buffer, packet, _INIT_DATA_OFFSET)
        # TODO Set/Provide different buffer for management session

        if self.expected_payload_length == self.bytes_read:
            self._finish_message()
        else:
            self.is_cont_packet_expected = True

    # TODO adjust
    async def _handler_unauthenticated(
        self, ctrl_byte: bytes, payload_length: int, packet_payload: bytes, packet
    ) -> None:
        self.expected_payload_length = payload_length
        self.bytes_read = 0

        await self._buffer_packet_data(self.buffer, packet, _INIT_DATA_OFFSET)
        # TODO Set/Provide different buffer for management session

        if self.expected_payload_length == self.bytes_read:
            self._finish_message()
        else:
            self.is_cont_packet_expected = True

    # CALLED BY WORKFLOW / SESSION CONTEXT

    async def write(self, msg: protobuf.MessageType, session_id: int = 0) -> None:
        pass
        # TODO protocol.write(self.iface, self.channel_id, session_id, msg)

    def create_new_session(
        self,
        passphrase="",
    ) -> None:  # TODO change it to output session data
        pass
        # create a new session with this passphrase

    # OTHER

    def _todo_clear_buffer(self):
        raise NotImplementedError()

    # TODO add debug logging to ACK handling
    def _handle_received_ACK(self, sync_bit: int) -> None:
        if self._ack_is_not_expected():
            return
        if self._ack_has_incorrect_sync_bit(sync_bit):
            return

        if self.waiting_for_ack_timeout is not None:
            self.waiting_for_ack_timeout.close()

        THP.sync_set_can_send_message(self.channel_cache, True)

    def _ack_is_not_expected(self) -> bool:
        return THP.sync_can_send_message(self.channel_cache)

    def _ack_has_incorrect_sync_bit(self, sync_bit: int) -> bool:
        return THP.sync_get_send_bit(self.channel_cache) != sync_bit


def load_cached_channels() -> dict[int, ChannelContext]:  # TODO
    channels: dict[int, ChannelContext] = {}
    cached_channels = cache_thp.get_all_allocated_channels()
    for c in cached_channels:
        channels[int.from_bytes(c.channel_id, "big")] = ChannelContext(c)
    return channels


def _decode_iface(cached_iface: bytes) -> WireInterface:
    if cached_iface == _WIRE_INTERFACE_USB:
        iface = usb.iface_wire
        if iface is None:
            raise RuntimeError("There is no valid USB WireInterface")
        return iface
    if __debug__ and cached_iface == _MOCK_INTERFACE_HID:
        # TODO"Not implemented, should return MockHID WireInterface
        return None
    # TODO implement bluetooth interface
    raise Exception("Unknown WireInterface")


def _encode_iface(iface: WireInterface) -> bytes:
    if iface is usb.iface_wire:
        return _WIRE_INTERFACE_USB
    # TODO implement bluetooth interface
    if __debug__:
        return _MOCK_INTERFACE_HID
    raise Exception("Unknown WireInterface")


def _is_ctrl_byte_continuation(ctrl_byte: int) -> bool:
    return ctrl_byte & 0x80 == CONTINUATION_PACKET


def _is_ctrl_byte_encrypted_transport(ctrl_byte: int) -> bool:
    return ctrl_byte & 0xEF == ENCRYPTED_TRANSPORT


def _is_ctrl_byte_handshake_init(ctrl_byte: int) -> bool:
    return ctrl_byte & 0xEF == HANDSHAKE_INIT


def _is_ctrl_byte_ack(ctrl_byte: int) -> bool:
    return ctrl_byte & 0xEF == ACK_MESSAGE


def _get_buffer_for_payload(
    payload_length: int, existing_buffer: utils.BufferType, max_length=_MAX_PAYLOAD_LEN
) -> utils.BufferType:
    if payload_length > max_length:
        raise ThpError("Message too large")
    if payload_length > len(existing_buffer):
        # allocate a new buffer to fit the message
        try:
            payload: utils.BufferType = bytearray(payload_length)
        except MemoryError:
            payload = bytearray(_REPORT_LENGTH)
            raise ThpError("Message too large")
        return payload

    # reuse a part of the supplied buffer
    return memoryview(existing_buffer)[:payload_length]
