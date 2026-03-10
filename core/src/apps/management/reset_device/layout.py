from micropython import const
from typing import TYPE_CHECKING

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

    Share = str | Sequence[str]
    Group = Sequence[Share]


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
    from trezor.ui.layouts.reset import (
        show_share_confirmation_failure,
        show_share_confirmation_success,
    )

    if await _do_confirm_share_words(share_index, share_words, group_index):
        await show_share_confirmation_success(
            share_index,
            num_of_shares,
            group_index,
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


async def show_backup_intro(
    single_share: bool, num_of_words: int | None = None
) -> None:
    from trezor.ui.layouts.reset import show_intro_backup

    await show_intro_backup(single_share, num_of_words)


class BackupMethod:
    def __init__(
        self,
        groups_of_shares: Sequence[Group],
    ) -> None:
        self.groups_of_shares = groups_of_shares

    async def handle_share(
        self, *, share: Share, share_index: int, num_of_shares: int, group_index: int
    ) -> None:
        raise NotImplementedError

    async def run(self) -> None:
        for group_index, group in enumerate(self.groups_of_shares):
            for share_index, share in enumerate(group):
                await self.handle_share(
                    share=share,
                    share_index=share_index,
                    num_of_shares=len(group),
                    group_index=group_index,
                )


class DisplayMnemonic(BackupMethod):

    async def handle_share(
        self, *, share: Share, share_index: int, num_of_shares: int, group_index: int
    ) -> None:
        if isinstance(share, str):
            share_words = share.split(" ")
        else:
            share_words = share

        while True:
            # display paginated share on the screen
            await show_share_words(
                share_words=share_words,
                share_index=share_index,
                group_index=group_index,
            )

            # make the user confirm words from the share
            if await _share_words_confirmed(
                share_index=share_index,
                share_words=share_words,
                num_of_shares=num_of_shares,
                group_index=group_index,
            ):
                break  # this share is confirmed, go to next one


class N4W1Storage(BackupMethod):

    async def handle_share(
        self, *, share: Share, share_index: int, num_of_shares: int, group_index: int
    ) -> None:
        import trezorui_api
        from trezor.ui.layouts.common import draw_simple

        from apps.debug import n4w1_mock

        if not isinstance(share, str):
            share = " ".join(share)
        # TODO: use protobuf?
        blob = share.encode()

        with n4w1_mock.ctx as ctx:
            draw_simple(
                trezorui_api.show_simple(
                    title="Backup",
                    text=f"Tap your N4W1 to backup {len(blob)} bytes",
                )
            )
            await ctx.write(key="mnemonic", value=blob)


async def show_backup_warning() -> None:
    from trezor.ui.layouts.reset import show_warning_backup

    await show_warning_backup()


async def show_backup_success() -> None:
    from trezor.ui.layouts.reset import show_success_backup

    await show_success_backup()


# Simple setups: BIP39 or SLIP39 1-of-1
# ===


async def show_and_confirm_single_share(
    method: type[BackupMethod], words: Sequence[str]
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning()

    return await method([[words]]).run()


# Complex setups: SLIP39, except 1-of-1
# ===


async def slip39_basic_show_and_confirm_shares(
    method: type[BackupMethod], shares: Sequence[str]
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning()

    await method([shares]).run()


async def slip39_advanced_show_and_confirm_shares(
    method: type[BackupMethod],
    groups_of_shares: Sequence[Sequence[str]],
) -> None:
    # warn user about mnemonic safety
    await show_backup_warning()

    await method(groups_of_shares).run()
