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

from trezorlib import device, messages

from .. import buttons
from ..common import MNEMONIC_SLIP39_BASIC_20_3of6


def enter_word(debug, word):
    word = word[:4]
    for coords in buttons.type_word(word):
        debug.click(coords)
    return debug.click(buttons.CONFIRM_WORD, wait=True)


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_recovery(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False
    device_handler.run(device.recover, pin_protection=False)

    # select number of words
    layout = debug.wait_layout()
    assert layout.text.startswith("Recovery mode")
    layout = debug.click(buttons.OK, wait=True)

    assert "Select number of words" in layout.text
    layout = debug.click(buttons.OK, wait=True)

    assert layout.text == "WordSelector"
    # click "20" at 2, 2
    coords = buttons.grid34(2, 2)
    layout = debug.click(coords, wait=True)
    assert "Enter any share" in layout.text

    expected_text = "Enter any share (20 words)"
    remaining = len(MNEMONIC_SLIP39_BASIC_20_3of6)
    for share in MNEMONIC_SLIP39_BASIC_20_3of6:
        assert expected_text in layout.text
        layout = debug.click(buttons.OK, wait=True)

        assert layout.text == "Slip39Keyboard"
        for word in share.split(" "):
            layout = enter_word(debug, word)

        remaining -= 1
        expected_text = "RecoveryHomescreen {} more".format(remaining)

    assert "You have successfully recovered your wallet" in layout.text
    layout = debug.click(buttons.OK, wait=True)

    assert layout.text == "Homescreen"

    assert isinstance(device_handler.result(), messages.Success)
    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False
