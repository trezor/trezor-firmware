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
from trezorlib.exceptions import Cancelled, TrezorFailure

PIN4 = "1234"
WIPE_CODE4 = "4321"
WIPE_CODE6 = "456789"

pytestmark = pytest.mark.skip_t1


def _input_flow_set_pin(debug, pin):
    yield  # do you want to set a new pin?
    print("set pin?")
    debug.press_yes()
    yield  # enter new pin
    print(f"enter pin {pin}")
    debug.input(pin)
    yield  # enter new pin again
    print(f"reenter pin {pin}")
    debug.input(pin)
    yield  # success
    print("success")
    debug.press_yes()


def _input_flow_change_pin(debug, old_pin, new_pin):
    yield  # do you want to change pin?
    debug.press_yes()
    yield  # enter current pin
    debug.input(old_pin)
    yield  # enter new pin
    debug.input(new_pin)
    yield  # enter new pin again
    debug.input(new_pin)
    yield  # success
    debug.press_yes()


def _input_flow_clear_pin(debug, old_pin):
    yield  # do you want to remove pin?
    debug.press_yes()
    yield  # enter current pin
    debug.input(old_pin)
    yield  # success
    debug.press_yes()


def _input_flow_set_wipe_code(debug, pin, wipe_code):
    yield  # do you want to set/change the wipe_code?
    debug.press_yes()
    if pin is not None:
        yield  # enter current pin
        debug.input(pin)
    yield  # enter new wipe code
    debug.input(wipe_code)
    yield  # enter new wipe code again
    debug.input(wipe_code)
    yield  # success
    debug.press_yes()


def _input_flow_remove_wipe_code(debug, pin):
    yield  # do you want to remove wipe code?
    debug.press_yes()
    yield  # enter current pin
    debug.input(pin)
    yield  # success
    debug.press_yes()


def _check_wipe_code(client, pin, wipe_code):
    client.clear_session()
    assert client.features.wipe_code_protection is True

    # Try to change the PIN to the current wipe code value. The operation should fail.
    with client, pytest.raises(TrezorFailure):
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5
            + [messages.Failure(code=messages.FailureType.PinInvalid)]
        )
        client.set_input_flow(_input_flow_change_pin(client.debug, pin, wipe_code))
        device.change_pin(client)


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_wipe_code(client):
    # Test set wipe code.
    assert client.features.wipe_code_protection is False

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_set_wipe_code(client.debug, PIN4, WIPE_CODE4))

        device.change_wipe_code(client)

    client.init_device()
    assert client.features.wipe_code_protection is True
    _check_wipe_code(client, PIN4, WIPE_CODE4)

    # Test change wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_set_wipe_code(client.debug, PIN4, WIPE_CODE6))

        device.change_wipe_code(client)

    client.init_device()
    assert client.features.wipe_code_protection is True
    _check_wipe_code(client, PIN4, WIPE_CODE6)

    # Test remove wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 3 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_clear_pin(client.debug, PIN4))

        device.change_wipe_code(client, remove=True)

    client.init_device()
    assert client.features.wipe_code_protection is False


@pytest.mark.setup_client()
def test_set_wipe_code_mismatch(client):
    # Let's set a wipe code.
    def input_flow():
        yield  # do you want to set the wipe code?
        client.debug.press_yes()
        yield  # enter new wipe code
        client.debug.input(WIPE_CODE4)
        yield  # enter new wipe code again (but different)
        client.debug.input(WIPE_CODE6)

        # failed retry
        yield  # enter new wipe code
        client.cancel()

    with client, pytest.raises(Cancelled):
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4 + [messages.Failure()]
        )
        client.set_input_flow(input_flow)

        device.change_wipe_code(client)

    # Check that there's still no wipe code protection now
    client.init_device()
    assert client.features.wipe_code_protection is False


@pytest.mark.setup_client(pin=PIN4)
def test_set_wipe_code_to_pin(client):
    def input_flow():
        yield  # do you want to set the wipe code?
        client.debug.press_yes()
        yield  # enter current pin
        client.debug.input(PIN4)
        yield  # enter new wipe code (same as PIN)
        client.debug.input(PIN4)

        # failed retry
        yield  # enter new wipe code
        client.debug.input(WIPE_CODE4)
        yield  # enter new wipe code again
        client.debug.input(WIPE_CODE4)
        yield  # success
        client.debug.press_yes()

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 6 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(input_flow)

        device.change_wipe_code(client)

    client.init_device()
    assert client.features.wipe_code_protection is True
    _check_wipe_code(client, PIN4, WIPE_CODE4)


@pytest.mark.setup_client()
def test_set_pin_to_wipe_code(client):
    # Set wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_set_wipe_code(client.debug, None, WIPE_CODE4))

        device.change_wipe_code(client)

    # Try to set the PIN to the current wipe code value.
    with client, pytest.raises(TrezorFailure):
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4
            + [messages.Failure(code=messages.FailureType.PinInvalid)]
        )
        client.set_input_flow(_input_flow_set_pin(client.debug, WIPE_CODE4))
        device.change_pin(client)


# TODO: this UI test should not be skipped, but because of the reseed it fails
# on device id match and I am not sure why
@pytest.mark.setup_client(pin=PIN4)
@pytest.mark.skip_ui
def test_wipe_code_activate(client):
    import time

    device_id = client.features.device_id

    # Set wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_set_wipe_code(client.debug, PIN4, WIPE_CODE4))

        device.change_wipe_code(client)

    # Try to change the PIN.
    ret = client.call_raw(messages.ChangePin(remove=False))

    # Confirm change PIN.
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Enter the wipe code instead of the current PIN
    assert ret == messages.ButtonRequest(code=messages.ButtonRequestType.Other)
    client.debug.input(WIPE_CODE4)
    client._raw_write(messages.ButtonAck())

    # Allow the device to display wipe code popup and restart.
    time.sleep(7)

    # Check that the device has been wiped.
    client.init_device()
    assert client.features.initialized is False
    assert client.features.pin_protection is False
    assert client.features.wipe_code_protection is False
    assert client.features.device_id != device_id
