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

"""The host side of the WARD service channel: announce yourself, then answer.

The daemon speaks once -- `WardServiceOpen` -- and from then on the DEVICE initiates and the
daemon answers (`WardServiceServer`). `WardServiceClient` speaks THP and `WardServiceClientV1` the
V1 codec; `ward_service_client` picks one by probing the endpoint.

The THP client uses a seedless session 0 (the service must hold no seed) and reads through
`Session.read`/`write`, never `call`, so acks go out on receipt rather than piggybacking on a reply.
One loop owns the channel; there is no second thread. On THP the device pins the daemon's static
key, so that key must be durable -- see `WardServiceClient`.
"""

from __future__ import annotations

import logging
import struct
import time
import typing as t

from . import client as _client
from . import exceptions, messages, protocol_v1
from .thp.channel import Channel
from .thp.client import TrezorClientThp
from .transport import Timeout
from .transport.udp import UdpTransport

if t.TYPE_CHECKING:
    from .client import TrezorClient
    from .mapping import ProtobufMapping
    from .models import TrezorModel
    from .protobuf import MessageType
    from .thp.client import ThpSession
    from .thp.credentials import Credential
    from .transport import Transport

    AnyWardServiceClient = t.Union["WardServiceClient", "WardServiceClientV1"]

LOG = logging.getLogger(__name__)
_C = t.TypeVar("_C", bound="_ServiceClientBase")

# Matches `apps.ward.service.PROTOCOL_VERSION`; the device refuses an unknown version by name.
PROTOCOL_VERSION = 1

# Emulator: the WARD interface is the UDP port at wire + 7 (4/5 are BLE, 6 is the Tropic model).
WARD_PORT_OFFSET = 7

# Real USB: the interface is found by this subclass/protocol pair, never by index.
WARD_USB_SUBCLASS = 0x57
WARD_USB_PROTOCOL = 0x01

# THE CODEC PROBE. A THP endpoint answers V1 framing with a V1 `Failure(InvalidProtocol)`, so the
# framing proves nothing; WHICH failure does. A codec endpoint refuses this unknown wire type with
# a `DataError` before touching the binding.
_CODEC_PROBE_WIRE_TYPE = 0xFEFE
_CODEC_REPORT_LEN = 64
_CODEC_MAGIC = b"?##"
_CODEC_HEADER_LEN = 9
_CODEC_PROBE_TIMEOUT_S = 1.0
# Retried: a stale PONGPONG from `Transport.is_ready` may still be queued on the socket.
_CODEC_PROBE_ATTEMPTS = 3


def _codec_probe_report() -> bytes:
    header = _CODEC_MAGIC + struct.pack(">HL", _CODEC_PROBE_WIRE_TYPE, 0)
    return header + b"\x00" * (_CODEC_REPORT_LEN - len(header))


def _failure_code(reply: bytes) -> int | None:
    """The `code` of a codec-framed `Failure`, or None. Parsed by hand: no mapping is assumed."""
    if len(reply) < _CODEC_HEADER_LEN or reply[: len(_CODEC_MAGIC)] != _CODEC_MAGIC:
        return None
    mtype, msize = struct.unpack(">HL", reply[len(_CODEC_MAGIC) : _CODEC_HEADER_LEN])
    if mtype != messages.Failure.MESSAGE_WIRE_TYPE:
        return None
    payload = reply[_CODEC_HEADER_LEN : _CODEC_HEADER_LEN + msize]
    if not payload or payload[0] != 0x08:  # field 1 (`code`), varint
        return None

    code = 0
    for shift, byte in enumerate(payload[1:]):
        code |= (byte & 0x7F) << (7 * shift)
        if not byte & 0x80:
            return code
    return None


def service_speaks_codec(ward: Transport) -> bool | None:
    """Whether the (already open) WARD endpoint speaks codec v1 rather than THP; side-effect free.

    None means inconclusive -- the caller decides, because a wrong guess runs the wrong transport.
    """
    for _attempt in range(_CODEC_PROBE_ATTEMPTS):
        try:
            ward.write_chunk(_codec_probe_report())
        except Exception:
            return None

        deadline = time.time() + _CODEC_PROBE_TIMEOUT_S
        while time.time() < deadline:
            try:
                reply = ward.read_chunk(timeout=_CODEC_PROBE_TIMEOUT_S)
            except Exception:
                break  # nothing came, or a stale wrong-sized frame: ask again
            code = _failure_code(reply)
            if code is None:
                continue
            return code != messages.FailureType.InvalidProtocol

    return None


WardServiceHandler = t.Callable[["MessageType"], "MessageType | None"]
"""A daemon: one device request -> one reply. None answers nothing (a lost reply; tests only)."""


def ward_transport(wire: Transport) -> Transport:
    """The transport for this device's WARD interface, given one for its wire interface."""
    if isinstance(wire, UdpTransport):
        host, port = wire.device
        return UdpTransport(f"{host}:{port + WARD_PORT_OFFSET}")

    return _webusb_ward_transport(wire)


