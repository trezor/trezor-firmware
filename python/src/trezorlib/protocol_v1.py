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
import struct
import typing as t
import warnings

import typing_extensions as tx

from . import client, exceptions, mapping, messages
from .log import DUMP_BYTES
from .thp import pairing
from .tools import enter_context

if t.TYPE_CHECKING:
    from .mapping import ProtobufMapping
    from .models import TrezorModel
    from .protobuf import MessageType
    from .transport import Transport

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
    while chunk_payload := buffer.read(chunk_size - 1):
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


class SessionV1(client.Session["TrezorClientV1", t.Optional[bytes]]):
    def __init__(
        self,
        client: TrezorClientV1,
        *,
        id: bytes | None = None,
        seedless: bool = False,
    ) -> None:
        super().__init__(client, id=id)
        self.seedless = seedless
        self.is_invalid = False

    def __str__(self) -> str:
        return f"SessionV1(id={self.id.hex() if self.id else '(none)'})"

    def _log_short_id(self) -> str:
        if self.id is None:
            return super()._log_short_id()
        return self.id.hex()[:8]

    @enter_context
    def initialize(self, *, derive_cardano: bool | None = None) -> messages.Features:
        """Initialize the session.

        This can:
        - create a new session if this instance has not been initialized yet
        - activate an existing session, and/or trigger an InvalidSessionError
          if the session has expired.
        """
        # notify the client that this is now the active session
        self.client._last_active_session = self
        LOG.info("Activating session %s", self, extra={"session": self})
        resp = self.call_raw(
            messages.Initialize(session_id=self.id, derive_cardano=derive_cardano)
        )
        features = messages.Features.ensure_isinstance(resp)
        session_id = features.session_id
        if session_id is None:
            LOG.error(
                "Trezor did not return a session ID. Session management is now broken."
            )
            warnings.warn("Your Trezor firmware does not support sessions.")

        if self.id is None or self.seedless:
            LOG.info("New session id %s", session_id.hex() if session_id else "(none)")
            self.id = session_id
        elif self.id != session_id:
            self.is_invalid = True
            self.client._close_session(self)
            LOG.error("Failed to resume session id %s", self.id.hex())
            raise exceptions.InvalidSessionError(session_id, from_message=resp)
        else:
            LOG.info("Resumed session id %s", self.id.hex())
        return features

    @classmethod
    def derive(
        cls,
        client_: TrezorClientV1,
        passphrase: str | t.Literal[client.PassphraseSetting.ON_DEVICE],
        derive_cardano: bool,
    ) -> tx.Self:
        new = cls(client_)
        new._derive(passphrase, derive_cardano)
        return new

    @enter_context
    def _derive(
        self,
        passphrase: str | t.Literal[client.PassphraseSetting.ON_DEVICE],
        derive_cardano: bool,
    ) -> None:
        """Create a new session with pre-derived seed for the given passphrase."""
        self.initialize(derive_cardano=derive_cardano)

        try:
            resp = self.call(client.GET_ROOT_FINGERPRINT_MESSAGE)
        except exceptions.InvalidSessionError as e:
            # raised by call() when an unexpected PassphraseRequest is received
            resp = e.from_message

        if isinstance(resp, messages.PassphraseRequest):
            # process PassphraseRequest / PassphraseAck
            if passphrase is client.PassphraseSetting.ON_DEVICE:
                ack = messages.PassphraseAck(on_device=True)
            else:
                ack = messages.PassphraseAck(passphrase=passphrase)
            resp = self.call(ack)

        elif (
            self.features.passphrase_always_on_device is True
            and passphrase is client.PassphraseSetting.ON_DEVICE
        ):
            # Passphrase was processed on device without asking the host. This is OK.
            pass

        elif passphrase:
            # We didn't get a PassphraseRequest, but passphrase_protection is enabled.
            # Looks like the session is already initialized. Bail out.
            raise exceptions.TrezorException(
                f"Failed to activate passphrase session {resp}"
            )

        # after processing any PassphraseRequest, we should have an Address response
        resp = messages.PublicKey.ensure_isinstance(resp)
        assert resp.root_fingerprint is not None
        self._root_fingerprint = resp.root_fingerprint.to_bytes(4, "big")
        self.client.refresh_features()

    def close(self) -> None:
        super().close()
        self.client._close_session(self)
        if self.seedless:
            self.is_invalid = False
            self.id = None


class NullPairing(pairing.PairingController):
    def __init__(self) -> None:
        # not calling super because we're not initializing the
        # parent class, which assumes it's getting a TrezorClientThp instance.
        # This should not be a problem in practice because we're pretending
        # to be paired already.
        pass

    @property
    def state(self) -> pairing.ControllerLifecycle:
        return pairing.ControllerLifecycle.FINISHED

    @property
    def methods(self) -> t.Collection[type[pairing.PairingMethod]]:
        return (pairing.SkipPairing,)

    def is_paired(self) -> bool:
        return True

    def finish(self, _no_call: bool = False) -> None:
        pass

    def skip(self) -> None:
        pass

    def request_credential(self, autoconnect: bool = False) -> pairing.Credential:
        raise ValueError("Pairing not available in protocol-v1")


