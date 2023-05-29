from typing import TYPE_CHECKING

from .. import buttons
from .common import go_next

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    if debug.model == "T":
        typed_word = word[:4]
        for coords in buttons.type_word(typed_word, is_slip39=is_slip39):
            debug.click(coords)

        return debug.click(buttons.CONFIRM_WORD, wait=True)
    elif debug.model == "R":
        letter_index = 0
        layout = debug.read_layout()

        # Letter choices
        while layout.find_values_by_key("letter_choices"):
            letter = word[letter_index]
            while not layout.get_middle_choice() == letter:
                layout = debug.press_right(wait=True)

            layout = debug.press_middle(wait=True)
            letter_index += 1

        # Word choices
        while not layout.get_middle_choice() == word:
            layout = debug.press_right(wait=True)

        return debug.press_middle(wait=True)
    else:
        raise ValueError("Unknown model")


def confirm_recovery(debug: "DebugLink") -> None:
    if debug.model == "T":
        if not debug.legacy_ui and not debug.legacy_debug:
            layout = debug.wait_layout()
            assert layout.title().startswith("WALLET RECOVERY")
        debug.click(buttons.OK, wait=True)
    elif debug.model == "R":
        layout = debug.wait_layout()
        assert layout.title() == "WALLET RECOVERY"
        debug.press_right(wait=True)
        debug.press_right()


def select_number_of_words(debug: "DebugLink", num_of_words: int = 20) -> None:
    debug.wait_layout()
    if debug.model == "T":
        # select number of words
        if not debug.legacy_ui and not debug.legacy_debug:
            assert "number of words" in debug.read_layout().text_content()
        layout = debug.click(buttons.OK, wait=True)
        if debug.legacy_ui:
            assert layout.json_str == "WordSelector"
        elif debug.legacy_debug:
            assert "SelectWordCount" in layout.json_str
        else:
            # Two title options
            assert layout.title() in ("SEED CHECK", "WALLET RECOVERY")

        # click the number
        word_option_offset = 6
        word_options = (12, 18, 20, 24, 33)
        index = word_option_offset + word_options.index(
            num_of_words
        )  # raises if num of words is invalid
        coords = buttons.grid34(index % 3, index // 3)
        layout = debug.click(coords, wait=True)
    elif debug.model == "R":
        assert "number of words" in debug.read_layout().text_content()
        layout = debug.press_right(wait=True)

        assert layout.title() == "NUMBER OF WORDS"

        # navigate to the number and confirm it
        word_options = (12, 18, 20, 24, 33)
        index = word_options.index(num_of_words)
        for _ in range(index):
            debug.press_right(wait=True)
        layout = debug.press_middle(wait=True)
    else:
        raise ValueError("Unknown model")

    if not debug.legacy_ui and not debug.legacy_debug:
        if num_of_words in (20, 33):
            assert "Enter any share" in layout.text_content()
        else:
            assert "Enter recovery seed" in layout.text_content()


def enter_share(debug: "DebugLink", share: str) -> "LayoutContent":
    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)

        if debug.legacy_ui:
            assert layout.json_str == "Slip39Keyboard"
        elif debug.legacy_debug:
            assert "MnemonicKeyboard" in layout.json_str
        else:
            assert layout.main_component() == "MnemonicKeyboard"

        for word in share.split(" "):
            layout = enter_word(debug, word, is_slip39=True)

        return layout
    elif debug.model == "R":
        layout = debug.press_right(wait=True)
        assert layout.title() == "WORD ENTERING"

        layout = debug.press_right(wait=True)
        assert "Slip39Entry" in layout.all_components()

        for word in share.split(" "):
            layout = enter_word(debug, word, is_slip39=True)

        return layout
    else:
        raise ValueError("Unknown model")


def enter_shares(debug: "DebugLink", shares: list[str]) -> None:
    layout = debug.read_layout()
    expected_text = "Enter any share"
    remaining = len(shares)
    for share in shares:
        assert expected_text in layout.text_content()
        layout = enter_share(debug, share)
        remaining -= 1
        expected_text = f"{remaining} more share"

    assert "You have finished recovering your wallet" in layout.text_content()


def enter_seed(debug: "DebugLink", seed_words: list[str]) -> None:
    if debug.model == "T":
        assert "Enter" in debug.read_layout().text_content()

        layout = debug.click(buttons.OK, wait=True)
        assert layout.main_component() == "MnemonicKeyboard"

        for word in seed_words:
            layout = enter_word(debug, word, is_slip39=False)

        assert "You have finished recovering your wallet" in layout.text_content()
    elif debug.model == "R":
        assert "Enter" in debug.read_layout().text_content()

        layout = debug.press_right(wait=True)
        assert layout.title() == "WORD ENTERING"

        layout = debug.press_right(wait=True)
        assert "Bip39Entry" in layout.all_components()

        for word in seed_words:
            layout = enter_word(debug, word, is_slip39=False)

        assert "You have finished recovering your wallet" in layout.text_content()


def finalize(debug: "DebugLink") -> None:
    layout = go_next(debug, wait=True)
    assert layout is not None
    assert layout.main_component() == "Homescreen"
