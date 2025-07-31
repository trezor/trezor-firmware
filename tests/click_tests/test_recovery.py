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

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

import pytest

from trezorlib import device, exceptions, messages
from trezorlib.transport.session import SessionV1

from ..common import MNEMONIC12, LayoutType, MNEMONIC_SLIP39_BASIC_20_3of6
from . import recovery
from .common import go_next
from .test_autolock import PIN4, set_autolock_delay, unlock_dry_run

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
    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session, device.recover, pin_protection=False
    )  # type: ignore

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
    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session, device.recover, pin_protection=False
    )  # type: ignore

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


@pytest.mark.protocol("protocol_v1")
def test_recovery_cancel_issue4613(device_handler: "BackgroundDeviceHandler"):
    """Test for issue fixed in PR #4613: After aborting the recovery flow from host
    side, it was impossible to exit recovery until device was restarted."""

    debug = device_handler.debuglink()

    # initiate and confirm the recovery
    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session, device.recover, type=messages.RecoveryType.DryRun
    )
    title = (
        "reset__check_wallet_backup_title"
        if device_handler.debuglink().layout_type is LayoutType.Eckhart
        else "recovery__title_dry_run"
    )
    recovery.confirm_recovery(debug, title=title)
    # select number of words
    recovery.select_number_of_words(debug, num_of_words=12)
    device_handler.client.transport.close()
    # abort the process running the recovery from host
    device_handler.kill_task()

    # Now Trezor is hanging, waiting for user interaction, but nobody is communicating
    # from the host side.

    # Reopen client and debuglink, closed by kill_task
    device_handler.client.transport.open()
    debug = device_handler.debuglink()

    # Ping the Trezor with an Initialize message (listed in DO_NOT_RESTART)
    try:
        session = SessionV1(device_handler.client, id=b"")
        session.client._last_active_session = session
        features = session.call(messages.Initialize())
    except exceptions.Cancelled:
        # due to a related problem, the first call in this situation will return
        # a Cancelled failure. This test does not care, we just retry.
        features = device_handler.client.get_seedless_session().call(
            messages.Initialize()
        )

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


@pytest.mark.models(skip=["legacy", "safe3"])
@pytest.mark.setup_client(pin=PIN4)
def test_recovery_slip39_issue5306(device_handler: "BackgroundDeviceHandler"):
    """Test for issue fixed in PR #5306: After tapping the key more times
    than its length, there was an internal error UF."""

    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(
        session, device.recover, type=messages.RecoveryType.DryRun
    )

    unlock_dry_run(debug)

    # select 20 words
    recovery.select_number_of_words(debug, 20)

    # go to mnemonic keyboard
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        layout = go_next(debug)
        assert layout.main_component() == "MnemonicKeyboard"
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        layout = debug.read_layout()
        assert "MnemonicKeyboard" in layout.all_components()
    else:
        raise ValueError(f"Unsupported layout type: {debug.layout_type}")

    # click the first key multiple times (more times than its length) to trigger the issue
    coords = list(debug.button_actions.type_word("a", is_slip39=True))
    for _ in range(3):
        debug.click(coords[0])

    # Make sure, the keyboard did not crash
    layout = debug.read_layout()
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        assert layout.main_component() == "MnemonicKeyboard"
    elif debug.layout_type is LayoutType.Caesar:
        assert "MnemonicKeyboard" in layout.all_components()
    else:
        raise ValueError(f"Unsupported layout type: {debug.layout_type}")

    # wait for the keyboard to lock
    time.sleep(10.1)
    if debug.layout_type is LayoutType.Eckhart:
        assert debug.read_layout().main_component() == "Homescreen"
    else:
        assert debug.read_layout().main_component() == "Lockscreen"
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()
