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

from trezorlib import device

from .. import buttons
from ..click_tests import recovery
from ..common import MNEMONIC_SLIP39_ADVANCED_20, MNEMONIC_SLIP39_BASIC_20_3of6
from ..device_handler import BackgroundDeviceHandler
from ..emulators import EmulatorWrapper
from ..upgrade_tests import core_only


@pytest.fixture
def emulator():
    with EmulatorWrapper("core") as emu:
        yield emu


def _restart(device_handler, emulator):
    device_handler.restart(emulator)
    return device_handler.debuglink()


@core_only
def test_abort(emulator):
    device_handler = BackgroundDeviceHandler(emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.recovery_mode is False

    device_handler.run(device.recover, pin_protection=False)
    layout = debug.wait_layout()
    assert layout.text.startswith("Recovery mode")

    layout = debug.click(buttons.OK, wait=True)
    assert "Select number of words" in layout.text

    device_handler.restart(emulator)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.recovery_mode is True

    # no waiting for layout because layout doesn't change
    layout = debug.read_layout()
    assert "Select number of words" in layout.text
    layout = debug.click(buttons.CANCEL, wait=True)

    assert layout.text.startswith("Abort recovery")
    layout = debug.click(buttons.OK, wait=True)

    assert layout.text == "Homescreen"
    features = device_handler.features()
    assert features.recovery_mode is False


@core_only
def test_recovery_single_reset(emulator):
    device_handler = BackgroundDeviceHandler(emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is False
    assert features.recovery_mode is False

    device_handler.run(device.recover, pin_protection=False)
    recovery.confirm_recovery(debug)

    recovery.select_number_of_words(debug)

    debug = _restart(device_handler, emulator)
    features = device_handler.features()
    assert features.recovery_mode is True

    # we need to enter the number of words again, that's a feature
    recovery.select_number_of_words(debug)
    recovery.enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)
    recovery.finalize(debug)

    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False


@core_only
def test_recovery_on_old_wallet(emulator):
    """Check that the recovery workflow started on a disconnected device can survive
    handling by the old Wallet.

    While Suite will send a RecoveryDevice message and hook into the running recovery
    flow, old Wallet can't do that and instead must repeatedly ask for features (via
    Initialize+GetFeatures). At minimum, these two messages must not interrupt the
    running recovery.
    """
    device_handler = BackgroundDeviceHandler(emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is False
    assert features.recovery_mode is False

    # enter recovery mode
    device_handler.run(device.recover, pin_protection=False)
    recovery.confirm_recovery(debug)

    # restart to get into stand-alone recovery
    debug = _restart(device_handler, emulator)
    features = device_handler.features()
    assert features.recovery_mode is True

    # enter number of words
    recovery.select_number_of_words(debug)

    first_share = MNEMONIC_SLIP39_BASIC_20_3of6[0]
    words = first_share.split(" ")

    # start entering first share
    layout = debug.read_layout()
    assert "Enter any share" in layout.text
    debug.press_yes()
    layout = debug.wait_layout()
    assert layout.text == "Slip39Keyboard"

    # enter first word
    debug.input(words[0])
    layout = debug.wait_layout()

    # while keyboard is open, hit the device with Initialize/GetFeatures
    device_handler.client.init_device()
    device_handler.client.refresh_features()

    # try entering remaining 19 words
    for word in words[1:]:
        assert layout.text == "Slip39Keyboard"
        debug.input(word)
        layout = debug.wait_layout()

    # check that we entered the first share successfully
    assert "2 more shares" in layout.text

    # try entering the remaining shares
    for share in MNEMONIC_SLIP39_BASIC_20_3of6[1:3]:
        recovery.enter_share(debug, share)

    recovery.finalize(debug)

    # check that the recovery succeeded
    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False


@core_only
def test_recovery_multiple_resets(emulator):
    def enter_shares_with_restarts(debug):
        shares = MNEMONIC_SLIP39_ADVANCED_20
        layout = debug.read_layout()
        expected_text = "Enter any share"
        remaining = len(shares)
        for share in shares:
            assert expected_text in layout.text
            layout = recovery.enter_share(debug, share)
            remaining -= 1
            expected_text = "Success You have entered"
            debug = _restart(device_handler, emulator)

        assert "You have successfully recovered your wallet" in layout.text

    device_handler = BackgroundDeviceHandler(emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is False
    assert features.recovery_mode is False

    # start device and recovery
    device_handler.run(device.recover, pin_protection=False)
    recovery.confirm_recovery(debug)

    # set number of words
    recovery.select_number_of_words(debug)

    # restart
    debug = _restart(device_handler, emulator)
    features = device_handler.features()
    assert features.recovery_mode is True

    # enter the number of words again, that's a feature!
    recovery.select_number_of_words(debug)

    # enter shares and restart after each one
    enter_shares_with_restarts(debug)
    debug = device_handler.debuglink()
    layout = debug.read_layout()
    assert layout.text == "Homescreen"

    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False
