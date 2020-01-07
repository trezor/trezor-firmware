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
from trezorlib.exceptions import Cancelled

PIN4 = "1234"
PIN6 = "789456"

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


def _check_pin(client, pin):
    client.clear_session()
    assert client.features.pin_protection is True

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_change_pin(client.debug, pin, pin))
        device.change_pin(client)


def _check_no_pin(client):
    client.clear_session()
    assert client.features.pin_protection is False

    def input_flow():
        yield from _input_flow_set_pin(client.debug, PIN4)
        yield from _input_flow_clear_pin(client.debug, PIN4)

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4
            + [messages.Success(), messages.Features()]
            + [messages.ButtonRequest()] * 3
            + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(input_flow)
        device.change_pin(client)
        device.change_pin(client, remove=True)

    assert client.features.pin_protection is False


@pytest.mark.setup_client()
def test_set_pin(client):
    assert client.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(client)

    # Let's set new PIN
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_set_pin(client.debug, PIN6))

        device.change_pin(client)

    client.init_device()
    assert client.features.pin_protection is True
    _check_pin(client, PIN6)


@pytest.mark.setup_client(pin=PIN4)
def test_change_pin(client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    # Let's change PIN
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_change_pin(client.debug, PIN4, PIN6))

        device.change_pin(client)

    # Check that there's still PIN protection now
    client.init_device()
    assert client.features.pin_protection is True
    # Check that the PIN is correct
    _check_pin(client, PIN6)


@pytest.mark.setup_client(pin=PIN4)
def test_remove_pin(client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    # Let's remove PIN
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 3 + [messages.Success(), messages.Features()]
        )
        client.set_input_flow(_input_flow_clear_pin(client.debug, PIN4))

        device.change_pin(client, remove=True)

    # Check that there's no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


@pytest.mark.setup_client()
def test_set_failed(client):
    assert client.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(client)

    # Let's set new PIN
    def input_flow():
        yield  # do you want to set pin?
        client.debug.press_yes()
        yield  # enter new pin
        client.debug.input(PIN4)
        yield  # enter new pin again (but different)
        client.debug.input(PIN6)

        # failed retry
        yield  # enter new pin
        client.cancel()

    with client, pytest.raises(Cancelled):
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4 + [messages.Failure()]
        )
        client.set_input_flow(input_flow)

        device.change_pin(client)

    # Check that there's still no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


@pytest.mark.setup_client(pin=PIN4)
def test_change_failed(client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    # Let's set new PIN
    def input_flow():
        yield  # do you want to change pin?
        client.debug.press_yes()
        yield  # enter current pin
        client.debug.input(PIN4)
        yield  # enter new pin
        client.debug.input("457891")
        yield  # enter new pin again (but different)
        client.debug.input("381847")

        # failed retry
        yield  # enter current pin again
        client.cancel()

    with client, pytest.raises(Cancelled):
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Failure()]
        )
        client.set_input_flow(input_flow)

        device.change_pin(client)

    # Check that there's still old PIN protection
    client.init_device()
    assert client.features.pin_protection is True
    _check_pin(client, PIN4)
