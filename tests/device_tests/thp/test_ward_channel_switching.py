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

"""TWO CONVERSATIONS ON ONE DEVICE, and what each one is allowed to do to the other.

Every other WARD service file is about one conversation: what the daemon may say, what the device
does with the answer. This one is about the SEAM between them -- the wallet host's channel and the
daemon's channel being live at the same time, on separate interfaces, with the device driving one
from inside a workflow running on the other.

WHAT THE SEAM IS MADE OF, ON A THP SERVICE CHANNEL. `ThpContext.dispatch_channel` is global and
holds exactly one channel -- whichever received a packet first -- and that channel's messages are
what the main loop dispatches. `InterfaceContext.active_channel` is PER INTERFACE and is what that
interface's write loop drains. The WARD interface has a dispatcher of its own
(`InterfaceContext.dispatch_loop`) and a buffer pool of its own (`wire.buffers_provider_for`),
because it must be able to hold a channel while another interface holds one.

AND ON A CODEC ONE, which is what every build serves by default. There is no channel, no dispatcher
and no pool of its own: one reader owns the interface, never lets go of it, and routes what it reads
into the mailbox the workflow is parked on. The seam is still a seam -- the WALLET side is THP
either way, and the device still drives one conversation from inside a workflow running on the other
-- so these tests run on both, and the handful that assert a THP MECHANISM rather than a property
say so individually.

So the properties worth a test are the ones that live in the gaps between those objects:

  the wallet channel behaves exactly as it did before the second interface existed;
  the service channel never takes `dispatch_channel`, so it can never displace the wallet's turn;
  a wallet channel restarting or being preempted does not cost the device its daemon;
  a daemon reconnecting, timing out, or misbehaving does not cost the device its wallet channel;
  a MicroPython session restart reattaches the persisted service channel, repeatedly;
  and neither interface ever ends up holding the other's buffers.

Each of those is a failure that presents FAR from its cause -- a hung daemon, a spurious
TRANSPORT_BUSY, a wallet channel that dies during someone else's error path -- so they are asserted
here rather than left to be noticed in a log.
"""

import contextlib
import time

import pytest

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.thp.channel import Channel
from trezorlib.thp.pairing import PairingController
from trezorlib.transport import Timeout
from trezorlib.ward_service import WardServiceServer

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_app import ward_app_pinned  # noqa: F401  -- autouse fixture, see tests/ward_app.py
from ...ward_service import bound_daemon
from ...ward_trie import WardTrie

pytestmark = [
    pytest.mark.protocol("thp"),
    pytest.mark.models("core"),
    # BOTH SERVICE TRANSPORTS, because the seam is not one of them. The WALLET side of it is THP
    # either way -- that is what `protocol("thp")` above pins -- and what changes underneath is only
    # how the device reaches its daemon. The invariants are about what a daemon failure is allowed
    # to do to the wallet channel, and they hold, or should, on both.
    #
    # The handful that genuinely test a THP-service MECHANISM -- reattachment, channel displacement,
    # the daemon pin and the reset that migrates it -- say so individually.
    pytest.mark.ward_transport("service"),
]

_APP = "TEST"

# How many wallet/WARD alternations `test_repeated_wallet_ward_wallet_switching` runs. The bugs it is
# looking for are state that accumulates -- a buffer not handed back, a dispatcher armed twice, a
# sync bit drifting -- and none of them shows on round one, so the count is high enough to be a soak
# rather than a smoke test. Each round is three wallet round trips and three WARD operations with
# screens in them, at roughly two seconds a round, which is why the test is marked slow.
_SWITCHES = 50


def _nothing_on_the_wire(entry_key: bytes):
    """A pull provider for the wallet channel that must never be called.

    On a service build the device asks the DAEMON. A pull arriving here would mean the read went to
    the wrong party -- and would silently succeed, since these tests' wallet host could answer it.
    """
    raise AssertionError("a read reached the wallet channel instead of the service")


