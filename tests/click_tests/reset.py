import shamir_mnemonic as shamir

from trezorlib import messages

from .. import buttons


def confirm_wait(debug, startswith):
    layout = debug.wait_layout()
    assert layout.text.startswith(startswith)
    debug.click(buttons.OK, wait=True)


def confirm_read(debug, startswith):
    layout = debug.read_layout()
    assert layout.text.startswith(startswith)
    debug.click(buttons.OK, wait=True)


def set_selection(debug, button, diff):
    layout = debug.read_layout()
    assert layout.text.startswith("Slip39NumInput")
    for _ in range(diff):
        debug.click(button, wait=False)
    debug.click(buttons.OK, wait=True)


def read_words(debug, is_advanced=False):
    def read_word(line: str):
        return line.split()[1]

    words = []
    layout = debug.read_layout()
    if is_advanced:
        assert layout.text.startswith("Group")
    else:
        assert layout.text.startswith("Recovery share")

    lines = layout.lines
    # first screen
    words.append(read_word(lines[3]))
    words.append(read_word(lines[4]))
    lines = debug.input(swipe=messages.DebugSwipeDirection.UP, wait=True).lines

    # screens 2 through
    for _ in range(4):
        words.append(read_word(lines[1]))
        words.append(read_word(lines[2]))
        words.append(read_word(lines[3]))
        words.append(read_word(lines[4]))
        lines = debug.input(swipe=messages.DebugSwipeDirection.UP, wait=True).lines

    # final screen
    words.append(read_word(lines[1]))
    words.append(read_word(lines[2]))
    debug.press_yes()

    return words


def confirm_words(debug, words):
    layout = debug.wait_layout()
    assert "Select word" in layout.text
    for _ in range(3):
        # "Select word 3 of 20"
        #              ^
        word_pos = int(layout.lines[1].split()[2])
        button_pos = layout.lines.index(words[word_pos - 1]) - 2
        layout = debug.click(buttons.RESET_WORD_CHECK[button_pos], wait=True)


def validate_mnemonics(mnemonics, expected_ems):
    # We expect these combinations to recreate the secret properly
    # In case of click tests the mnemonics are always XofX so no need for combinations
    ms = shamir.combine_mnemonics(mnemonics)
    identifier, iteration_exponent, _, _, _ = shamir._decode_mnemonics(mnemonics)
    ems = shamir._encrypt(ms, b"", iteration_exponent, identifier)
    assert ems == expected_ems