def _webusb_ward_transport(wire: Transport) -> Transport:
    """Same device, the interface whose descriptor says WARD. GAP(ward): unvalidated on hardware."""
    from .transport.webusb import WebUsbTransport

    if not isinstance(wire, WebUsbTransport):
        raise exceptions.TrezorException(
            f"cannot reach a WARD service interface over {type(wire).__name__}"
        )

    ward = WebUsbTransport(wire.device)
    ward.interface, ward.endpoint = _find_ward_interface(wire.device)
    return ward


def _find_ward_interface(device: t.Any) -> tuple[int, int]:
    """(interface number, IN endpoint number) of the WARD interface on this device."""
    for configuration in device.iterConfigurations():
        for interface in configuration.iterInterfaces():
            for setting in interface.iterSettings():
                if (
                    setting.getSubClass() != WARD_USB_SUBCLASS
                    or setting.getProtocol() != WARD_USB_PROTOCOL
                ):
                    continue
                for endpoint in setting.iterEndpoints():
                    address = endpoint.getAddress()
                    if address & 0x80:  # IN; ep_in 0x8n pairs with ep_out 0x0n
                        return setting.getNumber(), address & 0x7F
    raise exceptions.TrezorException("this device has no WARD service interface")


class _ServiceClientBase:
    """What both transports share: announcing, and the context-manager shape. Subclasses provide
    `connect`, `close`, `pair` and `call`."""

    if t.TYPE_CHECKING:

        def connect(self) -> None: ...
        def close(self) -> None: ...
        def pair(self, skip: bool = False) -> None: ...
        def call(self, msg: MessageType, timeout: float | None = None) -> MessageType: ...

    def announce(
        self, protocol_version: int | None = None
    ) -> messages.WardServiceOpenAck:
        """Bind this endpoint as the WARD service. Raises if the device refuses. The last thing
        this side initiates: afterwards the device asks and the daemon answers."""
        if protocol_version is None:
            protocol_version = PROTOCOL_VERSION
        answer = self.call(messages.WardServiceOpen(protocol_version=protocol_version))
        if isinstance(answer, messages.Failure):
            raise exceptions.TrezorFailure(answer)
        if not isinstance(answer, messages.WardServiceOpenAck):
            raise exceptions.TrezorException(
                f"unexpected answer to WardServiceOpen: {type(answer).__name__}"
            )
        return answer

    def open(
        self, handler: WardServiceHandler, *, skip_pairing: bool = False
    ) -> WardServiceServer:
        """connect, pair, announce -- and hand back the loop that serves from here on."""
        self.connect()
        self.pair(skip=skip_pairing)
        self.announce()
        return WardServiceServer(t.cast("AnyWardServiceClient", self), handler)

    def __enter__(self: _C) -> _C:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class WardServiceClient(_ServiceClientBase):
    """Bring up the THP service channel: handshake, pair, and announce.

    The device PINS the daemon's static key on first bind and refuses every other key, so the key
    must be durable: persist a `credential` (a `StaticCredential` carries the private key) or pass
    `static_privkey`. With neither, the key is random -- right for a first run only.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        credential: Credential | None = None,
        static_privkey: bytes | None = None,
        app: _client.AppManifest | None = None,
        model: TrezorModel | None = None,
    ) -> None:
        self.transport = transport
        self.static_privkey = static_privkey
        self.app = app if app is not None else _client.AppManifest(app_name="wardd")
        if credential is not None:
            self.app.credentials = (credential,)
        self._model = model
        self._client: TrezorClientThp | None = None
        self._session: ThpSession | None = None

    def connect(self) -> None:
        """Allocate a channel and complete the handshake. Idempotent.

        The channel is built here so the static key is in the Noise state before the handshake;
        the transport is held open for the client's lifetime, since the device may ask any time.
        """
        if self._client is not None:
            return

        self.transport.open()

        channel = Channel.allocate(self.transport)
        if self.static_privkey is not None:
            channel._init_noise(static_privkey=self.static_privkey)
        channel.open(self.app.get_credentials())
        self.static_privkey = channel.host_static_privkey

        self._client = TrezorClientThp(
            self.app,
            self.transport,
            mapping=None,
            model=self._model,
            channel=channel,
        )

    @property
    def client(self) -> TrezorClientThp:
        if self._client is None:
            raise exceptions.TrezorException("not connected")
        return self._client

    @property
    def channel(self) -> Channel:
        return self.client.channel

    @property
    def static_pubkey(self) -> bytes:
        """The key the device pins: what identifies this daemon."""
        return self.channel.get_host_static_pubkey()

    def pair(self, skip: bool = False) -> None:
        """Pair this channel if needed (`skip` is the debug-build shortcut). Pairing alone does not
        grant the service role; the pinned key does."""
        pairing = self.client.pairing
        if pairing.is_paired():
            return
        if skip:
            pairing.skip()
        else:
            from .thp.pairing import default_pairing_flow

            default_pairing_flow(pairing)

    def store_credential(self) -> Credential:
        """The durable identity, for the caller to persist."""
        return self.client.pairing.request_credential()

    @property
    def session(self) -> ThpSession:
        """Session zero, built directly: `get_session` sends `GetFeatures`, which this interface
        refuses, and does wallet-session work a seedless service has no use for."""
        if self._session is None:
            from .thp.client import ThpSession as _ThpSession

            self._session = _ThpSession(self.client, 0)
        return self._session

    def call(self, msg: MessageType, timeout: float | None = None) -> MessageType:
        """One request, one raw response (failures returned, not raised). Pre-announce only."""
        return self.session.call_raw(msg, timeout=timeout)

    def read(self, timeout: float | None = None) -> MessageType:
        """One device-initiated request. See `WardServiceServer`."""
        return self.session.read(timeout=timeout)

    def write(self, msg: MessageType) -> None:
        """The answer to the request just read."""
        self.session.write(msg)

    def close(self) -> None:
        """Close the channel: a closed channel frees the interface at once, an abandoned one only
        after it goes idle."""
        if self._client is not None:
            self._client.channel.close()
            self._client = None
        self._session = None
        self.transport.close()


class WardServiceClientV1(_ServiceClientBase):
    """The same daemon over the V1 codec.

    No Noise handshake, so no identity to pin or persist. WARD's guarantees do not rest on it:
    leaf authenticity, proofs, the WM attestation and the device's own nonce/counter/root decide
    what is accepted. A hostile process on this interface can fail or stall an operation, not
    inject state.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        mapping: ProtobufMapping | None = None,
    ) -> None:
        from .mapping import DEFAULT_MAPPING

        self.transport = transport
        self.mapping = mapping if mapping is not None else DEFAULT_MAPPING
        self._open = False

    def connect(self) -> None:
        """Open the transport and hold it open. Idempotent."""
        if self._open:
            return
        self.transport.open()
        self._open = True

    def pair(self, skip: bool = False) -> None:
        """Nothing to pair. Present so a caller can drive either client the same way."""

    def _send(self, msg: MessageType) -> None:
        msg_type, msg_bytes = self.mapping.encode(msg)
        protocol_v1.write(self.transport, msg_type, msg_bytes)

    def _recv(self, timeout: float | None = None) -> MessageType:
        msg_type, msg_bytes = protocol_v1.read(self.transport, timeout=timeout)
        return self.mapping.decode(msg_type, msg_bytes)

    def call(self, msg: MessageType, timeout: float | None = None) -> MessageType:
        """One request, one raw response (failures returned, not raised). Pre-announce only."""
        self.connect()
        self._send(msg)
        return self._recv(timeout=timeout)

    def read(self, timeout: float | None = None) -> MessageType:
        """One device-initiated request. See `WardServiceServer`."""
        self.connect()
        return self._recv(timeout=timeout)

    def write(self, msg: MessageType) -> None:
        """The answer to the request just read."""
        self._send(msg)

    def close(self) -> None:
        if self._open:
            self.transport.close()
            self._open = False


