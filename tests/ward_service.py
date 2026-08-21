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

"""A stand-in for `wardd`: a replica and a WM behind `trezorlib.ward_service`.

WHAT IS LEFT HERE IS ONLY WHAT A MOCK SHOULD BE. The channel, the pairing, the announce and the
responder loop are `trezorlib.ward_service`'s -- the real client a daemon will use -- so this file is
the daemon's BUSINESS LOGIC and nothing else: what the replica holds, what the WM says about it, and
the handful of knobs that make each failure mode reproducible.

That split is worth keeping honest. Anything living here is untested transport as far as production
is concerned, so the more of it that moves into the library, the more of these device tests exercise
the code a daemon will actually run.
"""

from __future__ import annotations

import threading
import typing as t
from contextlib import contextmanager

import pytest

from trezorlib import messages, ward
from trezorlib.client import AppManifest
from trezorlib.transport.udp import UdpTransport
from trezorlib.ward_service import (
    PROTOCOL_VERSION,
    WARD_PORT_OFFSET,
    WardServiceClient,
    WardServiceServer,
)
from trezorlib.ward_service import ward_transport as _ward_interface_of

from .ward_keys import EMPTY_ROOT, bip39_seed, derive_k_mac, derive_ward_id, root_mac

if t.TYPE_CHECKING:
    from trezorlib.debuglink import TrezorTestContext
    from trezorlib.protobuf import MessageType

    from .ward_trie import WardTrie
    from .ward_wm import MockWM

__all__ = [
    "DEFAULT_K_MAC",
    "DEFAULT_SEED",
    "DEFAULT_WARD_ID",
    "PROTOCOL_VERSION",
    "WARD_PORT_OFFSET",
    "MockWardService",
    "bound_daemon",
    "serves_ward_over_a_service_channel",
    "ward_transport",
]

# The keys of the wallet a default-set-up device holds: the default mnemonic and no passphrase
# (`SetupParams` in conftest.py). A daemon has to be able to reproduce the device's macs, since the
# WM cannot compute one -- so the fixture stands in for a device that already published.
DEFAULT_SEED = bip39_seed(" ".join(["all"] * 12))
DEFAULT_K_MAC = derive_k_mac(DEFAULT_SEED)
DEFAULT_WARD_ID = derive_ward_id(DEFAULT_SEED)

# Answered once per session by `serves_ward_over_a_service_channel`.
_IS_SERVICE_BUILD: bool | None = None


def _root_or_empty(root: bytes | None) -> bytes:
    """The form both sides agree on: an absent root IS the empty tree."""
    return root if root else EMPTY_ROOT


# How many times to ping before concluding the interface is not there. `UdpTransport`'s socket
# timeout is 100 ms, and a single missed reply is not evidence: the emulator answers the ping from
# its io poll, so a device busy inside a workflow can be slower than that. This decides which HALF
# OF THE TEST SUITE RUNS, so a false "absent" silently runs every connect-mode test against a
# service build -- ninety-odd failures whose cause is nowhere near where they appear. On a genuine
# connect build there is no socket bound at all and the first attempt fails at once with
# ECONNREFUSED, so the retries cost that build nothing.
_PROBE_ATTEMPTS = 10


def _open_ward_transport(client: TrezorTestContext) -> UdpTransport | None:
    """An open transport for the WARD interface, or None if this build has no such interface.

    PROBED, NOT ASKED. Which transport a firmware serves WARD over is a build option and the
    device has no way to report it -- there is no feature flag for it and deliberately so, since
    a host that has to be told would be a host that could be lied to about it.

    WHERE the interface is comes from `trezorlib.ward_service`, so a real daemon and this probe
    cannot end up disagreeing about it.
    """
    transport = client.transport
    if not isinstance(transport, UdpTransport):
        return None

    ward_iface = _ward_interface_of(transport)
    assert isinstance(ward_iface, UdpTransport)
    try:
        ward_iface.open()
    except Exception:
        return None
    for _attempt in range(_PROBE_ATTEMPTS):
        if ward_iface.is_ready():
            return ward_iface
    ward_iface.close()
    return None


