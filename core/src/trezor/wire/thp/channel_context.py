import ustruct  # pyright: ignore[reportMissingModuleSource]
from micropython import const  # pyright: ignore[reportMissingModuleSource]
from typing import TYPE_CHECKING  # pyright:ignore[reportShadowedImports]
from ubinascii import hexlify

import usb
from storage import cache_thp
from storage.cache_thp import KEY_LENGTH, TAG_LENGTH, ChannelCache
from trezor import loop, protobuf, utils
from trezor.messages import CreateNewSession
from trezor.wire import message_handler

from ..protocol_common import Context
from . import ChannelState, SessionState, checksum
from . import thp_session as THP
from .checksum import CHECKSUM_LENGTH
from .thp_messages import (
    ACK_MESSAGE,
    CONTINUATION_PACKET,
    ENCRYPTED_TRANSPORT,
    HANDSHAKE_INIT,
)
from .thp_session import ThpError

if TYPE_CHECKING:
    from trezorio import WireInterface  # pyright:ignore[reportMissingImports]


_WIRE_INTERFACE_USB = b"\x01"
_MOCK_INTERFACE_HID = b"\x00"

_PUBKEY_LENGTH = const(32)

INIT_DATA_OFFSET = const(5)
CONT_DATA_OFFSET = const(3)