def _read(session: Session, identifier: bytes):
    """A WARD read, driven from the wallet channel, with its screen walked.

    The expected responses pin that nothing was pulled on this channel: a connect build would show
    `WardEntryRequest` here.
    """
    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.ButtonRequest(name="ward_get_entry"), m.Success])
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.get_entry(session, _APP, identifier, _nothing_on_the_wire)


def _write(session: Session, identifier: bytes, value: bytes):
    """A WARD write, driven from the wallet channel.

    Ends in `WardMutationApplied` rather than `WardLeafAck`: the device publishes to the daemon
    itself, so the wallet host is told that the change happened and is given no leaf to keep.
    """
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_set_entry"), m.WardMutationApplied]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.set_entry(session, _APP, identifier, value, _nothing_on_the_wire)


def _reset_service(session: Session, force: bool = False):
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_reset_service"), m.WardResetServiceAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.reset_service(session, force=force)


@contextlib.contextmanager
def _desync_seen_from_the_daemon(wardd):
    """What losing the conversation looks like from the far side, which is not the same thing twice.

    UNDER THP the device CLOSES the channel, because a channel is the only place the conversation
    lives and a desynchronised one can never be resynchronised -- so the daemon's next read finds
    its channel gone and `serving()` re-raises that. Asserting it here is what says the conversation
    was destroyed rather than merely failed.

    ON THE CODEC there is nothing to close, and that is deliberate rather than a gap: the endpoint
    is the interface's reader and the binding names a fact about the interface, so the device drops
    the conversation without touching the transport and a daemon that comes back is simply heard
    again. The daemon therefore sees nothing at all, and the assertion is that it survives.
    """
    from trezorlib.ward_service import WardServiceClient

    if isinstance(wardd.service, WardServiceClient):
        with pytest.raises(AssertionError, match="UNALLOCATED_CHANNEL"):
            yield
    else:
        yield


def _same_daemon_key(wardd) -> bytes | None:
    """The key that makes a reconnecting daemon the SAME daemon, or None where there is no such
    thing.

    Only a THP service channel has an identity for the device to pin, so on the codec there is
    nothing to carry across a reconnect -- and nothing that would make the reconnect a DIFFERENT
    daemon either. Asked through this rather than `wardd.host_static_privkey` directly, because
    that property asserts THP on purpose and should keep doing so.
    """
    from trezorlib.ward_service import WardServiceClient

    if isinstance(wardd.service, WardServiceClient):
        return wardd.host_static_privkey
    return None


def _speak_out_of_turn(wardd) -> None:
    """Say something the device did not ask for, and get nowhere with it.

    THE RULE IS THE SAME ON BOTH TRANSPORTS -- after binding the device is the sole initiator --
    and only the shape of the refusal differs, which is why this is a helper rather than two tests.

    UNDER THP the ack is a side effect of the application READING, and nothing is listening once
    the conversation inverts, so no ack ever comes and the send itself gives up. ON THE CODEC there
    is no ack to withhold: the write lands, the reader refuses it by name, and the refusal sits
    unread until the next RPC mistakes it for its own answer. Either way it reaches no dispatcher,
    and the daemon pays for it on its next turn.
    """
    from trezorlib.ward_service import WardServiceClient

    if isinstance(wardd.service, WardServiceClient):
        assert wardd.channel is not None
        # Otherwise the send retries with backoff for a long time before giving up; what is being
        # asserted is that no ack ever comes, not how patient trezorlib is.
        wardd.channel.BUSY_RETRIES = 0
        with pytest.raises(Timeout):
            wardd.send(m.GetFeatures())
    else:
        wardd.send(m.GetFeatures())


