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

from ...ward_service import MockWardService

pytestmark = [pytest.mark.protocol("thp")]


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


def test_a_repeat_open_is_refused_while_the_binding_is_live(client: Client) -> None:
    """A daemon cannot re-announce itself on a channel that is already the service.

    It is the only way a LIVE binding can actually be collided with, and worth stating: two
    channels of the same daemon cannot collide, because THP replaces a channel that arrives with
    an already-known host static key -- so the older one is genuinely gone rather than merely
    unused. Refusing here keeps a daemon from resetting the service's state mid-conversation.
    """
    with MockWardService(client) as wardd:
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)
        resp = wardd.open_service()
        assert isinstance(resp, messages.Failure)
        assert resp.message == "a WARD service is already bound"


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


def test_a_bound_channel_accepts_nothing_host_initiated(client: Client) -> None:
    """Not even `GetFeatures`, and deliberately not `Cancel` or `EndSession` either.

    After binding, the device is the sole initiator. This stream has no request ids, so the device
    cannot distinguish an unsolicited host message from the reply it is waiting for -- which is why
    the rule is about direction rather than about which messages are harmless.
    """
    with MockWardService(client) as wardd:
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)

        for msg in (
            messages.GetFeatures(),
            messages.Cancel(),
            messages.EndSession(),
            messages.WardServiceOpen(protocol_version=1),
        ):
            resp = wardd.call(msg)
            assert isinstance(
                resp, messages.Failure
            ), f"{msg.__class__.__name__} was accepted on a bound service channel"


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
