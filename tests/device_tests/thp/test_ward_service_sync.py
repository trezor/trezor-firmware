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

"""Reading over the service channel, and the sync the device drives to make it possible.

THE FIRST WARD OPERATION OF A SESSION SYNCS ITSELF. On a connect build it cannot: the sync is a
sequence of requests the HOST issues, so the device can only report that it is offline and refuse.
Here the daemon is reachable whenever the device wants it, so "sync first" stops being something
the host has to know to do -- which is the practical difference the separate channel buys.
"""

import pytest

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_keys import bip39_seed, derive_k_mac, derive_ward_id
from ...ward_service import MockWardService
from ...ward_trie import WardTrie
from ...ward_wm import MockWM

pytestmark = [
    pytest.mark.protocol("thp"),
    pytest.mark.models("core"),
    pytest.mark.ward_transport("service"),
]

_APP = "TEST"

# The device under test uses the default mnemonic and no passphrase (`SetupParams` in
# tests/conftest.py), so the oracle can reproduce its keys.
_SEED = bip39_seed(" ".join(["all"] * 12))
_K_MAC = derive_k_mac(_SEED)
_WARD_ID = derive_ward_id(_SEED)


def _nothing_on_the_wire(entry_key: bytes):
    """A provider for the A channel that must never be called.

    On a service build the device asks the DAEMON, so a pull arriving on the wallet channel would
    mean the read had gone to the wrong party -- and it would silently succeed, because the wallet
    host in these tests happens to hold the same store.
    """
    raise AssertionError("a read reached the wallet channel instead of the service")


def _daemon(client: Client, store: WardTrie, wm: MockWM | None = None) -> MockWardService:
    """A connected, bound daemon serving `store`."""
    wardd = MockWardService(client)
    wardd.connect()
    assert isinstance(wardd.open_service(), m.WardServiceOpenAck)
    wardd.store = store
    wardd.wm = wm if wm is not None else MockWM()
    wardd.k_mac = _K_MAC
    return wardd


def _read(session: Session, identifier: bytes) -> tuple:
    """Run a read on the wallet channel, walking its screen.

    The expected responses pin that NOTHING was pulled on this channel: a connect build would
    show `WardEntryRequest` here.
    """
    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.ButtonRequest(name="ward_get_entry"), m.Success])
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        res = ward.get_entry(session, _APP, identifier, _nothing_on_the_wire)
    return res


def _write(session: Session, identifier: bytes, value: bytes) -> tuple:
    """Run a write on the wallet channel, walking its screen.

    Still ends in `WardLeafAck` on a service build: the device does not publish yet, so the leaf
    comes back to the wallet host and the host is what advances the daemon's replica. Handing the
    mutation to the daemon instead is the next unit, and this file is deliberately written so that
    it is the ACK type that changes and not the sync behaviour underneath.
    """
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_set_entry"), m.WardLeafAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        res = ward.set_entry(session, _APP, identifier, value, _nothing_on_the_wire)
    return res


