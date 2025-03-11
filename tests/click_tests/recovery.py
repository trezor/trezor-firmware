from typing import TYPE_CHECKING

from trezorlib.debuglink import LayoutType

from .. import translations as TR
from .common import go_next

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


DELETE_BTN_TEXTS = ("inputs__delete", "inputs__previous")


def enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
        typed_word = word[:4]
        for coords in debug.button_actions.type_word(typed_word, is_slip39=is_slip39):
            debug.click(coords)
        if debug.layout_type is LayoutType.Delizia and not is_slip39 and len(word) > 4:
            # T3T1 (delizia) BIP39 keyboard allows to "confirm" only if the word is fully written, you need to click the word to auto-complete
            debug.click(debug.screen_buttons.mnemonic_confirm())
        debug.click(debug.screen_buttons.mnemonic_confirm())
        return debug.read_layout()
    elif debug.layout_type is LayoutType.Caesar:
        letter_index = 0
        layout = debug.read_layout()

        # Letter choices
        while layout.find_values_by_key("letter_choices"):
            letter = word[letter_index]
            while not layout.get_middle_choice() == letter:
                debug.press_right()
                layout = debug.read_layout()

            debug.press_middle()
            layout = debug.read_layout()
            letter_index += 1

        # Word choices
        while not layout.get_middle_choice() == word:
            debug.press_right()
            layout = debug.read_layout()

        debug.press_middle()
        return debug.read_layout()
    else:
        raise ValueError("Unknown model")


def confirm_recovery(debug: "DebugLink", title: str = "recovery__title") -> None:
    layout = debug.read_layout()
    assert TR.translate(title) == layout.title()
    if debug.layout_type is LayoutType.Bolt:
        debug.click(debug.screen_buttons.ok())
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
    elif debug.layout_type is LayoutType.Caesar:
        for _ in range(layout.page_count()):
            debug.press_right()


def cancel_select_number_of_words(
    debug: "DebugLink",
    unlock_repeated_backup=False,
) -> None:
    if debug.layout_type is LayoutType.Bolt:
        assert debug.read_layout().text_content() == TR.recovery__num_of_words
        # click the button from ValuePad
        if unlock_repeated_backup:
            coords = debug.screen_buttons.word_count_repeated_cancel()
        else:
            coords = debug.screen_buttons.word_count_all_cancel()
        debug.click(coords)
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        layout = debug.read_layout()
        assert layout.title() == TR.word_count__title
        # navigate to the number and confirm it
        debug.press_left()
    elif debug.layout_type is LayoutType.Delizia:
        # click the button from ValuePad
        if unlock_repeated_backup:
            coords = debug.screen_buttons.word_count_repeated_cancel()
        else:
            coords = debug.screen_buttons.word_count_all_cancel()
        debug.click(coords)
    else:
        raise ValueError("Unknown model")


def select_number_of_words(
    debug: "DebugLink",
    num_of_words: int = 20,
    unlock_repeated_backup=False,
) -> None:
    layout = debug.read_layout()
    assert TR.recovery__num_of_words in layout.text_content()

    def select_bolt() -> "LayoutContent":
        # click the button from ValuePad
        if unlock_repeated_backup:
            coords = debug.screen_buttons.word_count_repeated_word(num_of_words)
        else:
            coords = debug.screen_buttons.word_count_all_word(num_of_words)

        debug.click(coords)
        return debug.read_layout()

    def select_caesar() -> "LayoutContent":
        # navigate to the number and confirm it
        word_options = (20, 33) if unlock_repeated_backup else (12, 18, 20, 24, 33)
        index = word_options.index(num_of_words)
        for _ in range(index):
            debug.press_right()
        debug.press_middle()
        return debug.read_layout()

    def select_delizia() -> "LayoutContent":
        # click the button from ValuePad
        if unlock_repeated_backup:
            coords = debug.screen_buttons.word_count_repeated_word(num_of_words)
        else:
            coords = debug.screen_buttons.word_count_all_word(num_of_words)
        debug.click(coords)
        return debug.read_layout()

    if debug.layout_type is LayoutType.Bolt:
        layout = select_bolt()
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        layout = debug.read_layout()
        assert layout.title() == TR.word_count__title
        layout = select_caesar()
    elif debug.layout_type is LayoutType.Delizia:
        layout = select_delizia()
    else:
        raise ValueError("Unknown model")

    if unlock_repeated_backup:
        if debug.layout_type is LayoutType.Caesar:
            assert TR.recovery__enter_backup in layout.text_content()
        else:
            assert (
                TR.recovery__only_first_n_letters in layout.text_content()
                or TR.recovery__enter_each_word in layout.text_content()
            )
    elif num_of_words in (20, 33):
        assert (
            TR.recovery__enter_backup in layout.text_content()
            or TR.recovery__enter_any_share in layout.text_content()
            or TR.recovery__only_first_n_letters in layout.text_content()
            or TR.recovery__enter_each_word in layout.text_content()
        )
    else:  # BIP-39
        assert (
            TR.recovery__enter_backup in layout.text_content()
            or TR.recovery__only_first_n_letters in layout.text_content()
            or TR.recovery__enter_each_word in layout.text_content()
        )


def enter_share(
    debug: "DebugLink",
    share: str,
    is_first: bool = True,
    before_title: str = "recovery__title_recover",
) -> "LayoutContent":
    if debug.layout_type is LayoutType.Caesar:
        assert TR.translate(before_title) in debug.read_layout().title()
        layout = debug.read_layout()
        for _ in range(layout.page_count()):
            debug.press_right()
            layout = debug.read_layout()
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        layout = debug.read_layout()
    else:
        assert TR.translate(before_title) in debug.read_layout().title()
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()

    assert "MnemonicKeyboard" in layout.all_components()

    for word in share.split(" "):
        layout = enter_word(debug, word, is_slip39=True)

    return layout


