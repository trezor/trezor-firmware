# This file is part of the Trezor project.
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

import time

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session


def test_delayed_ack(session: Session):
    br = session.call_raw(messages.Ping(message="delayed", button_protection=True))
    assert isinstance(br, messages.ButtonRequest)
    assert br.code == messages.ButtonRequestType.ProtectCall
    # confirm layout before ButtonAck is sent
    session.debug.press_yes()
    # "waiting" screen should be shown after 2 seconds on Core models
    # (following https://github.com/trezor/trezor-firmware/issues/5884)
    time.sleep(2.5)
    res = session.call_raw(messages.ButtonAck())
    res = messages.Success.ensure_isinstance(res)
    assert res.message == "delayed"


@pytest.mark.models("core")
def test_delayed_ack_abort(session: Session):
    br = session.call_raw(messages.Ping(message="delayed", button_protection=True))
    assert isinstance(br, messages.ButtonRequest)
    assert br.code == messages.ButtonRequestType.ProtectCall
    # confirm layout instead of sending ButtonAck
    session.debug.press_yes()
    # "waiting" screen should be shown after 2 seconds on Core models
    # (following https://github.com/trezor/trezor-firmware/issues/5884)
    time.sleep(2.5)
    session.debug.press_yes()  # abort flow on device (instead of ButtonAck)
    res = session.read()
    res = messages.Failure.ensure_isinstance(res)
    assert res.code == messages.FailureType.ActionCancelled
