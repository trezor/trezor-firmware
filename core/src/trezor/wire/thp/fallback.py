from typing import TYPE_CHECKING

from storage.cache_common import CHANNEL_KEY_RECEIVE, CHANNEL_NONCE_RECEIVE
from storage.cache_thp import TAG_LENGTH
from trezor import utils
from trezor.wire.errors import DataError
from trezor.wire.thp import received_message_handler
from trezor.wire.thp.writer import INIT_HEADER_LENGTH

from . import checksum, control_byte
from .checksum import CHECKSUM_LENGTH
from .crypto import BusyDecoder

if TYPE_CHECKING:
    from typing import Awaitable

    from .channel import Channel


class Fallback:
    _busy_decoder: BusyDecoder | None = None
    _noise_tag: bytearray | None = None
    session_id: int | None = None

    def __init__(self, channel: Channel, init_packet: memoryview) -> None:
        if len(init_packet) <= INIT_HEADER_LENGTH + CHECKSUM_LENGTH:
            raise ValueError("Invalid init packet - too short")

        self._channel: Channel = channel
        self.ctrl_byte: int = init_packet[0]
        self._crc_compare: bytearray = bytearray(4)
        self._is_finished: bool = False

        self._crc: int = checksum.compute_int(init_packet[:INIT_HEADER_LENGTH])

    def read_init_packet(self, buf: memoryview) -> Awaitable[None] | None:
        self._handle_crc(buf)

        # If the message has only one packet, handle ACK messages
        if len(buf) == self._channel.expected_payload_length:
            if not self._is_crc_checksum_valid():
                return None
            if control_byte.is_ack(self.ctrl_byte):
                ack_bit = control_byte.get_ack_bit(self.ctrl_byte)
                return received_message_handler.handle_ack(self._channel, ack_bit)

        self._prepare_decryption(buf)
        self._handle_decryption(buf)
        return None

    def read_cont_packet(self, buf: memoryview) -> None:
        self._handle_crc(buf)
        self._handle_decryption(buf)

    def finish(self) -> None:
        if self._is_finished:
            raise Exception("Fallback already finished!")
        self._is_finished = True

    def is_crc_checksum_valid(self) -> bool:
        if not self._is_finished:
            raise Exception("Fallback is not finished yet!")
        return self._is_crc_checksum_valid()

    def _is_crc_checksum_valid(self) -> bool:
        assert self._crc_compare is not None
        return self._crc.to_bytes(4, "big") == self._crc_compare

    def is_noise_tag_valid(self) -> bool:
        if not self._is_finished:
            raise Exception("Fallback is not finished yet!")
        assert self._busy_decoder is not None
        assert self._noise_tag is not None
        return self._busy_decoder.finish_and_check_tag(self._noise_tag)

    def _handle_crc(self, buf: memoryview) -> None:
        if (
            self._channel.expected_payload_length
            > len(buf) + self._channel.bytes_read + CHECKSUM_LENGTH
        ):
            # The CRC checksum is not in this packet, compute crc over whole buffer
            self._crc = checksum.compute_int(buf, self._crc)
        elif (
            self._channel.expected_payload_length >= len(buf) + self._channel.bytes_read
        ):
            # At least a part of the CRC checksum is in this packet, compute CRC over
            # the first (max(0, crc_copy_len)) bytes and add the rest of the bytes
            # (max 4) as the checksum from message into temp_crc_compare
            crc_copy_len = (
                self._channel.expected_payload_length
                - self._channel.bytes_read
                - CHECKSUM_LENGTH
            )
            self._crc = checksum.compute_int(buf[:crc_copy_len], self._crc)

            crc_checksum = buf[
                self._channel.expected_payload_length
                - CHECKSUM_LENGTH
                - len(buf)
                - self._channel.bytes_read :
            ]
            offset = CHECKSUM_LENGTH - len(buf[-CHECKSUM_LENGTH:])
            utils.memcpy(self._crc_compare, offset, crc_checksum, 0)
        else:
            raise DataError(
                f"Buffer (+bytes_read) ({len(buf)}+{self._channel.bytes_read})should not be bigger than payload{self._channel.expected_payload_length}"
            )

    def _prepare_decryption(self, buf: memoryview) -> None:
        key_receive = self._channel.channel_cache.get(CHANNEL_KEY_RECEIVE)
        nonce_receive = self._channel.channel_cache.get_int(CHANNEL_NONCE_RECEIVE)

        assert key_receive is not None
        assert nonce_receive is not None

        self._busy_decoder = BusyDecoder(key_receive, nonce_receive)
        self._noise_tag = bytearray(16)

    def _handle_decryption(self, buf: memoryview) -> None:
        if self._busy_decoder is None:
            raise Exception("Fallback decryption is not prepared")

        assert self._noise_tag is not None

        if (
            self._channel.expected_payload_length
            > len(buf) + self._channel.bytes_read + CHECKSUM_LENGTH + TAG_LENGTH
        ):
            # The noise tag is not in this packet, decrypt the whole buffer
            self._busy_decoder.decrypt_part(buf)
        elif (
            self._channel.expected_payload_length >= len(buf) + self._channel.bytes_read
        ):
            # At least a part of the noise tag is in this packet, decrypt
            # the first (max(0, dec_len)) bytes and add the rest of the bytes
            # as the noise_tag from message into temp_tag
            dec_len = (
                self._channel.expected_payload_length
                - self._channel.bytes_read
                - TAG_LENGTH
                - CHECKSUM_LENGTH
            )
            self._busy_decoder.decrypt_part(buf[:dec_len])

            noise_tag = buf[
                self._channel.expected_payload_length
                - CHECKSUM_LENGTH
                - TAG_LENGTH
                - len(buf)
                - self._channel.bytes_read :
            ]
            offset = (
                TAG_LENGTH + CHECKSUM_LENGTH - len(buf[-CHECKSUM_LENGTH - TAG_LENGTH :])
            )
            utils.memcpy(self._noise_tag, offset, noise_tag, 0)
        else:
            raise Exception("Buffer (+bytes_read) should not be bigger than payload")
        if self.session_id is None:
            self.session_id = buf[0]
