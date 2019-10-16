import pytest

from trezorlib import device, messages

from .. import buttons
from ..common import MNEMONIC_SLIP39_BASIC_20_3of6


def enter_word(debug, word):
    word = word[:4]
    for coords in buttons.type_word(word):
        debug.click(coords)
    return " ".join(debug.click(buttons.CONFIRM_WORD, wait=True))


def click_ok(debug):
    return " ".join(debug.click(buttons.OK, wait=True))


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_recovery(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False
    device_handler.run(device.recover, pin_protection=False)

    # select number of words
    text = " ".join(debug.wait_layout())
    assert text.startswith("Recovery mode")
    text = click_ok(debug)

    assert "Select number of words" in text
    text = click_ok(debug)

    assert text == "WordSelector"
    # click "20" at 2, 2
    coords = buttons.grid34(2, 2)
    lines = debug.click(coords, wait=True)
    text = " ".join(lines)

    expected_text = "Enter any share (20 words)"
    remaining = len(MNEMONIC_SLIP39_BASIC_20_3of6)
    for share in MNEMONIC_SLIP39_BASIC_20_3of6:
        assert expected_text in text
        text = click_ok(debug)

        assert text == "Slip39Keyboard"
        for word in share.split(" "):
            text = enter_word(debug, word)

        remaining -= 1
        expected_text = "RecoveryHomescreen {} more".format(remaining)

    assert "You have successfully recovered your wallet" in text
    text = click_ok(debug)

    assert text == "Homescreen"

    assert isinstance(device_handler.result(), messages.Success)
    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False
