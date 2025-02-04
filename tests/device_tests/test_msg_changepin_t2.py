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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import Cancelled, TrezorFailure

from ..input_flows import (
    InputFlowCodeChangeFail,
    InputFlowNewCodeMismatch,
    InputFlowWrongPIN,
)

PIN4 = "1234"
PIN60 = "789456" * 10
PIN_MAX = "".join(chr((i % 10) + ord("0")) for i in range(MAX_PIN_LENGTH))

pytestmark = pytest.mark.models("core")


def _check_pin(session: Session, pin: str):

    with session, session.client as client:
        client.ui.__init__(client.debug)
        client.use_pin_sequence([pin, pin, pin, pin, pin, pin])
        session.lock()
        assert session.features.pin_protection is True
        assert session.features.unlocked is False
        session.set_expected_responses([messages.ButtonRequest, messages.Address])
        btc.get_address(session, "Testnet", PASSPHRASE_TEST_PATH)


def _check_no_pin(session: Session):
    session.lock()
    assert session.features.pin_protection is False

    with session:
        session.set_expected_responses([messages.Address])
        btc.get_address(session, "Testnet", PASSPHRASE_TEST_PATH)


def test_set_pin(session: Session):
    assert session.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(session)

    # Let's set new PIN
    with session, session.client as client:
        if client.layout_type is LayoutType.Caesar:
            br_count = 6
        else:
            br_count = 4
        client.use_pin_sequence([PIN_MAX, PIN_MAX])
        session.set_expected_responses(
            [messages.ButtonRequest] * br_count + [messages.Success]
        )
        device.change_pin(session)

    assert session.features.pin_protection is True
    _check_pin(session, PIN_MAX)


@pytest.mark.setup_client(pin=PIN4)
def test_change_pin(session: Session):
    assert session.features.pin_protection is True

    # Check current PIN value
    _check_pin(session, PIN4)

    # Let's change PIN
    with session, session.client as client:
        client.use_pin_sequence([PIN4, PIN_MAX, PIN_MAX])
        if client.layout_type is LayoutType.Caesar:
            br_count = 6
        else:
            br_count = 5
        session.set_expected_responses(
            [messages.ButtonRequest] * br_count
            + [messages.Success]  # , messages.Features]
        )
        device.change_pin(session)

    # Check that there's still PIN protection now
    session.refresh_features()
    assert session.features.pin_protection is True
    # Check that the PIN is correct
    _check_pin(session, PIN_MAX)


@pytest.mark.setup_client(pin=PIN4)
def test_remove_pin(session: Session):
    assert session.features.pin_protection is True

    # Check current PIN value
    _check_pin(session, PIN4)

    # Let's remove PIN
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [messages.ButtonRequest] * 3 + [messages.Success]
        )
        device.change_pin(session, remove=True)

    # Check that there's no PIN protection now
    session.refresh_features()
    assert session.features.pin_protection is False
    _check_no_pin(session)


def test_set_failed(session: Session):
    assert session.features.pin_protection is False

    # Check that there's no PIN protection
    _check_no_pin(session)

    with session, session.client as client, pytest.raises(TrezorFailure):
        IF = InputFlowNewCodeMismatch(client, PIN4, PIN60, what="pin")
        client.set_input_flow(IF.get())

        device.change_pin(session)

    # Check that there's still no PIN protection now
    session.refresh_features()
    assert session.features.pin_protection is False
    _check_no_pin(session)


@pytest.mark.setup_client(pin=PIN4)
def test_change_failed(session: Session):
    assert session.features.pin_protection is True

    # Check current PIN value
    _check_pin(session, PIN4)

    with session, session.client as client, pytest.raises(Cancelled):
        IF = InputFlowCodeChangeFail(session, PIN4, "457891", "381847")
        client.set_input_flow(IF.get())

        device.change_pin(session)

    # Check that there's still old PIN protection
    session.refresh_features()
    assert session.features.pin_protection is True
    _check_pin(session, PIN4)


@pytest.mark.setup_client(pin=PIN4)
def test_change_invalid_current(session: Session):
    assert session.features.pin_protection is True

    # Check current PIN value
    _check_pin(session, PIN4)

    with session, session.client as client, pytest.raises(TrezorFailure):
        IF = InputFlowWrongPIN(client, PIN60)
        client.set_input_flow(IF.get())

        device.change_pin(session)

    # Check that there's still old PIN protection
    session.refresh_features()
    assert session.features.pin_protection is True
    _check_pin(session, PIN4)


@pytest.mark.models("delizia")
@pytest.mark.setup_client(pin=None)
def test_pin_menu_cancel_setup(session: Session):
    def cancel_pin_setup_input_flow():
        yield
        debug = session.client.debug
        # enter context menu
        debug.click(debug.screen_buttons.menu())
        debug.synchronize_at("VerticalMenu")
        # click "Cancel PIN setup"
        debug.click(debug.screen_buttons.vertical_menu_items()[0])
        debug.synchronize_at("Paragraphs")
        # swipe through info screen
        debug.swipe_up()
        debug.synchronize_at("PromptScreen")
        # tap to confirm
        debug.click(debug.screen_buttons.tap_to_confirm())

    with session, session.client as client, pytest.raises(Cancelled):
        client.set_input_flow(cancel_pin_setup_input_flow)
        session.call(messages.ChangePin())
    _check_no_pin(session)
