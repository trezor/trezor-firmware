from typing import TYPE_CHECKING

from shamir_mnemonic import shamir  # type: ignore

from trezorlib import messages

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink


def confirm_new_wallet(debug: "DebugLink") -> None:
    assert debug.wait_layout().title().startswith("WALLET CREATION")
    debug.click(buttons.OK, wait=True)


def confirm_read(debug: "DebugLink", title: str, hold: bool = False) -> None:
    layout = debug.read_layout()
    if title == "Caution":
        # TODO: could look into button texts
        assert "OK, I UNDERSTAND" in layout.json_str
    elif title == "Success":
        # TODO: improve this
        assert any(
            text in layout.text_content()
            for text in (
                "success",
                "finished",
                "done",
                "has been created",
                "Keep it safe",
            )
        )
    elif title == "Checklist":
        assert "number of shares" in layout.text_content().lower()
    else:
        assert title.upper() in layout.title()

    debug.click(buttons.OK, wait=True)


def set_selection(debug: "DebugLink", button: tuple[int, int], diff: int) -> None:
    assert "NumberInputDialog" in debug.read_layout().all_components()
    for _ in range(diff):
        debug.click(button)
    debug.click(buttons.OK, wait=True)


def read_words(
    debug: "DebugLink", backup_type: messages.BackupType, do_htc: bool = True
) -> list[str]:
    words: list[str] = []
    layout = debug.read_layout()

    if backup_type == messages.BackupType.Slip39_Advanced:
        assert layout.title().startswith("GROUP")
    elif backup_type == messages.BackupType.Slip39_Basic:
        assert layout.title().startswith("RECOVERY SHARE #")
    else:
        assert layout.title() == "RECOVERY SEED"

    # Swiping through all the page and loading the words
    for _ in range(layout.page_count() - 1):
        words.extend(layout.seed_words())
        layout = debug.input(swipe=messages.DebugSwipeDirection.UP, wait=True)
        assert layout is not None
    words.extend(layout.seed_words())

    # There is hold-to-confirm button
    if do_htc:
        debug.click_hold(buttons.OK, hold_ms=1500)
    else:
        # It would take a very long time to test 16-of-16 with doing 1500 ms HTC after
        # each word set
        debug.press_yes()

    return words


def confirm_words(debug: "DebugLink", words: list[str]) -> None:
    layout = debug.wait_layout()
    assert "Select word" in layout.text_content()
    for _ in range(3):
        # "Select word 3 of 20"
        #              ^
        word_pos = int(layout.text_content().split()[2])
        # Unifying both the buttons and words to lowercase
        btn_texts = [text.lower() for text in layout.button_contents()]
        wanted_word = words[word_pos - 1].lower()
        button_pos = btn_texts.index(wanted_word)
        layout = debug.click(buttons.RESET_WORD_CHECK[button_pos], wait=True)


def validate_mnemonics(mnemonics: list[str], expected_ems: bytes) -> None:
    # We expect these combinations to recreate the secret properly
    # In case of click tests the mnemonics are always XofX so no need for combinations
    groups = shamir.decode_mnemonics(mnemonics)
    ems = shamir.recover_ems(groups)
    assert expected_ems == ems.ciphertext
