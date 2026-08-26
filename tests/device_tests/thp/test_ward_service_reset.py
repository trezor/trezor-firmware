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

"""Retiring the WARD service binding.

THE CASE THIS EXISTS FOR is a daemon whose key is gone. Connecting a replacement does not help --
it correctly fails the pin check -- so there has to be a way to retire the pin, and retiring it
hands the role to whoever binds next. That makes this an ownership migration rather than a
credential reset, and the two have different obligations: a migration has to say what it abandons.

WHAT IT ABANDONS IS UNRESOLVED CLAIMS. A claim is a queued change handed to the service whose fate
is not yet known, and only the service that received it can settle it -- a fresh daemon serves a
wallet at genesis and has no history to fold. So the ordinary path refuses and says how many are
outstanding; `force` is for the case where the refusal cannot help, and it names the count on
screen.
"""

import pytest

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_app import ward_app_pinned  # noqa: F401  -- autouse fixture, see tests/ward_app.py
from ...ward_service import MockWardService, bound_daemon
from ...ward_trie import WardTrie

pytestmark = [
    pytest.mark.protocol("thp"),
    pytest.mark.models("core"),
    # THE RESET MIGRATES A DAEMON PIN, and only a THP service channel has one to migrate.
    pytest.mark.ward_transport("service-thp"),
]

_APP = "TEST"


def _nothing_on_the_wire(entry_key: bytes):
    raise AssertionError("a read reached the wallet channel instead of the service")


def _reset(session: Session, force: bool = False, br_name: str = "ward_reset_service"):
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name=br_name), m.WardResetServiceAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.reset_service(session, force=force)


def _read(session: Session, identifier: bytes):
    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.ButtonRequest(name="ward_get_entry"), m.Success])
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        return ward.get_entry(session, _APP, identifier, _nothing_on_the_wire)


def _queue(session: Session, identifier: bytes, value: bytes) -> None:
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, identifier, value)


def test_a_reset_hands_the_role_to_the_next_daemon(client: Client) -> None:
    """The whole point: after a reset, a daemon with a DIFFERENT key binds and serves.

    Both halves are the assertion. Refused before -- which is the pin doing its job, and the reason
    a reset has to exist at all -- and accepted after, from the same stranger. A reset that cleared
    the pin without freeing the interface would pass the first half and stall on the second.

    THE FIRST DAEMON IS CLOSED BEFORE THE STRANGER CONNECTS, and that is a property of the
    transport rather than tidiness: the interface tracks ONE channel, so a second daemon arriving
    while the first is live is turned away by THP before any of this is reached. Two channels of one
    daemon cannot collide either -- THP replaces a channel arriving with a known host static key --
    so the pin check is only ever reached on a free interface. Leaving the first open here would
    assert against a refusal from the wrong layer.
    """
    key = b"\x71" * 32
    stranger_key = b"\x72" * 32
    session = client.get_session()

    bound_daemon(client, WardTrie(), host_static_privkey=key).close()

    # The pin refuses a different daemon, which is what makes this a migration and not a reconnect.
    stranger = MockWardService(client)
    try:
        stranger.connect(host_static_privkey=stranger_key)
        refused = stranger.open_service()
        assert isinstance(refused, m.Failure)
        assert refused.message == "another daemon is bound as the WARD service"
    finally:
        stranger.close()

    ack = _reset(session)
    assert ack.unresolved == 0

    # ...and now the same stranger takes the role, and can actually serve.
    store = WardTrie()
    successor = bound_daemon(client, store, host_static_privkey=stranger_key)
    try:
        with successor.serving():
            assert (
                _read(client.get_session(), b"anything").response.message
                == "WARD entry shown"
            )
    finally:
        successor.close()


def test_a_reset_with_no_binding_is_refused(client: Client) -> None:
    """Reported rather than treated as success. A host given an ack here would conclude that a
    binding it never saw had been cleared -- and on a device where one is about to be made, that is
    a claim about state nobody holds."""
    session = client.get_session()
    with pytest.raises(exceptions.TrezorFailure) as err:
        ward.reset_service(session)
    assert "no WARD service is bound" in str(err.value)


