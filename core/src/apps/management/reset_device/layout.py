from typing import Sequence

from trezor import ui, utils
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action, confirm_blob, show_success, show_warning
from trezor.ui.layouts.reset import (  # noqa: F401
    confirm_word,
    show_share_words,
    slip39_advanced_prompt_group_threshold,
    slip39_advanced_prompt_number_of_groups,
    slip39_prompt_number_of_shares,
    slip39_prompt_threshold,
    slip39_show_checklist,
)


async def show_internal_entropy(entropy: bytes) -> None:
    await confirm_blob(
        "entropy",
        "Internal entropy",
        data=entropy,
        icon=ui.ICON_RESET,
        icon_color=ui.ORANGE_ICON,
        br_code=ButtonRequestType.ResetDevice,
    )


async def _confirm_share_words(
    share_index: int | None,
    share_words: Sequence[str],
    group_index: int | None = None,
) -> bool:
    # divide list into thirds, rounding up, so that chunking by `third` always yields
    # three parts (the last one might be shorter)
    third = (len(share_words) + 2) // 3

    offset = 0
    count = len(share_words)
    for part in utils.chunks(share_words, third):
        if not await confirm_word(share_index, part, offset, count, group_index):
            return False
        offset += len(part)

    return True


async def _show_confirmation_success(
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

    return await show_success("success_recovery", text, subheader=subheader)


async def _show_confirmation_failure(share_index: int | None) -> None:
    if share_index is None:
        header = "Recovery seed"
    else:
        header = f"Recovery share #{share_index + 1}"
    await show_warning(
        "warning_backup_check",
        header=header,
        subheader="That is the wrong word.",
        content="Please check again.",
        button="Check again",
        br_code=ButtonRequestType.ResetDevice,
    )


async def show_backup_warning(slip39: bool = False) -> None:
    if slip39:
        description = "Never make a digital copy of your recovery shares and never upload them online!"
    else:
        description = "Never make a digital copy of your recovery seed and never upload\nit online!"
    await confirm_action(
        "backup_warning",
        "Caution",
        description=description,
        verb="I understand",
        verb_cancel=None,
        icon=ui.ICON_NOCOPY,
        br_code=ButtonRequestType.ResetDevice,
    )


async def show_backup_success() -> None:
    text = "Use your backup\nwhen you need to\nrecover your wallet."
    await show_success("success_backup", text, subheader="Your backup is done.")


# BIP39
# ===


async def bip39_show_and_confirm_mnemonic(mnemonic: str) -> None:
    # warn user about mnemonic safety
    await show_backup_warning()

    words = mnemonic.split()

    while True:
        # display paginated mnemonic on the screen
        await show_share_words(share_words=words)

        # make the user confirm some words from the mnemonic
        if await _confirm_share_words(None, words):
            await _show_confirmation_success()
            break  # this share is confirmed, go to next one
        else:
            await _show_confirmation_failure(None)


# SLIP39
# ===


async def slip39_basic_show_and_confirm_shares(shares: Sequence[str]) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(slip39=True)

    for index, share in enumerate(shares):
        share_words = share.split(" ")
        while True:
            # display paginated share on the screen
            await show_share_words(share_words, index)

            # make the user confirm words from the share
            if await _confirm_share_words(index, share_words):
                await _show_confirmation_success(
                    share_index=index, num_of_shares=len(shares)
                )
                break  # this share is confirmed, go to next one
            else:
                await _show_confirmation_failure(index)


async def slip39_advanced_show_and_confirm_shares(
    shares: Sequence[Sequence[str]],
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning(slip39=True)

    for group_index, group in enumerate(shares):
        for share_index, share in enumerate(group):
            share_words = share.split(" ")
            while True:
                # display paginated share on the screen
                await show_share_words(share_words, share_index, group_index)

                # make the user confirm words from the share
                if await _confirm_share_words(share_index, share_words, group_index):
                    await _show_confirmation_success(
                        share_index=share_index,
                        num_of_shares=len(group),
                        group_index=group_index,
                    )
                    break  # this share is confirmed, go to next one
                else:
                    await _show_confirmation_failure(share_index)
