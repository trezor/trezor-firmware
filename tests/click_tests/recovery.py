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
    layout = debug.wait_layout()
    if debug.model == "T":
        assert layout.title().startswith(("RECOVER WALLET", "BACKUP CHECK"))
        debug.click(buttons.OK, wait=True)
    elif debug.model == "R":
        assert layout.title() == "RECOVER WALLET"
        debug.press_right(wait=True)
        debug.press_right()


def select_number_of_words(
    debug: "DebugLink", num_of_words: int = 20, wait: bool = True
) -> None:
    if wait:
        debug.wait_layout()
    if debug.model == "T":
        assert "number of words" in debug.read_layout().text_content()
        assert debug.read_layout().title() in (
            "BACKUP CHECK",
            "RECOVER WALLET",
        )

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

    if num_of_words in (20, 33):
        assert "Enter any share" in layout.text_content()
    else:
        assert "Enter your backup" in layout.text_content()


def enter_share(
    debug: "DebugLink", share: str, is_first: bool = True
) -> "LayoutContent":
    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)

        assert layout.main_component() == "MnemonicKeyboard"
        for word in share.split(" "):
            layout = enter_word(debug, word, is_slip39=True)

        return layout
    elif debug.model == "R":
        assert "RECOVER WALLET" in debug.wait_layout().title()
        layout = debug.press_right(wait=True)
        if is_first:
            # Word entering info
            debug.press_right()
            layout = debug.press_right(wait=True)
        assert "MnemonicKeyboard" in layout.all_components()

        for word in share.split(" "):
            layout = enter_word(debug, word, is_slip39=True)

        return layout
    else:
        raise ValueError("Unknown model")


def enter_shares(debug: "DebugLink", shares: list[str]) -> None:
    layout = debug.read_layout()
    expected_text = "Enter any share"
    for index, share in enumerate(shares):
        assert expected_text in layout.text_content()
        layout = enter_share(debug, share, is_first=index == 0)
        expected_text = f"{index + 1} of {len(shares)} shares entered"

    assert "Wallet recovered successfully" in layout.text_content()


def enter_seed(debug: "DebugLink", seed_words: list[str]) -> None:
    assert "Enter" in debug.read_layout().text_content()
    if debug.model == "T":
        layout = debug.click(buttons.OK, wait=True)
        assert layout.main_component() == "MnemonicKeyboard"
    elif debug.model == "R":
        layout = debug.press_right(wait=True)
        assert "RECOVER WALLET" in layout.title()
        debug.press_right()

        layout = debug.press_right(wait=True)
        assert "MnemonicKeyboard" in layout.all_components()

    for word in seed_words:
        layout = enter_word(debug, word, is_slip39=False)

    assert "Wallet recovered successfully" in layout.text_content()  # type: ignore


def finalize(debug: "DebugLink") -> None:
    layout = go_next(debug, wait=True)
    assert layout is not None
    assert layout.main_component() == "Homescreen"
