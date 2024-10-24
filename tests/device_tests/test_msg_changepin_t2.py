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
from trezorlib.client import MAX_PIN_LENGTH, PASSPHRASE_TEST_PATH
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import Cancelled, TrezorFailure

from .. import buttons
from ..input_flows import (
    InputFlowCodeChangeFail,
    InputFlowNewCodeMismatch,
    InputFlowWrongPIN,
)

PIN4 = "1234"
PIN60 = "789456" * 10
PIN_MAX = "".join(chr((i % 10) + ord("0")) for i in range(MAX_PIN_LENGTH))

pytestmark = pytest.mark.models("core")


def _check_pin(client: Client, pin: str):
    client.lock()
    assert client.features.pin_protection is True
    assert client.features.unlocked is False

    with client:
        client.use_pin_sequence([pin])
        client.set_expected_responses([messages.ButtonRequest, messages.Address])
        btc.get_address(client, "Testnet", PASSPHRASE_TEST_PATH)


def _check_no_pin(client: Client):
    client.lock()
    assert client.features.pin_protection is False

    with client:
        client.set_expected_responses([messages.Address])
        btc.get_address(client, "Testnet", PASSPHRASE_TEST_PATH)


def test_set_pin(client: Client):
    assert client.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(client)

    # Let's set new PIN
    with client:
        if client.layout_type is LayoutType.TR:
            br_count = 6
        else:
            br_count = 4
        client.use_pin_sequence([PIN_MAX, PIN_MAX])
        client.set_expected_responses(
            [messages.ButtonRequest] * br_count + [messages.Success, messages.Features]
        )
        device.change_pin(client)

    client.init_device()
    assert client.features.pin_protection is True
    _check_pin(client, PIN_MAX)


@pytest.mark.setup_client(pin=PIN4)
def test_change_pin(client: Client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    # Let's change PIN
    with client:
        client.use_pin_sequence([PIN4, PIN_MAX, PIN_MAX])
        if client.layout_type is LayoutType.TR:
            br_count = 6
        else:
            br_count = 5
        client.set_expected_responses(
            [messages.ButtonRequest] * br_count + [messages.Success, messages.Features]
        )
        device.change_pin(client)

    # Check that there's still PIN protection now
    client.init_device()
    assert client.features.pin_protection is True
    # Check that the PIN is correct
    _check_pin(client, PIN_MAX)


@pytest.mark.setup_client(pin=PIN4)
def test_remove_pin(client: Client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    # Let's remove PIN
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [messages.ButtonRequest] * 3 + [messages.Success, messages.Features]
        )
        device.change_pin(client, remove=True)

    # Check that there's no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


def test_set_failed(client: Client):
    assert client.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(client)

    with client, pytest.raises(TrezorFailure):
        IF = InputFlowNewCodeMismatch(client, PIN4, PIN60, what="pin")
        client.set_input_flow(IF.get())

        device.change_pin(client)

    # Check that there's still no PIN protection now
    client.init_device()
    assert client.features.pin_protection is False
    _check_no_pin(client)


@pytest.mark.setup_client(pin=PIN4)
def test_change_failed(client: Client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    with client, pytest.raises(Cancelled):
        IF = InputFlowCodeChangeFail(client, PIN4, "457891", "381847")
        client.set_input_flow(IF.get())

        device.change_pin(client)

    # Check that there's still old PIN protection
    client.init_device()
    assert client.features.pin_protection is True
    _check_pin(client, PIN4)


@pytest.mark.setup_client(pin=PIN4)
def test_change_invalid_current(client: Client):
    assert client.features.pin_protection is True

    # Check current PIN value
    _check_pin(client, PIN4)

    with client, pytest.raises(TrezorFailure):
        IF = InputFlowWrongPIN(client, PIN60)
        client.set_input_flow(IF.get())

        device.change_pin(client)

    # Check that there's still old PIN protection
    client.init_device()
    assert client.features.pin_protection is True
    _check_pin(client, PIN4)


@pytest.mark.models("mercury")
@pytest.mark.setup_client(pin=None)
def test_pin_menu_cancel_setup(client: Client):
    def cancel_pin_setup_input_flow():
        yield
        # enter context menu
        client.debug.click(buttons.CORNER_BUTTON)
        client.debug.synchronize_at("VerticalMenu")
        # click "Cancel PIN setup"
        client.debug.click(buttons.VERTICAL_MENU[0])
        client.debug.synchronize_at("Paragraphs")
        # swipe through info screen
        client.debug.swipe_up()
        client.debug.synchronize_at("PromptScreen")
        # tap to confirm
        client.debug.click(buttons.TAP_TO_CONFIRM)

    with client, pytest.raises(Cancelled):
        client.set_input_flow(cancel_pin_setup_input_flow)
        client.call(messages.ChangePin())
    _check_no_pin(client)