class TrezorClientV1(client.TrezorClient[SessionV1]):
    _seedless_session: SessionV1
    """Shared session instance for seedless calls. Will regenerate if it fails to resume."""

    _last_active_session: SessionV1 | None
    """The currently active session on the connected Trezor."""

    def __init__(
        self,
        app: client.AppManifest,
        transport: Transport,
        *,
        model: TrezorModel | None,
        mapping: ProtobufMapping | None,
    ) -> None:
        super().__init__(
            app=app,
            transport=transport,
            model=model,
            mapping=mapping,
            pairing=NullPairing(),
        )
        self._seedless_session = SessionV1(client=self, seedless=True)
        self._last_active_session = None

    def _close_session(self, session: SessionV1) -> None:
        if self._last_active_session is session:
            self._last_active_session = None

    def _invalidate(self) -> None:
        super()._invalidate()
        self._last_active_session = None

    def _activate(self, session: SessionV1) -> None:
        if self._last_active_session is not session:
            self._last_active_session = session
            session.initialize()

    def _get_any_session(self) -> SessionV1:
        if self._last_active_session is None:
            # create a new session instance
            return SessionV1(client=self, seedless=True)
        assert not self._last_active_session.is_invalid
        return self._last_active_session

    def _get_features(self) -> messages.Features:
        if self._last_active_session is None:
            # return the features that we got from Initialize()
            session = self._get_any_session()
            return session.initialize()
        return super()._get_features()

    def _get_session(
        self,
        *,
        passphrase: str | t.Literal[client.PassphraseSetting.ON_DEVICE] | None,
        derive_cardano: bool,
    ) -> SessionV1:
        """
        Returns a new session.
        """
        if passphrase is None:
            return self._seedless_session
        return SessionV1.derive(self, passphrase, derive_cardano)

    def _write(self, session: SessionV1, msg: MessageType) -> None:
        self._activate(session)
        LOG.debug(
            f"sending message: {msg.__class__.__name__}",
            extra={"protobuf": msg, "session": session},
        )
        msg_type, msg_bytes = self.mapping.encode(msg)
        LOG.log(
            DUMP_BYTES,
            f"encoded as type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
            extra={"session": session},
        )
        write(self.transport, msg_type, msg_bytes)

    def _read(self, session: SessionV1, timeout: float | None = None) -> MessageType:
        if session.is_invalid:
            raise exceptions.InvalidSessionError(session.id)
        if self._last_active_session is not session:
            raise exceptions.TrezorException("Reading from the wrong session")
        msg_type, msg_bytes = read(self.transport, timeout=timeout)
        LOG.log(
            DUMP_BYTES,
            f"received type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
            extra={"session": session},
        )
        msg = self.mapping.decode(msg_type, msg_bytes)
        LOG.debug(
            f"received message: {msg.__class__.__name__}",
            extra={"protobuf": msg, "session": session},
        )
        return msg


@enter_context
def probe(
    transport: Transport, *, mapping: ProtobufMapping = mapping.DEFAULT_MAPPING
) -> bool:
    """Probe the transport to see if it supports protocol v1."""
    ping_msg = messages.Ping(message="protocol-v1-test")
    ping_msg_type, ping_msg_bytes = mapping.encode(ping_msg)
    write(transport, ping_msg_type, ping_msg_bytes)
    resp_type, resp_bytes = read(transport)
    resp = mapping.decode(resp_type, resp_bytes)
    if isinstance(resp, messages.Failure):
        if resp.code == messages.FailureType.InvalidProtocol:
            return False
    return True


@enter_context
def sync_responses(
    transport: Transport,
    *,
    mapping: ProtobufMapping = mapping.DEFAULT_MAPPING,
    retries: int = 10,
) -> None:
    """Sync responses from the transport."""
    # cancel anything on screen -- on T1B1 this is the only way to exit e.g. a PIN prompt.
    cancel_msg = mapping.encode(messages.Cancel())
    write(transport, *cancel_msg)

    # prepare an unique message to wait for
    sync_string = "SYNC" + secrets.token_hex(8)
    ping_msg = mapping.encode(messages.Ping(message=sync_string))
    # prepare
    write(transport, *ping_msg)

    for _ in range(retries):
        resp_type, resp_bytes = read(transport)
        resp = mapping.decode(resp_type, resp_bytes)
        if isinstance(resp, messages.Success) and resp.message == sync_string:
            return
    raise exceptions.ProtocolError("Failed to sync responses")
