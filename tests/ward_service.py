# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

"""A minimal stand-in for `wardd`: enough to bind the service channel and be talked to.

DELIBERATELY NOT `trezorlib.thp.client.TrezorClientThp`. That client assumes it drives the
conversation -- it opens sessions with `ThpCreateNewSession`, which derives a wallet seed the
service must not have, and it reads only in reply to something it sent. The service channel is the
other way round: the daemon speaks once, to announce itself, and answers from then on.

ONE OWNER OF THE CHANNEL, ALWAYS. trezorlib's THP `Channel` is synchronous and stateful -- sync
bits, Noise state, transport reads -- so a reader in one thread plus a writer in another would have
one consume the frame the other is waiting for. With the device as sole initiator there is exactly
one loop and no second thread, which is why this file has no locking in it.

The responder loop and the real client belong in `trezorlib`; this exists so the device side can be
tested before the daemon does.
"""

from __future__ import annotations

import struct
import threading
import typing as t
from contextlib import contextmanager

import pytest

from trezorlib import messages, protobuf, ward
from trezorlib.thp.channel import Channel
from trezorlib.transport import Timeout
from trezorlib.transport.udp import UdpTransport

from .ward_keys import EMPTY_ROOT, root_mac

if t.TYPE_CHECKING:
    from trezorlib.debuglink import TrezorTestContext

# Offsets 4 and 5 are BLE's and 6 is the Tropic model's -- see `trezorlib._internal.emulator` and
# `core/embed/io/usb/usb_config.c`, which must agree.
WARD_PORT_OFFSET = 7

# Answered once per session by `serves_ward_over_a_service_channel`.
_IS_SERVICE_BUILD: bool | None = None

# `trezorlib.thp.client`'s application header: session id, message type.
_HEADER = ">BH"
_HEADER_LEN = struct.calcsize(_HEADER)

# Must match `apps.ward.service.PROTOCOL_VERSION`.
PROTOCOL_VERSION = 1


def _root_or_empty(root: bytes | None) -> bytes:
    """The form both sides agree on: an absent root IS the empty tree."""
    return root if root else EMPTY_ROOT


def _open_ward_transport(client: TrezorTestContext) -> UdpTransport | None:
    """An open transport for the WARD interface, or None if this build has no such interface.

    PROBED, NOT ASKED. Which transport a firmware serves WARD over is a build option and the
    device has no way to report it -- there is no feature flag for it and deliberately so, since
    a host that has to be told would be a host that could be lied to about it.
    """
    transport = client.transport
    if not isinstance(transport, UdpTransport):
        return None

    host, port = transport.device
    ward = UdpTransport(f"{host}:{port + WARD_PORT_OFFSET}")
    try:
        ward.open()
    except Exception:
        return None
    if not ward.is_ready():
        ward.close()
        return None
    return ward


def serves_ward_over_a_service_channel(client: TrezorTestContext) -> bool:
    """Whether this firmware is a SERVICE build. Cached: probing is a socket per call.

    Cached for the session rather than per test because it cannot change under us -- it is a
    property of the binary the emulator is running.
    """
    global _IS_SERVICE_BUILD

    if _IS_SERVICE_BUILD is None:
        ward = _open_ward_transport(client)
        _IS_SERVICE_BUILD = ward is not None
        if ward is not None:
            ward.close()
    return _IS_SERVICE_BUILD


def ward_transport(client: TrezorTestContext) -> UdpTransport:
    """A transport for the WARD interface, or skip if this build has none.

    Skipped rather than failed because the interface is a BUILD OPTION: a firmware serves WARD
    either over the ordinary connection or over its own channel, never both, so a connect build
    legitimately has nothing listening here.
    """
    ward = _open_ward_transport(client)
    if ward is None:
        pytest.skip("this build has no WARD service interface")
    return ward


