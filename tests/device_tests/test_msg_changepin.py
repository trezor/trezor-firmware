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

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure

PIN4 = "1234"
PIN6 = "789456"


pytestmark = pytest.mark.skip_t2


def _check_pin(client, pin):
    client.lock()
    with client:
        client.use_pin_sequence([pin])
        client.set_expected_responses([messages.PinMatrixRequest(), messages.Address()])
        client.call(messages.GetAddress())


def _check_no_pin(client):
    client.lock()
    with client:
        client.set_expected_responses([messages.Address()])
        client.call(messages.GetAddress())


def test_set_pin(client):
    assert client.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(client)

    # Let's set new PIN
    with client:
        client.use_pin_sequence([PIN6, PIN6])
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.PinMatrixRequest(),
                messages.PinMatrixRequest(),
                messages.Success(),
                messages.Features(),
            ]
        )
        device.change_pin(client)

    # Check that there's PIN protection now
    assert client.features.pin_protection is True
    # Check that the PIN is correct
    _check_pin(client, PIN6)


@pytest.mark.setup_client(pin=PIN4)
def test_change_pin(client):
    assert client.features.pin_protection is True
    # Check that there's PIN protection
    _check_pin(client, PIN4)

    # Let's change PIN
    with client:
        client.use_pin_sequence([PIN4, PIN6, PIN6])
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.PinMatrixRequest(),
                messages.PinMatrixRequest(),
                messages.PinMatrixRequest(),
                messages.Success(),
                messages.Features(),
            ]
        )
        device.change_pin(client)

    # Check that there's still PIN protection now
    assert client.features.pin_protection is True
    # Check that the PIN is correct
    _check_pin(client, PIN6)


@pytest.mark.setup_client(pin=PIN4)
def test_remove_pin(client):
    assert client.features.pin_protection is True
    # Check that there's PIN protection
    _check_pin(client, PIN4)

    # Let's remove PIN
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.PinMatrixRequest(),
                messages.Success(),
                messages.Features(),
            ]
        )
        device.change_pin(client, remove=True)

    # Check that there's no PIN protection now
    assert client.features.pin_protection is False
    _check_no_pin(client)


def test_set_mismatch(client):
    assert client.features.pin_protection is False
    # Check that there's no PIN protection
    _check_no_pin(client)

    # Let's set new PIN
    with pytest.raises(TrezorFailure, match="PIN mismatch"), client:
        # use different PINs for first and second attempt. This will fail.
        client.use_pin_sequence([PIN4, PIN6])
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.PinMatrixRequest(),
                messages.PinMatrixRequest(),
                messages.Failure(),
            ]
        )
        device.change_pin(client)

    # Check that there's still no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


@pytest.mark.setup_client(pin=PIN4)
def test_change_mismatch(client):
    assert client.features.pin_protection is True

    # Let's set new PIN
    with pytest.raises(TrezorFailure, match="PIN mismatch"), client:
        client.use_pin_sequence([PIN4, PIN6, PIN6 + "3"])
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.PinMatrixRequest(),
                messages.PinMatrixRequest(),
                messages.PinMatrixRequest(),
                messages.Failure(),
            ]
        )
        device.change_pin(client)

    # Check that there's still old PIN protection
    client.init_device()
    assert client.features.pin_protection is True
    _check_pin(client, PIN4)


@pytest.mark.parametrize("invalid_pin", ("1204", "", "1234567891"))
def test_set_invalid(client, invalid_pin):
    assert client.features.pin_protection is False

    # Let's set an invalid PIN
    ret = client.call_raw(messages.ChangePin())
    assert isinstance(ret, messages.ButtonRequest)

    # Press button
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Send a PIN containing an invalid digit
    assert isinstance(ret, messages.PinMatrixRequest)
    ret = client.call_raw(messages.PinMatrixAck(pin=invalid_pin))

    # Ensure the invalid PIN is detected
    assert isinstance(ret, messages.Failure)

    # Check that there's still no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


@pytest.mark.parametrize("invalid_pin", ("1204", "", "1234567891"))
@pytest.mark.setup_client(pin=PIN4)
def test_enter_invalid(client, invalid_pin):
    assert client.features.pin_protection is True

    # use an invalid PIN
    ret = client.call_raw(messages.GetAddress())

    # Send a PIN containing an invalid digit
    assert isinstance(ret, messages.PinMatrixRequest)
    ret = client.call_raw(messages.PinMatrixAck(pin=invalid_pin))

    # Ensure the invalid PIN is detected
    assert isinstance(ret, messages.Failure)
