from __future__ import annotations

import hashlib
import hmac
import logging
import os
import typing as t
from binascii import hexlify
from enum import IntEnum

import click
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ... import exceptions, messages
from ...mapping import ProtobufMapping
from .. import Transport
from ..thp import checksum, curve25519, thp_io
from ..thp.channel_data import ChannelData
from ..thp.checksum import CHECKSUM_LENGTH
from ..thp.message_header import MessageHeader
from . import control_byte
from .channel_database import ChannelDatabase, get_channel_db
from .protocol_and_channel import ProtocolAndChannel

LOG = logging.getLogger(__name__)

MANAGEMENT_SESSION_ID: int = 0


def _sha256_of_two(val_1: bytes, val_2: bytes) -> bytes:
    hash = hashlib.sha256(val_1)
    hash.update(val_2)
    return hash.digest()


def _hkdf(chaining_key: bytes, input: bytes):
    temp_key = hmac.new(chaining_key, input, hashlib.sha256).digest()
    output_1 = hmac.new(temp_key, b"\x01", hashlib.sha256).digest()
    ctx_output_2 = hmac.new(temp_key, output_1, hashlib.sha256)
    ctx_output_2.update(b"\x02")
    output_2 = ctx_output_2.digest()
    return (output_1, output_2)


def _get_iv_from_nonce(nonce: int) -> bytes:
    if not nonce <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("Nonce overflow, terminate the channel")
    return bytes(4) + nonce.to_bytes(8, "big")