def _wallet_round_trip(client: Client) -> None:
    """An ordinary wallet call, of the kind that RESTARTS the MicroPython session.

    `Ping` is deliberate: `GetFeatures` is in `AVOID_RESTARTING_FOR`, so it would leave the loop --
    and with it the `ThpContext` and every `Channel` object -- standing. Half of what this file
    tests is what survives the restart, so the wallet traffic here has to cause one.
    """
    assert client.ping("wallet is alive") == "wallet is alive"


def _wallet_channel_kept(client: Client, channel_id: int) -> None:
    """The wallet channel is the SAME one, and still works.

    Both halves are needed. trezorlib reconnects transparently on a dead channel, so a test that
    only called something would pass over the wallet channel having been killed and silently
    replaced -- which is exactly the damage a WARD failure must not do.
    """
    assert client.channel.channel_id == channel_id, "the wallet channel was replaced"
    _wallet_round_trip(client)


def _second_wallet_channel(client: Client) -> Channel:
    """Another wallet channel, of the same host.

    THE STATIC KEY IS REUSED ON PURPOSE. The WARD app role is pinned to a host's static key, so a
    channel with a fresh key is a DIFFERENT application as far as the device is concerned and is
    refused the role -- which would make a preemption test fail for a reason that has nothing to do
    with preemption. Reusing the key is also what a real host reconnecting looks like: the key lives
    in the credential it stored when it paired.
    """
    channel = Channel.allocate(client.transport)
    channel._init_noise(static_privkey=client.channel.host_static_privkey)
    channel.open(credentials=[])
    channel.BUSY_RETRIES = 0
    return channel


def _take_over_the_wire(client: Client, channel: Channel) -> None:
    """Make `channel` the wallet channel this client speaks on, pairing it as a new host would."""
    client.channel = channel
    client.client.pairing = PairingController(client.client)
    client.client.pairing.skip()
    client.client.pairing.finish()


@pytest.mark.slow
def test_repeated_wallet_ward_wallet_switching(client: Client) -> None:
    """Wallet, WARD, wallet, WARD -- a dozen times over, alternating reads and writes.

    THE POINT IS THE REPETITION, not any single round trip: everything here passes once by the time
    the other service files are green. What a loop adds is state that only accumulates -- a buffer
    pool that hands out one pair and would answer None the second time, a dispatcher armed once per
    channel, a `dispatch_channel` slot that must end each round empty for the next wallet message to
    claim it. A leak in any of those shows up as a hang, a TRANSPORT_BUSY, or a WARD operation that
    can no longer find its daemon -- and shows up on round two or round ten, never on round one.

    The wallet call is `Ping`, so every round restarts the MicroPython session under both channels.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = bound_daemon(client, store)
    try:
        with wardd.serving():
            for i in range(_SWITCHES):
                _wallet_round_trip(client)
                assert _read(session, b"absent").leaf is None
                _wallet_round_trip(client)
                res = _write(session, b"entry-%d" % i, b"value-%d" % i)
                assert res.counter == i + 1
                _wallet_round_trip(client)
                # ...and what was just written reads back, so the two channels agree about the
                # tree after every alternation rather than merely both being alive.
                assert _read(session, b"entry-%d" % i).leaf is None

        assert store.counter == _SWITCHES
    finally:
        wardd.close()


def test_wallet_session_restart_reattaches_service_channel(client: Client) -> None:
    """The daemon binds ONCE and stays bound across every session restart the wallet causes.

    UNDER THP a `Channel` object does not survive a restart; the Rust channel behind it does. So the
    service channel has to be REATTACHED -- `ThpContext.attach_existing_channel` -- before the
    device can write to it, because a channel that is not its interface's `active_channel` cannot be
    written at all: `Channel.write` pokes a write loop that drains only that one.

    ON THE CODEC there is nothing to reattach, and the property outlives the mechanism: the binding
    names a fact about the INTERFACE rather than a handle that can go stale, and the reader is
    respawned by `wire.setup` on the next session. Same assertion either way, which is what makes it
    worth running on both -- it is stated from the daemon's side, in what it was asked, and never
    mentions how the device got there.

    Asserted through the daemon's own view: it announces itself once, and every WARD operation
    afterwards is served without another `WardServiceOpen`. A reattach that failed would not be
    subtle -- the device would report no bound service, or write into a channel nobody drains -- but
    it would look like a daemon problem, which is why the count is pinned from this side.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = bound_daemon(client, store)
    try:
        with wardd.serving():
            for _ in range(4):
                # Restarts the session: the `ThpContext` and both `Channel` objects are rebuilt.
                _wallet_round_trip(client)
                assert _read(session, b"absent").leaf is None

        # One sync for the session, then a fetch per read -- and nothing else. `WardServiceOpen` is
        # not in here at all: it is answered by the DEVICE, before `serving()` starts, so the daemon
        # never had to repeat it.
        assert wardd.served == ["WardSyncRequest"] + ["WardServiceFetch"] * 4
    finally:
        wardd.close()


