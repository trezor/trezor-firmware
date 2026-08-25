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

TWO TRANSPORTS, ONE PROTOCOL. `WardServiceClient` speaks THP; `WardServiceClientV1` speaks the V1
codec, for models that have no THP at all (Safe 5 and everything before it). What differs is only
how bytes get across -- the inversion, the message set and the single-owner rule are identical, so
`WardServiceServer` serves either one. Pick with `ward_service_client`.

WHAT MAKES THIS DIFFERENT FROM EVERY OTHER trezorlib CLIENT is that the conversation inverts.
Ordinarily the host asks and the device answers, and the whole client is built around that: sessions
are opened by `ThpCreateNewSession`, reads happen in reply to something just written. Here the daemon
speaks exactly once -- `WardServiceOpen`, to say which channel it is -- and from then on the DEVICE
initiates and the daemon answers. `WardServiceClient` covers the first half and `WardServiceServer`
the second, and they are two classes rather than one because the same process is a client until it
announces and a server afterwards.

NO WALLET SESSION, DELIBERATELY. `ThpCreateNewSession` derives a seed, and the service must not have
one: every derivation a WARD operation needs happens in the wallet workflow that calls the service.
So this uses a seedless session (`get_session(passphrase=None)`), and the device's receive boundary
refuses `ThpCreateNewSession` on this interface anyway.

ONE OWNER OF THE CHANNEL, ALWAYS. trezorlib's THP `Channel` is synchronous and stateful -- sync bits,
Noise state, transport reads -- so a reader in one thread plus a writer in another would have one
consume the frame the other is waiting for. With the device as the sole initiator there is exactly one
loop and no second thread, which is why there is no locking here. A caller that wants the loop off
its main thread owns that decision, and owns keeping everything else off this channel.

ACKS GO OUT ON RECEIPT, and this is the subtle one. `Channel._send_ack` SKIPS the standalone ack when
an interact context is active, so the ack can piggyback on the next outgoing message -- which is
right for a host driving a workflow and wrong here: the device would wait through a whole database
lookup and proof construction before learning its request had even arrived. So the loop below reads
through `Session.read`/`Session.write`, which unlike `Session.call` do not enter that context. It
follows that a caller must not wrap serving in one either.

THE IDENTITY THAT MATTERS IS THE STATIC KEY. The device pins it, so it is what separates "the daemon"
from "a paired host", and it has to survive restarts -- see `WardServiceClient`.
"""

from __future__ import annotations

import logging
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

# The protocol this module speaks, matching `apps.ward.service.PROTOCOL_VERSION`. The device refuses
# a version it does not know by name rather than negotiating down, so a daemon built against older
# firmware is told what is wrong instead of misreading a field.
PROTOCOL_VERSION = 1

# WHERE THE INTERFACE IS, and it is found rather than assumed -- see `ward_transport`.
#
# On the emulator every interface is a UDP port at a fixed offset from the wire one: 21324 + 7. Four
# and five are BLE's and six is the Tropic model's, which is why this is seven.
WARD_PORT_OFFSET = 7

# On real USB the interface carries a subclass/protocol pair of its own, where the wire interface
# uses 0x00/0x00. That pair is the handle: see `ward_transport` for why an index is not.
WARD_USB_SUBCLASS = 0x57
WARD_USB_PROTOCOL = 0x01

WardServiceHandler = t.Callable[["MessageType"], "MessageType | None"]
"""What a daemon is: a function from one device request to one reply.

