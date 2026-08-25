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

"""Binding the WARD service channel."""

import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.transport import Timeout

from ...ward_service import MockWardService

pytestmark = [
    pytest.mark.protocol("thp"),
    # DECLARED, not inferred. These used to be skipped on a connect build as a side effect of
    # `MockWardService.__init__` reaching for the interface through a fixture that skipped when it
    # was absent. Now that the mock builds a real `WardServiceClient`, which has no business
    # skipping tests, the marker has to say so -- and saying so is better anyway: an implicit skip
    # inside a constructor is invisible to anyone reading this file.
    pytest.mark.ward_transport("service"),
]


def test_a_daemon_binds_itself_as_the_service(client: Client) -> None:
    """WardServiceOpen with no ThpCreateNewSession before it, and no pre-existing service slot.

    Both halves matter. `ThpCreateNewSession` is what derives and stores a wallet seed, and the
    service must not have one -- so the bootstrap has to work without it. And the session slot the
    service uses is allocated BY this handler: an unknown session id arrives as an ephemeral
    seedless context, so requiring the slot to exist first would make the bootstrap impossible.
    """
    with MockWardService(client) as wardd:
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)


def test_it_is_refused_on_the_wire_interface(client: Client) -> None:
    """The interface IS the authorisation boundary.

    Everything the device believes about the service rests on which interface the channel arrived
    on -- a separate OS claim that the wallet host does not hold. Accepting this on the wire
    interface would let Suite answer for the replica.
    """
    session = client.get_session()
    resp = session.call_raw(messages.WardServiceOpen(protocol_version=1))
    assert isinstance(resp, messages.Failure)


def test_an_unsupported_protocol_version_is_refused_by_name(client: Client) -> None:
    """Refused rather than negotiated down. A daemon speaking a different message set would
    otherwise be discovered by misreading a field."""
    with MockWardService(client) as wardd:
        resp = wardd.open_service(protocol_version=0xFFFF)
        assert isinstance(resp, messages.Failure)
        # ...and nothing was bound, so a correct daemon can still take the role
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)


def test_the_pinned_daemon_rebinds_after_a_restart(client: Client) -> None:
    """The case that actually happens: wardd restarts and comes back on a new channel.

    Two things have to hold together for this to work. The pin must recognise it -- same key, so it
    is the same daemon -- and the recorded binding, which names a channel that no longer exists,
    must not lock it out. A binding counts only while its channel is open, which is why this is a
    rebind rather than a permanent refusal until reboot.
    """
    key = b"\x51" * 32
    first = MockWardService(client)
    try:
        first.connect(host_static_privkey=key)
        assert isinstance(first.open_service(), messages.WardServiceOpenAck)
    finally:
        first.close()

    again = MockWardService(client)
    try:
        again.connect(host_static_privkey=key)
        assert isinstance(again.open_service(), messages.WardServiceOpenAck)
    finally:
        again.close()


def test_a_different_daemon_is_refused_once_pinned(client: Client) -> None:
    """Pairing is not enough. Every paired host passes the pairing check -- Suite included -- so
    without a pin any of them could open the WARD interface and answer for the replica.

    Asserted on the refusal MESSAGE, because the wrong reason is easy to get here: the previous
    channel is still open on the device, so a stranger would also be turned away as "already
    bound". This checks it is turned away as the wrong daemon, which is the check that survives the
    first channel going away.
    """
    pinned_key = b"\x41" * 32
    daemon = MockWardService(client)
    try:
        daemon.connect(host_static_privkey=pinned_key)
        assert isinstance(daemon.open_service(), messages.WardServiceOpenAck)
    finally:
        daemon.close()

    stranger = MockWardService(client)
    try:
        stranger.connect(host_static_privkey=b"\x42" * 32)
        resp = stranger.open_service()
        assert isinstance(resp, messages.Failure)
        assert resp.message == "another daemon is bound as the WARD service"
    finally:
        stranger.close()


def test_a_bound_channel_is_not_listening(client: Client) -> None:
    """Not "refused" -- NOT EVEN ACKNOWLEDGED. The device stops reading the channel once the
    conversation inverts, so a host-initiated message does not get a reply and does not get a
    THP ack either: the ack is emitted as a side effect of the application reading, and nothing
    is reading on the daemon's behalf.

    That is stronger than a refusal and it is what makes the single-initiator rule structural. A
    channel has one incoming mailbox: if the device kept a dispatcher parked on it, that dispatcher
    and the workflow awaiting its own reply would race for the same message, and which one won
    would depend on scheduling. Nothing reads the channel except the workflow that just wrote a
    request, so the race cannot arise -- and the daemon finds out at once rather than waiting on a
    reply that is never coming.

    Deliberately includes `Cancel` and `EndSession`. Both are host-initiated, and letting either
    back would recreate exactly the ambiguity above -- this stream has no request ids, so the
    device cannot tell an unsolicited `Cancel` from the reply it is waiting for.
    """
    with MockWardService(client) as wardd:
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)

        assert wardd.channel is not None
        # Without this the send retries with exponential backoff for a long time before giving
        # up. What is being asserted is that it never succeeds, not how patient trezorlib is.
        wardd.channel.BUSY_RETRIES = 0

        for msg in (
            messages.GetFeatures(),
            messages.Cancel(),
            messages.EndSession(),
            messages.WardServiceOpen(protocol_version=1),
        ):
            with pytest.raises(Timeout):
                wardd.send(msg)


def test_an_unbound_channel_accepts_nothing_else_either(client: Client) -> None:
    """The interface serves ONE message before binding, not a general THP surface.

    Otherwise the WARD interface would be a second, unaudited way to reach every handler the
    device has -- including `ThpCreateNewSession`, which is precisely the thing the service must
    never be able to do.
    """
    with MockWardService(client) as wardd:
        for msg in (messages.ThpCreateNewSession(), messages.GetFeatures()):
            resp = wardd.call(msg)
            assert isinstance(
                resp, messages.Failure
            ), f"{msg.__class__.__name__} was accepted on an unbound service channel"