def test_wallet_preemption_does_not_kill_ward_service(client: Client) -> None:
    """A second wallet host preempts the first. The daemon is not collateral.

    Preemption kills `ThpContext.dispatch_channel` and forces a session restart, and the service
    channel is neither of those things: it never holds the dispatch slot -- an interface that serves
    its own dispatch does not install one there -- so the newcomer's packet has nothing of the
    daemon's to displace.

    IT USED NOT TO BE FREE OF CONSEQUENCE IN THE OTHER DIRECTION EITHER, which is why this is worth
    pinning from both ends: before `_retire_displaced_channel`, a daemon reconnect could only get in
    by having a wallet channel preempted on its behalf. The two interfaces now lose channels
    independently, and this is the half that says a wallet-side preemption stays wallet-side.
    """
    store = WardTrie()
    wardd = bound_daemon(client, store)
    try:
        with wardd.serving():
            # Host A: prove it works, and prove the daemon is reachable through it.
            first = client.get_session()
            assert _read(first, b"absent").leaf is None
            served_by_a = len(wardd.served)

            channel_b = _second_wallet_channel(client)
            # `Ping` restarted the loop above, so nothing is in flight -- but the incumbent was
            # written to moments ago, and an incumbent inside `_PREEMPT_TIMEOUT_MS` is treated as
            # in use. Waiting it out is what makes the takeover a preemption rather than a
            # TRANSPORT_BUSY, which is `test_preemption_busy`'s subject and not this file's.
            time.sleep(1.1)
            _take_over_the_wire(client, channel_b)

            # Host B, on a channel the device has never dispatched before, reaches the SAME daemon.
            second = client.get_session()
            assert _read(second, b"absent").leaf is None
            assert wardd.served[served_by_a:] == ["WardSyncRequest", "WardServiceFetch"]
    finally:
        wardd.close()


def test_service_reconnect_does_not_kill_wallet_channel(client: Client) -> None:
    """A daemon goes away and comes back. The wallet channel does not notice.

    What makes this worth asserting is that a reconnect is not passive on the device: the arriving
    channel displaces the incumbent on the service interface (`_retire_displaced_channel`), which
    closes a channel and clears its sessions. All of that has to stay on one interface -- the
    channel it closes must be the departed daemon's, and the buffers it moves across must be the
    service pool's.

    THE SAME KEY, so this is a reconnect and not an ownership migration: the pin recognises the
    daemon, and the binding it holds names a channel that no longer exists.
    """
    key = b"\x63" * 32
    session = client.get_session()
    channel_id = client.channel.channel_id

    first = bound_daemon(client, WardTrie(), host_static_privkey=key)
    try:
        with first.serving():
            assert _read(session, b"absent").leaf is None
    finally:
        first.close()

    _wallet_channel_kept(client, channel_id)

    store = WardTrie()
    again = bound_daemon(client, store, host_static_privkey=key)
    try:
        with again.serving():
            # The SAME wallet session drives it -- not a fresh one, which would hide a session
            # that had been cleared by the reconnect on the other interface.
            assert _read(session, b"absent").leaf is None
            # A WRITE TAKES A FRESH SESSION, and that is a statement about the device rather than
            # about this daemon: session readiness is NOT invalidated when the binding is replaced,
            # so the session above stays "online" and publishes straight at a daemon it has never
            # synced with. Harmless with two genesis replicas, and caught by the WM's CAS when it
            # is not -- but it means a write on `session` would reach this daemon before any
            # `WardSyncRequest`, which is a property of `become_ready` and not of the seam this
            # file is about.
            assert _write(client.get_session(), b"after", b"reconnect").counter == 1
        assert store.counter == 1
    finally:
        again.close()

    _wallet_channel_kept(client, channel_id)


