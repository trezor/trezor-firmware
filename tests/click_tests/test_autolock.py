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

import math
import time
from typing import TYPE_CHECKING

import pytest

from trezorlib import btc, device, exceptions, messages
from trezorlib.tools import parse_path

from .. import buttons, common
from ..tx_cache import TxCache
from . import recovery

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler
    from trezorlib.debuglink import DebugLink, LayoutContent

TX_CACHE = TxCache("Bitcoin")

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)

PIN4 = "1234"

WORDS_20 = buttons.grid34(2, 2)
CENTER_BUTTON = buttons.grid35(1, 2)


def set_autolock_delay(device_handler: "BackgroundDeviceHandler", delay_ms: int):
    debug = device_handler.debuglink()

    device_handler.run(device.apply_settings, auto_lock_delay_ms=delay_ms)  # type: ignore

    layout = debug.wait_layout()

    if debug.model == "T":
        assert "PinKeyboard" in layout.str_content
    elif debug.model == "R":
        assert "PinEntry" in layout.str_content

    debug.input("1234")

    layout = debug.wait_layout()
    assert (
        f"auto-lock your device after {delay_ms // 1000} seconds"
        in layout.text_content()
    )

    if debug.model == "T":
        debug.click(buttons.OK)
    elif debug.model == "R":
        debug.press_right()

    layout = debug.wait_layout()
    assert "Homescreen" in layout.str_content
    assert device_handler.result() == "Settings applied"


