from micropython import const
from typing import TYPE_CHECKING, Protocol

from trezor import utils
from trezor.ui.layouts.reset import (  # noqa: F401
    show_share_words,
    slip39_advanced_prompt_group_threshold,
    slip39_advanced_prompt_number_of_groups,
    slip39_prompt_number_of_shares,
    slip39_prompt_threshold,
    slip39_show_checklist,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

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
    # sort list to make UI tests independent on micropython hash function
    non_duplicates = sorted(set(share_words))
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
        share_threshold: int | None = None,
        group_threshold: int | None = None,
    ) -> None:
        self.words = words
        self.index = index
        self.num_of_shares = num_of_shares
        self.group_index = group_index
        self.share_threshold = share_threshold
        self.group_threshold = group_threshold


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
    handler: BackupHandler,
    shares: Sequence[str],
    threshold: int,
) -> None:
    return await handler.backup(
        ShareInfo(
            words=share.split(" "),
            index=index,
            num_of_shares=len(shares),
            share_threshold=threshold,
        )
        for index, share in enumerate(shares)
    )


async def slip39_advanced_show_and_confirm_shares(
    handler: BackupHandler,
    shares: Sequence[Sequence[str]],
    thresholds: Sequence[int],
    group_threshold: int,
) -> None:
    return await handler.backup(
        ShareInfo(
            words=share.split(" "),
            index=share_index,
            num_of_shares=len(group),
            group_index=group_index,
            share_threshold=thresholds[group_index],
            group_threshold=group_threshold,
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
    from trezor.enums import BackupMethod

    if utils.USE_N1W1:
        if method is None:
            from trezor.ui.layouts.recovery import choose_method

            method = await choose_method(
                TR.backup__title_create_wallet_backup,
                TR.backup__type_create,
            )

        if method is BackupMethod.N1W1:
            return _N1W1Backup()

    if method not in (None, BackupMethod.Display):
        from trezor import log

        if __debug__:
            log.warning(__name__, "Unsupported backup method: %s", method)

    return _DisplayBackup()


if utils.USE_N1W1:
    import trezorui_api
    from trezor import TR
    from trezor.ui.layouts.common import raise_if_not_confirmed

    import apps.management.n1w1.context as n1w1

    if TYPE_CHECKING:
        from buffer_types import AnyBytes

    class RetryWrite(Exception):
        def __init__(self, msg: str) -> None:
            self.msg = msg

    class _N1W1Backup:
        def __init__(self) -> None:
            # If we decide to cancel and wipe in the middle, we'll check the UIDs to avoid wiping unrelated card.
            self.uids = set()

        async def intro(self, num_of_words: int | None = None) -> None:
            # FIXME: can be displayed before number of shares, thresholds are selected
            pass

        async def backup(self, iter_shares: Iterable[ShareInfo]) -> None:
            shares = list(iter_shares)

            if len(shares) == 1:
                description = "Single-share NFC backup is not recommended."
            elif shares[0].group_index is not None:
                description = f"SLIP-39 advanced NFC backup on {len(shares)} cards is not recommended."
            else:
                description = f"Get {len(shares)} N1W1s to write the wallet backup on them."

            # TODO: Hint: use any 2 ...
            # TODO: menu: skip backup, modify backup scheme
            with trezorui_api.show_info(
                title="Backup wallet",
                description=description,
                button=("Start", True),
            ) as layout:
                await raise_if_not_confirmed(layout, br_name="backup_nfc_before")

            # TODO(N1W1): warn user about safety

            # backup all shares
            # TODO: collect card IDs in case we want to abort & erase
            for share in shares:
                await self._backup_share(share)

        async def _backup_share(self, share: ShareInfo) -> None:
            # TODO(N1W1): use protobuf?
            blob = " ".join(share.words).encode()

            if share.index == 0 or share.num_of_shares is None:
                description, button = (
                    "Start with any N1W1.",
                    TR.n1w1__footer_first,
                )
            elif share.index == share.num_of_shares - 1:
                description, button = "Use next N1W1.", TR.n1w1__footer_last
            else:
                description, button = "Use next N1W1.", TR.n1w1__footer_next

            while True:
                try:
                    with n1w1.ctx as ctx:
                        uid = await _write_share(
                            ctx,
                            description,
                            blob,
                        )
                    self.uids.add(uid)
                    break
                except RetryWrite as exc:
                    with trezorui_api.show_warning(
                        title=TR.words__important,
                        button=TR.buttons__continue,
                        description=exc.msg,
                        danger=True,
                    ) as layout:
                        await raise_if_not_confirmed(layout, br_name="backup_retry")
                    # wait for a new N1W1 tag
                    continue

            button = TR.buttons__continue
            if (
                share.index is None
                or share.num_of_shares is None
                or share.share_threshold is None
            ):  # single share
                description = "N1W1 is ready.\n\nUse it any time to recover the wallet."
            elif (
                share.index == share.num_of_shares - 1 and share.group_threshold is None
            ):  # multi-share last card, not slip39advanced
                description = f"All N1W1s are ready.\n\nUse any {share.share_threshold} of these {share.num_of_shares} cards at any time to recover the wallet."
                button = TR.instructions__continue_in_app
                # TODO: not a clickable button, should disappear when?
            elif (
                share.group_threshold is None
            ):  # multi-share not last card, not slip39advanced
                description = f"N1W1 {share.index + 1} of {share.num_of_shares} is ready."
            else:  # generic for slip39advanced
                description = "N1W1 is ready."
            with trezorui_api.show_success(
                title=TR.words__title_done,
                description=description,
                button=button,
                allow_cancel=False,
            ) as layout:
                await raise_if_not_confirmed(layout, br_name="backup_nfc_success")

    async def _write_share(
        ctx: n1w1.N1W1Context, description: str, blob: AnyBytes
    ) -> bytes:
        from trezor.ui.layouts.progress import progress

        await ctx.confirm_connect(
            title="Backup wallet",
            description=description,
            br_name="backup_write",
        )
        # TODO pin protection

        progress_obj = progress(
            title="Writing to N1W1...", description="Wait"
        )
        try:
            progress_obj.start()
            progress_cb = n1w1.time_based_progress(progress_obj)

            uid = await ctx.uid(progress_cb=progress_cb)

            # continue N1W1 communication (the tag is connected)
            result = await ctx.read_share(progress_cb=progress_cb)
            if result is not None:
                raise RetryWrite(TR.n1w1__err_nonempty)

            await ctx.write_share(value=blob, progress_cb=progress_cb)
            progress_obj.report(1000)
        except Exception as exc:
            if (reason := n1w1.is_retryable(exc)) is not None:
                raise RetryWrite(reason)
            raise
        finally:
            progress_obj.stop()

        return uid
