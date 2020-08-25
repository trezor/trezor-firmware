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
from trezorlib.client import PASSPHRASE_TEST_PATH
from trezorlib.exceptions import Cancelled

PIN4 = "1234"
PIN6 = "789456"

pytestmark = pytest.mark.skip_t1


def _check_pin(client, pin):
    client.lock()
    assert client.features.pin_protection is True
    assert client.features.unlocked is False

    with client:
        client.use_pin_sequence([pin])
        client.set_expected_responses([messages.ButtonRequest(), messages.Address()])
        btc.get_address(client, "Testnet", PASSPHRASE_TEST_PATH)


def _check_no_pin(client):
    client.lock()
    assert client.features.pin_protection is False

    with client:
        client.set_expected_responses([messages.Address()])
        btc.get_address(client, "Testnet", PASSPHRASE_TEST_PATH)


def test_set_pin(client):
    assert client.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(client)

    # Let's set new PIN
    with client:
        client.use_pin_sequence([PIN6, PIN6])
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4 + [messages.Success(), messages.Features()]
        )
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
        client.use_pin_sequence([PIN4, PIN6, PIN6])
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success(), messages.Features()]
        )
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
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [messages.ButtonRequest()] * 3 + [messages.Success(), messages.Features()]
        )
        device.change_pin(client, remove=True)

    # Check that there's no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


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
