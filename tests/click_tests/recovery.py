from typing import TYPE_CHECKING

from trezorlib import models

from .. import buttons
from .. import translations as TR
from .common import get_possible_btn_texts, go_next

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


DELETE_BTN_TEXTS = get_possible_btn_texts("inputs__delete") + get_possible_btn_texts(
    "inputs__previous"
)


def enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    if debug.model in (models.T2T1, models.T3T1):
        typed_word = word[:4]
        for coords in buttons.type_word(typed_word, is_slip39=is_slip39):
            debug.click(coords)
        if debug.model is models.T3T1 and not is_slip39 and len(word) > 4:
            # T3T1 (mercury) BIP39 keyboard allows to "confirm" only if the word is fully written, you need to click the word to auto-complete
            debug.click(buttons.CONFIRM_WORD, wait=True)
        return debug.click(buttons.CONFIRM_WORD, wait=True)
    elif debug.model in (models.T2B1,):
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


def confirm_recovery(debug: "DebugLink", title: str = "recovery__title") -> None:
    layout = debug.wait_layout()
    TR.assert_equals(layout.title(), title)
    if debug.model in (models.T2T1,):
        debug.click(buttons.OK, wait=True)
    elif debug.model in (models.T3T1,):
        debug.swipe_up(wait=True)
    elif debug.model in (models.T2B1,):
        debug.press_right(wait=True)


def select_number_of_words(
    debug: "DebugLink",
    num_of_words: int = 20,
    wait: bool = True,
    unlock_repeated_backup=False,
) -> None:
    if wait:
        debug.wait_layout()
    if debug.model in (models.T2T1,):
        TR.assert_equals(debug.read_layout().text_content(), "recovery__num_of_words")
        # click the number
        word_option_offset = 6
        word_options = (12, 18, 20, 24, 33)
        index = word_option_offset + word_options.index(
            num_of_words
        )  # raises if num of words is invalid
        coords = buttons.grid34(index % 3, index // 3)
        layout = debug.click(coords, wait=True)
    elif debug.model in (models.T2B1,):
        layout = debug.press_right(wait=True)
        TR.assert_equals(layout.title(), "word_count__title")

        # navigate to the number and confirm it
        word_options = (12, 18, 20, 24, 33)
        index = word_options.index(num_of_words)
        for _ in range(index):
            debug.press_right(wait=True)
        layout = debug.press_middle(wait=True)
    elif debug.model in (models.T3T1,):
        if num_of_words == 12:
            coords = buttons.grid34(0, 1)
        elif num_of_words == 18:
            coords = buttons.grid34(2, 1)
        elif num_of_words == 20:
            coords = buttons.grid34(0, 2)
        elif num_of_words == 24:
            coords = buttons.grid34(2, 2)
        elif num_of_words == 33:
            coords = buttons.grid34(1, 3)
        else:
            raise ValueError("Invalid num_of_words")
        layout = debug.click(coords, wait=True)
    else:
        raise ValueError("Unknown model")

    if unlock_repeated_backup:
        if debug.model in (models.T2B1,):
            TR.assert_in(layout.text_content(), "recovery__enter_backup")
        else:
            TR.assert_in_multiple(
                layout.text_content(),
                ["recovery__only_first_n_letters", "recovery__enter_each_word"],
            )
    elif num_of_words in (20, 33):
        TR.assert_in_multiple(
            layout.text_content(),
            [
                "recovery__enter_backup",
                "recovery__enter_any_share",
                "recovery__only_first_n_letters",
                "recovery__enter_each_word",
            ],
        )
    else:  # BIP-39
        TR.assert_in_multiple(
            layout.text_content(),
            [
                "recovery__enter_backup",
                "recovery__only_first_n_letters",
                "recovery__enter_each_word",
            ],
        )


def enter_share(
    debug: "DebugLink",
    share: str,
    is_first: bool = True,
    before_title: str = "recovery__title_recover",
) -> "LayoutContent":
    if debug.model in (models.T2B1,):
        TR.assert_in(debug.read_layout().title(), before_title)
        layout = debug.wait_layout()
        for _ in range(layout.page_count()):
            layout = debug.press_right(wait=True)
    elif debug.model in (models.T3T1,):
        layout = debug.swipe_up(wait=True)
    else:
        TR.assert_in(debug.read_layout().title(), before_title)
        layout = debug.click(buttons.OK, wait=True)

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
    TR.assert_in_multiple(
        debug.read_layout().text_content(),
        [
            "recovery__enter_backup",
            "recovery__enter_any_share",
            "recovery__only_first_n_letters",
            "recovery__enter_each_word",
            text,
        ],
    )
    for index, share in enumerate(shares):
        enter_share(
            debug, share, is_first=index == 0, before_title=enter_share_before_title
        )
        if index < len(shares) - 1:
            # FIXME: when ui-t3t1 done for shamir, we want to check the template below
            TR.assert_in(debug.read_layout().title(), enter_share_before_title)
            # TR.assert_in(
            #     debug.read_layout().text_content(),
            #     "recovery__x_of_y_entered_template",
            #     template=(index + 1, len(shares)),
            # )

    TR.assert_in(debug.read_layout().text_content(), after_layout_text)


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

    TR.assert_in(debug.read_layout().text_content(), after_layout_text)


def enter_seed_previous_correct(
    debug: "DebugLink", seed_words: list[str], bad_indexes: dict[int, str]
) -> None:
    prepare_enter_seed(debug)

    i = 0
    go_back = False
    bad_word = ""
    while True:
        assert i >= 0

        if i >= len(seed_words):
            break

        if go_back:
            go_back = False
            if debug.model in (models.T2T1, models.T3T1):
                debug.swipe_right(wait=True)
                for _ in range(len(bad_word)):
                    debug.click(buttons.RECOVERY_DELETE, wait=True)
            elif debug.model in (models.T2B1,):
                layout = debug.read_layout()

                while layout.get_middle_choice() not in DELETE_BTN_TEXTS:
                    layout = debug.press_right(wait=True)
                layout = debug.press_middle(wait=True)

                for _ in range(len(bad_word)):
                    while layout.get_middle_choice() not in DELETE_BTN_TEXTS:
                        layout = debug.press_left(wait=True)
                    layout = debug.press_middle(wait=True)
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
    TR.assert_in_multiple(
        debug.read_layout().text_content(),
        [
            "recovery__enter_backup",
            "recovery__only_first_n_letters",
            "recovery__enter_each_word",
            layout_text,
        ],
    )
    if debug.model in (models.T2T1,):
        debug.click(buttons.OK, wait=True)
    elif debug.model in (models.T3T1,):
        debug.swipe_up(wait=True)
        debug.swipe_up(wait=True)
    elif debug.model in (models.T2B1,):
        debug.press_right(wait=True)
        debug.press_right()
        layout = debug.press_right(wait=True)
        assert "MnemonicKeyboard" in layout.all_components()


def finalize(debug: "DebugLink") -> None:
    layout = go_next(debug, wait=True)
    assert layout is not None
    assert layout.main_component() == "Homescreen"