@pytest.mark.slow
def test_service_timeout_does_not_damage_wallet_channel(client: Client) -> None:
    """A silent daemon costs the WARD operation and nothing else.

    The device tears the service channel down when an RPC times out -- it is the sole initiator, so
    there is no later turn in which it could notice a late answer and resynchronise. That teardown
    runs from inside a workflow on the WALLET channel, which is what makes it worth a test: the
    channel it closes and the binding it clears must be the service's.

    IMMEDIATELY afterwards, which is the second half of the assertion. `RPC_TIMEOUT_MS` has just
    elapsed inside a wallet workflow; if the wallet channel came back only after its own retransmit
    or preempt window, a user would see the whole device stall for a WARD failure.
    """
    session = client.get_session()
    channel_id = client.channel.channel_id
    wardd = bound_daemon(client)
    try:
        # No `serving()`: nothing will answer.
        with pytest.raises(exceptions.TrezorFailure) as err:
            ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)
        assert "did not answer" in str(err.value)
    finally:
        wardd.close()

    _wallet_channel_kept(client, channel_id)
    # ...and the wallet session is intact too, not merely the channel: a session cleared by the
    # teardown would fail here instead of being refused for having no service.
    with pytest.raises(exceptions.TrezorFailure):
        ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)


def test_malformed_service_reply_does_not_damage_wallet_channel(client: Client) -> None:
    """A daemon that answers something else entirely. Only its own conversation is destroyed.

    An answer of the wrong type leaves the device unable to say where it is in the stream: with no
    request ids, the next read would be one message behind forever. So `_desynchronised` closes the
    service channel and clears the binding -- and everything it touches has to belong to the
    service. The wallet channel is mid-workflow while it happens, since the failing read is running
    on it.
    """
    session = client.get_session()
    channel_id = client.channel.channel_id
    wardd = bound_daemon(client, WardTrie())
    # A daemon of its own opinion. Replacing the SERVER rather than the mock's `handle` keeps this
    # to the transport: what a well-formed daemon would answer is `..._sync.py`'s subject.
    wardd.server = WardServiceServer(
        wardd.service, lambda _request: m.Success(message="not what was asked")
    )
    try:
        # THE DAEMON'S OWN VIEW OF THE TEARDOWN, which differs by transport -- see the helper.
        with _desync_seen_from_the_daemon(wardd):
            with wardd.serving():
                with pytest.raises(exceptions.TrezorFailure):
                    ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)
    finally:
        wardd.close()

    _wallet_channel_kept(client, channel_id)

    # The binding went with the channel and the PIN DID NOT: the same daemon reconnects and serves.
    # Which is the right pair of facts -- a wrong answer says the transport is confused, and says
    # nothing about which daemon is entitled to the role, so erasing the pin here would turn every
    # desynchronised reply into an ownership migration.
    again = bound_daemon(client, WardTrie(), host_static_privkey=_same_daemon_key(wardd))
    try:
        with again.serving():
            assert _read(client.get_session(), b"absent").leaf is None
    finally:
        again.close()