@pytest.mark.setup_client(pin=PIN4)
def test_autolock_interrupts_signing(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)

    debug = device_handler.debuglink()
    # try to sign a transaction
    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/0"),
        amount=390000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    device_handler.run(btc.sign_tx, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE)  # type: ignore

    layout = debug.wait_layout()
    assert "1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1" in layout.text_content().replace(
        " ", ""
    )

    if debug.model == "T":
        debug.click(buttons.OK, wait=True)
        debug.click(buttons.OK, wait=True)
        layout = debug.click(buttons.OK, wait=True)
        assert "Total amount: 0.0039 BTC" in layout.text_content()
    elif debug.model == "R":
        debug.press_right(wait=True)
        debug.press_right(wait=True)
        layout = debug.press_right(wait=True)
        assert "TOTAL AMOUNT 0.0039 BTC" in layout.text_content()

    # wait for autolock to kick in
    time.sleep(10.1)
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_autolock_passphrase_keyboard(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # TODO: find out why TR does lock here
    if debug.model == "R":
        pytest.skip("Somehow the device locks itself and then triggers Cancelled")

    # get address
    device_handler.run(common.get_test_address)  # type: ignore

    # enter passphrase - slowly
    layout = debug.wait_layout()
    if debug.model == "T":
        assert "PassphraseKeyboard" in layout.str_content
    elif debug.model == "R":
        assert "PassphraseEntry" in layout.str_content

    if debug.model == "R":
        # Going into the first character category (abc)
        debug.press_middle()

    # keep clicking for long enough to trigger the autolock if it incorrectly ignored key presses
    for _ in range(math.ceil(11 / 1.5)):
        if debug.model == "T":
            debug.click(CENTER_BUTTON)
        elif debug.model == "R":
            debug.press_middle()
        time.sleep(1.5)

    # Confirm the passphrase
    if debug.model == "T":
        debug.click(buttons.OK, wait=True)
    elif debug.model == "R":
        debug.press_left()  # go to BACK
        debug.press_middle()  # PRESS back
        debug.press_left()  # go to ENTER
        debug.press_middle()  # press ENTER
        debug.wait_layout()

    assert device_handler.result() == "mnF4yRWJXmzRB6EuBzuVigqeqTqirQupxJ"


@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_autolock_interrupts_passphrase(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # get address
    device_handler.run(common.get_test_address)  # type: ignore

    # enter passphrase - slowly
    layout = debug.wait_layout()
    if debug.model == "T":
        assert "PassphraseKeyboard" in layout.str_content
    elif debug.model == "R":
        assert "PassphraseEntry" in layout.str_content

    if debug.model == "R":
        # Going into the first character category (abc)
        debug.press_middle()

    # autolock must activate even if we pressed some buttons
    for _ in range(math.ceil(6 / 1.5)):
        if debug.model == "T":
            debug.click(CENTER_BUTTON)
        elif debug.model == "R":
            debug.press_middle()
        time.sleep(1.5)

    # wait for autolock to kick in
    time.sleep(10.1)
    layout = debug.wait_layout()
    assert "Lockscreen" in layout.str_content
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


def unlock_dry_run(debug: "DebugLink", wait_r: bool = True) -> "LayoutContent":
    layout = debug.wait_layout()
    assert "Do you really want to check the recovery seed?" in layout.text_content()
    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)
        assert "PinKeyboard" in layout.str_content
    elif debug.model == "R":
        layout = debug.press_right(wait=True)
        assert "PinEntry" in layout.str_content

    layout = debug.input(PIN4, wait=True)
    assert layout is not None
    return layout


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_locks_at_number_of_words(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # TODO: find out why TR does lock here
    if debug.model == "R":
        pytest.skip("TR does not want to be unlocked below")

    device_handler.run(device.recover, dry_run=True)  # type: ignore

    layout = unlock_dry_run(debug)
    assert "select the number of words " in layout.text_content()

    # wait for autolock to trigger
    time.sleep(10.1)
    layout = debug.wait_layout()
    assert "Lockscreen" in layout.str_content
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()

    # unlock
    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)
        assert "PinKeyboard" in layout.str_content
    elif debug.model == "R":
        # TODO: why does not work for TR in any way? Read_layout, wait_layout, wait=True...
        layout = debug.press_right(wait=True)
        assert "PinEntry" in layout.str_content
    layout = debug.input(PIN4, wait=True)
    assert layout is not None

    # we are back at homescreen
    assert "select the number of words" in layout.text_content()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_locks_at_word_entry(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run(device.recover, dry_run=True)  # type: ignore

    unlock_dry_run(debug)

    # select 20 words
    recovery.select_number_of_words(debug, 20, wait_r=False)

    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)
        assert "MnemonicKeyboard" in layout.str_content
    elif debug.model == "R":
        layout = debug.press_right(wait=True)
        assert "WORD ENTERING" in layout.title()
        layout = debug.press_right(wait=True)
        assert "Slip39Entry" in layout.str_content

    # make sure keyboard locks
    time.sleep(10.1)
    layout = debug.wait_layout()
    assert "Lockscreen" in layout.str_content
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_enter_word_slowly(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # TODO: find out why TR does lock here
    if debug.model == "R":
        pytest.skip("Somehow the device locks itself during button clicks")

    device_handler.run(device.recover, dry_run=True)  # type: ignore

    unlock_dry_run(debug)

    # select 20 words
    recovery.select_number_of_words(debug, 20, wait_r=False)

    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)
        assert "MnemonicKeyboard" in layout.str_content

        # type the word OCEAN slowly
        for coords in buttons.type_word("ocea", is_slip39=True):
            time.sleep(9)
            debug.click(coords)
        layout = debug.click(buttons.CONFIRM_WORD, wait=True)
        # should not have locked, even though we took 9 seconds to type each letter
        assert "MnemonicKeyboard" in layout.str_content
    elif debug.model == "R":
        layout = debug.press_right(wait=True)
        assert "WORD ENTERING" in layout.title()
        layout = debug.press_right(wait=True)
        assert "Slip39Entry" in layout.str_content

        # type the word `ACADEMIC` slowly (A, C, and the whole word confirmation)
        for _ in range(3):
            time.sleep(9)
            debug.press_middle()
        layout = debug.wait_layout()
        # should not have locked, even though we took 9 seconds to type each letter
        assert "Slip39Entry" in layout.str_content

    device_handler.kill_task()