def ward_service_client(
    client: TrezorClient,
    *,
    credential: Credential | None = None,
    static_privkey: bytes | None = None,
    app: _client.AppManifest | None = None,
    speaks_codec: bool | None = None,
) -> AnyWardServiceClient:
    """A daemon client for this device's WARD interface, of whichever kind it speaks.

    Decided by probing the service endpoint (independent of the wire protocol); pass
    `speaks_codec` to skip the probe. The identity arguments are THP-only.
    """
    transport = ward_transport(client.transport)

    if speaks_codec is None:
        transport.open()
        try:
            probed = service_speaks_codec(transport)
        finally:
            transport.close()
        # inconclusive means codec: every build serves it unless deliberately built otherwise
        speaks_codec = True if probed is None else probed

    if speaks_codec:
        return WardServiceClientV1(transport, mapping=client.mapping)

    return WardServiceClient(
        transport,
        credential=credential,
        static_privkey=static_privkey,
        app=app,
        model=client.model,
    )


class WardServiceServer:
    """The loop that answers the device once the endpoint is bound, over either client.

    One request, one reply, no pipelining: `serve_one` is the protocol and `serve_forever` repeats it.
    """

    def __init__(self, client: AnyWardServiceClient, handler: WardServiceHandler) -> None:
        self.client = client
        self.handler = handler
        self.served: list[str] = []  # every request answered, in order

    def serve_one(self, timeout: float | None = None) -> str:
        """Answer exactly one device request; returns its name. Raises `Timeout` if none came."""
        request = self.client.read(timeout=timeout)
        name = type(request).__name__
        self.served.append(name)

        reply = self.handler(request)
        if reply is not None:
            self.client.write(reply)
        else:
            LOG.info("handler answered nothing to %s", name)
        return name

    def serve_forever(
        self,
        stop: t.Callable[[], bool] | None = None,
        poll_timeout: float = 0.5,
    ) -> None:
        """Answer requests until `stop` says otherwise. `poll_timeout` only paces `stop` checks;
        the device owns the real deadline (`RPC_TIMEOUT_MS` in `apps.ward.service`)."""
        while stop is None or not stop():
            try:
                self.serve_one(timeout=poll_timeout)
            except Timeout:
                continue
