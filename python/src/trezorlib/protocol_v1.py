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
import struct
import typing as t

from . import client, exceptions, messages
from .log import DUMP_BYTES
from .transport import Transport

if t.TYPE_CHECKING:
    from .mapping import ProtobufMapping
    from .models import TrezorModel

LOG = logging.getLogger(__name__)

HEADER_FMT = ">HL"
HEADER_LEN = struct.calcsize(HEADER_FMT)


def write(transport: Transport, message_type: int, message_data: bytes) -> None:
    """Write message bytes to transport, chunked according to protocol v1."""
    chunk_size = transport.CHUNK_SIZE
    header = struct.pack(HEADER_FMT, message_type, len(message_data))

    if chunk_size is None:
        transport.write_chunk(header + message_data)
        return

    buffer = io.BytesIO(b"##" + header + message_data)
    while chunk_payload := buffer.read(chunk_size):
        chunk = b"?" + chunk_payload
        # pad to chunk size
        chunk = chunk.ljust(chunk_size, b"\x00")
        transport.write_chunk(chunk)


def read(transport: Transport, timeout: float | None = None) -> tuple[int, bytes]:
    """Read out and reassemble protocol-v1 chunked message from transport."""
    if timeout is None:
        timeout = client._DEFAULT_READ_TIMEOUT

    # Chunked transports prefix the first packet with "?##" and all following packets with "?".
    # Non-chunked (i.e., bridge) just load all the data in one go.
    use_chunk_magic = transport.CHUNK_SIZE is not None

    def read_next_chunk() -> bytes:
        chunk = transport.read_chunk(timeout=timeout)
        if use_chunk_magic and chunk[:1] != b"?":
            raise exceptions.ProtocolError(f"Missing chunk magic: {chunk.hex()}")
        return chunk[1:]

    # process first chunk
    chunk = read_next_chunk()
    if use_chunk_magic:
        # '?' was stripped in read_next_chunk(), we just detect the "##"
        if chunk[:2] != b"##":
            raise exceptions.ProtocolError(
                f"Unexpected first chunk magic: {chunk.hex()}"
            )
        chunk = chunk[2:]

    # extract header
    header = chunk[:HEADER_LEN]
    msg_type, datalen = struct.unpack(HEADER_FMT, header)

    # read rest of the message
    buffer = bytearray(chunk[HEADER_LEN:])
    while len(buffer) < datalen:
        buffer.extend(read_next_chunk())
    return msg_type, bytes(buffer[:datalen])


class SessionV1(client.Session["TrezorClientV1"]):
    def __init__(
        self,
        client: TrezorClientV1,
        *,
        session_id: bytes | None = None,
        seedless: bool = False,
    ) -> None:
        super().__init__(client)
        self.session_id = session_id
        self.seedless = seedless
        self.is_invalid = False

    def resume(self) -> None:
        if self.session_id is None:
            raise RuntimeError("resuming session without id")
        self.initialize()

    def _activate_self(self) -> None:
        if self.is_invalid:
            raise exceptions.InvalidSessionError(self.session_id)
        if self.client._last_active_session is not self:
            self.client._last_active_session = self
            self.resume()

    def _write(self, msg: t.Any) -> None:
        self._activate_self()
        LOG.debug(
            f"sending message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )
        msg_type, msg_bytes = self.client.mapping.encode(msg)
        LOG.log(
            DUMP_BYTES,
            f"encoded as type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        write(self.client.transport, msg_type, msg_bytes)

    def _read(self, timeout: float | None = None) -> t.Any:
        if self.is_invalid:
            raise exceptions.InvalidSessionError(self.session_id)
        assert self.client._last_active_session is self
        msg_type, msg_bytes = self._read(timeout=timeout)
        LOG.log(
            DUMP_BYTES,
            f"received type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        msg = self.client.mapping.decode(msg_type, msg_bytes)
        LOG.debug(
            f"received message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )

        from .debuglink import TrezorClientDebugLink

        if isinstance(self.client, TrezorClientDebugLink):
            self.client.notify_read(msg)

        return msg

    def initialize(self, *, derive_cardano: bool | None = None) -> None:
        # avoid triggering a resume() in _activate_self()
        self.client._last_active_session = self
        resp = self.call_raw(
            messages.Initialize(
                session_id=self.session_id, derive_cardano=derive_cardano
            )
        )
        features = messages.Features.ensure_isinstance(resp)
        session_id = features.session_id
        if self.session_id is None or self.seedless:
            self.session_id = session_id
        elif self.session_id != session_id:
            self.is_invalid = True
            raise exceptions.InvalidSessionError(session_id)

    def derive_seed(
        self,
        passphrase: str | type[client.PassphraseOnDevice],
        derive_cardano: bool,
    ) -> None:
        if self.session_id is not None:
            raise exceptions.TrezorException("Session already initialized")
        self.initialize(derive_cardano=derive_cardano)
        resp = self.call(
            messages.GetAddress(
                address_n=client.PASSPHRASE_TEST_PATH, coin_name="Testnet"
            )
        )
        # no passphrase was requested
        if isinstance(resp, messages.Address):
            if self.features.passphrase_protection is True:
                raise exceptions.TrezorException(
                    "Failed to activate passphrase session"
                )
            if passphrase not in (None, client.PassphraseOnDevice):
                raise exceptions.PassphraseDisabledError

            return

        resp = messages.PassphraseRequest.ensure_isinstance(resp)
        if passphrase is client.PassphraseOnDevice:
            ack = messages.PassphraseAck(on_device=True)
        else:
            assert isinstance(passphrase, str)
            ack = messages.PassphraseAck(passphrase=passphrase)
        resp = self.call(ack)
        if isinstance(resp, messages.Deprecated_PassphraseStateRequest):
            self.session_id = resp.state
            resp = self.call(messages.Deprecated_PassphraseStateAck())
        messages.Address.ensure_isinstance(resp)
        self.refresh_features()


class TrezorClientV1(client.TrezorClient[SessionV1]):
    _last_active_session: SessionV1 | None = None

    def __init__(
        self,
        transport: Transport,
        *,
        model: TrezorModel | None,
        mapping: ProtobufMapping | None,
        app_name: str,
        host_name: str | None,
    ) -> None:
        """
        TODO
        """
        super().__init__(
            model=model,
            mapping=mapping,
            app_name=app_name,
            host_name=host_name,
        )
        LOG.info(f"creating client instance for device: {transport.get_path()}")
        self.transport = transport
        self._seedless_session = SessionV1(client=self, seedless=True)

    def get_session(
        self,
        passphrase: str | type[client.PassphraseOnDevice] | None = "",
        *,
        derive_cardano: bool = False,
    ) -> SessionV1:
        """
        Returns a new session.
        """
        if passphrase is None:
            return self._seedless_session
        session = SessionV1(client=self)
        session.derive_seed(passphrase, derive_cardano)
        return session

    def _get_features(self) -> messages.Features:
        return self._seedless_session.call(
            messages.GetFeatures(), expect=messages.Features
        )
