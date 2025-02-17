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

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

import pytest

from trezorlib import device, exceptions, messages

from ..common import MNEMONIC12, MNEMONIC_SLIP39_BASIC_20_3of6
from . import recovery

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


@contextmanager
def prepare_recovery_and_evaluate(
    device_handler: "BackgroundDeviceHandler",
) -> Generator["DebugLink", None, None]:
    features = device_handler.features()
    debug = device_handler.debuglink()
    assert features.initialized is False
    device_handler.run(device.recover, pin_protection=False)  # type: ignore

    yield debug

    device_handler.result()

    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_status == messages.RecoveryStatus.Nothing


@contextmanager
def prepare_recovery_and_evaluate_cancel(
    device_handler: "BackgroundDeviceHandler",
) -> Generator["DebugLink", None, None]:
    features = device_handler.features()
    debug = device_handler.debuglink()
    assert features.initialized is False
    device_handler.run(device.recover, pin_protection=False)  # type: ignore

    yield debug

    with pytest.raises(exceptions.Cancelled):
        device_handler.result()

    features = device_handler.features()
    assert features.initialized is False
    assert features.recovery_status == messages.RecoveryStatus.Nothing


@pytest.mark.setup_client(uninitialized=True)
def test_recovery_slip39_basic(device_handler: "BackgroundDeviceHandler"):
    with prepare_recovery_and_evaluate(device_handler) as debug:
        recovery.confirm_recovery(debug)
        recovery.select_number_of_words(debug)
        recovery.enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)
        recovery.finalize(debug)


@pytest.mark.setup_client(uninitialized=True)
def test_recovery_cancel_number_of_words(device_handler: "BackgroundDeviceHandler"):
    with prepare_recovery_and_evaluate_cancel(device_handler) as debug:
        recovery.confirm_recovery(debug)
        recovery.cancel_select_number_of_words(debug)


@pytest.mark.setup_client(uninitialized=True)
def test_recovery_bip39(device_handler: "BackgroundDeviceHandler"):
    with prepare_recovery_and_evaluate(device_handler) as debug:
        recovery.confirm_recovery(debug)
        recovery.select_number_of_words(debug, num_of_words=12)
        recovery.enter_seed(debug, MNEMONIC12.split())
        recovery.finalize(debug)


@pytest.mark.setup_client(uninitialized=True)
def test_recovery_bip39_previous_word(device_handler: "BackgroundDeviceHandler"):
    with prepare_recovery_and_evaluate(device_handler) as debug:
        recovery.confirm_recovery(debug)
        recovery.select_number_of_words(debug, num_of_words=12)
        seed_words: list[str] = MNEMONIC12.split()
        bad_indexes = {1: seed_words[-1], 7: seed_words[0]}
        recovery.enter_seed_previous_correct(debug, seed_words, bad_indexes)
        recovery.finalize(debug)


def test_recovery_cancel_issue4613(device_handler: "BackgroundDeviceHandler"):
    """Test for issue fixed in PR #4613: After aborting the recovery flow from host
    side, it was impossible to exit recovery until device was restarted."""

    debug = device_handler.debuglink()

    # initiate and confirm the recovery
    device_handler.run(device.recover, type=messages.RecoveryType.DryRun)
    recovery.confirm_recovery(debug, title="recovery__title_dry_run")
    # select number of words
    recovery.select_number_of_words(debug, num_of_words=12)
    # abort the process running the recovery from host
    device_handler.kill_task()

    # Now Trezor is hanging, waiting for user interaction, but nobody is communicating
    # from the host side.

    # Reopen client and debuglink, closed by kill_task
    device_handler.client.open()
    debug = device_handler.debuglink()

    # Ping the Trezor with an Initialize message (listed in DO_NOT_RESTART)
    try:
        features = device_handler.client.call(messages.Initialize())
    except exceptions.Cancelled:
        # due to a related problem, the first call in this situation will return
        # a Cancelled failure. This test does not care, we just retry.
        features = device_handler.client.call(messages.Initialize())

    assert features.recovery_status == messages.RecoveryStatus.Recovery
    # Trezor is sitting in recovery_homescreen now, waiting for the user to select
    # number of words
    recovery.select_number_of_words(debug, num_of_words=12)
    # Trezor is waiting at "enter any word" screen, which has a Cancel button
    recovery.cancel_recovery(debug)

    # We should be back at homescreen
    layout = debug.read_layout()
    assert layout.main_component() == "Homescreen"
    features = device_handler.client.refresh_features()
    assert features.recovery_status == messages.RecoveryStatus.Nothing
