from .. import buttons


def enter_word(debug, word):
    word = word[:4]
    for coords in buttons.type_word(word):
        debug.click(coords)
    return debug.click(buttons.CONFIRM_WORD, wait=True)


def confirm_recovery(debug):
    layout = debug.wait_layout()
    assert layout.text.startswith("Recovery mode")
    debug.click(buttons.OK, wait=True)


def select_number_of_words(debug, num_of_words=20):
    layout = debug.read_layout()

    # select number of words
    assert "Select number of words" in layout.text
    layout = debug.click(buttons.OK, wait=True)
    assert layout.text == "WordSelector"

    # click the number
    word_option_offset = 6
    word_options = (12, 18, 20, 24, 33)
    index = word_option_offset + word_options.index(
        num_of_words
    )  # raises if num of words is invalid
    coords = buttons.grid34(index % 3, index // 3)
    layout = debug.click(coords, wait=True)
    assert "Enter any share" in layout.text


def enter_share(debug, share: str):
    layout = debug.click(buttons.OK, wait=True)

    assert layout.text == "Slip39Keyboard"
    for word in share.split(" "):
        layout = enter_word(debug, word)

    return layout


def enter_shares(debug, shares: list):
    layout = debug.read_layout()
    expected_text = "Enter any share"
    remaining = len(shares)
    for share in shares:
        assert expected_text in layout.text
        layout = enter_share(debug, share)
        remaining -= 1
        expected_text = f"RecoveryHomescreen {remaining} more"

    assert "You have successfully recovered your wallet" in layout.text


def finalize(debug):
    layout = debug.click(buttons.OK, wait=True)
    assert layout.text == "Homescreen"
