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

TX_CACHE = TxCache("Bitcoin")

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)

PIN4 = "1234"

WORDS_20 = buttons.grid34(2, 2)


def set_autolock_delay(device_handler: "BackgroundDeviceHandler", delay_ms: int):
    debug = device_handler.debuglink()

    device_handler.run(device.apply_settings, auto_lock_delay_ms=delay_ms)

    layout = debug.wait_layout()
    assert layout.text == "< PinKeyboard >"
    debug.input("1234")

    layout = debug.wait_layout()
    assert (
        f"auto-lock your device after {delay_ms // 1000} seconds"
        in layout.get_content()
    )
    debug.click(buttons.OK)

    layout = debug.wait_layout()
    assert layout.text.startswith("< Homescreen")
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

    device_handler.run(btc.sign_tx, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE)

    layout = debug.wait_layout()
    assert "1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1" in layout.get_content().replace(" ", "")

    debug.click(buttons.OK, wait=True)
    debug.click(buttons.OK, wait=True)

    layout = debug.click(buttons.OK, wait=True)
    assert "Total amount: 0.0039 BTC" in layout.get_content()

    # wait for autolock to kick in
    time.sleep(10.1)
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_autolock_passphrase_keyboard(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # get address
    device_handler.run(common.get_test_address)

    # enter passphrase - slowly
    layout = debug.wait_layout()
    assert layout.text == "< PassphraseKeyboard >"

    CENTER_BUTTON = buttons.grid35(1, 2)
    # keep clicking for long enough to trigger the autolock if it incorrectly ignored key presses
    for _ in range(math.ceil(11 / 1.5)):
        debug.click(CENTER_BUTTON)
        time.sleep(1.5)

    debug.click(buttons.OK, wait=True)
    assert device_handler.result() == "mnF4yRWJXmzRB6EuBzuVigqeqTqirQupxJ"


@pytest.mark.setup_client(pin=PIN4, passphrase=True)
def test_autolock_interrupts_passphrase(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    # get address
    device_handler.run(common.get_test_address)

    # enter passphrase - slowly
    layout = debug.wait_layout()
    assert layout.text == "< PassphraseKeyboard >"

    CENTER_BUTTON = buttons.grid35(1, 2)
    # autolock must activate even if we pressed some buttons
    for _ in range(math.ceil(6 / 1.5)):
        debug.click(CENTER_BUTTON)
        time.sleep(1.5)

    # wait for autolock to kick in
    time.sleep(10.1)
    layout = debug.wait_layout()
    assert layout.text.startswith("< Lockscreen")
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_locks_at_number_of_words(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run(device.recover, dry_run=True)

    # unlock
    layout = debug.wait_layout()
    assert "Do you really want to check the recovery seed?" in layout.get_content()
    layout = debug.click(buttons.OK, wait=True)
    assert layout.text == "< PinKeyboard >"
    layout = debug.input(PIN4, wait=True)
    assert "Select number of words " in layout.get_content()

    # wait for autolock to trigger
    time.sleep(10.1)
    layout = debug.wait_layout()
    assert layout.text.startswith("< Lockscreen")
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()

    # unlock
    layout = debug.click(buttons.OK, wait=True)
    assert layout.text == "< PinKeyboard >"
    layout = debug.input(PIN4, wait=True)

    # we are back at homescreen
    assert "Select number of words" in layout.get_content()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_locks_at_word_entry(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run(device.recover, dry_run=True)

    # unlock
    layout = debug.wait_layout()
    assert "Do you really want to check the recovery seed?" in layout.get_content()
    layout = debug.click(buttons.OK, wait=True)
    assert layout.text == "< PinKeyboard >"
    layout = debug.input(PIN4, wait=True)

    # select 20 words
    recovery.select_number_of_words(debug, 20)

    layout = debug.click(buttons.OK, wait=True)
    # make sure keyboard locks
    assert layout.text == "< MnemonicKeyboard >"
    time.sleep(10.1)
    layout = debug.wait_layout()
    assert layout.text.startswith("< Lockscreen")
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


@pytest.mark.setup_client(pin=PIN4)
def test_dryrun_enter_word_slowly(device_handler: "BackgroundDeviceHandler"):
    set_autolock_delay(device_handler, 10_000)
    debug = device_handler.debuglink()

    device_handler.run(device.recover, dry_run=True)

    # unlock
    layout = debug.wait_layout()
    assert "Do you really want to check the recovery seed?" in layout.get_content()
    layout = debug.click(buttons.OK, wait=True)
    assert layout.text == "< PinKeyboard >"
    layout = debug.input(PIN4, wait=True)

    # select 20 words
    recovery.select_number_of_words(debug, 20)

    layout = debug.click(buttons.OK, wait=True)
    # type the word OCEAN slowly
    assert layout.text == "< MnemonicKeyboard >"
    for coords in buttons.type_word("ocea", is_slip39=True):
        time.sleep(9)
        debug.click(coords)
    layout = debug.click(buttons.CONFIRM_WORD, wait=True)
    # should not have locked, even though we took 9 seconds to type each letter
    assert layout.text == "< MnemonicKeyboard >"
    device_handler.kill_task()
