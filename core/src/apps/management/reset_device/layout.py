from micropython import const
from typing import Sequence

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import show_success
from trezor.ui.layouts.reset import (  # noqa: F401
    show_share_words,
    slip39_advanced_prompt_group_threshold,
    slip39_advanced_prompt_number_of_groups,
    slip39_prompt_number_of_shares,
    slip39_prompt_threshold,
    slip39_show_checklist,
)

_NUM_OF_CHOICES = const(3)


async def show_internal_entropy(entropy: bytes) -> None:
    from trezor.ui.layouts import confirm_blob

    await confirm_blob(
        "entropy",
        TR.entropy__title,
        entropy,
        br_code=ButtonRequestType.ResetDevice,
    )


async def _confirm_word(
    share_index: int | None,
    share_words: Sequence[str],
    offset: int,
    count: int,
    group_index: int | None = None,
) -> bool:
    from trezor.crypto import random
    from trezor.ui.layouts.reset import select_word

    # remove duplicates
    non_duplicates = list(set(share_words))
    # shuffle list
    random.shuffle(non_duplicates)
    # take top _NUM_OF_CHOICES words
    choices = non_duplicates[:_NUM_OF_CHOICES]
    # select first of them
    checked_word = choices[0]
    # find its index
    checked_index = share_words.index(checked_word) + offset
    # shuffle again so the confirmed word is not always the first choice
    random.shuffle(choices)
    # let the user pick a word
    selected_word: str = await select_word(
        choices, share_index, checked_index, count, group_index
    )
    # confirm it is the correct one
    return selected_word == checked_word


async def _share_words_confirmed(
    share_index: int | None,
    share_words: Sequence[str],
    num_of_shares: int | None = None,
    group_index: int | None = None,
) -> bool:
    """Shows initial dialog asking the user to select words, then presents
    word selectors. Shows success popup if the user is done, failure if the confirmation
    went wrong.

    Return true if the words are confirmed successfully.
    """
    # TODO: confirm_action("Select the words bla bla")

    if await _do_confirm_share_words(share_index, share_words, group_index):
        await _show_confirmation_success(
            share_index,
            num_of_shares,
            group_index,
        )
        return True
    else:
        await _show_confirmation_failure()

    return False


async def _do_confirm_share_words(
    share_index: int | None,
    share_words: Sequence[str],
    group_index: int | None = None,
) -> bool:
    from trezor import utils

    # divide list into thirds, rounding up, so that chunking by `third` always yields
    # three parts (the last one might be shorter)
    third = (len(share_words) + 2) // 3

    offset = 0
    count = len(share_words)
    for part in utils.chunks(share_words, third):
        if not await _confirm_word(share_index, part, offset, count, group_index):
            return False
        offset += len(part)

    return True


async def _show_confirmation_success(
    share_index: int | None = None,
    num_of_shares: int | None = None,
    group_index: int | None = None,
) -> None:
    if share_index is None or num_of_shares is None:  # it is a BIP39 backup
        subheader = TR.reset__finished_verifying_seed
        text = ""

    elif share_index == num_of_shares - 1:
        if group_index is None:
            subheader = TR.reset__finished_verifying_shares
        else:
            subheader = TR.reset__finished_verifying_group_template.format(
                group_index + 1
            )
        text = ""

    else:
        if group_index is None:
            subheader = TR.reset__share_checked_successfully_template.format(
                share_index + 1
            )
            text = TR.reset__continue_with_share_template.format(share_index + 2)
        else:
            subheader = TR.reset__group_share_checked_successfully_template.format(
                group_index + 1, share_index + 1
            )
            text = TR.reset__continue_with_next_share

    return await show_success("success_recovery", text, subheader)


async def _show_confirmation_failure() -> None:
    from trezor.ui.layouts.reset import show_reset_warning

    await show_reset_warning(
        "warning_backup_check",
        TR.words__please_check_again,
        TR.reset__wrong_word_selected,
        TR.buttons__check_again,
        ButtonRequestType.ResetDevice,
    )


async def show_backup_warning(slip39: bool = False) -> None:
    from trezor.ui.layouts.reset import show_warning_backup

    await show_warning_backup(slip39)


async def show_backup_success() -> None:
    from trezor.ui.layouts.reset import show_success_backup

    await show_success_backup()


# BIP39
# ===


async def bip39_show_and_confirm_mnemonic(mnemonic: str) -> None:
    # warn user about mnemonic safety
    await show_backup_warning()

    words = mnemonic.split()

    while True:
        # display paginated mnemonic on the screen
        await show_share_words(words)

        # make the user confirm some words from the mnemonic
        if await _share_words_confirmed(None, words):
            break  # mnemonic is confirmed, go next


# SLIP39
# ===


async def slip39_basic_show_and_confirm_shares(shares: Sequence[str]) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(True)

    for index, share in enumerate(shares):
        share_words = share.split(" ")
        while True:
            # display paginated share on the screen
            await show_share_words(share_words, index)

            # make the user confirm words from the share
            if await _share_words_confirmed(index, share_words, len(shares)):
                break  # this share is confirmed, go to next one


async def slip39_advanced_show_and_confirm_shares(
    shares: Sequence[Sequence[str]],
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(True)

    for group_index, group in enumerate(shares):
        for share_index, share in enumerate(group):
            share_words = share.split(" ")
            while True:
                # display paginated share on the screen
                await show_share_words(share_words, share_index, group_index)

                # make the user confirm words from the share
                if await _share_words_confirmed(
                    share_index, share_words, len(group), group_index
                ):
                    break  # this share is confirmed, go to next one
