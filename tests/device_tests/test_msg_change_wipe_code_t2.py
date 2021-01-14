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
from trezorlib.exceptions import Cancelled, TrezorFailure

PIN4 = "1234"
WIPE_CODE4 = "4321"
WIPE_CODE6 = "456789"

pytestmark = pytest.mark.skip_t1


def _check_wipe_code(client, pin, wipe_code):
    client.init_device()
    assert client.features.wipe_code_protection is True

    # Try to change the PIN to the current wipe code value. The operation should fail.
    with client, pytest.raises(TrezorFailure):
        client.use_pin_sequence([pin, wipe_code, wipe_code])
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5
            + [messages.Failure(code=messages.FailureType.PinInvalid)]
        )
        device.change_pin(client)


def _ensure_unlocked(client, pin):
    with client:
        client.use_pin_sequence([pin])
        btc.get_address(client, "Testnet", PASSPHRASE_TEST_PATH)

    client.init_device()


@pytest.mark.setup_client(pin=PIN4)
def test_set_remove_wipe_code(client):
    # Test set wipe code.
    assert client.features.wipe_code_protection is None

    _ensure_unlocked(client, PIN4)
    assert client.features.wipe_code_protection is False

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4, WIPE_CODE4, WIPE_CODE4])
        device.change_wipe_code(client)

    client.init_device()
    assert client.features.wipe_code_protection is True
    _check_wipe_code(client, PIN4, WIPE_CODE4)

    # Test change wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4, WIPE_CODE6, WIPE_CODE6])
        device.change_wipe_code(client)

    client.init_device()
    assert client.features.wipe_code_protection is True
    _check_wipe_code(client, PIN4, WIPE_CODE6)

    # Test remove wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 3 + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4])
        device.change_wipe_code(client, remove=True)

    client.init_device()
    assert client.features.wipe_code_protection is False


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
    _ensure_unlocked(client, PIN4)

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 6 + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([PIN4, PIN4, WIPE_CODE4, WIPE_CODE4])
        device.change_wipe_code(client)

    client.init_device()
    assert client.features.wipe_code_protection is True
    _check_wipe_code(client, PIN4, WIPE_CODE4)


def test_set_pin_to_wipe_code(client):
    # Set wipe code.
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4 + [messages.Success, messages.Features]
        )
        client.use_pin_sequence([WIPE_CODE4, WIPE_CODE4])
        device.change_wipe_code(client)

    # Try to set the PIN to the current wipe code value.
    with client, pytest.raises(TrezorFailure):
        client.set_expected_responses(
            [messages.ButtonRequest()] * 4
            + [messages.Failure(code=messages.FailureType.PinInvalid)]
        )
        client.use_pin_sequence([WIPE_CODE4, WIPE_CODE4])
        device.change_pin(client)
