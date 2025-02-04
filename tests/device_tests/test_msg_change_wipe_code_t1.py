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

from trezorlib import device, exceptions, messages
from trezorlib.client import MAX_PIN_LENGTH
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

PinType = messages.PinMatrixRequestType

PIN4 = "1234"
WIPE_CODE4 = "4321"
WIPE_CODE6 = "456789"
WIPE_CODE_MAX = "".join(chr((i % 9) + ord("1")) for i in range(MAX_PIN_LENGTH))
WIPE_CODE_TOO_LONG = WIPE_CODE_MAX + "1"

pytestmark = pytest.mark.models("legacy")


def _set_wipe_code(session: Session, pin, wipe_code):
    # Set/change wipe code.
    with session.client as client, session:
        if session.features.pin_protection:
            pins = [pin, wipe_code, wipe_code]
            pin_matrices = [
                messages.PinMatrixRequest(type=PinType.Current),
                messages.PinMatrixRequest(type=PinType.WipeCodeFirst),
                messages.PinMatrixRequest(type=PinType.WipeCodeSecond),
            ]
        else:
            pins = [wipe_code, wipe_code]
            pin_matrices = [
                messages.PinMatrixRequest(type=PinType.WipeCodeFirst),
                messages.PinMatrixRequest(type=PinType.WipeCodeSecond),
            ]

        client.use_pin_sequence(pins)
        session.set_expected_responses(
            [messages.ButtonRequest()] + pin_matrices + [messages.Success]
        )
        device.change_wipe_code(session)


def _change_pin(session: Session, old_pin, new_pin):
    assert session.features.pin_protection is True
    with session.client as client:
        client.use_pin_sequence([old_pin, new_pin, new_pin])
        try:
            return device.change_pin(session)
        except exceptions.TrezorFailure as f:
            return f.failure


def _check_wipe_code(session: Session, pin, wipe_code):
    """Check that wipe code is set by changing the PIN to it."""
    f = _change_pin(session, pin, wipe_code)
    assert isinstance(f, messages.Failure)


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_wipe_code(session: Session):
    # Check that wipe code protection status is not revealed in locked state.
    assert session.features.wipe_code_protection is None

    # Test set wipe code.
    _set_wipe_code(session, PIN4, WIPE_CODE_MAX)

    # Check that there's wipe code protection now.
    assert session.features.wipe_code_protection is True

    # Check that the wipe code is correct.
    _check_wipe_code(session, PIN4, WIPE_CODE_MAX)

    # Test change wipe code.
    _set_wipe_code(session, PIN4, WIPE_CODE6)

    # Check that there's still wipe code protection now.
    assert session.features.wipe_code_protection is True

    # Check that the wipe code is correct.
    _check_wipe_code(session, PIN4, WIPE_CODE6)

    # Test remove wipe code.
    with session.client as client:
        client.use_pin_sequence([PIN4])
        device.change_wipe_code(session, remove=True)

    # Check that there's no wipe code protection now.
    assert session.features.wipe_code_protection is False


def test_set_wipe_code_mismatch(session: Session):
    # Check that there is no wipe code protection.
    session.ensure_unlocked()
    session.refresh_features()
    assert session.features.wipe_code_protection is False

    # Let's set a new wipe code.
    with session.client as client, session:
        client.use_pin_sequence([WIPE_CODE4, WIPE_CODE6])
        session.set_expected_responses(
            [
                messages.ButtonRequest(),
                messages.PinMatrixRequest(type=PinType.WipeCodeFirst),
                messages.PinMatrixRequest(type=PinType.WipeCodeSecond),
                messages.Failure(code=messages.FailureType.WipeCodeMismatch),
            ]
        )
        with pytest.raises(exceptions.TrezorFailure):
            device.change_wipe_code(session)

    # Check that there is no wipe code protection.
    client.refresh_features()
    assert client.features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_set_wipe_code_to_pin(session: Session):
    # Check that wipe code protection status is not revealed in locked state.
    assert session.features.wipe_code_protection is None

    # Let's try setting the wipe code to the curent PIN value.
    with session.client as client, session:
        client.use_pin_sequence([PIN4, PIN4])
        session.set_expected_responses(
            [
                messages.ButtonRequest(),
                messages.PinMatrixRequest(type=PinType.Current),
                messages.PinMatrixRequest(type=PinType.WipeCodeFirst),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(exceptions.TrezorFailure):
            device.change_wipe_code(session)

    # Check that there is no wipe code protection.
    client.refresh_features()
    assert client.features.wipe_code_protection is False


def test_set_pin_to_wipe_code(session: Session):
    # Set wipe code.
    session.refresh_features()
    _set_wipe_code(session, None, WIPE_CODE4)

    # Try to set the PIN to the current wipe code value.
    with session.client as client, session:
        client.use_pin_sequence([WIPE_CODE4, WIPE_CODE4])
        session.set_expected_responses(
            [
                messages.ButtonRequest(),
                messages.PinMatrixRequest(type=PinType.NewFirst),
                messages.PinMatrixRequest(type=PinType.NewSecond),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(exceptions.TrezorFailure):
            device.change_pin(session)

    # Check that there is no PIN protection.
    assert session.features.pin_protection is False
    resp = session.call_raw(
        messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0"))
    )
    assert isinstance(resp, messages.Address)


@pytest.mark.parametrize("invalid_wipe_code", ("1204", "", WIPE_CODE_TOO_LONG))
def test_set_wipe_code_invalid(session: Session, invalid_wipe_code: str):
    # Let's set the wipe code
    ret = session.call_raw(messages.ChangeWipeCode())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm
    session.client.debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    # Enter a wipe code containing an invalid digit
    assert isinstance(ret, messages.PinMatrixRequest)
    assert ret.type == PinType.WipeCodeFirst
    ret = session.call_raw(messages.PinMatrixAck(pin=invalid_wipe_code))

    # Ensure the invalid wipe code is detected
    assert isinstance(ret, messages.Failure)

    # Check that there's still no wipe code protection.
    session = session.client.resume_session(session)
    session.ensure_unlocked()
    assert session.features.wipe_code_protection is False
