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

import io
import logging
import secrets
import time
import typing as t
from enum import Enum, IntEnum, auto

import typing_extensions as tx
from noise.connection import Keypair, NoiseConnection

from .. import client, messages, protobuf, transport
from ..exceptions import (
    DeviceLockedError,
    ProtocolError,
    StateMismatchError,
    TrezorException,
)
from . import control_byte, curve25519, exceptions, thp_io
from .credentials import TrezorPublicKeys, find_credential
from .message import Message

if t.TYPE_CHECKING:
    from noise.functions.keypair import KeyPair
    from noise.noise_protocol import NoiseProtocol

    from .credentials import Credential

LOG = logging.getLogger(__name__)

DEFAULT_SESSION_ID: int = 0

MAX_RETRANSMISSION_COUNT = 20
ACK_TIMEOUT = 0.5


class ChannelState(IntEnum):
    """Lifecycle state of the channel.

    Values are ordered and you can use numeric comparison operators to check
    the current phase.
    """

    UNALLOCATED = auto()
    """Channel has not been allocated."""
    ALLOCATED = auto()
    """Channel has been allocated."""
    HANDSHAKE_PHASE = auto()
    """Handshake in progress."""
    PAIRING_PHASE = auto()
    """Pairing in progress."""
    CREDENTIAL_PHASE = auto()
    """Pairing complete, credentials can be requested."""
    ENCRYPTED_TRANSPORT = auto()
    """Encrypted transport in progress."""

    def is_handshake_done(self) -> bool:
        return self > ChannelState.HANDSHAKE_PHASE


class PairingState(Enum):
    UNPAIRED = b"\x00"
    PAIRED = b"\x01"
    PAIRED_AUTOCONNECT = b"\x02"

    def is_paired(self) -> bool:
        return self in (self.PAIRED, self.PAIRED_AUTOCONNECT)


MT = t.TypeVar("MT", bound=protobuf.MessageType)


def encode_proto(message: protobuf.MessageType) -> bytes:
    buf = io.BytesIO()
    protobuf.dump_message(buf, message)
    return buf.getvalue()


def decode_proto(message_type: type[MT], message_data: bytes) -> MT:
    buf = io.BytesIO(message_data)
    return protobuf.load_message(buf, message_type)


def _keypair_from_private_bytes(noise: NoiseProtocol, private_bytes: bytes) -> KeyPair:
    return noise.dh_fn.klass.from_private_bytes(private_bytes)


class ChannelClosedError(TrezorException):
    """Channel is closed."""

    def __init__(self) -> None:
        super().__init__(self.__doc__)


