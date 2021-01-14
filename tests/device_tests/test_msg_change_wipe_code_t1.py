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

PinType = messages.PinMatrixRequestType

PIN4 = "1234"
WIPE_CODE4 = "4321"
WIPE_CODE6 = "456789"

pytestmark = pytest.mark.skip_t2


def _set_wipe_code(client, pin, wipe_code):
    # Set/change wipe code.
    with client:
        if client.features.pin_protection:
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
        client.set_expected_responses(
            [messages.ButtonRequest()]
            + pin_matrices
            + [messages.Success, messages.Features]
        )
        device.change_wipe_code(client)


def _change_pin(client, old_pin, new_pin):
    assert client.features.pin_protection is True
    with client:
        client.use_pin_sequence([old_pin, new_pin, new_pin])
        try:
            return device.change_pin(client)
        except exceptions.TrezorFailure as f:
            return f.failure


def _check_wipe_code(client, pin, wipe_code):
    """Check that wipe code is set by changing the PIN to it."""
    f = _change_pin(client, pin, wipe_code)
    assert isinstance(f, messages.Failure)


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_wipe_code(client):
    # Check that wipe code protection status is not revealed in locked state.
    assert client.features.wipe_code_protection is None

    # Test set wipe code.
    _set_wipe_code(client, PIN4, WIPE_CODE4)

    # Check that there's wipe code protection now.
    client.init_device()
    assert client.features.wipe_code_protection is True

    # Check that the wipe code is correct.
    _check_wipe_code(client, PIN4, WIPE_CODE4)

    # Test change wipe code.
    _set_wipe_code(client, PIN4, WIPE_CODE6)

    # Check that there's still wipe code protection now.
    client.init_device()
    assert client.features.wipe_code_protection is True

    # Check that the wipe code is correct.
    _check_wipe_code(client, PIN4, WIPE_CODE6)

    # Test remove wipe code.
    with client:
        client.use_pin_sequence([PIN4])
        device.change_wipe_code(client, remove=True)

    # Check that there's no wipe code protection now.
    client.init_device()
    assert client.features.wipe_code_protection is False


def test_set_wipe_code_mismatch(client):
    # Check that there is no wipe code protection.
    client.ensure_unlocked()
    assert client.features.wipe_code_protection is False

    # Let's set a new wipe code.
    with client:
        client.use_pin_sequence([WIPE_CODE4, WIPE_CODE6])
        client.set_expected_responses(
            [
                messages.ButtonRequest(),
                messages.PinMatrixRequest(type=PinType.WipeCodeFirst),
                messages.PinMatrixRequest(type=PinType.WipeCodeSecond),
                messages.Failure(code=messages.FailureType.WipeCodeMismatch),
            ]
        )
        with pytest.raises(exceptions.TrezorFailure):
            device.change_wipe_code(client)

    # Check that there is no wipe code protection.
    client.init_device()
    assert client.features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_set_wipe_code_to_pin(client):
    # Check that wipe code protection status is not revealed in locked state.
    assert client.features.wipe_code_protection is None

    # Let's try setting the wipe code to the curent PIN value.
    with client:
        client.use_pin_sequence([PIN4, PIN4])
        client.set_expected_responses(
            [
                messages.ButtonRequest(),
                messages.PinMatrixRequest(type=PinType.Current),
                messages.PinMatrixRequest(type=PinType.WipeCodeFirst),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(exceptions.TrezorFailure):
            device.change_wipe_code(client)

    # Check that there is no wipe code protection.
    client.init_device()
    assert client.features.wipe_code_protection is False


def test_set_pin_to_wipe_code(client):
    # Set wipe code.
    _set_wipe_code(client, None, WIPE_CODE4)

    # Try to set the PIN to the current wipe code value.
    with client:
        client.use_pin_sequence([WIPE_CODE4, WIPE_CODE4])
        client.set_expected_responses(
            [
                messages.ButtonRequest(),
                messages.PinMatrixRequest(type=PinType.NewFirst),
                messages.PinMatrixRequest(type=PinType.NewSecond),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(exceptions.TrezorFailure):
            device.change_pin(client)

    # Check that there is no PIN protection.
    client.init_device()
    assert client.features.pin_protection is False
    resp = client.call_raw(messages.GetAddress())
    assert isinstance(resp, messages.Address)


@pytest.mark.parametrize("invalid_wipe_code", ("1204", "", "1234567891"))
def test_set_wipe_code_invalid(client, invalid_wipe_code):
    # Let's set the wipe code
    ret = client.call_raw(messages.ChangeWipeCode())
    assert isinstance(ret, messages.ButtonRequest)

    # Confirm
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Enter a wipe code containing an invalid digit
    assert isinstance(ret, messages.PinMatrixRequest)
    assert ret.type == PinType.WipeCodeFirst
    ret = client.call_raw(messages.PinMatrixAck(pin=invalid_wipe_code))

    # Ensure the invalid wipe code is detected
    assert isinstance(ret, messages.Failure)

    # Check that there's still no wipe code protection.
    client.init_device()
    client.ensure_unlocked()
    assert client.features.wipe_code_protection is False
