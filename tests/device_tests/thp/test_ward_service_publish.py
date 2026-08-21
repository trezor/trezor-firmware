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

"""Publishing a mutation to the WARD service, and adopting the attestation that comes back.

WHAT THIS REMOVES IS THE UNCONFIRMED WINDOW. On a connect build a write ends with the device handing
the leaf to the host and knowing nothing more: the host has to store it, publish the counter to the
WM, and run a three-message sync round before the device will believe its own write landed. Every
state in between is one only the host can see. Here the device hands the mutation to the party that
owns the replica and gets the attestation in the same exchange -- so "did my change apply?" has an
answer the device computed rather than one it was told.

AND IT IS STRICTLY STRONGER THAN RECONCILE, which is the part worth testing carefully. Reconcile
adopts any root that reproduces an attested mac. Here the device minted the mac itself before
anybody else saw the transition, and requires the attestation to name that exact counter and that
exact mac -- so the tests below spend most of their effort on what happens when it does not.
"""

import pytest

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_service import DEFAULT_WARD_ID, bound_daemon
from ...ward_trie import WardTrie
from ...ward_wm import MockWM

pytestmark = [
    pytest.mark.protocol("thp"),
    pytest.mark.models("core"),
    pytest.mark.ward_transport("service"),
]

_APP = "TEST"
_WARD_ID = DEFAULT_WARD_ID


def _nothing_on_the_wire(entry_key: bytes):
    """A provider for the wallet channel that must never be called -- see the sync tests."""
    raise AssertionError("a read reached the wallet channel instead of the service")


def _write(session: Session, identifier: bytes, value: bytes):
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_set_entry"), m.WardMutationApplied]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.set_entry(session, _APP, identifier, value, _nothing_on_the_wire)


def _delete(session: Session, identifier: bytes, expect_screen: bool = True):
    expected = [m.WardMutationApplied]
    if expect_screen:
        expected.insert(0, m.ButtonRequest(name="ward_delete_entry"))
    with session.test_ctx as ctx:
        ctx.set_expected_responses(expected)
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.delete_entry(session, _APP, identifier, _nothing_on_the_wire)


def _read(session: Session, identifier: bytes):
    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.ButtonRequest(name="ward_get_entry"), m.Success])
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.get_entry(session, _APP, identifier, _nothing_on_the_wire)


def _queue(session: Session, identifier: bytes, value: bytes) -> None:
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, identifier, value)


def _still_queued(session: Session, identifier: bytes) -> bool:
    """Whether the device's flash still holds this change as PENDING.

    THE FLASH FLAG IS THE ASSERTION, not the ack. A publication whose answer is lost reports failure
    to the host while having succeeded at the daemon -- so the interesting states are exactly the
    ones where what the host was told and what is true disagree, and only the record can be asked.
    """
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_queue_get_entry"), m.WardQueueGetAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ack = ward.queue_get_entry(session, _APP, identifier)
    return bool(ack.pending)


def test_a_write_is_published_and_adopted(client: Client) -> None:
    """The whole point, in one exchange: the device writes, the daemon's replica advances, the WM
    attests the head the device computed, and the device adopts it before answering the host.

    The round trips are pinned because the absence of a fourth one is the claim being made: the
    following read needs NO sync, which is only true if the write's own attestation moved the head.
    A connect build would need a three-message round here before that read could work at all.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = bound_daemon(client, store)
    try:
        with wardd.serving():
            res = _write(session, b"addr1", b"value1")
            assert res.counter == 1
            assert res.leaf is None  # the wallet host is given no replica to keep

            read = _read(session, b"addr1")
            assert read.response.message == "WARD entry shown"

        assert store.counter == 1  # the daemon holds it...
        assert wardd.wm.head(_WARD_ID)[0] == 1  # ...and so does the WM
        assert wardd.served == [
            "WardSyncRequest",  # the write's own sync, this session's first operation
            "WardServiceFetch",  # the current state to derive against
            "WardPublish",
            "WardServiceFetch",  # the read -- no sync, because the head already moved
        ]
    finally:
        wardd.close()


def test_an_attestation_for_another_head_is_refused(client: Client) -> None:
    """The check that makes this route stronger than reconcile.

    The WM's remaining freedom is not forgery -- it cannot compute a mac -- it is to answer a
    question that was not asked: to attest some other head, authentically, in reply to this nonce.
    The device minted the counter and the mac itself, so it can refuse on identity rather than on
    verifiability.

    THAT THE HEAD DID NOT MOVE is asserted by what happens next rather than by reading it back.
    Had the device adopted the attested counter 2, the following sync would fail its own
    anti-rollback check -- the daemon can only attest 1 -- and the read would be impossible. It
    succeeding is the proof that nothing was adopted.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = bound_daemon(client, store)
    wardd.publish_ack_override = (2, b"\xaa" * 32)
    try:
        with wardd.serving():
            with pytest.raises(exceptions.TrezorFailure) as err:
                _write(session, b"addr1", b"value1")
            assert "does not name the head this device published" in str(err.value)

            wardd.publish_ack_override = None
            assert _read(session, b"addr1").response.message == "WARD entry shown"
    finally:
        wardd.close()


