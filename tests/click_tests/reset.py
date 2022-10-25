from typing import TYPE_CHECKING

from shamir_mnemonic import shamir

from trezorlib import messages

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink


def confirm_wait(debug: "DebugLink", title: str) -> None:
    layout = debug.wait_layout()
    assert title.upper() in layout.get_title()
    debug.click(buttons.OK, wait=True)


def confirm_read(debug: "DebugLink", title: str) -> None:
    layout = debug.read_layout()
    if title == "Caution":
        assert "OK, I UNDERSTAND" in layout.text
    elif title == "Success":
        assert any(
            text in layout.get_content() for text in ("success", "finished", "done")
        )
    else:
        assert title.upper() in layout.get_title()
    debug.click(buttons.OK, wait=True)


def set_selection(debug: "DebugLink", button: tuple[int, int], diff: int) -> None:
    layout = debug.read_layout()
    assert "NumberInputDialog" in layout.text
    for _ in range(diff):
        debug.click(button, wait=False)
    debug.click(buttons.OK, wait=True)


def read_words(debug: "DebugLink", is_advanced: bool = False) -> list[str]:
    words: list[str] = []
    layout = debug.read_layout()
    if is_advanced:
        assert layout.get_title().startswith("GROUP")
    else:
        assert layout.get_title().startswith("RECOVERY SHARE #")

    # Swiping through all the page and loading the words
    for _ in range(layout.get_page_count() - 1):
        words.extend(layout.get_seed_words())
        layout = debug.input(swipe=messages.DebugSwipeDirection.UP, wait=True)
    words.extend(layout.get_seed_words())

    debug.press_yes()

    return words


def confirm_words(debug: "DebugLink", words: list[str]) -> None:
    layout = debug.wait_layout()
    assert "Select word" in layout.text
    for _ in range(3):
        # "Select word 3 of 20"
        #              ^
        word_pos = int(layout.get_content().split()[2])
        # Unifying both the buttons and words to lowercase
        btn_texts = [text.lower() for text in layout.get_button_texts()]
        wanted_word = words[word_pos - 1].lower()
        button_pos = btn_texts.index(wanted_word)
        layout = debug.click(buttons.RESET_WORD_CHECK[button_pos], wait=True)


def validate_mnemonics(mnemonics: list[str], expected_ems: bytes) -> None:
    # We expect these combinations to recreate the secret properly
    # In case of click tests the mnemonics are always XofX so no need for combinations
    groups = shamir.decode_mnemonics(mnemonics)
    ems = shamir.recover_ems(groups)
    assert expected_ems == ems.ciphertext
