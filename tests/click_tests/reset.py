import re
from typing import TYPE_CHECKING

from shamir_mnemonic import shamir  # type: ignore

from trezorlib import messages, models

from .. import buttons
from .. import translations as TR

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink


def confirm_new_wallet(debug: "DebugLink") -> None:
    TR.assert_equals_multiple(
        debug.read_layout().title(),
        ["reset__title_create_wallet", "reset__title_create_wallet_shamir"],
    )
    if debug.model in (models.T2T1, models.T3T1):
        debug.click(buttons.OK)
    elif debug.model in (models.T2B1,):
        debug.press_right()
        debug.press_right()


def confirm_read(debug: "DebugLink", middle_r: bool = False) -> None:
    if debug.model in (models.T2T1, models.T3T1):
        debug.click(buttons.OK)
    elif debug.model in (models.T2B1,):
        page_count = debug.read_layout().page_count()
        if page_count > 1:
            for _ in range(page_count - 1):
                debug.press_right()
        if middle_r:
            debug.press_middle()
        else:
            debug.press_right()


def set_selection(debug: "DebugLink", button: tuple[int, int], diff: int) -> None:
    if debug.model in (models.T2T1, models.T3T1):
        assert "NumberInputDialog" in debug.read_layout().all_components()
        for _ in range(diff):
            debug.click(button)
        debug.click(buttons.OK)
    elif debug.model in (models.T2B1,):
        layout = debug.read_layout()
        if layout.title() in TR.translate(
            "reset__title_number_of_shares"
        ) + TR.translate("words__title_threshold"):
            # Special info screens
            layout = debug.press_right()
        assert "NumberInput" in layout.all_components()
        if button == buttons.RESET_MINUS:
            for _ in range(diff):
                debug.press_left()
        else:
            for _ in range(diff):
                debug.press_right()
        debug.press_middle()


def read_words(
    debug: "DebugLink", backup_type: messages.BackupType, do_htc: bool = True
) -> list[str]:
    words: list[str] = []

    if debug.model in (models.T2B1,):
        debug.press_right()

    # Swiping through all the pages and loading the words
    layout = debug.read_layout()
    for _ in range(layout.page_count() - 1):
        words.extend(layout.seed_words())
        layout = debug.swipe_up()
        assert layout is not None
    if debug.model in (models.T2T1, models.T3T1):
        words.extend(layout.seed_words())

    # There is hold-to-confirm button
    if do_htc:
        if debug.model in (models.T2T1, models.T3T1):
            debug.click(buttons.OK, hold_ms=1500)
        elif debug.model in (models.T2B1,):
            debug.press_right(hold_ms=1200)
    else:
        # It would take a very long time to test 16-of-16 with doing 1500 ms HTC after
        # each word set
        debug.press_yes()

    return words


def confirm_words(debug: "DebugLink", words: list[str]) -> None:
    layout = debug.read_layout()
    if debug.model in (models.T2T1, models.T3T1):
        TR.assert_template(layout.text_content(), "reset__select_word_x_of_y_template")
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
    elif debug.model in (models.T2B1,):
        TR.assert_in(layout.text_content(), "reset__select_correct_word")
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
