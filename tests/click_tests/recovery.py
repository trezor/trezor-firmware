from typing import TYPE_CHECKING

from trezorlib.debuglink import LayoutType

from .. import buttons
from .. import translations as TR
from .common import go_next

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


DELETE_BTN_TEXTS = ("inputs__delete", "inputs__previous")


def enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    if debug.layout_type in (LayoutType.TT, LayoutType.Mercury):
        typed_word = word[:4]
        for coords in buttons.type_word(typed_word, is_slip39=is_slip39):
            debug.click(coords)
        if debug.layout_type is LayoutType.Mercury and not is_slip39 and len(word) > 4:
            # T3T1 (mercury) BIP39 keyboard allows to "confirm" only if the word is fully written, you need to click the word to auto-complete
            debug.click(buttons.CONFIRM_WORD)
        return debug.click(buttons.CONFIRM_WORD)
    elif debug.layout_type is LayoutType.TR:
        letter_index = 0
        layout = debug.read_layout()

        # Letter choices
        while layout.find_values_by_key("letter_choices"):
            letter = word[letter_index]
            while not layout.get_middle_choice() == letter:
                layout = debug.press_right()

            layout = debug.press_middle()
            letter_index += 1

        # Word choices
        while not layout.get_middle_choice() == word:
            layout = debug.press_right()

        return debug.press_middle()
    else:
        raise ValueError("Unknown model")


def confirm_recovery(debug: "DebugLink", title: str = "recovery__title") -> None:
    layout = debug.read_layout()
    assert TR.translate(title) == layout.title()
    if debug.layout_type is LayoutType.TT:
        debug.click(buttons.OK)
    elif debug.layout_type is LayoutType.Mercury:
        debug.swipe_up()
    elif debug.layout_type is LayoutType.TR:
        for _ in range(layout.page_count()):
            debug.press_right()


def select_number_of_words(
    debug: "DebugLink",
    num_of_words: int = 20,
    unlock_repeated_backup=False,
) -> None:
    def select_tt() -> "LayoutContent":
        # click the button from ValuePad
        if unlock_repeated_backup:
            coords_map = {20: buttons.grid34(0, 2), 33: buttons.grid34(1, 2)}
        else:
            coords_map = {
                12: buttons.grid34(0, 2),
                18: buttons.grid34(1, 2),
                20: buttons.grid34(2, 2),
                24: buttons.grid34(0, 3),
                33: buttons.grid34(1, 3),
            }
        coords = coords_map.get(num_of_words)
        if coords is None:
            raise ValueError("Invalid num_of_words")
        return debug.click(coords)

    def select_tr() -> "LayoutContent":
        # navigate to the number and confirm it
        word_options = (20, 33) if unlock_repeated_backup else (12, 18, 20, 24, 33)
        index = word_options.index(num_of_words)
        for _ in range(index):
            debug.press_right()
        return debug.press_middle()

    def select_mercury() -> "LayoutContent":
        # click the button from ValuePad
        if unlock_repeated_backup:
            coords_map = {20: buttons.MERCURY_NO, 33: buttons.MERCURY_YES}
        else:
            coords_map = {
                12: buttons.grid34(0, 1),
                18: buttons.grid34(2, 1),
                20: buttons.grid34(0, 2),
                24: buttons.grid34(2, 2),
                33: buttons.grid34(1, 3),
            }
        coords = coords_map.get(num_of_words)
        if coords is None:
            raise ValueError("Invalid num_of_words")
        return debug.click(coords)

    if debug.layout_type is LayoutType.TT:
        assert debug.read_layout().text_content() == TR.recovery__num_of_words
        layout = select_tt()
    elif debug.layout_type is LayoutType.TR:
        layout = debug.press_right()
        assert layout.title() == TR.word_count__title
        layout = select_tr()
    elif debug.layout_type is LayoutType.Mercury:
        layout = select_mercury()
    else:
        raise ValueError("Unknown model")

    if unlock_repeated_backup:
        if debug.layout_type is LayoutType.TR:
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
    if debug.layout_type is LayoutType.TR:
        assert TR.translate(before_title) in debug.read_layout().title()
        layout = debug.read_layout()
        for _ in range(layout.page_count()):
            layout = debug.press_right()
    elif debug.layout_type is LayoutType.Mercury:
        layout = debug.swipe_up()
    else:
        assert TR.translate(before_title) in debug.read_layout().title()
        layout = debug.click(buttons.OK)

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
            if debug.layout_type is LayoutType.TT:
                debug.swipe_right()
                for _ in range(len(bad_word)):
                    debug.click(buttons.RECOVERY_DELETE)
            elif debug.layout_type is LayoutType.TR:
                layout = debug.read_layout()

                while layout.get_middle_choice() not in DELETE_BTNS:
                    layout = debug.press_right()
                layout = debug.press_middle()

                for _ in range(len(bad_word)):
                    while layout.get_middle_choice() not in DELETE_BTNS:
                        layout = debug.press_left()
                    layout = debug.press_middle()
            elif debug.layout_type is LayoutType.Mercury:
                debug.click(buttons.RECOVERY_DELETE)  # Top-left
                for _ in range(len(bad_word)):
                    debug.click(buttons.RECOVERY_DELETE)
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
    if debug.layout_type is LayoutType.TT:
        debug.click(buttons.OK)
    elif debug.layout_type is LayoutType.Mercury:
        debug.swipe_up()
        debug.swipe_up()
    elif debug.layout_type is LayoutType.TR:
        debug.press_right()
        debug.press_right()
        layout = debug.press_right()
        assert "MnemonicKeyboard" in layout.all_components()


def finalize(debug: "DebugLink") -> None:
    layout = go_next(debug)
    assert layout is not None
    assert layout.main_component() == "Homescreen"
