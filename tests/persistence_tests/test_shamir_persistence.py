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
from trezorlib.debuglink import DebugLink, LayoutType
from trezorlib.messages import RecoveryStatus

from ..click_tests import common, recovery
from ..common import MNEMONIC_SLIP39_ADVANCED_20, MNEMONIC_SLIP39_BASIC_20_3of6
from ..device_handler import BackgroundDeviceHandler
from ..emulators import Emulator
from ..upgrade_tests import core_only


def _restart(
    device_handler: BackgroundDeviceHandler, core_emulator: Emulator
) -> DebugLink:
    device_handler.restart(core_emulator)
    return device_handler.debuglink()


@core_only
def test_abort(core_emulator: Emulator):
    device_handler = BackgroundDeviceHandler(core_emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    if debug.layout_type is LayoutType.Delizia:
        pytest.skip("abort not supported on T3T1")

    assert features.recovery_status == RecoveryStatus.Nothing

    device_handler.run(device.recover, pin_protection=False)

    recovery.confirm_recovery(debug)
    layout = debug.read_layout()
    assert "number of words" in layout.text_content()

    debug = _restart(device_handler, core_emulator)
    features = device_handler.features()

    assert features.recovery_status == RecoveryStatus.Recovery

    assert "number of words" in debug.read_layout().text_content()
    # clicking at 24 in word choice
    recovery.select_number_of_words(debug, 24)

    # Cancelling the backup
    assert "Enter your backup" in debug.read_layout().text_content()
    layout = common.go_back(debug)

    assert layout.title().lower() in ("abort recovery", "cancel recovery")
    for _ in range(layout.page_count()):
        common.go_next(debug)

    assert debug.read_layout().main_component() == "Homescreen"
    features = device_handler.features()
    assert features.recovery_status == RecoveryStatus.Nothing


@core_only
def test_recovery_single_reset(core_emulator: Emulator):
    device_handler = BackgroundDeviceHandler(core_emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is False
    assert features.recovery_status == RecoveryStatus.Nothing

    device_handler.run(device.recover, pin_protection=False)

    recovery.confirm_recovery(debug)

    recovery.select_number_of_words(debug)

    debug = _restart(device_handler, core_emulator)
    features = device_handler.features()
    assert features.recovery_status == RecoveryStatus.Recovery

    # we need to enter the number of words again, that's a feature
    recovery.select_number_of_words(debug)
    recovery.enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)
    recovery.finalize(debug)

    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_status == RecoveryStatus.Nothing


@core_only
def test_recovery_on_old_wallet(core_emulator: Emulator):
    """Check that the recovery workflow started on a disconnected device can survive
    handling by the old Wallet.

    While Suite will send a RecoveryDevice message and hook into the running recovery
    flow, old Wallet can't do that and instead must repeatedly ask for features (via
    Initialize+GetFeatures). At minimum, these two messages must not interrupt the
    running recovery.
    """

    def assert_mnemonic_keyboard(debug: DebugLink) -> None:
        layout = debug.read_layout()
        if debug.layout_type == LayoutType.Caesar:
            # UI Caesar (TS3) has the keyboard wrapped in a Frame
            assert "MnemonicKeyboard" in layout.all_components()
        else:
            assert layout.main_component() == "MnemonicKeyboard"

    device_handler = BackgroundDeviceHandler(core_emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is False
    assert features.recovery_status == RecoveryStatus.Nothing

    # enter recovery mode
    device_handler.run(device.recover, pin_protection=False)

    recovery.confirm_recovery(debug)

    # restart to get into stand-alone recovery
    debug = _restart(device_handler, core_emulator)
    features = device_handler.features()
    assert features.recovery_status == RecoveryStatus.Recovery

    # enter number of words
    recovery.select_number_of_words(debug)

    first_share = MNEMONIC_SLIP39_BASIC_20_3of6[0]
    words = first_share.split(" ")

    # start entering first share
    assert (
        "Enter any share" in debug.read_layout().text_content()
        or "Enter each word" in debug.read_layout().text_content()
    )
    debug.press_yes()
    assert_mnemonic_keyboard(debug)

    # enter first word
    debug.input(words[0])
    layout = debug.read_layout()

    # while keyboard is open, hit the device with Initialize/GetFeatures
    device_handler.client.init_device()
    device_handler.client.refresh_features()

    # try entering remaining 19 words
    for word in words[1:]:
        assert_mnemonic_keyboard(debug)
        debug.input(word)
        layout = debug.read_layout()

    # check that we entered the first share successfully
    assert "2 more shares needed" in layout.text_content()

    # try entering the remaining shares
    for share in MNEMONIC_SLIP39_BASIC_20_3of6[1:3]:
        recovery.enter_share(debug, share)

    recovery.finalize(debug)

    # check that the recovery succeeded
    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_status == RecoveryStatus.Nothing


@core_only
def test_recovery_multiple_resets(core_emulator: Emulator):
    def enter_shares_with_restarts(debug: DebugLink) -> None:
        shares = MNEMONIC_SLIP39_ADVANCED_20
        layout = debug.read_layout()
        expected_text = "Enter any share"
        if debug.layout_type == LayoutType.Delizia:
            expected_text = "Enter each word"
        remaining = len(shares)
        for share in shares:
            assert expected_text in layout.text_content()
            layout = recovery.enter_share(debug, share)
            remaining -= 1
            expected_text = "You have entered"
            debug = _restart(device_handler, core_emulator)

        assert "Wallet recovery completed" in layout.text_content()

    device_handler = BackgroundDeviceHandler(core_emulator.client)
    debug = device_handler.debuglink()
    features = device_handler.features()

    assert features.initialized is False
    assert features.recovery_status == RecoveryStatus.Nothing

    # start device and recovery
    device_handler.run(device.recover, pin_protection=False)

    recovery.confirm_recovery(debug)

    # set number of words
    recovery.select_number_of_words(debug)

    # restart
    debug = _restart(device_handler, core_emulator)
    features = device_handler.features()
    assert features.recovery_status == RecoveryStatus.Recovery

    # enter the number of words again, that's a feature!
    recovery.select_number_of_words(debug)

    # enter shares and restart after each one
    enter_shares_with_restarts(debug)
    debug = device_handler.debuglink()
    assert debug.read_layout().main_component() == "Homescreen"

    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_status == RecoveryStatus.Nothing