class ProtocolV2(ProtocolAndChannel):
    channel_id: int
    channel_database: ChannelDatabase
    key_request: bytes
    key_response: bytes
    nonce_request: int
    nonce_response: int
    sync_bit_send: int
    sync_bit_receive: int

    _has_valid_channel: bool = False
    _features: messages.Features | None = None

    def __init__(
        self,
        transport: Transport,
        mapping: ProtobufMapping,
        channel_data: ChannelData | None = None,
    ) -> None:
        self.channel_database: ChannelDatabase = get_channel_db()
        super().__init__(transport, mapping, channel_data)
        if channel_data is not None:
            self.channel_id = channel_data.channel_id
            self.key_request = bytes.fromhex(channel_data.key_request)
            self.key_response = bytes.fromhex(channel_data.key_response)
            self.nonce_request = channel_data.nonce_request
            self.nonce_response = channel_data.nonce_response
            self.sync_bit_receive = channel_data.sync_bit_receive
            self.sync_bit_send = channel_data.sync_bit_send
            self._has_valid_channel = True

    def get_channel(self) -> ProtocolV2:
        if not self._has_valid_channel:
            self._establish_new_channel()
        return self

    def get_channel_data(self) -> ChannelData:
        return ChannelData(
            protocol_version=2,
            transport_path=self.transport.get_path(),
            channel_id=self.channel_id,
            key_request=self.key_request,
            key_response=self.key_response,
            nonce_request=self.nonce_request,
            nonce_response=self.nonce_response,
            sync_bit_receive=self.sync_bit_receive,
            sync_bit_send=self.sync_bit_send,
        )

    def read(self, session_id: int) -> t.Any:
        sid, msg_type, msg_data = self.read_and_decrypt()
        if sid != session_id:
            raise Exception("Received messsage on a different session.")
        self.channel_database.save_channel(self)
        return self.mapping.decode(msg_type, msg_data)

    def write(self, session_id: int, msg: t.Any) -> None:
        msg_type, msg_data = self.mapping.encode(msg)
        self._encrypt_and_write(session_id, msg_type, msg_data)
        self.channel_database.save_channel(self)

    def get_features(self) -> messages.Features:
        if not self._has_valid_channel:
            self._establish_new_channel()
        if self._features is None:
            self.update_features()
        assert self._features is not None
        return self._features

    def update_features(self) -> None:
        message = messages.GetFeatures()
        message_type, message_data = self.mapping.encode(message)
        self.session_id: int = 0
        self._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
        _ = self._read_until_valid_crc_check()  # TODO check ACK
        _, msg_type, msg_data = self.read_and_decrypt()
        features = self.mapping.decode(msg_type, msg_data)
        if not isinstance(features, messages.Features):
            raise exceptions.TrezorException("Unexpected response to GetFeatures")
        self._features = features

    def _establish_new_channel(self) -> None:
        self.sync_bit_send = 0
        self.sync_bit_receive = 0
        # Send channel allocation request
        # Note that [:8] on the following line is required when tests use
        # WITH_MOCK_URANDOM. Without [:8] such tests will (almost always) fail.
        channel_id_request_nonce = os.urandom(8)[:8]
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            MessageHeader.get_channel_allocation_request_header(12),
            channel_id_request_nonce,
        )

        # Read channel allocation response
        header, payload = self._read_until_valid_crc_check()
        if not self._is_valid_channel_allocation_response(
            header, payload, channel_id_request_nonce
        ):
            # TODO raise exception here, I guess
            raise Exception("Invalid channel allocation response.")

        self.channel_id = int.from_bytes(payload[8:10], "big")
        self.device_properties = payload[10:]

        # Send handshake init request
        ha_init_req_header = MessageHeader(0, self.channel_id, 36)
        # Note that [:32] on the following line is required when tests use
        # WITH_MOCK_URANDOM. Without [:32] such tests will (almost always) fail.
        host_ephemeral_privkey = curve25519.get_private_key(os.urandom(32)[:32])
        host_ephemeral_pubkey = curve25519.get_public_key(host_ephemeral_privkey)

        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport, ha_init_req_header, host_ephemeral_pubkey
        )

        # Read ACK
        header, payload = self._read_until_valid_crc_check()
        if not header.is_ack() or len(payload) > 0:
            click.echo("Received message is not a valid ACK", err=True)

        # Read handshake init response
        header, payload = self._read_until_valid_crc_check()
        self._send_ack_0()

        if not header.is_handshake_init_response():
            click.echo(
                "Received message is not a valid handshake init response message",
                err=True,
            )

        trezor_ephemeral_pubkey = payload[:32]
        encrypted_trezor_static_pubkey = payload[32:80]
        noise_tag = payload[80:96]

        # TODO check noise tag
        LOG.debug("noise_tag: %s", hexlify(noise_tag).decode())

        # Prepare and send handshake completion request
        PROTOCOL_NAME = b"Noise_XX_25519_AESGCM_SHA256\x00\x00\x00\x00"
        IV_1 = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        IV_2 = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        h = _sha256_of_two(PROTOCOL_NAME, self.device_properties)
        h = _sha256_of_two(h, host_ephemeral_pubkey)
        h = _sha256_of_two(h, trezor_ephemeral_pubkey)
        ck, k = _hkdf(
            PROTOCOL_NAME,
            curve25519.multiply(host_ephemeral_privkey, trezor_ephemeral_pubkey),
        )

        aes_ctx = AESGCM(k)
        try:
            trezor_masked_static_pubkey = aes_ctx.decrypt(
                IV_1, encrypted_trezor_static_pubkey, h
            )
        except Exception as e:
            click.echo(
                f"Exception of type{type(e)}", err=True
            )  # TODO how to handle potential exceptions? Q for Matejcik
        h = _sha256_of_two(h, encrypted_trezor_static_pubkey)
        ck, k = _hkdf(
            ck, curve25519.multiply(host_ephemeral_privkey, trezor_masked_static_pubkey)
        )
        aes_ctx = AESGCM(k)

        tag_of_empty_string = aes_ctx.encrypt(IV_1, b"", h)
        h = _sha256_of_two(h, tag_of_empty_string)
        # TODO: search for saved credentials (or possibly not, as we skip pairing phase)

        zeroes_32 = int.to_bytes(0, 32, "little")
        temp_host_static_privkey = curve25519.get_private_key(zeroes_32)
        temp_host_static_pubkey = curve25519.get_public_key(temp_host_static_privkey)
        aes_ctx = AESGCM(k)
        encrypted_host_static_pubkey = aes_ctx.encrypt(IV_2, temp_host_static_pubkey, h)
        h = _sha256_of_two(h, encrypted_host_static_pubkey)
        ck, k = _hkdf(
            ck, curve25519.multiply(temp_host_static_privkey, trezor_ephemeral_pubkey)
        )
        msg_data = self.mapping.encode_without_wire_type(
            messages.ThpHandshakeCompletionReqNoisePayload(
                pairing_methods=[
                    messages.ThpPairingMethod.NoMethod,
                ]
            )
        )

        aes_ctx = AESGCM(k)

        encrypted_payload = aes_ctx.encrypt(IV_1, msg_data, h)
        h = _sha256_of_two(h, encrypted_payload)
        ha_completion_req_header = MessageHeader(
            0x12,
            self.channel_id,
            len(encrypted_host_static_pubkey)
            + len(encrypted_payload)
            + CHECKSUM_LENGTH,
        )
        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport,
            ha_completion_req_header,
            encrypted_host_static_pubkey + encrypted_payload,
        )

        # Read ACK
        header, payload = self._read_until_valid_crc_check()
        if not header.is_ack() or len(payload) > 0:
            click.echo("Received message is not a valid ACK", err=True)

        # Read handshake completion response, ignore payload as we do not care about the state
        header, _ = self._read_until_valid_crc_check()
        if not header.is_handshake_comp_response():
            click.echo(
                "Received message is not a valid handshake completion response",
                err=True,
            )
        self._send_ack_1()

        self.key_request, self.key_response = _hkdf(ck, b"")
        self.nonce_request = 0
        self.nonce_response = 1

        # Send StartPairingReqest message
        message = messages.ThpStartPairingRequest()
        message_type, message_data = self.mapping.encode(message)

        self._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)

        # Read ACK
        header, payload = self._read_until_valid_crc_check()
        if not header.is_ack() or len(payload) > 0:
            click.echo("Received message is not a valid ACK", err=True)

        # Read
        _, msg_type, msg_data = self.read_and_decrypt()
        maaa = self.mapping.decode(msg_type, msg_data)

        assert isinstance(maaa, messages.ThpEndResponse)
        self._has_valid_channel = True

    def _send_ack_0(self):
        LOG.debug("sending ack 0")
        header = MessageHeader(0x20, self.channel_id, 4)
        thp_io.write_payload_to_wire_and_add_checksum(self.transport, header, b"")

    def _send_ack_1(self):
        LOG.debug("sending ack 1")
        header = MessageHeader(0x28, self.channel_id, 4)
        thp_io.write_payload_to_wire_and_add_checksum(self.transport, header, b"")

    def _encrypt_and_write(
        self,
        session_id: int,
        message_type: int,
        message_data: bytes,
        ctrl_byte: int | None = None,
    ) -> None:
        assert self.key_request is not None
        aes_ctx = AESGCM(self.key_request)

        if ctrl_byte is None:
            ctrl_byte = control_byte.add_seq_bit_to_ctrl_byte(0x04, self.sync_bit_send)
            self.sync_bit_send = 1 - self.sync_bit_send

        sid = session_id.to_bytes(1, "big")
        msg_type = message_type.to_bytes(2, "big")
        data = sid + msg_type + message_data
        nonce = _get_iv_from_nonce(self.nonce_request)
        self.nonce_request += 1
        encrypted_message = aes_ctx.encrypt(nonce, data, b"")
        header = MessageHeader(
            ctrl_byte, self.channel_id, len(encrypted_message) + CHECKSUM_LENGTH
        )

        thp_io.write_payload_to_wire_and_add_checksum(
            self.transport, header, encrypted_message
        )

    def read_and_decrypt(self) -> t.Tuple[int, int, bytes]:
        header, raw_payload = self._read_until_valid_crc_check()
        if control_byte.is_ack(header.ctrl_byte):
            return self.read_and_decrypt()
        if not header.is_encrypted_transport():
            click.echo(
                "Trying to decrypt not encrypted message!"
                + hexlify(header.to_bytes_init() + raw_payload).decode(),
                err=True,
            )

        if not control_byte.is_ack(header.ctrl_byte):
            LOG.debug(
                "--> Get sequence bit %d %s %s",
                control_byte.get_seq_bit(header.ctrl_byte),
                "from control byte",
                hexlify(header.ctrl_byte.to_bytes(1, "big")).decode(),
            )
            if control_byte.get_seq_bit(header.ctrl_byte):
                self._send_ack_1()
            else:
                self._send_ack_0()
        aes_ctx = AESGCM(self.key_response)
        nonce = _get_iv_from_nonce(self.nonce_response)
        self.nonce_response += 1

        message = aes_ctx.decrypt(nonce, raw_payload, b"")
        session_id = message[0]
        message_type = message[1:3]
        message_data = message[3:]
        return (
            session_id,
            int.from_bytes(message_type, "big"),
            message_data,
        )

    def _read_until_valid_crc_check(
        self,
    ) -> t.Tuple[MessageHeader, bytes]:
        is_valid = False
        header, payload, chksum = thp_io.read(self.transport)
        while not is_valid:
            is_valid = checksum.is_valid(chksum, header.to_bytes_init() + payload)
            if not is_valid:
                click.echo(
                    "Received a message with an invalid checksum:"
                    + hexlify(header.to_bytes_init() + payload + chksum).decode(),
                    err=True,
                )
                header, payload, chksum = thp_io.read(self.transport)

        return header, payload

    def _is_valid_channel_allocation_response(
        self, header: MessageHeader, payload: bytes, original_nonce: bytes
    ) -> bool:
        if not header.is_channel_allocation_response():
            click.echo(
                "Received message is not a channel allocation response", err=True
            )
            return False
        if len(payload) < 10:
            click.echo("Invalid channel allocation response payload", err=True)
            return False
        if payload[:8] != original_nonce:
            click.echo(
                "Invalid channel allocation response payload (nonce mismatch)", err=True
            )
            return False
        return True

    class ControlByteType(IntEnum):
        CHANNEL_ALLOCATION_RES = 1
        HANDSHAKE_INIT_RES = 2
        HANDSHAKE_COMP_RES = 3
        ACK = 4
        ENCRYPTED_TRANSPORT = 5
