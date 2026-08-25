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

"""What stands in for the WARD app role on a transport that has no identities.

THE COUNTERPART TO `device_tests/thp/test_ward_app_role.py`, which tests the pin. There is no pin
here and cannot be: protocol v1 carries no host key, so the device cannot tell one connected
application from another by any means. What replaces it is the user, per operation, on the device's
own screen -- and the ordering is the whole of it. Every WARD confirmation carries the value among
its properties, so by the time it is answered the secret is already displayed; with no pin deciding
who may trigger that, TRIGGERING A READ IS THE DISCLOSURE. So a reveal is asked about first, alone,
while it is still unrevealed.

WHAT IS NOT CLAIMED. This does not make `app_id` a permission -- any connected application may still
ASK to display any entry. It makes it impossible to do so without the user reading which one first.
See `apps.ward.app_role`.
"""

import pytest

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_app import REVEAL_BR, reject_flow

pytestmark = [
    pytest.mark.protocol("v1"),
    pytest.mark.models("core"),
]

_APP = "TEST"
_IDENT = b"addr1"


def _offline_read(session: Session) -> m.WardQueueGetAck:
    """The cheapest host-facing WARD request there is: the device's own store, no backend.

    The same probe the THP file uses, and for the same reason -- what is under test is what has to
    be answered before it runs, not what it answers.
    """
    return ward.queue_get_entry(session, app_id=_APP, identifier=_IDENT)


def _screens(ctx) -> list[str]:
    """The ButtonRequest names raised so far in this block."""
    return [r.name for r in ctx.actual_responses if type(r).__name__ == "ButtonRequest"]


def test_a_read_asks_before_it_reveals(session: Session) -> None:
    """The reveal screen comes FIRST, and the operation's own screen follows it.

    First because the check runs in the wire filter, before the handler has looked at the request
    at all -- which is the only place it can run and still be ahead of the disclosure.
    """
    with session.test_ctx as ctx:
        ctx.actual_responses.clear()
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        _offline_read(session)
        assert _screens(ctx) == [REVEAL_BR, "ward_queue_get_entry"]


def test_it_asks_every_time(session: Session) -> None:
    """UNLIKE THE THP ROLE SCREEN, which is asked once and then never again.

    That difference is the point rather than an oversight. The THP screen grants a lasting thing --
    which application owns WARD from here on -- and can be answered once because there is a key to
    remember it by. Here there is nothing to remember: consent that outlived the operation would be
    consent given to a party the device cannot name, and the next request might be anyone's.
    """
    for _ in range(2):
        with session.test_ctx as ctx:
            ctx.actual_responses.clear()
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            _offline_read(session)
            assert _screens(ctx) == [REVEAL_BR, "ward_queue_get_entry"]


def test_refusing_it_stops_the_operation(session: Session) -> None:
    """A refusal has to fail the request, not fall through to the operation's own screen.

    The failure mode this guards is a reveal prompt that is decorative: answered, ignored, and
    followed by the disclosure anyway.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(reject_flow(session))
        # `Cancelled` rather than `TrezorFailure`: a refused confirmation is the user declining,
        # not the device rejecting the request, and trezorlib keeps those apart.
        with pytest.raises(exceptions.Cancelled):
            _offline_read(session)


# THE NEGATIVE HALF -- that an operation showing back only what the caller sent is NOT asked about
# -- is pinned in `core/tests/test_apps.ward.handlers.py::TestWardRevealPolicy`, where the list can
# be compared directly. Asserting it here would mean driving a write, which needs a backend and a
# synced session on a service build and would make this file about something else. What this file
# pins instead is that the sequence is EXACTLY the reveal screen and the operation's own -- so an
# extra screen, wherever it came from, fails a test above.


def test_a_second_connection_is_not_refused(client: Client) -> None:
    """No pin means no lock-out, which is a consequence to state rather than a feature to claim.

    On THP a second application is refused outright. Here the device cannot tell there IS a second
    application, so what it does instead is ask again -- and the assertion is that a fresh session
    works at all, since a device that refused it would be enforcing a role it has no way to hold.
    """
    first = client.get_session()
    with first.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(first).get())
        _offline_read(first)

    second = client.get_session()
    with second.test_ctx as ctx:
        ctx.actual_responses.clear()
        ctx.set_input_flow(InputFlowConfirmAllWarnings(second).get())
        _offline_read(second)
        assert _screens(ctx) == [REVEAL_BR, "ward_queue_get_entry"]