class Channel:
    CHUNK_SIZE: t.ClassVar[int | None] = None

    pairing_state: PairingState = PairingState.UNPAIRED
    sync_bit_send: bool = False
    sync_bit_receive: bool = False

    BUSY_RETRIES: int = MAX_RETRANSMISSION_COUNT
    BUSY_BACKOFF_TIME: float = 0.1

    def __init__(
        self,
        *,
        transport: transport.Transport,
        channel_id: int,
        device_properties: messages.ThpDeviceProperties,
        prologue: bytes,
        channel_state: ChannelState = ChannelState.UNALLOCATED,
    ) -> None:
        LOG.info("Initializing channel %04x", channel_id)
        self.transport = transport
        self.channel_id = channel_id
        self.device_properties = device_properties
        self.sync_bit_send = False
        self.sync_bit_receive = False
        self.prologue = prologue
        self.host_static_privkey: bytes = secrets.token_bytes(32)
        self._noise: NoiseConnection | None = None
        self.state = channel_state

    @property
    def noise(self) -> NoiseConnection:
        if self._noise is None:
            raise ChannelClosedError
        return self._noise

    @property
    def handshake_hash(self) -> bytes:
        self._assert_handshake_done()
        return self.noise.get_handshake_hash()

    def _assert_handshake_done(self) -> None:
        if not self.state.is_handshake_done():
            raise StateMismatchError("Handshake is not finished")

    def get_host_static_pubkey(self) -> bytes:
        return curve25519.get_public_key(self.host_static_privkey)

    def sync_responses(
        self, retries: int = MAX_RETRANSMISSION_COUNT, timeout: float = 10.0
    ) -> None:
        """Make sure the event loop is running and ready."""
        with self.transport:
            nonce = secrets.token_bytes(8)
            message = Message.broadcast(control_byte.PING, nonce)
            thp_io.write_payload_to_wire(self.transport, message)
            for _ in range(1 + retries):
                message = self._read(timeout=timeout)
                if not message.is_pong():
                    LOG.debug(
                        "Discarding non-pong message: %s", message.to_bytes().hex()
                    )
                    continue
                if message.data != nonce:
                    LOG.warning(
                        "Read ping response with unexpected nonce: %s",
                        message.to_bytes().hex(),
                    )
                    continue
                return

        raise transport.Timeout(f"Failed to sync in {retries} retries")

    @classmethod
    def allocate(
        cls, transport: transport.Transport, retries: int = thp_io.DEFAULT_MAX_RETRIES
    ) -> tx.Self:
        # send channel allocation request
        LOG.info("Allocating new channel")
        nonce = secrets.token_bytes(8)
        message = Message.broadcast(control_byte.CHANNEL_ALLOCATION_REQ, nonce)
        with transport:
            thp_io.write_payload_to_wire(transport, message)
            # read channel allocation response
            for r in range(1 + retries):
                message = thp_io.read(transport, max_retries=retries - r)
                if not message.is_channel_allocation_response():
                    LOG.info("Not a channel allocation response, ignoring: %s", message)
                    continue
                if len(message.data) < 10 or message.data[:8] != nonce:
                    LOG.warning(
                        "Unexpected channel allocation nonce. Expected: %s, got: %s",
                        nonce.hex(),
                        message.data[:8].hex() or "(empty)",
                    )
                    continue
                channel_id = int.from_bytes(message.data[8:10], "big")
                LOG.info("Allocated channel %04x", channel_id)
                prologue = message.data[10:]
                device_properties = decode_proto(messages.ThpDeviceProperties, prologue)
                LOG.debug("Device properties: %s", device_properties)
                return cls(
                    transport=transport,
                    channel_id=channel_id,
                    device_properties=device_properties,
                    prologue=prologue,
                    channel_state=ChannelState.ALLOCATED,
                )
        raise ProtocolError("Retries exceeded while allocating channel")

    def _init_noise(
        self,
        *,
        static_privkey: bytes | None = None,
        ephemeral_privkey: bytes | None = None,
    ) -> None:
        if static_privkey is not None:
            self.host_static_privkey = static_privkey

        noise = NoiseConnection.from_name(b"Noise_XX_25519_AESGCM_SHA256")
        noise.set_as_initiator()
        noise.set_keypair_from_private_bytes(Keypair.STATIC, self.host_static_privkey)
        if ephemeral_privkey is not None:
            noise.set_keypair_from_private_bytes(Keypair.EPHEMERAL, ephemeral_privkey)
        noise.set_prologue(self.prologue)
        noise.start_handshake()

        self._noise = noise

    def is_open(self) -> bool:
        return self.state.is_handshake_done()

    def open(
        self,
        credentials: t.Iterable[Credential],
        *,
        force_unlock: bool = False,
    ) -> None:
        if self.state is ChannelState.UNALLOCATED:
            raise StateMismatchError("Channel is not allocated")
        if self.state > ChannelState.ALLOCATED:
            # channel is already open
            return

        if self._noise is None:
            self._init_noise()

        self.state = ChannelState.HANDSHAKE_PHASE
        with self.transport:
            try:
                LOG.info("Performing handshake for channel %04x", self.channel_id)
                self._send_handshake_init_request(force_unlock)
                self._read_handshake_init_response()
                self._send_handshake_completion_request(credentials)
                self._read_handshake_completion_response()
                LOG.info("Handshake completed for channel %04x", self.channel_id)
            except Exception:
                # any other failure during handshake will close the channel
                self.close()
                raise

    def close(self) -> None:
        self._noise = None
        self.state = ChannelState.UNALLOCATED
        self.pairing_state = PairingState.UNPAIRED

    def _send_handshake_init_request(self, unlock: bool) -> None:
        payload = self.noise.write_message(bytes([unlock]))
        ha_init_req_message = Message(
            control_byte.HANDSHAKE_INIT_REQ, self.channel_id, bytes(payload)
        )
        self._send_message(ha_init_req_message)

    def _read_handshake_init_response(self) -> None:
        try:
            message = self._read()
        except exceptions.ThpError as e:
            if e.code == exceptions.ThpErrorCode.DEVICE_LOCKED:
                raise DeviceLockedError from e
            raise
        self._send_ack(message)
        if not message.is_handshake_init_response():
            raise ProtocolError(f"Not a valid handshake init response: {message}")

        empty_string = self.noise.read_message(message.data)
        if empty_string != b"":
            raise ProtocolError(
                f"Unexpected data in handshake init response: {empty_string.hex()}"
            )

    def _send_handshake_completion_request(
        self, credentials: t.Iterable[Credential]
    ) -> None:
        trezor_public_keys = TrezorPublicKeys.from_noise(
            self.noise.noise_protocol.handshake_state
        )
        cred = find_credential(credentials, trezor_public_keys)
        if cred is not None:
            LOG.info(
                "Found credential for channel %04x: %s",
                self.channel_id,
                cred.trezor_pubkey.hex(),
            )
            # load the credential
            credential = cred.credential
            # set the appropriate host static privkey
            self.host_static_privkey = cred.host_privkey
            keypair = _keypair_from_private_bytes(
                self.noise.noise_protocol, cred.host_privkey
            )
            self.noise.noise_protocol.handshake_state.s = keypair
        else:
            # credential was not found
            credential = None

        msg_data = encode_proto(
            messages.ThpHandshakeCompletionReqNoisePayload(
                host_pairing_credential=credential
            )
        )
        message2 = self.noise.write_message(payload=msg_data)

        ha_completion_req_message = Message(
            control_byte.HANDSHAKE_COMP_REQ, self.channel_id, bytes(message2)
        )
        self._send_message(ha_completion_req_message)

    def _read_handshake_completion_response(self) -> None:
        # Read handshake completion response
        message = self._read()
        self._send_ack(message)
        if not message.is_handshake_comp_response():
            LOG.error(
                "Received message is not a valid handshake completion response: %s",
                message,
            )
            raise ProtocolError(f"Not a valid handshake completion response: {message}")

        trezor_state = self.noise.decrypt(bytes(message.data))
        try:
            self.pairing_state = PairingState(trezor_state)
        except ValueError:
            raise ProtocolError(f"Invalid trezor state: {trezor_state.hex()}")

        LOG.info("Channel %04x is %s", self.channel_id, self.pairing_state.name)
        if not self.pairing_state.is_paired():
            self.state = ChannelState.PAIRING_PHASE
        else:
            self.state = ChannelState.CREDENTIAL_PHASE

    def _send_message(self, message: Message) -> None:
        msg_with_seq_bit = message.with_seq_bit(self.sync_bit_send)
        self.sync_bit_send = not self.sync_bit_send

        retries_left = self.BUSY_RETRIES
        retry_backoff_time = self.BUSY_BACKOFF_TIME

        def should_back_off() -> bool:
            nonlocal retries_left, retry_backoff_time
            if retries_left <= 0:
                return False
            retries_left -= 1
            time.sleep(retry_backoff_time)
            retry_backoff_time *= 2
            return True

        while True:
            try:
                thp_io.write_payload_to_wire(self.transport, msg_with_seq_bit)
                try:
                    self._read_ack(msg_with_seq_bit)
                except transport.Timeout:
                    if should_back_off():
                        continue
                    raise
                break
            except exceptions.ThpError as e:
                if (
                    e.code == exceptions.ThpErrorCode.TRANSPORT_BUSY
                    and should_back_off()
                ):
                    continue
                raise

    def _send_ack(self, acked_message: Message) -> None:
        ack = control_byte.make_ack_for(acked_message.ctrl_byte)
        ack_message = Message(ack, acked_message.cid, b"")
        thp_io.write_payload_to_wire(self.transport, ack_message)

    def _read_ack(self, message: Message) -> None:
        expected_seq_bit = message.seq_bit
        retries = MAX_RETRANSMISSION_COUNT
        time_start = time.monotonic()
        for _ in range(1 + retries):
            time_elapsed = time.monotonic() - time_start
            message = self._read(timeout=ACK_TIMEOUT - time_elapsed)
            if not message.is_ack() or len(message.data) > 0:
                LOG.error("Received message is not a valid ACK: %s", message)
                # data messages and their acks should have been handled by _read()
                continue
            if message.ack_bit != expected_seq_bit:
                LOG.warning("Received ACK with unexpected sequence bit: %s", message)
                continue
            return
        raise transport.Timeout(
            f"Failed to read ACK in {retries} retries for message: {message}"
        )

    def write_chunk(self, data: bytes, /) -> None:
        self._assert_handshake_done()
        encrypted_data = self.noise.encrypt(data)
        message = Message(
            control_byte.ENCRYPTED_TRANSPORT, self.channel_id, encrypted_data
        )
        self._send_message(message)

    def read_chunk(self, *, timeout: float | None = None) -> bytes:
        self._assert_handshake_done()
        while True:
            message = self._read(timeout)
            if message.cid != self.channel_id:
                LOG.info("Discarding message from different channel: %s", message)
                continue
            if control_byte.is_ack(message.ctrl_byte):
                LOG.warning("Unexpected ACK: %s", message)
                continue
            if not message.is_encrypted_transport():
                LOG.error("Trying to decrypt not encrypted message! (%s)", message)

            self._send_ack(message)
            return self.noise.decrypt(bytes(message.data))

    def _read(self, timeout: float | None = None) -> Message:
        if timeout is None:
            timeout = client._DEFAULT_READ_TIMEOUT

        while True:
            message = thp_io.read(self.transport, timeout)
            if message.seq_bit is not None:
                if message.seq_bit != self.sync_bit_receive:
                    LOG.warning(
                        "Received unexpected message: sync bit=%d, expected=%d",
                        message.seq_bit,
                        self.sync_bit_receive,
                    )
                    self._send_ack(message)
                    continue

                self.sync_bit_receive = not self.sync_bit_receive

            if control_byte.is_error(message.ctrl_byte):
                code = message.data[0]
                raise exceptions.ThpError(code)

            return message
