from micropython import const
from typing import TYPE_CHECKING, Iterable, Protocol, Sequence

from trezor.ui.layouts.reset import (  # noqa: F401
    show_share_words,
    slip39_advanced_prompt_group_threshold,
    slip39_advanced_prompt_number_of_groups,
    slip39_prompt_number_of_shares,
    slip39_prompt_threshold,
    slip39_show_checklist,
)

if TYPE_CHECKING:
    from trezor.messages import BackupMethod

_NUM_OF_CHOICES = const(3)


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


class ShareInfo:
    def __init__(
        self,
        *,
        words: Sequence[str],
        index: int | None,
        num_of_shares: int | None = None,
        group_index: int | None = None,
    ) -> None:
        self.words = words
        self.index = index
        self.num_of_shares = num_of_shares
        self.group_index = group_index


if TYPE_CHECKING:

    class BackupHandler(Protocol):
        async def intro(self, num_of_words: int | None = None) -> None:
            """Show introductory layout about the backup."""

        async def backup(self, iter_shares: Iterable[ShareInfo]) -> None:
            """Backup all the provided shares."""


async def _share_words_confirmed(share: ShareInfo) -> bool:
    """Shows initial dialog asking the user to select words, then presents
    word selectors. Shows success popup if the user is done, failure if the confirmation
    went wrong.

    Return true if the words are confirmed successfully.
    """
    from trezor.ui.layouts.reset import (
        show_share_confirmation_failure,
        show_share_confirmation_success,
    )

    if await _do_confirm_share_words(share.index, share.words, share.group_index):
        await show_share_confirmation_success(
            share.index,
            share.num_of_shares,
            share.group_index,
        )
        return True
    else:
        await show_share_confirmation_failure()

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


async def show_backup_success() -> None:
    from trezor.ui.layouts.reset import show_success_backup

    await show_success_backup()


# Simple setups: BIP39 or SLIP39 1-of-1
# ===


async def show_and_confirm_single_share(
    handler: BackupHandler, words: Sequence[str]
) -> None:
    return await handler.backup((ShareInfo(words=words, index=None),))


# Complex setups: SLIP39, except 1-of-1
# ===


async def slip39_basic_show_and_confirm_shares(
    handler: BackupHandler, shares: Sequence[str]
) -> None:
    return await handler.backup(
        ShareInfo(words=share.split(" "), index=index, num_of_shares=len(shares))
        for index, share in enumerate(shares)
    )


async def slip39_advanced_show_and_confirm_shares(
    handler: BackupHandler,
    shares: Sequence[Sequence[str]],
) -> None:
    return await handler.backup(
        ShareInfo(
            words=share.split(" "),
            index=share_index,
            num_of_shares=len(group),
            group_index=group_index,
        )
        for group_index, group in enumerate(shares)
        for share_index, share in enumerate(group)
    )


class _DisplayBackup:

    async def intro(self, num_of_words: int | None = None) -> None:
        from trezor.ui.layouts.reset import show_intro_backup

        # show backup information (`num_of_words` is unset for multi-share backups)
        await show_intro_backup(num_of_words=num_of_words)

    async def backup(self, iter_shares: Iterable[ShareInfo]) -> None:
        from trezor.ui.layouts.reset import show_warning_backup

        # warn user about mnemonic safety
        await show_warning_backup()

        # backup all shares
        for share in iter_shares:
            await self._backup_share(share)

    async def _backup_share(self, share: ShareInfo) -> None:
        while True:
            # display paginated share on the screen
            await show_share_words(
                share_words=share.words,
                share_index=share.index,
                group_index=share.group_index,
            )

            # make the user confirm words from the share
            if await _share_words_confirmed(share):
                break  # this share is confirmed, go to next one


async def choose_backup_handler(method: BackupMethod | None) -> BackupHandler:
    # TODO: prompt the user if method is `None`.
    if __debug__:
        from trezor.enums import BackupMethod

        if method not in (None, BackupMethod.Display):
            from trezor import log

            log.warning(__name__, "Unsupported backup method: %s", method)

    return _DisplayBackup()