REPORT_LENGTH = const(64)
MAX_PAYLOAD_LEN = const(60000)


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
    def create_new_channel(
        cls, iface: WireInterface, buffer: utils.BufferType
    ) -> "ChannelContext":
        channel_cache = cache_thp.get_new_unauthenticated_channel(_encode_iface(iface))
        r = cls(channel_cache)
        r.set_buffer(buffer)
        r.set_channel_state(ChannelState.TH1)
        return r

    # ACCESS TO CHANNEL_DATA

    def get_channel_state(self) -> int:
        state = int.from_bytes(self.channel_cache.state, "big")
        print("get_ch_state", state)
        return state

    def set_channel_state(self, state: ChannelState) -> None:
        print("set_ch_state", int.from_bytes(state.to_bytes(1, "big"), "big"))
        self.channel_cache.state = bytearray(state.to_bytes(1, "big"))

    def set_buffer(self, buffer: utils.BufferType) -> None:
        self.buffer = buffer
        print("set buffer channel", type(self.buffer))

    # CALLED BY THP_MAIN_LOOP

    async def receive_packet(self, packet: utils.BufferType):
        print("receive packet")
        ctrl_byte = packet[0]
        if _is_ctrl_byte_continuation(ctrl_byte):
            await self._handle_cont_packet(packet)
        else:
            await self._handle_init_packet(packet)

        if self.expected_payload_length + INIT_DATA_OFFSET == self.bytes_read:
            self._finish_message()
            await self._handle_completed_message()

    async def _handle_init_packet(self, packet: utils.BufferType):
        print("handle_init_packet")
        ctrl_byte, _, payload_length = ustruct.unpack(">BHH", packet)
        self.expected_payload_length = payload_length
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
        print("self.buffer2")
        try:
            # TODO for now, we create a new big buffer every time. It should be changed
            self.buffer: utils.BufferType = _get_buffer_for_message(
                payload_length, self.buffer
            )
        except Exception as e:
            print(e)
        print("payload len", payload_length)
        print("self.buffer", self.buffer)
        print("self.buuffer.type", type(self.buffer))
        print("len", len(self.buffer))
        await self._buffer_packet_data(self.buffer, packet, 0)
        print("end init")

    async def _handle_cont_packet(self, packet: utils.BufferType):
        print("cont")
        if not self.is_cont_packet_expected:
            return  # Continuation packet is not expected, ignoring
        await self._buffer_packet_data(self.buffer, packet, CONT_DATA_OFFSET)

    async def _handle_completed_message(self):
        print("handling completed message")
        ctrl_byte, _, payload_length = ustruct.unpack(">BHH", self.buffer)
        msg_len = payload_length + INIT_DATA_OFFSET
        print("checksum check")
        printBytes(self.buffer)
        if not checksum.is_valid(
            checksum=self.buffer[msg_len - CHECKSUM_LENGTH : msg_len],
            data=self.buffer[: msg_len - CHECKSUM_LENGTH],
        ):
            # checksum is not valid -> ignore message
            self._todo_clear_buffer()
            return
        print("sync bit")
        sync_bit = (ctrl_byte & 0x10) >> 4
        if _is_ctrl_byte_ack(ctrl_byte):
            self._handle_received_ACK(sync_bit)
            self._todo_clear_buffer()
            return

        state = self.get_channel_state()
        _print_state(state)

        if state is ChannelState.TH1:
            if not _is_ctrl_byte_handshake_init:
                raise ThpError("Message received is not a handshake init request!")
            if not payload_length == _PUBKEY_LENGTH + CHECKSUM_LENGTH:
                raise ThpError(
                    "Message received is not a valid handshake init request!"
                )
            host_ephemeral_key = bytearray(
                self.buffer[INIT_DATA_OFFSET : msg_len - CHECKSUM_LENGTH]
            )
            cache_thp.set_channel_host_ephemeral_key(
                self.channel_cache, host_ephemeral_key
            )
            # TODO send ack in response
            # TODO send handshake init response message
            self.set_channel_state(ChannelState.TH2)
            return

        if not _is_ctrl_byte_encrypted_transport(ctrl_byte):
            print("message is not encrypted. Ignoring")
            # TODO ignore message
            self._todo_clear_buffer()
            return

        if state is ChannelState.ENCRYPTED_TRANSPORT:
            self._decrypt_buffer()
            session_id, message_type = ustruct.unpack(
                ">BH", self.buffer[INIT_DATA_OFFSET:]
            )
            if session_id == 0:
                try:
                    buf = self.buffer[INIT_DATA_OFFSET + 3 : msg_len - CHECKSUM_LENGTH]

                    expected_type = protobuf.type_for_wire(message_type)
                    message = message_handler.wrap_protobuf_load(buf, expected_type)
                    print(message)
                    # ------------------------------------------------TYPE ERROR------------------------------------------------
                    session_message: CreateNewSession = message
                    print("passphrase:", session_message.passphrase)
                    # await thp_messages.handle_CreateNewSession(message)
                    if session_message.passphrase is not None:
                        self.create_new_session(session_message.passphrase)
                    else:
                        self.create_new_session()
                except Exception as e:
                    print("Proč??")
                    print(e)
                return
                # TODO not finished

            if session_id not in self.sessions:
                raise Exception("Unalloacted session")

            session_state = self.sessions[session_id].get_session_state()
            if session_state is SessionState.UNALLOCATED:
                raise Exception("Unalloacted session")

            await self.sessions[session_id].receive_message(
                message_type,
                self.buffer[INIT_DATA_OFFSET + 3 : msg_len - CHECKSUM_LENGTH],
            )

        if state is ChannelState.TH2:
            print("th2 branche")
            host_encrypted_static_pubkey = self.buffer[
                INIT_DATA_OFFSET : INIT_DATA_OFFSET + KEY_LENGTH + TAG_LENGTH
            ]
            handshake_completion_request_noise_payload = self.buffer[
                INIT_DATA_OFFSET + KEY_LENGTH + TAG_LENGTH : msg_len - CHECKSUM_LENGTH
            ]
            print(
                host_encrypted_static_pubkey,
                handshake_completion_request_noise_payload,
            )  # TODO remove
            # TODO send ack in response
            # TODO send hanshake completion response
            self.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)
        print("end completed message")

    def _decrypt(self, payload) -> bytes:
        return payload  # TODO add decryption process

    def _decrypt_buffer(self) -> None:
        pass
        # TODO decode buffer in place

    async def _buffer_packet_data(
        self, payload_buffer: utils.BufferType, packet: utils.BufferType, offset: int
    ):
        self.bytes_read += utils.memcpy(payload_buffer, self.bytes_read, packet, offset)
        print("bytes, read:", self.bytes_read)

    def _finish_message(self):
        self.bytes_read = 0
        self.expected_payload_length = 0
        self.is_cont_packet_expected = False

    # CALLED BY WORKFLOW / SESSION CONTEXT

    async def write(self, msg: protobuf.MessageType, session_id: int = 0) -> None:
        pass
        # TODO protocol.write(self.iface, self.channel_id, session_id, msg)

    def create_new_session(
        self,
        passphrase="",
    ) -> None:  # TODO change it to output session data
        print("create new session")
        from trezor.wire.thp.session_context import SessionContext

        session = SessionContext.create_new_session(self)
        print("help")
        self.sessions[session.session_id] = session
        print("new session created. Session id:", session.session_id)

    # OTHER

    def _todo_clear_buffer(self):
        # TODO Buffer clearing not implemented
        pass

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


