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

"""Taking the WARD app role, so a test that is not about the role does not have to notice it.

WHAT THE DEVICE DOES. The first host to send a user-facing WARD message is pinned in flash by its
static key, after the user holds to confirm, and every other host is refused from then on -- one
party operates WARD per device, chosen by the user. See `apps.ward.app_role` and
`docs/core/misc/ward-channels.md`.

WHY THAT NEEDS A FIXTURE. Every test starts from a wiped device, so every test's first WARD request
would raise that confirmation -- and roughly a hundred existing tests pin an exact ButtonRequest
sequence, none of which is about who may use WARD. Paying for the role once, before the test body
runs, keeps those sequences describing what they were written to describe.

DELIBERATELY OPT-IN, module by module, rather than an autouse fixture in a shared conftest: the tests
that ARE about the role must see an unpinned device, and a fixture that silently pinned it everywhere
would make those tests impossible to write. Import the fixture where you want it:

    from ...ward_app import ward_app_pinned  # noqa: F401  -- autouse fixture
"""

from __future__ import annotations

import typing as t

import pytest

from trezorlib import exceptions, ward

from .input_flows import InputFlowBase, InputFlowConfirmAllWarnings

if t.TYPE_CHECKING:
    from trezorlib.debuglink import DebugSession as Session

# Not a plausible entry, and it does not have to be: the request only has to REACH the role check,
# which runs before the handler looks at anything. What it then answers -- missing, or a failure
# about an uninitialised device -- is irrelevant and is swallowed below.
_PIN_APP = "__ward_app_role__"
_PIN_IDENT = b"__ward_app_role__"


def take_ward_app_role(session: Session) -> None:
    """Make one throwaway WARD request, confirming whatever it shows, and swallow the answer.

    THE SCREEN IS THE POINT, not the request. A queued read is used because it is the cheapest
    host-facing WARD message there is: it touches no backend, needs no synced session, and cannot
    change any state the caller then has to undo.

    Failures are swallowed for the same reason -- an uninitialised device refuses this request after
    the role has already been granted, and a test that wanted the refusal is not calling this.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        try:
            ward.queue_get_entry(session, app_id=_PIN_APP, identifier=_PIN_IDENT)
        except exceptions.TrezorFailure:
            pass


@pytest.fixture(autouse=True)
def ward_app_pinned(session: Session) -> None:
    """Grant the test's host the WARD app role before its own assertions begin."""
    take_ward_app_role(session)


class _RejectFlow(InputFlowBase):
    """Walk a confirm screen to its final page and REFUSE it.

    Mirrors `InputFlowConfirmAllWarnings` page by page and diverges only at the decision, so
    the screens under test are reached the same way they are when confirmed -- a cancel that
    bailed on page one would not prove the confirmation is the thing guarding the write.

    The button-press direction is per layout: Bolt and Caesar have a No button, while Delizia
    and Eckhart cancel through the menu (item 0), the same route
    `InputFlowNewWipeCodeCancel` takes.
    """

    def input_flow_bolt(self):
        yield
        self.debug.press_no()

    def input_flow_caesar(self):
        yield
        self.debug.press_no()

    def input_flow_delizia(self):
        yield
        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.synchronize_at("VerticalMenu")
        self.debug.button_actions.navigate_to_menu_item(0)

    def input_flow_eckhart(self):
        yield
        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.synchronize_at("VerticalMenu")
        self.debug.button_actions.navigate_to_menu_item(0)

def reject_flow(session: Session):
    """The flow above, ready for `set_input_flow`. Lives here rather than in a test module because
    more than one WARD test file needs to refuse a screen, and the per-layout cancel route is exactly
    the kind of knowledge that goes wrong when it is copied."""
    return _RejectFlow(session).get()
