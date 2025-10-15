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

import pytest

from trezorlib import btc, device, messages
from trezorlib.client import MAX_PIN_LENGTH
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure

from ..input_flows import InputFlowNewCodeMismatch, InputFlowNewWipeCodeCancel

PIN4 = "1234"
WIPE_CODE4 = "4321"
WIPE_CODE6 = "456789"
WIPE_CODE_MAX = "".join(chr((i % 10) + ord("0")) for i in range(MAX_PIN_LENGTH))

pytestmark = pytest.mark.models("core")


def _check_wipe_code(session: Session, pin: str, wipe_code: str):
    # session.init_device()
    assert session.features.wipe_code_protection is True

    # Try to change the PIN to the current wipe code value. The operation should fail.
    with session.test_ctx as client, pytest.raises(TrezorFailure):
        client.use_pin_sequence([pin, wipe_code, wipe_code])
        if session.layout_type is LayoutType.Caesar:
            br_count = 6
        else:
            br_count = 5
        client.set_expected_responses(
            [messages.ButtonRequest()] * br_count
            + [messages.Failure(code=messages.FailureType.PinInvalid)]
        )
        device.change_pin(session)


def _ensure_unlocked(session: Session, pin: str):
    with session.test_ctx:
        session.test_ctx.use_pin_sequence([pin])
        session.ensure_unlocked()

    session.refresh_features()


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_wipe_code(session: Session):

    # Test set wipe code.
    assert session.features.wipe_code_protection is None
    _ensure_unlocked(session, PIN4)
    assert session.features.wipe_code_protection is False

    if session.layout_type is LayoutType.Caesar:
        br_count = 6
    else:
        br_count = 5

    with session.test_ctx as client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * br_count
            + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4, WIPE_CODE_MAX, WIPE_CODE_MAX])
        device.change_wipe_code(session)

    # session.init_device()
    assert session.features.wipe_code_protection is True
    _check_wipe_code(session, PIN4, WIPE_CODE_MAX)

    # Test change wipe code.
    with session.test_ctx as client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * br_count
            + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4, WIPE_CODE6, WIPE_CODE6])
        device.change_wipe_code(session)

    # session.init_device()
    assert session.features.wipe_code_protection is True
    _check_wipe_code(session, PIN4, WIPE_CODE6)

    # Test remove wipe code.
    with session.test_ctx as client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 3 + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4])
        device.change_wipe_code(session, remove=True)

    # session.init_device()
    assert session.features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_set_wipe_code_mismatch(session: Session):
    _ensure_unlocked(session, PIN4)

    with session.test_ctx as client, pytest.raises(Cancelled):
        IF = InputFlowNewCodeMismatch(
            session, WIPE_CODE4, WIPE_CODE6, what="wipe_code", pin=PIN4
        )
        client.set_input_flow(IF.get())

        device.change_wipe_code(session)

    # Check that there's still no wipe code protection now
    # session.init_device()
    assert session.features.wipe_code_protection is False


def test_set_wipe_code_cancel(session: Session):
    with session.test_ctx as client, pytest.raises(Cancelled):
        IF = InputFlowNewWipeCodeCancel(session)
        client.set_input_flow(IF.get())
        device.change_wipe_code(session)


@pytest.mark.setup_client(pin=PIN4)
def test_set_wipe_code_to_pin(session: Session):
    _ensure_unlocked(session, PIN4)

    with session.test_ctx as client:
        if client.layout_type is LayoutType.Caesar:
            br_count = 8
        else:
            br_count = 7
        client.set_expected_responses(
            [messages.ButtonRequest()] * br_count
            + [messages.Success, messages.Features],
        )
        client.use_pin_sequence([PIN4, PIN4, WIPE_CODE4, WIPE_CODE4])
        device.change_wipe_code(session)

    # session.init_device()
    assert session.features.wipe_code_protection is True
    _check_wipe_code(session, PIN4, WIPE_CODE4)


def test_set_wipe_code_without_pin(session: Session):
    # Make sure that both PIN and wipe code are not set.
    assert session.features.pin_protection is False
    assert session.features.wipe_code_protection is False
    # Expect an error when trying to set the wipe code without a PIN being turned on.
    with session.test_ctx, pytest.raises(Cancelled):
        device.change_wipe_code(session)


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_pin_without_removing_wipe_code(session: Session):
    _ensure_unlocked(session, PIN4)
    # Make sure the PIN is set.
    assert session.features.pin_protection is True
    # Make sure the wipe code is not set.
    assert session.features.wipe_code_protection is False

    # Set wipe code
    with session.test_ctx as client:
        client.use_pin_sequence([PIN4, WIPE_CODE4, WIPE_CODE4])
        device.change_wipe_code(session)

    # Make sure the wipe code is set.
    assert session.features.wipe_code_protection is True

    # Remove PIN without wipe code being turned off.
    with session.test_ctx:
        # Expect an error when trying to remove PIN with enabled wipe code.
        with pytest.raises(Cancelled):
            device.change_pin(session, remove=True)