Returning None answers nothing, which is not a normal outcome but a representable one -- it is what a
lost reply looks like from the device's side, and the device is specified to treat that as an
ambiguous failure rather than a refusal. Tests use it; a real daemon should not.
"""


def ward_transport(wire: Transport) -> Transport:
    """The transport for this device's WARD interface, given one for its wire interface.

    LOCATED, NOT INDEXED, and that is a requirement rather than a nicety. `usb_configure` assigns
    interface numbers in call order, and which interfaces a build carries depends on options that
    have nothing to do with WARD -- webauthn follows `universal_fw`, vcp and debug follow their own.
    Making the service channel its own build axis widens that further. So a daemon that hardcoded an
    index would be reading whichever interface that particular firmware happened to put there.

    The subclass/protocol pair is stable across all of it, because it describes what the interface IS
    rather than where it landed.
    """
    if isinstance(wire, UdpTransport):
        host, port = wire.device
        return UdpTransport(f"{host}:{port + WARD_PORT_OFFSET}")

    return _webusb_ward_transport(wire)


def _webusb_ward_transport(wire: Transport) -> Transport:
    """Same device, the interface whose descriptor says WARD.

    GAP(ward): unvalidated on real hardware. Appending an interface must not disturb interface 0 or
    1 -- trezorlib hardcodes those for wire and debug -- and the endpoint budget on the smallest
    model has not been checked. Both are hardware questions this cannot answer from an emulator.
    """
    from .transport.webusb import WebUsbTransport

    if not isinstance(wire, WebUsbTransport):
        raise exceptions.TrezorException(
            f"cannot reach a WARD service interface over {type(wire).__name__}"
        )

    ward = WebUsbTransport(wire.device)
    # Set after construction because `WebUsbTransport.__init__` knows only two interfaces, wire and
    # debug, and derives both from a flag. Teaching it a third by name would put a WARD-specific
    # concept into the generic transport; this keeps the knowledge here, where the rest of it is.
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
                    if address & 0x80:  # IN
                        # The firmware pairs ep_in 0x8n with ep_out 0x0n, and the transport takes
                        # the number both share.
                        return setting.getNumber(), address & 0x7F
    raise exceptions.TrezorException("this device has no WARD service interface")


class WardServiceClient:
    """Bring up the service channel: handshake, pair, and announce.

    IDENTITY IS THE POINT OF THE CONSTRUCTOR ARGUMENTS. The device PINS the daemon's static public
    key on first bind, and refuses every other key from then on -- so a daemon that comes back with a
    fresh key is not merely unrecognised, it is locked out, and recovery is an ownership migration
    with a user decision in it (`WardResetService`). The key therefore has to be durable, and there
    are two ways to hold one:

      `credential` -- what a daemon that has paired should persist. A `StaticCredential` carries the
                      host private key along with the pairing credential, and the handshake installs
                      it, so reconnecting is automatic and needs no separate key store.

      `static_privkey` -- the lower-level handle, for a daemon that keeps only the key, and for tests
                      that need to say "the same daemon" or "a different one" without pairing twice.

    Neither given, the key is random: correct for a FIRST run and wrong for every later one, so a
    caller taking that path must pair, request a credential and store it before exiting.
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

    # --- bringing the channel up -----------------------------------------------------------

    def connect(self) -> None:
        """Allocate a channel and complete the handshake. Idempotent.

        The channel is built HERE rather than by `TrezorClientThp`, which allocates its own, because
        the static key has to be installed into the Noise state before the handshake starts. Letting
        the client do it and replacing the channel afterwards would leave a second open channel on an
        interface that holds exactly one -- so the interface would be occupied by the one being
        discarded.
        """
        if self._client is not None:
            return

        # HELD OPEN FOR THIS CLIENT'S LIFETIME, which is what makes a daemon different from a CLI
        # call. Every operation below wraps the transport in `with`, and `Transport` ref-counts that
        # -- so without a standing open the count returns to zero when the handshake ends and the
        # socket closes underneath the channel that just finished negotiating over it. The device is
        # the initiator here and may ask at any moment, so there is no later point at which reopening
        # would be the natural thing to do.
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
        """The key the device pins. What identifies this daemon, and nothing else does."""
        return self.channel.get_host_static_pubkey()

    def pair(self, skip: bool = False) -> None:
        """Pair this channel, if it is not paired already.

        PAIRING IS NECESSARY BUT SAYS NOTHING about the service role. It proves the host holds a
        credential this device issued, which every paired host does, Suite included -- which is
        exactly why the device pins a key on top of it. An unpaired channel never gets as far as
        being refused: the device answers every application message on it as unrecognised.

        `skip` is the debug-build shortcut the device tests use. A real daemon runs a real pairing
        flow (`thp.pairing.default_pairing_flow`) and then `store_credential`.
        """
        pairing = self.client.pairing
        if pairing.is_paired():
            return
        if skip:
            pairing.skip()
        else:
            from .thp.pairing import default_pairing_flow

            default_pairing_flow(pairing)

    def store_credential(self) -> Credential:
        """The durable identity, for the caller to persist. See the class docstring."""
        return self.client.pairing.request_credential()

    @property
    def session(self) -> ThpSession:
        """Session zero, built directly -- `get_session` does not apply on this interface.

        NOT AN OPTIMISATION, A NECESSITY. `TrezorClient.get_session` begins with
        `check_firmware_version`, which reads `features`, which sends `GetFeatures` -- and the
        device's receive boundary accepts nothing but `WardServiceOpen` on this interface before
        binding, and dispatches nothing at all after it. So the ordinary path fails on its first
        message, in a way that reads as a protocol error rather than as "that question cannot be
        asked here".

        Nothing is lost with it. Everything it does is about a WALLET session -- passphrase
        capabilities, Cardano derivation, a session id to derive under -- and a service has none of
        that by design: it holds no seed, and every derivation a WARD operation needs happens in the
        wallet workflow that called it.
        """
        if self._session is None:
            from .thp.client import ThpSession as _ThpSession

            self._session = _ThpSession(self.client, 0)
        return self._session

    # --- announcing ------------------------------------------------------------------------

    def call(
        self, msg: MessageType, timeout: float | None = None
    ) -> MessageType:
        """One request, one raw response, with failures returned rather than raised.

        Only useful before the conversation inverts -- which in practice means `WardServiceOpen` and
        nothing else. Raw because a refusal is information a daemon acts on: "another daemon is bound"
        and "unsupported protocol version" call for different behaviour, and both arrive as Failure.
        """
        return self.session.call_raw(msg, timeout=timeout)

    def read(self, timeout: float | None = None) -> MessageType:
        """One device-initiated request. See `WardServiceServer`."""
        return self.session.read(timeout=timeout)

    def write(self, msg: MessageType) -> None:
        """The answer to the request just read."""
        self.session.write(msg)

    def announce(self, protocol_version: int | None = None) -> messages.WardServiceOpenAck:
        """Bind this channel as the WARD service. Raises if the device refuses.

        THE LAST THING THIS SIDE INITIATES. Afterwards the device asks and the daemon answers, so a
        further host-initiated message on this channel gets no reply AND no ack -- the device stops
        reading it, and the ack is a side effect of the application reading.
        """
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
        return WardServiceServer(self, handler)

    def close(self) -> None:
        """Close the channel, which frees the interface for the next daemon.

        Worth doing rather than dropping the socket: on the device an interface tracks one channel,
        and a closed one is displaced at once while a merely abandoned one is displaced only after it
        goes idle.
        """
        if self._client is not None:
            self._client.channel.close()
            self._client = None
        self._session = None
        self.transport.close()

    def __enter__(self) -> WardServiceClient:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class WardServiceClientV1:
    """The same daemon, on a device that speaks the V1 codec.

    NO IDENTITY, AND NOTHING TO PERSIST. The codec carries no Noise handshake, so there is no static
    key for the device to pin and no credential to store -- `WardServiceOpen` establishes only that
    a process is listening on the dedicated interface. That is the whole of the transport-level
    authentication, deliberately: WARD's own guarantees do not rest on it. Leaf authenticity, the
    MPT proof, the WM attestation and the device-minted nonce/counter/mac are what accept an answer,
    and none of them ask who sent it.

    So a hostile process that can open this interface can fail an operation, answer wrongly or force
    an unnecessary sync. It cannot inject state.

    ONE OWNER OF THE TRANSPORT, same as THP and for a plainer reason: a UDP socket or a USB endpoint
    has one reader, and a second one would consume the frame the first is waiting for.
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

    # --- bringing the interface up ---------------------------------------------------------

    def connect(self) -> None:
        """Open the transport and hold it open. Idempotent.

        HELD FOR THIS CLIENT'S LIFETIME, for the same reason as the THP client: `Transport` is
        ref-counted, and the device may ask at any moment, so there is no later point at which
        reopening would be the natural thing to do.
        """
        if self._open:
            return
        self.transport.open()
        self._open = True

    def pair(self, skip: bool = False) -> None:
        """Nothing to pair. Present so a caller can drive either client the same way."""

    # --- talking ---------------------------------------------------------------------------

    def _send(self, msg: MessageType) -> None:
        msg_type, msg_bytes = self.mapping.encode(msg)
        protocol_v1.write(self.transport, msg_type, msg_bytes)

    def _recv(self, timeout: float | None = None) -> MessageType:
        msg_type, msg_bytes = protocol_v1.read(self.transport, timeout=timeout)
        return self.mapping.decode(msg_type, msg_bytes)

    def call(self, msg: MessageType, timeout: float | None = None) -> MessageType:
        """One request, one raw response, with failures returned rather than raised.

        Only useful before the conversation inverts -- in practice `WardServiceOpen` and nothing
        else. Raw because a refusal is information a daemon acts on.
        """
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

    def announce(
        self, protocol_version: int | None = None
    ) -> messages.WardServiceOpenAck:
        """Bind this interface as the WARD service. Raises if the device refuses.

        THE LAST THING THIS SIDE INITIATES. Afterwards the device asks and the daemon answers, and
        a further host-initiated message is read by whichever RPC is in flight, fails its type check
        and costs the daemon the conversation. With nothing in flight it is refused by name.
        """
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
        """connect, announce -- and hand back the loop that serves from here on."""
        self.connect()
        self.announce()
        return WardServiceServer(self, handler)

    def close(self) -> None:
        if self._open:
            self.transport.close()
            self._open = False

    def __enter__(self) -> WardServiceClientV1:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def ward_service_client(
    client: TrezorClient,
    *,
    credential: Credential | None = None,
    static_privkey: bytes | None = None,
    app: _client.AppManifest | None = None,
) -> AnyWardServiceClient:
    """A daemon client for this device's WARD interface, of whichever kind it speaks.

    DECIDED BY THE WIRE CLIENT, not by probing the service interface. Which protocol a device
    speaks is a property of the device, already established by whatever opened the wire connection
    -- asking the service interface again would be a second answer to a settled question, and one
    that a silent daemon-less interface cannot give.

    The identity arguments are THP's and are ignored on a codec device, which has no identity to
    carry. That is not an oversight; see `WardServiceClientV1`.
    """
    from .protocol_v1 import TrezorClientV1

    transport = ward_transport(client.transport)

    if isinstance(client, TrezorClientV1):
        return WardServiceClientV1(transport, mapping=client.mapping)

    return WardServiceClient(
        transport,
        credential=credential,
        static_privkey=static_privkey,
        app=app,
        model=client.model,
    )


class WardServiceServer:
    """The loop that answers the device, once the service endpoint is bound.

    TRANSPORT-NEUTRAL, because the inversion is a property of the protocol and not of the wire. It
    talks to the client through `read`/`write`, which both `WardServiceClient` (THP) and
    `WardServiceClientV1` (codec) provide.

    A LOOP OF ONE MESSAGE, exposed as `serve_one`, because that is the whole protocol: the device
    writes a request and reads the reply, and there is no pipelining, no request ids and no second
    conversation. `serve_forever` is that one step repeated.
    """

    def __init__(self, client: AnyWardServiceClient, handler: WardServiceHandler) -> None:
        self.client = client
        self.handler = handler
        # Every request answered, in order. A caller that wants to know how many round trips an
        # operation took counts these rather than inferring it from timing.
        self.served: list[str] = []

    def serve_one(self, timeout: float | None = None) -> str:
        """Answer exactly one device-initiated request. Returns the name of what it was.

        Raises `Timeout` if nothing arrives, which is not an error condition here -- the device asks
        only when a WARD operation needs something, so quiet is the normal state. `serve_forever`
        treats it as such.
        """
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
        """Answer requests until `stop` says otherwise, or forever.

        `poll_timeout` only decides how often `stop` is consulted; it is not a deadline on anything.
        The governing deadline is the device's, and it is the device that gives up on a daemon that
        stops answering -- see `RPC_TIMEOUT_MS` in `apps.ward.service`.
        """
        while stop is None or not stop():
            try:
                self.serve_one(timeout=poll_timeout)
            except Timeout:
                continue