def test_a_genesis_read_syncs_itself(client: Client) -> None:
    """An empty tree, a WM that has never seen this wallet, and a read that still works.

    Everything the WM needs to open this wallet's history comes from the device: it cannot compute
    a mac, holding no key of ours, so the opening head is supplied and signed by the device and the
    WM adopts it. Without that a genesis wallet could never acquire a first head -- and since a
    READ may be a wallet's first WARD operation, it cannot be left to the first write.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = _daemon(client, store)
    try:
        with wardd.serving():
            res = _read(session, b"nothing-here")
        assert res.response.message == "WARD entry shown"
        # ...and the WM now holds the opening head the device authorised, at counter 0
        assert wardd.wm.head(_WARD_ID) is not None
        assert wardd.wm.head(_WARD_ID)[0] == 0
    finally:
        wardd.close()


def test_the_read_is_served_by_the_daemon(client: Client) -> None:
    """A leaf the wallet channel never sees. The store is the daemon's, and the proof comes back
    over its own channel -- which is the whole point of the arrangement."""
    store = WardTrie()
    session = client.get_session()
    wardd = _daemon(client, store)
    try:
        with wardd.serving():
            res = _read(session, b"absent")
        assert res.leaf is None  # a read builds no leaf
    finally:
        wardd.close()


def test_without_a_daemon_a_read_fails_closed(client: Client) -> None:
    """No binding, so no sync, so no read. Refused rather than served from anywhere else: a read
    that fell back would let a hostile party choose which of two answers the user sees."""
    session = client.get_session()
    with pytest.raises(exceptions.TrezorFailure):
        ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)


def test_a_genesis_write_syncs_itself_too(client: Client) -> None:
    """The other kind of first operation. A write needs the current state to derive against, so it
    needs the same head-init bootstrap a read does -- and getting it only on the read path would
    leave a wallet whose first WARD operation happens to be a write unable to perform it at all."""
    store = WardTrie()
    session = client.get_session()
    wardd = _daemon(client, store)
    try:
        with wardd.serving():
            res = _write(session, b"first", b"value")
        assert res.auth_commit is not None  # a transition really was authorised
        assert wardd.wm.head(_WARD_ID)[0] == 0  # ...against the opening head the WM adopted
    finally:
        wardd.close()


def test_the_device_follows_a_head_the_daemon_moved(client: Client) -> None:
    """The multi-writer case, and the one the chain fold exists for.

    The device does not commit its own writes -- the head moves only when an attestation names it
    -- so after a write the daemon's replica is one transition ahead. On a connect build the host
    has to know to run a sync round before the next read will work. Here the device notices on the
    fetch, folds the link it is missing, and adopts, without the wallet host doing anything.

    Asserted on the ROUND TRIPS as well as the value: a read that quietly served from the device's
    own older tree would return the same absence and look identical.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = _daemon(client, store)
    try:
        with wardd.serving():
            res = _write(session, b"moved", b"v1")
            ward.apply(store, res)
            assert store.counter == 1  # the daemon is ahead; the device is still at 0

            read = _read(session, b"moved")
            assert read.response.message == "WARD entry shown"

            # ...and the head it adopted STUCK: a second read needs no sync at all. Which is what
            # separates having adopted the daemon's head from having merely survived one read.
            _read(session, b"moved")

        # The sync for the write, then the write's own fetch; then the read's fetch, which is told
        # to sync, the sync, and the one retry; then the second read's single fetch.
        assert wardd.served == [
            "WardSyncRequest",
            "WardServiceFetch",
            "WardServiceFetch",
            "WardSyncRequest",
            "WardServiceFetch",
            "WardServiceFetch",
        ]
    finally:
        wardd.close()


def test_a_second_session_syncs_again(client: Client) -> None:
    """Readiness is per session, and has to be: a session begins knowing nothing current.

    The binding is device-wide and outlives any session, so this is the pairing that must not
    happen -- a fresh session inheriting the previous one's belief that it shares a head with the
    daemon. Counted rather than inferred, because a session that wrongly considered itself ready
    would still read correctly here; only the missing round trip shows it.
    """
    store = WardTrie()
    wardd = _daemon(client, store)
    try:
        with wardd.serving():
            _read(client.get_session(), b"absent")
            first = list(wardd.served)
            _read(client.get_session(), b"absent")
            second = wardd.served[len(first) :]

        assert first == ["WardSyncRequest", "WardServiceFetch"]
        assert second == ["WardSyncRequest", "WardServiceFetch"]
    finally:
        wardd.close()


