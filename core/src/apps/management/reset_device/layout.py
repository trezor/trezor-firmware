from micropython import const
from typing import TYPE_CHECKING, Iterable, Iterator, Protocol, Sequence

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
    from trezor.loop import Task
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


if utils.USE_N4W1:

    from trezor import TR
    from trezor.ui import Layout
    from trezor.ui.layouts.common import interact

    if TYPE_CHECKING:
        from buffer_types import AnyBytes

        from apps.debug.n4w1_mock import N4W1Context

    class Retry(Exception):
        def __init__(self, msg: str) -> None:
            self.msg = msg

    class _N4W1Backup:

        async def intro(self, num_of_words: int | None = None) -> None:
            # TODO: design/copy
            pass

        async def backup(self, iter_shares: Iterable[ShareInfo]) -> None:
            # TODO: warn user about safety

            # backup all shares
            for share in iter_shares:
                await self._backup_share(share)

        async def _backup_share(self, share: ShareInfo) -> None:
            import trezorui_api
            from trezor import TR
            from trezor.ui.layouts.common import raise_if_not_confirmed

            from apps.debug import n4w1_mock

            # TODO: use protobuf?
            blob = " ".join(share.words).encode()

            if share.index == 0 or share.num_of_shares is None:
                description, button = TR.n4w1__hold_first, TR.n4w1__footer_first
            elif share.index == share.num_of_shares - 1:
                description, button = TR.n4w1__hold_last, TR.n4w1__footer_last
            else:
                description, button = TR.n4w1__hold_next, TR.n4w1__footer_next

            while True:
                try:
                    with n4w1_mock.ctx as ctx:
                        # may raise a retriable error
                        return await _backup_share(ctx, description, button, blob)
                except Retry as exc:
                    await raise_if_not_confirmed(
                        trezorui_api.show_warning(
                            title=TR.words__important,
                            button=TR.buttons__continue,
                            description=exc.msg,
                            danger=True,
                        ),
                        br_name="backup_retry",
                    )
                    # wait for a new N4W1 tag
                    continue

    async def _backup_share(
        ctx: N4W1Context, description: str, button: str, blob: AnyBytes
    ) -> None:
        from trezor.ui import Shutdown
        from trezor.ui.layouts.progress import progress
        from trezorui_api import CONFIRMED, show_info

        class _LayoutWrite(Layout):

            result: AnyBytes | None | Exception = None

            def create_tasks(self) -> Iterator[Task]:
                """Run N4W1 write operation in the backgroud of this layout."""

                async def _write_task() -> None:
                    try:
                        _LayoutWrite.result = await ctx.read(key="mnemonic")
                    except Exception as exc:
                        _LayoutWrite.result = exc

                    try:
                        # emitting a message raises Shutdown exception
                        self._emit_message(CONFIRMED)
                    except Shutdown:
                        pass

                yield from super().create_tasks()
                yield _write_task()

        await interact(
            show_info(
                title=TR.backup__title_create_wallet_backup,
                description=description,
                button=(button, False),
                external_menu=True,
            ),
            br_name="backup_write",
            confirm_only=True,
            layout_type=_LayoutWrite,
        )

        result = _LayoutWrite.result
        if isinstance(result, Exception):
            raise result
        if result is not None:
            raise Retry("Non-empty N4W1 tag.")

        # continue N4W1 communication (the tag is ready)
        progress_obj = progress(description=TR.n4w1__writing)
        progress_obj.start()
        progress_obj.report(100)
        try:
            await ctx.write(key="mnemonic", value=blob)
            # TODO: animate during I/O?
            progress_obj.report(1000)
        finally:
            progress_obj.stop()
            progress_obj = None

    async def _choose_method() -> BackupMethod:
        import trezorui_api

        index = await interact(
            trezorui_api.select_word(
                title=TR.backup__title_create_wallet_backup,
                description="Select the type of wallet backup you want to create.",
                words=("N4W1 backup", "Wordlist backup", ""),
            ),
            br_name="backup_retry",
        )
        return (BackupMethod.N4W1, BackupMethod.Display)[index]


async def choose_backup_handler(method: BackupMethod | None) -> BackupHandler:
    if utils.USE_N4W1:
        from trezor.enums import BackupMethod

        if utils.USE_N4W1:
            if method is None:
                method = await _choose_method()

            if method is BackupMethod.N4W1:
                return _N4W1Backup()

        if method not in (None, BackupMethod.Display):
            from trezor import log

            if __debug__:
                log.warning(__name__, "Unsupported backup method: %s", method)

    return _DisplayBackup()