def serves_ward_over_a_service_channel(client: TrezorTestContext) -> bool:
    """Whether this firmware is a SERVICE build. Cached: probing is a socket per call.

    Cached for the session rather than per test because it cannot change under us -- it is a
    property of the binary the emulator is running.
    """
    global _IS_SERVICE_BUILD

    if _IS_SERVICE_BUILD is None:
        ward_iface = _open_ward_transport(client)
        _IS_SERVICE_BUILD = ward_iface is not None
        if ward_iface is not None:
            ward_iface.close()
    return _IS_SERVICE_BUILD


def ward_transport(client: TrezorTestContext) -> UdpTransport:
    """A transport for the WARD interface, or skip if this build has none.

    Skipped rather than failed because the interface is a BUILD OPTION: a firmware serves WARD
    either over the ordinary connection or over its own channel, never both, so a connect build
    legitimately has nothing listening here.
    """
    ward_iface = _open_ward_transport(client)
    if ward_iface is None:
        pytest.skip("this build has no WARD service interface")
    return ward_iface


class MockWardService:
    """A replica, a WM, and the knobs that make each failure mode reproducible.

    THE WM IS NEVER ASKED TO COMPUTE A MAC, and preserving that asymmetry is most of the point of
    this mock. A real WM holds only (counter, mac) and no key of this wallet, so every mac it stores
    was handed to it -- by a device in production, and by the oracle's `root_mac` here.
    """

    def __init__(self, client: TrezorTestContext) -> None:
        # NOTE: constructing this on a connect build no longer skips the test. It used to, as a side
        # effect of reaching for the interface through `ward_transport`; a real client has no
        # business skipping tests, so a file that needs the interface says
        # `pytest.mark.ward_transport("service")` and says it where it can be read.
        self._client = client
        # A MANIFEST OF ITS OWN, sharing only the button callback. A daemon is a separate host
        # application, so it must not inherit the test client's CREDENTIALS -- one matching this
        # Trezor would install the wallet host's static key into this channel's handshake, and every
        # test that distinguishes one daemon from another would be talking about the wrong key. The
        # button callback is the one thing worth borrowing: pairing raises a `ButtonRequest`, and in
        # a test the answer is "press it over debuglink" rather than "wait for a person".
        self.service = WardServiceClient(
            _ward_interface_of(client.transport),
            app=AppManifest(
                app_name="wardd-mock",
                button_callback=client.client.app.button_callback,
            ),
        )
        self.server = WardServiceServer(self.service, self.handle)

        # What the daemon serves from. Set by the test; a daemon with no replica can still bind,
        # which is the state a freshly started one is in.
        self.store: WardTrie | None = None
        self.wm: MockWM | None = None
        self.k_mac = b""
        self.timestamp_base = 1_700_000_000
        # The wallet this daemon is answering for, learned from the first sync. `WardServiceFetch`
        # and `WardPublish` do not carry it, because one logical service fronts one replica -- so
        # the sync is where it is established, exactly as it is for a real wardd.
        self.ward_id: bytes | None = None

        # --- knobs, each naming the one device-side behaviour it exists to reach ---
        # Answer every fetch with `WardSyncRequired`, whatever the device's head. Models a daemon
        # that disagrees with the device and keeps disagreeing.
        self.always_out_of_sync = False
        # Apply and publish a mutation, then say nothing. The ambiguous failure the write-ahead
        # journal exists for: the write DID land and the device cannot know it.
        self.drop_publish_ack = False
        # Attest a DIFFERENT (counter, mac) than the one that was published, signed properly. Models
        # a WM that is authentic but not answering the question asked -- which is the only freedom a
        # WM has, since it cannot forge a mac.
        self.publish_ack_override: tuple[int, bytes] | None = None

        self._stop = False
        self.error: Exception | None = None

    # --- lifecycle ---------------------------------------------------------------------

    @property
    def served(self) -> list[str]:
        """Every request answered, in order. Counted rather than timed -- see `serve_one`."""
        return self.server.served

    @property
    def host_static_privkey(self) -> bytes | None:
        """The identity the device pins. Recorded so a test can reconnect AS THE SAME daemon,
        which is what separates "a stranger" from "the same daemon twice"."""
        return self.service.static_privkey

    def connect(self, host_static_privkey: bytes | None = None) -> None:
        """Handshake and pair.

        PAIRING IS NOT OPTIONAL. A handshaked-but-unpaired channel sits in the pairing state, where
        every application message is refused as unrecognised -- so without it the device's own
        checks would never be reached and a test asserting "refused" would pass for the wrong
        reason.

        `host_static_privkey` makes the daemon's identity choosable: the key is what the device
        pins, and a distinct one is how "a different daemon" is expressed. Left unset it is random,
        which is what a real daemon that has lost its key would look like. A real daemon that has
        NOT lost it persists the same value, inside the credential it stores after pairing.
        """
        self.service.static_privkey = host_static_privkey
        self.service.connect()
        self.service.pair(skip=True)

    def close(self) -> None:
        self.service.close()

    def __enter__(self) -> MockWardService:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- announcing -------------------------------------------------------------------

    @property
    def channel(self):
        """The THP channel, for tests that need to reach below the protocol."""
        return self.service.channel

    def send(self, msg: MessageType) -> None:
        """Write without reading -- ONLY to prove that a daemon cannot.

        Deliberately absent from `trezorlib.ward_service`: after binding, the device is the sole
        initiator, so an unsolicited message from this side is not a supported operation but the
        thing the inversion exists to rule out. It gets no reply and no THP ack -- the ack is a side
        effect of the application reading -- so this raises `Timeout`, which is the assertion.
        """
        self.service.session.write(msg)

    def call(self, msg: MessageType, timeout: float | None = None) -> MessageType:
        return self.service.call(msg, timeout=timeout)

    def open_service(self, protocol_version: int | None = None) -> MessageType:
        """Announce this channel as the WARD service, RAW.

        Raw because half of these tests are about being refused, and the refusal IS the assertion:
        `WardServiceClient.announce` raises, which is right for a daemon and useless here.
        """
        if protocol_version is None:
            protocol_version = PROTOCOL_VERSION
        return self.call(messages.WardServiceOpen(protocol_version=protocol_version))

    # --- serving, which is all the daemon does after announcing itself -------------------

    def serve_one(self, timeout: float | None = None) -> str:
        return self.server.serve_one(timeout=timeout)

    def serve_forever(self) -> None:
        """Answer requests until told to stop, or until something goes wrong.

        A FAILURE IS RECORDED, NOT SWALLOWED. A responder that died quietly would present as the
        device timing out on an unanswered request -- which is a real failure mode of its own, so
        the two must not be confusable. `serving` re-raises whatever landed here.
        """
        try:
            self.server.serve_forever(stop=lambda: self._stop)
        except Exception as exc:  # noqa: B902
            self.error = exc

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

    def handle(self, request: MessageType) -> "MessageType | None":
        """The daemon itself: one device request in, one reply out.

        The dispatch is on the message NAME rather than `isinstance`, so the mock stays readable
        against a message set that grows -- and so an unexpected request is named in the failure
        rather than silently falling through to a reply of the wrong type.
        """
        name = type(request).__name__
        if name == "WardSyncRequest":
            return self._sync_response(request)
        if name == "WardServiceFetch":
            return self._fetch_response(request)
        if name == "WardPublish":
            return self._publish_response(request)
        raise AssertionError(f"the daemon was asked something it cannot serve: {name}")

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
        self.ward_id = ward_id

        counter = self.store.counter
        mac = root_mac(self.k_mac, ward_id, counter, self.store.root())
        timestamp = self.timestamp_base + counter

        if self.wm.head(ward_id) is None:
            # First contact: adopt the head the device says it holds, authorised by its own
            # signature over it, and attest that.
            self.wm.attest_head(
                ward_id, request.nonce, request.current_mac, request.head_init_sig
            )
        wm_head = self.wm.head(ward_id)
        assert wm_head is not None  # just bootstrapped above if it was not there
        if counter != wm_head[0]:
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

    def _publish_response(self, request):
        """CAS the WM, then apply locally. None means "say nothing", for the ambiguous case.

        THE ORDER IS THE ONE A REAL wardd MUST FOLLOW, minus the durability. Its CAS-and-attest is
        atomic at the WM, but the boundary between the WM and its own replica is not: a crash
        between the two leaves the WM ahead of a replica that no longer holds the transition the
        device needs to catch up on. wardd closes that with a write-ahead journal -- stage, CAS,
        promote. An in-memory mock has nothing to crash between, so it collapses the two and only
        the ORDER survives here: nothing is applied locally that the WM refused.

        THE `from` HEAD COMES FROM THE WM, not from the request, and that is what makes the
        compare-and-swap real. `WardPublish` names only the counter it REACHES -- a device advances
        by exactly one -- so `from_counter` is derivable, but `from_mac` is not: the daemon holds no
        key of this wallet and could not compute one. Taking it from the WM means a device whose
        head has been overtaken is refused on the counter, and a device that forked at the same
        counter is refused on the signature. Both are definitive.
        """
        from .ward_wm import MockWM

        assert self.store is not None and self.wm is not None
        assert self.ward_id is not None, "a publish before any sync: no wallet established"
        ward_id = self.ward_id

        head = self.wm.head(ward_id)
        assert head is not None, "the sync bootstraps the WM, so a head must exist by now"
        _head_counter, head_mac, _ts = head

        try:
            counter, mac, timestamp, signature = self.wm.publish_and_attest(
                ward_id,
                request.nonce,
                request.counter - 1,
                head_mac,
                request.counter,
                request.mac,
                request.wm_sig,
                self.timestamp_base + request.counter,
            )
        except MockWM.Conflict as exc:
            # Definitive: the write is known not to have landed. Nothing is applied, and the
            # channel stays up because nothing about the conversation became unclear.
            return messages.WardPublishConflict(head_counter=exc.head_counter)

        self._commit(request)

        if self.drop_publish_ack:
            return None

        if self.publish_ack_override is not None:
            counter, mac = self.publish_ack_override
            signature = self.wm.sign(ward_id, request.nonce, counter, mac, timestamp)

        return messages.WardPublishAck(
            counter=counter, mac=mac, timestamp=timestamp, wm_signature=signature
        )

    def _commit(self, request) -> None:
        """Apply the published mutation to this daemon's replica.

        Through `ward.apply`, which is the same function a connect-mode host uses, so both
        transports advance a replica by ONE piece of logic. A second copy of "what does this
        mutation do to the tree" is how the two quietly stop agreeing about the root -- and a root
        disagreement surfaces as an unattributable proof failure on the device.
        """
        ward.apply(
            self.store,
            ward.WardResult(
                request,
                request.entry_key,
                ward.Leaf(request.identity, request.content),
                counter=request.counter,
                auth_commit=request.auth_commit,
            ),
        )


