from typing import TYPE_CHECKING

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    typed_word = word[:4]
    for coords in buttons.type_word(typed_word, is_slip39=is_slip39):
        debug.click(coords)

    return debug.click(buttons.CONFIRM_WORD, wait=True)


def confirm_recovery(debug: "DebugLink") -> None:
    if not debug.legacy_ui and not debug.legacy_debug:
        layout = debug.wait_layout()
        assert layout.title().startswith("WALLET RECOVERY")
    debug.click(buttons.OK, wait=True)


def select_number_of_words(debug: "DebugLink", num_of_words: int = 20) -> None:
    # select number of words
    if not debug.legacy_ui and not debug.legacy_debug:
        assert "number of words" in debug.read_layout().text_content()
    layout = debug.click(buttons.OK, wait=True)
    if debug.legacy_ui:
        assert layout.json_str == "WordSelector"
    elif debug.version < (2, 6, 1):
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

    if not debug.legacy_ui and not debug.legacy_debug:
        if num_of_words in (20, 33):
            assert "Enter any share" in layout.text_content()
        else:
            assert "Enter recovery seed" in layout.text_content()


def enter_share(debug: "DebugLink", share: str) -> "LayoutContent":
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
    assert "Enter" in debug.read_layout().text_content()

    layout = debug.click(buttons.OK, wait=True)
    assert layout.main_component() == "MnemonicKeyboard"

    for word in seed_words:
        layout = enter_word(debug, word, is_slip39=False)

    assert "You have finished recovering your wallet" in layout.text_content()


def finalize(debug: "DebugLink") -> None:
    layout = debug.click(buttons.OK, wait=True)
    assert layout.main_component() == "Homescreen"