def test_a_conflict_is_definitive_and_keeps_the_channel(client: Client) -> None:
    """Somebody else wrote first: known not to have landed, so the channel stays up.

    A conflict is a FACT, and that is what separates it from every other failure here. The write
    definitely did not happen, so there is nothing unclear about the conversation and no reason to
    close it -- the operation fails cleanly and the next one carries on over the same channel. An
    ambiguous failure is the opposite case and is torn down; see the dropped-ack test.

    The WM's head is moved behind everyone's back to produce it, which is what a second device
    writing looks like from here.
    """
    store = WardTrie()
    session = client.get_session()
    wm = MockWM()
    wardd = bound_daemon(client, store, wm=wm)
    try:
        with wardd.serving():
            # A sync first, so the WM holds this wallet's opening head at 0.
            _read(session, b"addr1")

            # ...and now somebody else advances it. The mac is not one this device minted, which is
            # exactly the situation: the device cannot explain the WM's head any more.
            wm.publish(_WARD_ID, 1, b"\xbb" * 32, 1)

            with pytest.raises(exceptions.TrezorFailure) as err:
                _write(session, b"addr1", b"value1")
            assert "moved the head first" in str(err.value)

            # NOTHING WAS APPLIED. The daemon commits only what the WM accepted, so its replica is
            # untouched -- a conflict that had already been written locally would leave the daemon
            # serving a state no authority vouches for.
            assert store.counter == 0
            assert len(store) == 0

            # THE CHANNEL IS STILL THERE, which is the claim this test exists for: the device can
            # still ask and the daemon still answers, so a conflict costs one operation rather than
            # the conversation. Asserted on the requests SERVED and deliberately not on what the
            # next operation returns -- the fixture's sync republishes the head it holds, so the
            # recovery here is the mock's rather than the protocol's and is not what is being
            # claimed. (A real WM compare-and-swaps; `MockWM.publish` does not, by design.)
            before = len(wardd.served)
            _read(session, b"addr1")
            assert len(wardd.served) > before
    finally:
        wardd.close()


@pytest.mark.slow
def test_a_dropped_publish_ack_is_settled_by_the_next_sync(client: Client) -> None:
    """The ambiguous failure, end to end -- and the one where reporting the ack would lie.

    The daemon applied the mutation and the WM attested it; only the answer was lost. So the write
    DID land and the device cannot know it. What must happen: the operation fails, the channel goes
    (the outcome is unknown, so the conversation is unusable), the claim in flash survives, and the
    next sync folds the transition, sees this change's own authorisation among the ones it crossed,
    and settles the record as landed.

    ASSERTED ON THE FLASH FLAG rather than on any response, because the broken behaviour here
    reports success: a device that cleared the record when it handed the mutation over would look
    identical until the change silently failed to exist.
    """
    key = b"\x5d" * 32
    store = WardTrie()
    wm = MockWM()
    session = client.get_session()

    _queue(session, b"addr1", b"queued_value")

    wardd = bound_daemon(client, store, wm=wm, host_static_privkey=key)
    wardd.drop_publish_ack = True
    try:
        with wardd.serving():
            with pytest.raises(exceptions.TrezorFailure) as err:
                ward.flush_queue(session, _nothing_on_the_wire)
            assert "did not answer" in str(err.value)

        # It landed everywhere except on the device.
        assert store.counter == 1
        assert wm.head(_WARD_ID)[0] == 1
        assert _still_queued(session, b"addr1") is True
    finally:
        wardd.close()

    # The daemon reconnects -- the channel was torn down, the pin was not -- and the next sync
    # settles what the lost ack left open.
    again = bound_daemon(client, store, wm=wm, host_static_privkey=key)
    try:
        with again.serving():
            later = client.get_session()
            _read(later, b"addr1")
            assert _still_queued(later, b"addr1") is False
    finally:
        again.close()


def test_a_flush_drains_and_settles_each_change(client: Client) -> None:
    """`remaining` is the host's loop condition, so it has to survive the split.

    Two queued changes, published one per request: the host loops while `remaining` is non-zero,
    and each publication settles its own record as it goes. Dropping the field would strand every
    queued change after the first -- the loop would exit on the missing value and nothing would ask
    again.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = bound_daemon(client, store)
    try:
        _queue(session, b"addr1", b"first")
        _queue(session, b"addr2", b"second")

        with wardd.serving():
            first = ward.flush_queue(session, _nothing_on_the_wire)
            assert isinstance(first.response, m.WardFlushQueueApplied)
            assert first.remaining == 1
            assert first.leaf is None

            second = ward.flush_queue(session, _nothing_on_the_wire)
            assert second.remaining == 0

            empty = ward.flush_queue(session, _nothing_on_the_wire)
            assert empty.remaining == 0

        assert store.counter == 2
        assert _still_queued(session, b"addr1") is False
        assert _still_queued(session, b"addr2") is False
        # An empty drain publishes nothing: three flushes, two publications.
        assert wardd.served.count("WardPublish") == 2
    finally:
        wardd.close()


def test_an_idempotent_delete_publishes_nothing(client: Client) -> None:
    """No transition, so nothing to publish and nothing to put at risk.

    Deleting a path that provably holds nothing changes no state and authorises no transition, so a
    publication would be a round trip that could only fail -- and dropping the online latch for it
    would cost the session its readiness over an operation that did nothing. The absence is already
    PROVED by this point: the fetch had to exhibit a non-membership witness against the trusted
    root before this branch was reached.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = bound_daemon(client, store)
    try:
        with wardd.serving():
            res = _delete(session, b"never-existed", expect_screen=False)
            assert res.counter == 0

            # STILL READY afterwards: the next read needs no sync of its own.
            _read(session, b"never-existed")

        assert "WardPublish" not in wardd.served
        assert wardd.served == [
            "WardSyncRequest",
            "WardServiceFetch",  # the delete's proof of absence
            "WardServiceFetch",  # the read
        ]
    finally:
        wardd.close()