@pytest.mark.setup_client(passphrase=True)
def test_another_wallet_is_not_served_from_this_replica(client: Client) -> None:
    """A hidden wallet against a daemon that holds a different wallet's replica: refused.

    ONE LOGICAL SERVICE PER WALLET is a deployment precondition rather than something the protocol
    negotiates -- `WardServiceFetch` does not even carry a ward_id, because the daemon has only one
    replica to answer from. So what has to hold is that the mismatch is CAUGHT rather than served:
    the links carry authorisations only a device of the other wallet could have issued, and the
    attested mac is over a tree this wallet never built.

    The failure direction is the whole point. Serving would present another wallet's entries as
    this one's, which is precisely the "cannot verify reading as verified" confusion the subsystem
    is built to refuse.
    """
    store = WardTrie()
    wardd = _daemon(client, store)
    try:
        with wardd.serving():
            # Give the daemon a real head first: two empty trees agree trivially, and a test that
            # passed on that would prove nothing.
            owner = client.get_session(passphrase="")
            ward.apply(store, _write(owner, b"theirs", b"secret"))

            other = client.get_session(passphrase="hidden")
            with pytest.raises(exceptions.TrezorFailure):
                ward.get_entry(other, _APP, b"theirs", _nothing_on_the_wire)
    finally:
        wardd.close()


def test_a_sync_requirement_buys_exactly_one_retry(client: Client) -> None:
    """One sync, one retry, then an error -- counted, not timed.

    A daemon that still says "out of sync" about the head the device just adopted FROM THAT SAME
    DAEMON is disagreeing with itself. Asking a third time cannot resolve that; it can only spin in
    front of the user, which is the one failure mode a fail-closed read does not otherwise have.
    """
    store = WardTrie()
    session = client.get_session()
    wardd = _daemon(client, store)
    wardd.always_out_of_sync = True
    try:
        with wardd.serving():
            with pytest.raises(exceptions.TrezorFailure):
                ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)
        # The first fetch, then the sync it forced, then the one retry. Nothing after it.
        assert wardd.served == [
            "WardSyncRequest",
            "WardServiceFetch",
            "WardSyncRequest",
            "WardServiceFetch",
        ]
    finally:
        wardd.close()


@pytest.mark.slow
def test_a_silent_daemon_fails_closed(client: Client) -> None:
    """Bound, but not answering. The read must fail rather than hang.

    Worth the wall-clock this costs: every other WARD failure is an error the user sees, and a
    workflow parked forever on a daemon that went away is the one that is not.
    """
    session = client.get_session()
    wardd = _daemon(client, WardTrie())
    try:
        # No `serving()`: nothing will answer.
        with pytest.raises(exceptions.TrezorFailure) as err:
            ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)
        assert "did not answer" in str(err.value)
    finally:
        wardd.close()


@pytest.mark.slow
def test_a_torn_down_service_can_come_back(client: Client) -> None:
    """What the timeout leaves behind, checked from the far side.

    The unanswered request is abandoned mid-flight, so the channel is closed rather than reused:
    the device is the sole initiator and there is no host turn in which it could ever notice a
    late answer and resynchronise. Closing is therefore the only way back -- and the way back has
    to actually work, or one silent moment would cost the service until the device rebooted.

    The pin survives it, which is what makes this a reconnect and not an ownership migration:
    the same key binds again.
    """
    key = b"\x57" * 32
    store = WardTrie()

    silent = MockWardService(client)
    silent.connect(host_static_privkey=key)
    assert isinstance(silent.open_service(), m.WardServiceOpenAck)
    session = client.get_session()
    try:
        with pytest.raises(exceptions.TrezorFailure):
            ward.get_entry(session, _APP, b"anything", _nothing_on_the_wire)
    finally:
        silent.close()

    again = MockWardService(client)
    again.connect(host_static_privkey=key)
    assert isinstance(again.open_service(), m.WardServiceOpenAck)
    again.store = store
    again.wm = MockWM()
    again.k_mac = _K_MAC
    try:
        with again.serving():
            res = _read(client.get_session(), b"anything")
        assert res.response.message == "WARD entry shown"
    finally:
        again.close()
