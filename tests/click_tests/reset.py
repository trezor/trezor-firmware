import re
from typing import TYPE_CHECKING

from shamir_mnemonic import shamir  # type: ignore

from trezorlib.debuglink import LayoutType

from .. import buttons
from .. import translations as TR

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink


def confirm_new_wallet(debug: "DebugLink") -> None:
    assert debug.read_layout().title() == TR.reset__title_create_wallet
    if debug.layout_type is LayoutType.Bolt:
        debug.click(buttons.OK)
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.click(buttons.TAP_TO_CONFIRM)
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        debug.press_right()
    assert (
        TR.backup__new_wallet_successfully_created in debug.read_layout().text_content()
        or TR.backup__new_wallet_created in debug.read_layout().text_content()
    )
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()


def confirm_read(debug: "DebugLink", middle_r: bool = False) -> None:
    if debug.layout_type is LayoutType.Bolt:
        debug.click(buttons.OK)
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
    elif debug.layout_type is LayoutType.Caesar:
        page_count = debug.read_layout().page_count()
        if page_count > 1:
            for _ in range(page_count - 1):
                debug.press_right()
        if middle_r:
            debug.press_middle()
        else:
            debug.press_right()


def cancel_backup(
    debug: "DebugLink", middle_r: bool = False, confirm: bool = False
) -> None:
    if debug.layout_type is LayoutType.Bolt:
        debug.click(buttons.CANCEL)
        debug.click(buttons.CANCEL)
    elif debug.layout_type is LayoutType.Delizia:
        debug.click(buttons.CORNER_BUTTON)
        debug.click(buttons.VERTICAL_MENU[0])
        if confirm:
            debug.swipe_up()
            debug.click(buttons.TAP_TO_CONFIRM)
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_left()
        debug.press_left()


def set_selection(debug: "DebugLink", button: tuple[int, int], diff: int) -> None:
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        assert "NumberInputDialog" in debug.read_layout().all_components()
        for _ in range(diff):
            debug.click(button)
        if debug.layout_type is LayoutType.Bolt:
            debug.click(buttons.OK)
        else:
            debug.swipe_up()
    elif debug.layout_type is LayoutType.Caesar:
        layout = debug.read_layout()
        if (
            layout.title()
            in TR.reset__title_number_of_shares + TR.words__title_threshold
        ):
            # Special info screens
            layout = debug.press_right()
        assert "NumberInput" in layout.all_components()
        if button == buttons.reset_minus(debug.model.internal_name):
            for _ in range(diff):
                debug.press_left()
        else:
            for _ in range(diff):
                debug.press_right()
        debug.press_middle()


def read_words(debug: "DebugLink", do_htc: bool = True) -> list[str]:
    words: list[str] = []

    if debug.layout_type is LayoutType.Caesar:
        debug.press_right()
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()

    # Swiping through all the pages and loading the words
    layout = debug.read_layout()
    for _ in range(layout.page_count() - 1):
        words.extend(layout.seed_words())
        layout = debug.swipe_up()
        assert layout is not None
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        words.extend(layout.seed_words())

    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()

    # There is hold-to-confirm button
    if do_htc:
        if debug.layout_type is LayoutType.Bolt:
            debug.click(buttons.OK, hold_ms=1500)
        elif debug.layout_type is LayoutType.Delizia:
            debug.click(buttons.TAP_TO_CONFIRM, hold_ms=1500)
        elif debug.layout_type is LayoutType.Caesar:
            debug.press_right(hold_ms=1200)
    else:
        # It would take a very long time to test 16-of-16 with doing 1500 ms HTC after
        # each word set
        debug.press_yes()

    return words


def confirm_words(debug: "DebugLink", words: list[str]) -> None:
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()

    layout = debug.read_layout()
    if debug.layout_type is LayoutType.Bolt:
        assert TR.regexp("reset__select_word_x_of_y_template").match(
            layout.text_content()
        )
        for _ in range(3):
            # "Select word 3 of 20"
            #              ^
            word_pos_match = re.search(r"\d+", debug.read_layout().text_content())
            assert word_pos_match is not None
            word_pos = int(word_pos_match.group(0))
            # Unifying both the buttons and words to lowercase
            btn_texts = [
                text.lower() for text in layout.tt_check_seed_button_contents()
            ]
            wanted_word = words[word_pos - 1].lower()
            button_pos = btn_texts.index(wanted_word)
            layout = debug.click(buttons.RESET_WORD_CHECK[button_pos])
    elif debug.layout_type is LayoutType.Delizia:
        assert TR.regexp("reset__select_word_x_of_y_template").match(layout.subtitle())
        for _ in range(3):
            # "Select word 3 of 20"
            #              ^
            word_pos_match = re.search(r"\d+", debug.read_layout().subtitle())
            assert word_pos_match is not None
            word_pos = int(word_pos_match.group(0))
            # Unifying both the buttons and words to lowercase
            btn_texts = [
                text.lower() for text in layout.tt_check_seed_button_contents()
            ]
            wanted_word = words[word_pos - 1].lower()
            button_pos = btn_texts.index(wanted_word)
            layout = debug.click(buttons.VERTICAL_MENU[button_pos])
    elif debug.layout_type is LayoutType.Caesar:
        assert TR.reset__select_correct_word in layout.text_content()
        layout = debug.press_right()
        for _ in range(3):
            # "SELECT 2ND WORD"
            #         ^
            word_pos_match = re.search(r"\d+", layout.title())
            assert word_pos_match is not None
            word_pos = int(word_pos_match.group(0))

            wanted_word = words[word_pos - 1].lower()

            while not layout.get_middle_choice() == wanted_word:
                layout = debug.press_right()

            layout = debug.press_middle()


def validate_mnemonics(mnemonics: list[str], expected_ems: bytes) -> None:
    # We expect these combinations to recreate the secret properly
    # In case of click tests the mnemonics are always XofX so no need for combinations
    groups = shamir.decode_mnemonics(mnemonics)
    ems = shamir.recover_ems(groups)
    assert expected_ems == ems.ciphertext