class MockWardService:
    """The daemon's side of the channel: open it, announce, then answer what the device asks."""

    def __init__(self, client: TrezorTestContext, session_id: int = 0) -> None:
        self._client = client
        self._mapping = client.client.mapping
        self.session_id = session_id
        self.transport = ward_transport(client)
        self.channel: Channel | None = None
        # The key the device pins. Recorded so a test can reconnect AS THE SAME daemon, which is
        # what separates "a stranger" from "the same daemon twice".
        self.host_static_privkey: bytes | None = None
        # What the daemon serves from. Set by the test; a daemon with no replica can still bind,
        # which is the state a freshly started one is in.
        self.store = None
        self.wm = None
        self.k_mac = b""
        self.timestamp_base = 1_700_000_000
        # Every request this daemon has answered, in order. A test that wants to assert how many
        # round trips an operation took counts these rather than inferring it from timing.
        self.served: list[str] = []
        # Answer every fetch with `WardSyncRequired`, whatever the device's head. Models a daemon
        # that disagrees with the device and keeps disagreeing.
        self.always_out_of_sync = False
        self._stop = False
        self.error: Exception | None = None

    # --- lifecycle ---------------------------------------------------------------------

    def connect(self, host_static_privkey: bytes | None = None) -> Channel:
        """Allocate a channel, handshake, and pair it.

        PAIRING IS NOT OPTIONAL. A handshaked-but-unpaired channel sits in the pairing state, where
        every application message is refused as unrecognised -- so without this the device's own
        checks would never be reached and a test asserting "refused" would pass for the wrong
        reason.

        `host_static_privkey` makes the daemon's identity choosable: the key is what the device
        pins, and a distinct one is how "a different daemon" is expressed. Left unset it is random
        per channel, which is what a real daemon that has lost its key would look like.
        """
        channel = Channel.allocate(self.transport)
        channel._init_noise(static_privkey=host_static_privkey)
        self.host_static_privkey = channel.host_static_privkey
        channel.open([])
        self.channel = channel
        self._pair(channel)
        return channel

    def _pair(self, channel: Channel) -> None:
        """Pair via SkipPairing, borrowing the host's client for the exchange.

        `PairingController` drives the conversation through `client.channel`, so the client is
        pointed at this channel and put back afterwards -- the wallet channel must keep working,
        and these tests exist precisely to check the two do not disturb each other.
        """
        from trezorlib.thp.pairing import PairingController

        client = self._client.client
        saved_channel = client.channel
        saved_pairing = client.pairing
        saved_interact = client._interact_ctx
        try:
            client.channel = channel
            client._interact_ctx = client._interact()
            pairing = PairingController(client)
            client.pairing = pairing
            pairing.skip()
        finally:
            client.channel = saved_channel
            client.pairing = saved_pairing
            client._interact_ctx = saved_interact

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        self.transport.close()

    def __enter__(self) -> MockWardService:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- the application layer ---------------------------------------------------------

    def send(self, msg: protobuf.MessageType) -> None:
        assert self.channel is not None
        msg_type, msg_bytes = self._mapping.encode(msg)
        self.channel.write_chunk(
            struct.pack(_HEADER, self.session_id, msg_type) + msg_bytes
        )

    def receive(self, timeout: float | None = None) -> protobuf.MessageType:
        assert self.channel is not None
        raw = self.channel.read_chunk(timeout=timeout)
        session_id, msg_type = struct.unpack(_HEADER, raw[:_HEADER_LEN])
        assert session_id == self.session_id, "reply arrived for another session"
        return self._mapping.decode(msg_type, raw[_HEADER_LEN:])

    def call(
        self, msg: protobuf.MessageType, timeout: float | None = None
    ) -> protobuf.MessageType:
        self.send(msg)
        return self.receive(timeout=timeout)

    def open_service(
        self, protocol_version: int | None = None
    ) -> protobuf.MessageType:
        """Announce this channel as the WARD service. The last thing the daemon initiates."""
        if protocol_version is None:
            protocol_version = PROTOCOL_VERSION
        return self.call(messages.WardServiceOpen(protocol_version=protocol_version))

    # --- serving, which is all the daemon does after announcing itself -------------------

    def serve_one(self, timeout: float | None = None) -> str:
        """Answer exactly one device-initiated request. Returns which one it was.

        A LOOP OF ONE, deliberately exposed. The device asks and the daemon answers, so a test that
        wants to assert how many round trips an operation took can count them here instead of
        inferring it from timing.
        """
        request = self.receive(timeout=timeout)
        name = request.__class__.__name__

        self.served.append(name)

        if name == "WardSyncRequest":
            self.send(self._sync_response(request))
        elif name == "WardServiceFetch":
            self.send(self._fetch_response(request))
        else:
            raise AssertionError(f"the daemon was asked something it cannot serve: {name}")

        return name

    def serve_forever(self) -> None:
        """Answer requests until told to stop, or until something goes wrong.

        A FAILURE IS RECORDED, NOT SWALLOWED. A responder that died quietly would present as the
        device timing out on an unanswered request -- which is a real failure mode of its own, so
        the two must not be confusable. `serving` re-raises whatever landed here.
        """
        while not self._stop:
            try:
                self.serve_one(timeout=0.5)
            except Timeout:
                continue
            except Exception as exc:  # noqa: B902
                self.error = exc
                return

    @contextmanager
    def serving(self) -> t.Iterator[MockWardService]:
        """Run the responder in a thread for the duration of the block.

        A THREAD IS SAFE HERE AND ONLY HERE. trezorlib's THP `Channel` is synchronous and stateful
        -- sync bits, Noise state, transport reads -- so two threads sharing one channel would have
        each consuming frames the other is waiting for. This thread owns the SERVICE channel and
        touches nothing else; the wallet channel stays with the main thread. In production the two
        are separate processes and the question does not arise.
        """
        self._stop = False
        self.error = None
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        try:
            yield self
        finally:
            self._stop = True
            thread.join(timeout=5)
            if self.error is not None:
                raise AssertionError(f"the daemon failed while serving: {self.error!r}")

    # --- what a daemon knows ------------------------------------------------------------

    def _sync_response(self, request):
        """The current head, attested, with the links from the device's head forward.

        THE WM IS TOLD THE MAC, never asked to compute one: it holds no key of ours and could not.
        Preserving that asymmetry is the point of the mock, so the mac comes from the oracle's
        `root_mac` here exactly as it would come from a device in production.

        A wallet the WM has never seen bootstraps from the device's own authorised opening head --
        which is why `current_mac` and `head_init_sig` are on the request at all.
        """
        assert self.store is not None and self.wm is not None
        ward_id = request.ward_id

        counter = self.store.counter
        mac = root_mac(self.k_mac, ward_id, counter, self.store.root())
        timestamp = self.timestamp_base + counter

        if self.wm.head(ward_id) is None:
            # First contact: adopt the head the device says it holds, authorised by its own
            # signature over it, and attest that.
            self.wm.attest_head(
                ward_id, request.nonce, request.current_mac, request.head_init_sig
            )
        if counter != self.wm.head(ward_id)[0]:
            # A head the WM does not hold yet. In production a device's publish would have put it
            # there; here the fixture is standing in for that device.
            self.wm.publish(ward_id, counter, mac, timestamp)

        att_counter, att_mac, att_timestamp, signature = self.wm.attest(
            ward_id, request.nonce
        )

        links = [
            messages.WardChainLink(
                from_counter=fc,
                from_root=fr,
                to_counter=tc,
                to_root=tr,
                auth_commit=ac,
            )
            for (fc, fr, tc, tr, ac) in self.store.links
            if fc >= (request.current_counter or 0)
        ]

        return messages.WardSyncResponse(
            counter=att_counter,
            mac=att_mac,
            timestamp=att_timestamp,
            wm_signature=signature,
            links=links,
        )

    def _fetch_response(self, request):
        """A leaf and its proof, or `WardSyncRequired` if the device is behind.

        HEAD-AWARE, which is the point of the request carrying a head at all: serving a proof
        against a root the device does not trust would fail on the device with nothing to say why.
        Both fields are compared -- several roots may share a counter across forks.
        """
        assert self.store is not None

        # NORMALISED THROUGH `EMPTY_ROOT` ON BOTH SIDES. The device stores an empty tree as
        # `EMPTY_ROOT` -- a real hash -- specifically so that state cannot be confused with "no
        # root at all", which is what "cannot verify" looks like. The host trie reports None for
        # the same tree. Comparing the two raw forms says a freshly synced genesis wallet is out
        # of sync with the very daemon it just synced from.
        if self.always_out_of_sync:
            return messages.WardSyncRequired()

        if (request.current_counter or 0) != self.store.counter or _root_or_empty(
            request.current_root
        ) != _root_or_empty(self.store.root()):
            return messages.WardSyncRequired()

        # The same `EntryProvider` the connect path serves from, so both transports answer a
        # fetch from ONE piece of host logic. A second copy of "what does this store hold at this
        # path" is exactly the kind of divergence that makes a proof failure unattributable.
        answer = ward.store_provider(self.store)(request.entry_key)
        leaf = answer.leaf
        return messages.WardEntryAck(
            identity=leaf.identity if leaf is not None else None,
            content=leaf.content if leaf is not None else None,
            proof=answer.proof or [],
            witness_entry_key=answer.witness_entry_key,
            witness_commit=answer.witness_commit,
        )
