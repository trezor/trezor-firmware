from micropython import const
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from typing import Sequence
    from trezor.wire import GenericContext

if __debug__:
    from apps import debug

_NUM_OF_CHOICES = const(3)


async def show_internal_entropy(ctx: GenericContext, entropy: bytes) -> None:
    from trezor import ui
    from trezor.ui.layouts import confirm_blob

    await confirm_blob(
        ctx,
        "entropy",
        "Internal entropy",
        entropy,
        icon=ui.ICON_RESET,
        icon_color=ui.ORANGE_ICON,
        br_code=ButtonRequestType.ResetDevice,
    )


async def _confirm_word(
    ctx: GenericContext,
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

    if __debug__:
        debug.reset_word_index.publish(checked_index)

    # let the user pick a word
    selected_word: str = await select_word(
        ctx, choices, share_index, checked_index, count, group_index
    )
    # confirm it is the correct one
    return selected_word == checked_word


async def _confirm_share_words(
    ctx: GenericContext,
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
        if not await _confirm_word(ctx, share_index, part, offset, count, group_index):
            return False
        offset += len(part)

    return True


async def _show_confirmation_success(
    ctx: GenericContext,
    share_index: int | None = None,
    num_of_shares: int | None = None,
    group_index: int | None = None,
) -> None:
    if share_index is None or num_of_shares is None:  # it is a BIP39 backup
        subheader = "You have finished\nverifying your\nrecovery seed."
        text = ""

    elif share_index == num_of_shares - 1:
        if group_index is None:
            subheader = "You have finished\nverifying your\nrecovery shares."
        else:
            subheader = f"You have finished\nverifying your\nrecovery shares\nfor group {group_index + 1}."
        text = ""

    else:
        if group_index is None:
            subheader = f"Recovery share #{share_index + 1}\nchecked successfully."
            text = f"Continue with share #{share_index + 2}."
        else:
            subheader = f"Group {group_index + 1} - Share {share_index + 1}\nchecked successfully."
            text = "Continue with the next\nshare."

    return await show_success(ctx, "success_recovery", text, subheader)


async def _show_confirmation_failure(
    ctx: GenericContext, share_index: int | None
) -> None:
    from trezor.ui.layouts import show_warning

    if share_index is None:
        header = "Recovery seed"
    else:
        header = f"Recovery share #{share_index + 1}"
    await show_warning(
        ctx,
        "warning_backup_check",
        "Please check again.",
        header,
        "That is the wrong word.",
        "Check again",
        ButtonRequestType.ResetDevice,
    )


async def show_backup_warning(ctx: GenericContext, slip39: bool = False) -> None:
    from trezor.ui.layouts.reset import show_warning_backup

    await show_warning_backup(ctx, slip39)


async def show_backup_success(ctx: GenericContext) -> None:
    text = "Use your backup\nwhen you need to\nrecover your wallet."
    await show_success(ctx, "success_backup", text, "Your backup is done.")


# BIP39
# ===


async def bip39_show_and_confirm_mnemonic(ctx: GenericContext, mnemonic: str) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(ctx)

    words = mnemonic.split()

    while True:
        # display paginated mnemonic on the screen
        await show_share_words(ctx, words)

        # make the user confirm some words from the mnemonic
        if await _confirm_share_words(ctx, None, words):
            await _show_confirmation_success(ctx)
            break  # this share is confirmed, go to next one
        else:
            await _show_confirmation_failure(ctx, None)


# SLIP39
# ===


async def slip39_basic_show_and_confirm_shares(
    ctx: GenericContext, shares: Sequence[str]
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(ctx, True)

    for index, share in enumerate(shares):
        share_words = share.split(" ")
        while True:
            # display paginated share on the screen
            await show_share_words(ctx, share_words, index)

            # make the user confirm words from the share
            if await _confirm_share_words(ctx, index, share_words):
                await _show_confirmation_success(ctx, index, len(shares))
                break  # this share is confirmed, go to next one
            else:
                await _show_confirmation_failure(ctx, index)


async def slip39_advanced_show_and_confirm_shares(
    ctx: GenericContext, shares: Sequence[Sequence[str]]
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(ctx, True)

    for group_index, group in enumerate(shares):
        for share_index, share in enumerate(group):
            share_words = share.split(" ")
            while True:
                # display paginated share on the screen
                await show_share_words(ctx, share_words, share_index, group_index)

                # make the user confirm words from the share
                if await _confirm_share_words(
                    ctx, share_index, share_words, group_index
                ):
                    await _show_confirmation_success(
                        ctx,
                        share_index,
                        len(group),
                        group_index,
                    )
                    break  # this share is confirmed, go to next one
                else:
                    await _show_confirmation_failure(ctx, share_index)