def test_an_unresolved_claim_refuses_the_reset(client: Client) -> None:
    """Refused, and the refusal is ACTIONABLE: it names how many, so the host knows the fix is to
    reconnect the current service and drain them rather than to retry.

    The claim is produced the way a real one is -- a flush whose answer never arrived -- because
    that is the only state in which the device genuinely does not know. A test that wrote a claim
    directly would not exercise the ordering `mark_offered` is built around.
    """
    key = b"\x73" * 32
    store = WardTrie()
    session = client.get_session()

    _queue(session, b"addr1", b"queued_value")

    wardd = bound_daemon(client, store, host_static_privkey=key)
    wardd.drop_publish_ack = True
    try:
        with wardd.serving():
            with pytest.raises(exceptions.TrezorFailure):
                ward.flush_queue(session, _nothing_on_the_wire)
    finally:
        wardd.close()

    with pytest.raises(exceptions.TrezorFailure) as err:
        ward.reset_service(session)
    assert "1 queued changes are unresolved" in str(err.value)

    # STILL BOUND. The refusal has to leave the binding alone, or the recovery it recommends --
    # reconnect the current service -- would be the one thing it had just made impossible.
    again = bound_daemon(client, store, host_static_privkey=key)
    again.close()


def test_force_resets_and_reports_what_it_abandoned(client: Client) -> None:
    """`force` is for the case the refusal cannot help with: the daemon is gone for good.

    It reports the count rather than clearing anything. The queued change stays PENDING and
    re-offerable, which is the recoverable direction and the rule the rest of the subsystem keeps --
    the user was asked about the BINDING, not about their data. Whether it ever gets published again
    now depends on a service that can produce this wallet's history, and there may never be one; the
    device does not pretend otherwise, and does not throw the change away on that account either.
    """
    key = b"\x74" * 32
    store = WardTrie()
    session = client.get_session()

    _queue(session, b"addr1", b"queued_value")

    wardd = bound_daemon(client, store, host_static_privkey=key)
    wardd.drop_publish_ack = True
    try:
        with wardd.serving():
            with pytest.raises(exceptions.TrezorFailure):
                ward.flush_queue(session, _nothing_on_the_wire)
    finally:
        wardd.close()

    ack = _reset(session, force=True, br_name="ward_reset_service_force")
    assert ack.unresolved == 1

    # The record survived the migration...
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_queue_get_entry"), m.WardQueueGetAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        assert ward.queue_get_entry(session, _APP, b"addr1").pending is True

    # ...and a new daemon can bind, which is what was being bought.
    successor = bound_daemon(client, WardTrie(), host_static_privkey=b"\x75" * 32)
    successor.close()


def test_a_reset_is_refused_on_the_service_interface(client: Client) -> None:
    """The receive boundary, checked from the far side.

    `WardServiceOpen` is the only thing the service interface accepts before binding, so a daemon
    cannot retire its own pin -- and it has no reason to want to. Worth pinning because the message
    is registered on a service build and the natural mistake is to assume "a WARD service message"
    means "on the service channel".
    """
    wardd = MockWardService(client)
    try:
        wardd.connect()
        answer = wardd.call(m.WardResetService())
        assert isinstance(answer, m.Failure)
        assert answer.message == "not accepted on the WARD service channel"
    finally:
        wardd.close()


def test_a_live_service_is_displaced_by_the_reset(client: Client) -> None:
    """Resetting while the bound daemon is STILL THERE -- the branch the other tests never reach.

    Every other case here has the incumbent already gone, which is the motivating one; this is the
    deliberate migration, where the daemon is reachable and the user is retiring it anyway. It is
    the only path through `close_bound_channel`'s live branch, and the one where skipping the close
    would be invisible in review and fatal in use: the pin would be retired and the interface still
    occupied, so the successor could never bind and the device would have no service at all.

    The displaced daemon learns by having its channel closed, rather than by being left holding one
    that nothing answers for.
    """
    key = b"\x76" * 32
    successor_key = b"\x77" * 32
    session = client.get_session()

    incumbent = bound_daemon(client, WardTrie(), host_static_privkey=key)
    try:
        assert _reset(session).unresolved == 0
    finally:
        incumbent.close()

    store = WardTrie()
    successor = bound_daemon(client, store, host_static_privkey=successor_key)
    try:
        with successor.serving():
            assert (
                _read(client.get_session(), b"anything").response.message
                == "WARD entry shown"
            )
    finally:
        successor.close()