def bound_daemon(
    client: TrezorTestContext,
    store: "WardTrie | None" = None,
    wm: "MockWM | None" = None,
    k_mac: bytes | None = None,
    host_static_privkey: bytes | None = None,
) -> MockWardService:
    """A connected, bound daemon serving `store` -- the starting state of every service test.

    Bound BUT NOT READY, which is the distinction the state machine turns on: the device knows
    which daemon it talks to and nothing more. Readiness comes from a sync, and the sync happens
    when a WARD operation first needs one.

    A throwaway `MockWM` is fine when the test has no opinion about the WM -- it only has to hold
    one (counter, mac) pair for the length of the test. Tests that assert on the WM's own state, or
    that move its head behind the device's back, pass their own.
    """
    from .ward_trie import WardTrie as _WardTrie
    from .ward_wm import MockWM as _MockWM

    wardd = MockWardService(client)
    wardd.connect(host_static_privkey=host_static_privkey)
    ack = wardd.open_service()
    assert isinstance(ack, messages.WardServiceOpenAck), f"bind refused: {ack}"
    wardd.store = store if store is not None else _WardTrie()
    wardd.wm = wm if wm is not None else _MockWM()
    wardd.k_mac = k_mac if k_mac is not None else DEFAULT_K_MAC
    return wardd