def enter_shares(
    debug: "DebugLink",
    shares: list[str],
    enter_share_before_title: str = "recovery__title_recover",
    text: str = "recovery__enter_any_share",
    after_layout_text: str = "recovery__wallet_recovered",
) -> None:
    assert (
        TR.recovery__enter_backup in debug.read_layout().text_content()
        or TR.recovery__enter_any_share in debug.read_layout().text_content()
        or TR.recovery__only_first_n_letters in debug.read_layout().text_content()
        or TR.recovery__enter_each_word in debug.read_layout().text_content()
        or TR.translate(text) in debug.read_layout().text_content()
    )
    for index, share in enumerate(shares):
        enter_share(
            debug, share, is_first=index == 0, before_title=enter_share_before_title
        )
        if index < len(shares) - 1:
            # FIXME: when ui-t3t1 done for shamir, we want to check the template below
            assert TR.translate(enter_share_before_title) in debug.read_layout().title()
            # TR.assert_in(
            #     debug.read_layout().text_content(),
            #     "recovery__x_of_y_entered_template",
            #     template=(index + 1, len(shares)),
            # )

    assert TR.translate(after_layout_text) in debug.read_layout().text_content()


def enter_seed(
    debug: "DebugLink",
    seed_words: list[str],
    is_slip39=False,
    prepare_layout_text: str = "recovery__enter_backup",
    after_layout_text: str = "recovery__wallet_recovered",
) -> None:
    prepare_enter_seed(debug, prepare_layout_text)

    for word in seed_words:
        enter_word(debug, word, is_slip39=is_slip39)

    assert TR.translate(after_layout_text) in debug.read_layout().text_content()


def enter_seed_previous_correct(
    debug: "DebugLink", seed_words: list[str], bad_indexes: dict[int, str]
) -> None:
    prepare_enter_seed(debug)

    DELETE_BTNS = [TR.translate(btn) for btn in DELETE_BTN_TEXTS]

    i = 0
    go_back = False
    bad_word = ""
    while True:
        assert i >= 0

        if i >= len(seed_words):
            break

        if go_back:
            go_back = False
            if debug.layout_type is LayoutType.Bolt:
                debug.swipe_right()
                for _ in range(len(bad_word)):
                    debug.click(debug.screen_buttons.mnemonic_erase())
            elif debug.layout_type is LayoutType.Caesar:
                layout = debug.read_layout()

                while layout.get_middle_choice() not in DELETE_BTNS:
                    debug.press_right()
                    layout = debug.read_layout()
                debug.press_middle()
                layout = debug.read_layout()

                for _ in range(len(bad_word)):
                    while layout.get_middle_choice() not in DELETE_BTNS:
                        debug.press_left()
                        layout = debug.read_layout()
                    debug.press_middle()
                    layout = debug.read_layout()
            elif debug.layout_type is LayoutType.Delizia:
                debug.click(debug.screen_buttons.mnemonic_erase())  # Top-left
                for _ in range(len(bad_word)):
                    debug.click(debug.screen_buttons.mnemonic_erase())
            continue

        if i in bad_indexes:
            word = bad_indexes.pop(i)
            bad_word = word
            go_back = True
        else:
            word = seed_words[i]
            i += 1
        layout = enter_word(debug, word, is_slip39=False)

    # TR.assert_in(debug.read_layout().text_content(), "recovery__wallet_recovered")


def prepare_enter_seed(
    debug: "DebugLink", layout_text: str = "recovery__enter_backup"
) -> None:
    assert (
        TR.recovery__enter_backup in debug.read_layout().text_content()
        or TR.recovery__only_first_n_letters in debug.read_layout().text_content()
        or TR.recovery__enter_each_word in debug.read_layout().text_content()
        or TR.translate(layout_text) in debug.read_layout().text_content()
    )
    if debug.layout_type is LayoutType.Bolt:
        debug.click(debug.screen_buttons.ok())
    elif debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.swipe_up()
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_right()
        debug.press_right()
        debug.press_right()
        layout = debug.read_layout()
        assert "MnemonicKeyboard" in layout.all_components()


def finalize(debug: "DebugLink") -> None:
    layout = go_next(debug)
    assert layout is not None
    assert layout.main_component() == "Homescreen"


def cancel_recovery(debug: "DebugLink", recovery_type: str = "dry_run") -> None:
    title = TR.translate(f"recovery__title_{recovery_type}")
    cancel_title = TR.translate(f"recovery__title_cancel_{recovery_type}")

    layout = debug.read_layout()
    assert title in layout.title()

    if debug.layout_type is LayoutType.Bolt:
        debug.click(debug.screen_buttons.cancel())
        layout = debug.read_layout()
        assert cancel_title in layout.title()
        debug.click(debug.screen_buttons.ok())
    elif debug.layout_type is LayoutType.Caesar:
        debug.press_left()
        layout = debug.read_layout()
        assert cancel_title in layout.title()
        for _ in range(layout.page_count()):
            debug.press_right()
    elif debug.layout_type is LayoutType.Delizia:
        # go to menu
        debug.click(debug.screen_buttons.menu())
        layout = debug.read_layout()
        assert (
            TR.translate(f"recovery__cancel_{recovery_type}") in layout.text_content()
        )
        debug.click(debug.screen_buttons.vertical_menu_items()[0])
    else:
        raise ValueError("Unknown model")

    layout = debug.read_layout()
    assert layout.main_component() == "Homescreen"
