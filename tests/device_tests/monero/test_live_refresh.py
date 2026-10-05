# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ...common import MNEMONIC12


def _live_refresh_prompts(session: Session, path: str) -> int:
    """Start and finish an empty live refresh, return the number of prompts."""
    names: list[str | None] = []

    def input_flow():
        default = client.ui.default_input_flow()
        next(default)
        while True:
            br = yield
            names.append(br.name)
            default.send(br)

    with session.test_ctx as client:
        client.set_input_flow(input_flow())
        session.call(
            messages.MoneroLiveRefreshStartRequest(address_n=parse_path(path)),
            expect=messages.MoneroLiveRefreshStartAck,
        )
        session.call(
            messages.MoneroLiveRefreshFinalRequest(),
            expect=messages.MoneroLiveRefreshFinalAck,
        )
    return names.count("live_refresh")


@pytest.mark.altcoin
@pytest.mark.monero
@pytest.mark.models("core")
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_monero_live_refresh_approval_per_account(session: Session):
    # approval is remembered within the session
    assert _live_refresh_prompts(session, "m/44h/128h/0h") == 1
    assert _live_refresh_prompts(session, "m/44h/128h/0h") == 0
    # switching account asks again, then remembers the new account
    assert _live_refresh_prompts(session, "m/44h/128h/1h") == 1
    assert _live_refresh_prompts(session, "m/44h/128h/1h") == 0
    # approving account 1 doesn't cover account 0
    assert _live_refresh_prompts(session, "m/44h/128h/0h") == 1