def load_cached_channels(buffer: utils.BufferType) -> dict[int, ChannelContext]:  # TODO
    channels: dict[int, ChannelContext] = {}
    cached_channels = cache_thp.get_all_allocated_channels()
    for c in cached_channels:
        channels[int.from_bytes(c.channel_id, "big")] = ChannelContext(c)
    for c in channels.values():
        c.set_buffer(buffer)
    return channels


def _decode_iface(cached_iface: bytes) -> WireInterface:
    if cached_iface == _WIRE_INTERFACE_USB:
        iface = usb.iface_wire
        if iface is None:
            raise RuntimeError("There is no valid USB WireInterface")
        return iface
    if __debug__ and cached_iface == _MOCK_INTERFACE_HID:
        raise NotImplementedError("Should return MockHID WireInterface")
    # TODO implement bluetooth interface
    raise Exception("Unknown WireInterface")


def _encode_iface(iface: WireInterface) -> bytes:
    if iface is usb.iface_wire:
        return _WIRE_INTERFACE_USB
    # TODO implement bluetooth interface
    if __debug__:
        return _MOCK_INTERFACE_HID
    raise Exception("Unknown WireInterface")


def _get_buffer_for_message(
    payload_length: int, existing_buffer: utils.BufferType, max_length=MAX_PAYLOAD_LEN
) -> utils.BufferType:
    length = payload_length + INIT_DATA_OFFSET
    print("length", length)
    print("existing buffer type", type(existing_buffer))
    if length > max_length:
        raise ThpError("Message too large")

    if length > len(existing_buffer):
        # allocate a new buffer to fit the message
        try:
            payload: utils.BufferType = bytearray(length)
        except MemoryError:
            payload = bytearray(REPORT_LENGTH)
            raise ThpError("Message too large")
        return payload

    # reuse a part of the supplied buffer
    return memoryview(existing_buffer)[:length]


def _is_ctrl_byte_continuation(ctrl_byte: int) -> bool:
    return ctrl_byte & 0x80 == CONTINUATION_PACKET


def _is_ctrl_byte_encrypted_transport(ctrl_byte: int) -> bool:
    return ctrl_byte & 0xEF == ENCRYPTED_TRANSPORT


def _is_ctrl_byte_handshake_init(ctrl_byte: int) -> bool:
    return ctrl_byte & 0xEF == HANDSHAKE_INIT


def _is_ctrl_byte_ack(ctrl_byte: int) -> bool:
    return ctrl_byte & 0xEF == ACK_MESSAGE


def _print_state(cs: int) -> None:
    if cs == ChannelState.ENCRYPTED_TRANSPORT:
        print("state: encrypted transport")
    elif cs == ChannelState.TH1:
        print("state: th1")
    elif cs == ChannelState.TH2:
        print("state: th2")
    elif cs == ChannelState.TP1:
        print("state: tp1")
    elif cs == ChannelState.TP2:
        print("state: tp2")
    elif cs == ChannelState.TP3:
        print("state: tp3")
    elif cs == ChannelState.TP4:
        print("state: tp4")
    elif cs == ChannelState.TP5:
        print("state: tp5")
    elif cs == ChannelState.UNALLOCATED:
        print("state: unallocated")
    elif cs == ChannelState.UNAUTHENTICATED:
        print("state: unauthenticated")
    else:
        print(cs)
        print("state: <not implemented printout>")


def printBytes(a):
    print(hexlify(a).decode("utf-8"))