@pytest.mark.slow
def test_unsolicited_service_message_cannot_enter_wallet_dispatch(client: Client) -> None:
    """A bound daemon speaks out of turn. The wallet never sees it; the daemon pays for it.

    THE DIRECTION IS THE WHOLE ASSERTION. `dispatch_channel` is global -- one slot, whichever
    channel received a packet first -- so the thing that must not happen is a message from the
    daemon's channel being dispatched as if the wallet host had sent it, or being reassembled into
    a buffer the wallet channel then reads. What happens instead is that it sits unread on the
    service channel, because nothing is listening there once the conversation inverts, and the next
    RPC reads it, fails the type check, and loses the service channel.

    So: no ack for the daemon, an unaffected wallet, and a WARD operation that fails closed.
    """
    session = client.get_session()
    channel_id = client.channel.channel_id
    wardd = bound_daemon(client, WardTrie())
    try:
        _speak_out_of_turn(wardd)

        # The wallet channel is untouched -- and it is answering its OWN messages, which is what
        # rules out the unsolicited one having been dispatched here.
        _wallet_channel_kept(client, channel_id)

        # The next WARD operation is the one that pays: it reads the stale message instead of its
        # own reply, and takes the service channel down rather than acting on it.
        with pytest.raises(exceptions.TrezorFailure):
            ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)
    finally:
        wardd.close()

    _wallet_channel_kept(client, channel_id)


@pytest.mark.ward_transport("service-thp")
def test_service_reset_does_not_restart_or_break_wallet(client: Client) -> None:
    """Retiring the binding is a WARD operation, not a device event.

    `WardResetService` arrives on the wallet channel and closes a channel on the other interface --
    the sort of cross-interface teardown that is easy to write as "close what is open" and have it
    reach one object too many. The wallet channel driving it must come out of it unchanged, and the
    successor must find a working interface rather than one still holding the retired daemon's
    channel or its buffers.
    """
    session = client.get_session()
    channel_id = client.channel.channel_id

    live = bound_daemon(client, WardTrie(), host_static_privkey=b"\x64" * 32)
    try:
        with live.serving():
            assert _read(session, b"absent").leaf is None
        # Reset while the daemon's channel is still OPEN, which is the case that has something to
        # tear down; a reset after `close()` would assert against an already-empty interface.
        assert _reset_service(session).unresolved == 0
    finally:
        live.close()

    _wallet_channel_kept(client, channel_id)

    store = WardTrie()
    successor = bound_daemon(client, store, host_static_privkey=b"\x65" * 32)
    try:
        _wallet_channel_kept(client, channel_id)
        with successor.serving():
            assert _write(session, b"after-reset", b"value").counter == 1
        assert store.counter == 1
    finally:
        successor.close()

    _wallet_channel_kept(client, channel_id)


