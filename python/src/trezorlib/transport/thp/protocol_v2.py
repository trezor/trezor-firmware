# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import logging
import os
import typing as t
from binascii import hexlify

from noise.connection import Keypair, NoiseConnection

from ... import exceptions, messages, protobuf
from ...mapping import ProtobufMapping
from .. import Transport
from ..thp import checksum, thp_io
from ..thp.checksum import CHECKSUM_LENGTH
from ..thp.message_header import MessageHeader
from . import control_byte
from .channel import Channel

LOG = logging.getLogger(__name__)

DEFAULT_SESSION_ID: int = 0

MAX_RETRANSMISSION_COUNT = 50

TREZOR_STATE_UNPAIRED = b"\x00"
TREZOR_STATE_PAIRED = b"\x01"
TREZOR_STATE_PAIRED_AUTOCONNECT = b"\x02"
TREZOR_STATES = [
    TREZOR_STATE_UNPAIRED,
    TREZOR_STATE_PAIRED,
    TREZOR_STATE_PAIRED_AUTOCONNECT,
]

if t.TYPE_CHECKING:
    pass
MT = t.TypeVar("MT", bound=protobuf.MessageType)


class ProtocolV2Channel(Channel):
    channel_id: int
    sync_bit_send: int
    sync_bit_receive: int
    handshake_hash: bytes
    device_properties: bytes

    _features: messages.Features | None = None
    _is_paired: bool = False

    def __init__(
        self,
        transport: Transport,
        mapping: ProtobufMapping,
        credential: bytes | None = None,
        prepare_channel_without_pairing: bool = True,
    ) -> None:
        super().__init__(transport, mapping)
        self._reset_sync_bits()
        self._support_ack_piggybacking = False
        if prepare_channel_without_pairing:
            # allow skipping unrelated response packets (e.g. in case of retransmissions)
            self._do_channel_allocation(retries=MAX_RETRANSMISSION_COUNT)
            LOG.debug("THP channel allocated: %04x", self.channel_id)
            self._do_handshake(credential=credential)
            LOG.debug("THP handshake done: is_paired=%s", self._is_paired)

    def get_channel(self) -> ProtocolV2Channel:
        if not self._is_paired:
            raise RuntimeError("Channel is not paired")
        return self

    def read(self, session_id: int, timeout: float | None = None) -> t.Any:
        sid, msg_type, msg_data = self.read_and_decrypt(timeout)
        if sid != session_id:
            raise Exception(
                f"Received messsage on a different session (expected/received): ({session_id}/{sid}) "
            )
        return self.mapping.decode(msg_type, msg_data)

    def write(self, session_id: int, msg: t.Any) -> None:
        msg_type, msg_data = self.mapping.encode(msg)
        self._encrypt_and_write(session_id, msg_type, msg_data)

    def get_features(self) -> messages.Features:
        if not self._is_paired:
            raise RuntimeError("Channel is not paired")
        if self._features is None:
            self.update_features()
        assert self._features is not None
        return self._features

    def update_features(self, timeout: float | None = None) -> None:
        message = messages.GetFeatures()
        message_type, message_data = self.mapping.encode(message)
        self.session_id: int = DEFAULT_SESSION_ID
        self._encrypt_and_write(DEFAULT_SESSION_ID, message_type, message_data)
        header, _payload = self._read_until_valid_crc_check()
        if not header.is_ack():
            raise exceptions.TrezorException("ACK expected")
        _, msg_type, msg_data = self.read_and_decrypt(timeout)
        features = self.mapping.decode(msg_type, msg_data)
        if not isinstance(features, messages.Features):
            raise exceptions.TrezorException("Unexpected response to GetFeatures")
        self._features = features

    def _send_message(
        self,
        message: protobuf.MessageType,
        session_id: int = DEFAULT_SESSION_ID,
    ) -> None:
        message_type, message_data = self.mapping.encode(message)
        self._encrypt_and_write(session_id, message_type, message_data)
        self._read_ack()

    def _read_message(self, message_type: type[MT], timeout: float | None = None) -> MT:
        _, msg_type, msg_data = self.read_and_decrypt(timeout)
        msg = self.mapping.decode(msg_type, msg_data)
        assert isinstance(msg, message_type)
        return msg

    def _reset_sync_bits(self) -> None:
        self.sync_bit_send = 0
        self.sync_bit_receive = 0

    def sync_responses(
        self, retries: int = MAX_RETRANSMISSION_COUNT, timeout: float = 10.0
    ) -> None:
        """Make sure the event loop is running and ready."""
        nonce = os.urandom(8)
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            MessageHeader.get_ping_header(len(nonce) + CHECKSUM_LENGTH),
            nonce,
        )
        for _ in range(1 + retries):
            header, payload = self._read_until_valid_crc_check(timeout=timeout)
            if self._is_valid_pong(header, payload, nonce):
                break
        else:
            raise RuntimeError("Invalid ping response")

    def _do_channel_allocation(self, retries: int = 0) -> None:
        channel_allocation_nonce = os.urandom(8)
        self._send_channel_allocation_request(channel_allocation_nonce)
        cid, dp = self._read_channel_allocation_response(
            channel_allocation_nonce, retries=retries
        )
        self.channel_id = cid
        self.device_properties = dp

    def _send_channel_allocation_request(self, nonce: bytes) -> None:
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            MessageHeader.get_channel_allocation_request_header(
                len(nonce) + CHECKSUM_LENGTH
            ),
            nonce,
        )

    def _read_channel_allocation_response(
        self, expected_nonce: bytes, retries: int = 0
    ) -> tuple[int, bytes]:
        for _ in range(1 + retries):
            header, payload = self._read_until_valid_crc_check()
            if self._is_valid_channel_allocation_response(
                header, payload, expected_nonce
            ):
                break
        else:
            raise Exception("Invalid channel allocation response.")

        channel_id = int.from_bytes(payload[8:10], "big")
        device_properties = payload[10:]

        dp = self.mapping.decode_without_wire_type(
            messages.ThpDeviceProperties, device_properties
        )
        assert isinstance(dp, messages.ThpDeviceProperties)
        version = (dp.protocol_version_major, dp.protocol_version_minor)
        self._support_ack_piggybacking = version >= (2, 1)
        LOG.debug(
            "THP version=%s ACK piggybacking=%s",
            "{}.{}".format(*version),
            self._support_ack_piggybacking,
        )

        return (channel_id, device_properties)

    def _init_noise(
        self,
        randomness_static: bytes | None = None,
        randomness_ephemeral: bytes | None = None,
    ) -> None:
        randomness_static = randomness_static or os.urandom(32)
        self._noise = NoiseConnection.from_name(b"Noise_XX_25519_AESGCM_SHA256")
        self._noise.set_as_initiator()
        self._noise.set_keypair_from_private_bytes(Keypair.STATIC, randomness_static)
        if randomness_ephemeral is not None:
            self._noise.set_keypair_from_private_bytes(
                Keypair.EPHEMERAL, randomness_ephemeral
            )
        prologue = bytes(self.device_properties)
        self._noise.set_prologue(prologue)
        self._noise.start_handshake()

    def _do_handshake(
        self,
        credential: bytes | None = None,
        host_static_randomness: bytes | None = None,
        host_ephemeral_randomness: bytes | None = None,
    ) -> None:

        randomness_static = host_static_randomness or os.urandom(32)
        if host_ephemeral_randomness is not None:
            self._init_noise(randomness_static, host_ephemeral_randomness)
        else:
            self._init_noise(randomness_static)
        self._send_handshake_init_request()
        self._read_ack()
        self._read_handshake_init_response()
        self._send_handshake_completion_request(
            credential,
        )
        self._read_ack()
        return self._read_handshake_completion_response()

    def _send_handshake_init_request(self, try_to_unlock: bool = True) -> None:
        payload = self._noise.write_message(bytes([try_to_unlock]))
        ctrl_byte = control_byte.HANDSHAKE_INIT_REQ
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(
            ctrl_byte=ctrl_byte, seq_bit=0
        )
        if self._support_ack_piggybacking:
            ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(
                ctrl_byte=ctrl_byte, ack_bit=1
            )
        ha_init_req_header = MessageHeader(
            ctrl_byte, self.channel_id, len(payload) + CHECKSUM_LENGTH
        )

        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport, ha_init_req_header, payload
        )

    def _read_handshake_init_response(self) -> bytes:
        header, payload = self._read_until_valid_crc_check()

        if not header.is_handshake_init_response():
            LOG.error("Received message is not a valid handshake init response message")

        if not self._support_ack_piggybacking:
            self._send_ack_bit(bit=0)
        self._noise.read_message(payload)
        return payload

    def _send_handshake_completion_request(
        self,
        credential: bytes | None = None,
    ) -> None:
        # TODO implement key recognition
        # print(
        #     "TREZOR's static pubkey:\n",
        #     self.noise.noise_protocol.handshake_state.rs.public.public_bytes_raw(),
        # )

        msg_data = self.mapping.encode_without_wire_type(
            messages.ThpHandshakeCompletionReqNoisePayload(
                host_pairing_credential=credential,
            )
        )
        message2 = self._noise.write_message(payload=msg_data)

        ctrl_byte = control_byte.HANDSHAKE_COMP_REQ
        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(
            ctrl_byte=ctrl_byte, seq_bit=1
        )
        if self._support_ack_piggybacking:
            ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(
                ctrl_byte=ctrl_byte, ack_bit=0
            )
        ha_completion_req_header = MessageHeader(
            0x12,
            self.channel_id,
            len(message2) + CHECKSUM_LENGTH,
        )
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            ha_completion_req_header,
            message2,  # encrypted_host_static_pubkey + encrypted_payload,
        )
        self.handshake_hash = self._noise.get_handshake_hash()

    def _read_handshake_completion_response(self) -> None:
        # Read handshake completion response
        header, data = self._read_until_valid_crc_check()
        if not header.is_handshake_comp_response():
            LOG.error("Received message is not a valid handshake completion response")
        trezor_state = self._noise.decrypt(bytes(data))
        assert trezor_state in TREZOR_STATES
        if not self._support_ack_piggybacking:
            self._send_ack_bit(bit=1)
        self._is_paired = trezor_state != TREZOR_STATE_UNPAIRED

    def _read_ack(self) -> None:
        header, payload = self._read_until_valid_crc_check()
        if not header.is_ack() or len(payload) > 0:
            LOG.error("Received message is not a valid ACK")
        LOG.debug("Received ACK %s", control_byte.get_ack_bit(header.ctrl_byte))

    def _send_ack_bit(self, bit: int) -> None:
        if bit not in (0, 1):
            raise ValueError("Invalid ACK bit")
        LOG.debug("Sending ACK %s", bit)
        ctrl_byte = 0x20 if bit == 0 else 0x28
        header = MessageHeader(ctrl_byte, self.channel_id, 4)
        thp_io.write_payload_to_wire_and_add_checksum(self.transport, header, b"")

    def _encrypt_and_write(
        self,
        session_id: int,
        message_type: int,
        message_data: bytes,
    ) -> None:

        ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(0x04, self.sync_bit_send)
        self.sync_bit_send = 1 - self.sync_bit_send

        if self._support_ack_piggybacking:
            ack_bit = 1 - self.sync_bit_receive  # previously received sync bit
            ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(ctrl_byte, ack_bit)
            LOG.debug("Piggybacking ACK bit %d", ack_bit)

        sid = session_id.to_bytes(1, "big")
        msg_type = message_type.to_bytes(2, "big")
        data = sid + msg_type + message_data

        encrypted_message = self._noise.encrypt(data)

        header = MessageHeader(
            ctrl_byte, self.channel_id, len(encrypted_message) + CHECKSUM_LENGTH
        )

        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport, header, encrypted_message
        )

    def read_and_decrypt(
        self, timeout: float | None = None
    ) -> t.Tuple[int, int, bytes]:
        while True:
            header, raw_payload = self._read_until_valid_crc_check(timeout)
            if header.cid != self.channel_id:
                # Received message from different channel - discard
                continue
            if control_byte.is_ack(header.ctrl_byte):
                LOG.debug("Received ACK %s", control_byte.get_ack_bit(header.ctrl_byte))
                continue
            if not header.is_encrypted_transport():
                LOG.error(
                    "Trying to decrypt not encrypted message! ("
                    + hexlify(header.to_bytes_init() + raw_payload).decode()
                    + ")"
                )

            seq_bit = control_byte.get_seq_bit(header.ctrl_byte)
            assert seq_bit is not None
            LOG.debug(
                "--> Get sequence bit %d %s %s",
                seq_bit,
                "from control byte",
                hexlify(header.ctrl_byte.to_bytes(1, "big")).decode(),
            )
            # TODO: it is OK to piggyback THP ACKs, except the last one (#6153)
            self._send_ack_bit(bit=seq_bit)

            message = self._noise.decrypt(bytes(raw_payload))
            session_id = message[0]
            message_type = message[1:3]
            message_data = message[3:]
            return (
                session_id,
                int.from_bytes(message_type, "big"),
                message_data,
            )

    def _read_until_valid_crc_check(
        self, timeout: float | None = None
    ) -> t.Tuple[MessageHeader, bytes]:
        if timeout is None:
            timeout = self._DEFAULT_READ_TIMEOUT

        while True:
            header, payload, chksum = thp_io.read(self.transport, timeout)
            if not checksum.is_valid(chksum, header.to_bytes_init() + payload):
                LOG.error(
                    "Received a message with an invalid checksum:"
                    + hexlify(header.to_bytes_init() + payload + chksum).decode()
                )
                continue

            seq_bit = control_byte.get_seq_bit(header.ctrl_byte)
            if seq_bit is not None:
                if seq_bit != self.sync_bit_receive:
                    LOG.warning(
                        "Received unexpected message: sync bit=%d, expected=%d",
                        seq_bit,
                        self.sync_bit_receive,
                    )
                    continue

                self.sync_bit_receive = 1 - self.sync_bit_receive

            if control_byte.is_error(header.ctrl_byte):
                code = payload[0]
                raise _ERRORS_MAP.get(code) or exceptions.ThpUnknownError(code)

            return header, payload

    def _is_valid_channel_allocation_response(
        self, header: MessageHeader, payload: bytes, original_nonce: bytes
    ) -> bool:
        if not header.is_channel_allocation_response():
            LOG.error("Received message is not a channel allocation response")
            return False
        if len(payload) < 10:
            LOG.error("Invalid channel allocation response payload")
            return False
        if payload[:8] != original_nonce:
            LOG.error("Invalid channel allocation response payload (nonce mismatch)")
            return False
        return True

    def _is_valid_pong(
        self, header: MessageHeader, payload: bytes, original_nonce: bytes
    ) -> bool:
        if not header.is_pong():
            LOG.error("Received message is not a pong")
            return False
        if payload != original_nonce:
            LOG.error("Invalid pong payload (nonce mismatch)")
            return False
        return True


_ERRORS_MAP = {
    1: exceptions.TransportBusy,
    2: exceptions.UnallocatedChannel,
    3: exceptions.DecryptionFailed,
    5: exceptions.DeviceLocked,
}