def test_large_messages_cross_the_seam_in_both_directions(client: Client) -> None:
    """A value too big for a channel's own buffer, written and read back, repeatedly.

    THE LARGE BUFFERS ARE SHARED AND BORROWED PER MESSAGE. A channel keeps a small buffer of its
    own -- enough for the handshake and for ordinary wallet traffic -- and reaches for the one
    shared 8.5 kB buffer only when a message does not fit. Every test above rides entirely in the
    small buffers, so none of them touches that path at all.

    WHAT THIS IS LOOKING FOR IS A LEASE THAT WAS NOT GIVEN BACK. That only shows up when the two
    channels want the same buffer at the same time, and getting them to is the whole design of this
    test -- because most WARD flows will not. A large message on its own proves nothing: a channel
    is allowed to keep a buffer it already holds, and a MicroPython session restart wipes any lease
    that was stranded, so a leak between workflows is invisible.

    THE OVERWRITE IS THE LEVER. Writing a large value over a key that ALREADY HOLDS one puts both
    large messages inside a single workflow, in the same direction, on different channels: the
    wallet's `WardSetEntry` arrives large and is still held while the device asks the daemon for the
    existing entry -- whose `WardEntryAck` comes back large too, on the service channel. Both want
    the shared receive buffer, and the second one gets it only if the first gave it back.

    A first write to a fresh key does not do this: the fetch that precedes it answers with nothing.
    Which is why the loop below writes each key twice.
    """
    session = client.get_session()
    store = WardTrie()
    wardd = bound_daemon(client, store)

    big = bytes(range(256)) * 8  # 2048 bytes, and not compressible into looking small
    bigger = bytes(range(256)) * 9  # a second large value, so the overwrite really changes it

    try:
        with wardd.serving():
            for i in range(2):
                identifier = b"big-%d" % i
                assert _write(session, identifier, big).counter == i * 2 + 1
                # THE OVERWRITE, and the point of the test: a large request held on the wallet
                # channel while a large answer arrives on the service channel.
                assert _write(session, identifier, bigger).counter == i * 2 + 2
                # A read, so the large leaf also crosses the service interface with no large wallet
                # message in flight -- the ordinary case, and cheap to cover here.
                assert _read(session, identifier).response.message == "WARD entry shown"
                # ...and an ordinary small call, which is what would be refused or hang if any of
                # the above had walked off with the buffer.
                _wallet_round_trip(client)
        assert store.counter == 4
        # THE MESSAGES REALLY WERE LARGE, which is the premise the whole test rests on -- if the
        # device had quietly stored something smaller, everything above would pass in the small
        # buffers and assert nothing. A 2048-byte value packs to 2056 and seals into the 4096-byte
        # AEAD bucket, four times a channel's own 1024-byte buffer.
        assert all(
            len(leaf.content.encrypted.ct) >= 4096 for leaf in store.blobs.values()
        ), "the values that crossed the seam were not large after all"
    finally:
        wardd.close()

    # The wallet channel is the same one throughout: a stranded lease kills a channel rather than
    # failing a call, and trezorlib would reconnect over that silently.
    _wallet_channel_kept(client, client.channel.channel_id)


@pytest.mark.ward_transport("service-thp")
def test_the_interfaces_never_borrow_each_others_buffers(client: Client) -> None:
    """Daemons come and go; both interfaces can still allocate a channel afterwards.

    THE POOLS ARE HANDED OUT ONCE. `wire.Provider` gives its pair to the first caller and answers
    None to every caller after that, which is deliberate -- it is how a second host on the wire
    interface is turned away with TRANSPORT_BUSY -- and it is also what makes a misplaced buffer
    unrecoverable rather than merely wasteful. So each path that moves a channel has to move the
    buffers with it: `_retire_displaced_channel` carries them across to the replacement rather than
    asking the provider again, and `attach_existing_channel` refuses instead of building a channel
    with none.

    A pool that ended up on the wrong interface, or was dropped on a teardown, presents as an
    interface that has simply stopped accepting channels -- no error anywhere near the cause. Hence
    the shape of this test: churn the service interface, then ask BOTH interfaces for a new channel
    and drive real traffic over each.
    """
    key = b"\x66" * 32
    session = client.get_session()

    for _ in range(3):
        wardd = bound_daemon(client, WardTrie(), host_static_privkey=key)
        try:
            with wardd.serving():
                assert _read(session, b"absent").leaf is None
            _wallet_round_trip(client)
        finally:
            wardd.close()

    # A wallet channel the device has never seen, and a daemon after it -- in that order,
    # because a wire-side channel replacement and a service-side bind draw from different pools and
    # a mix-up shows only when both happen. Neither would be possible if the churn above had left a
    # pool held by a channel that is gone: the wire interface would answer TRANSPORT_BUSY, and the
    # bind would be refused for want of buffers on the service interface.
    _take_over_the_wire(client, _second_wallet_channel(client))
    _wallet_round_trip(client)

    store = WardTrie()
    final = bound_daemon(client, store, host_static_privkey=key)
    try:
        with final.serving():
            assert _write(client.get_session(), b"last", b"value").counter == 1
        assert store.counter == 1
    finally:
        final.close()
