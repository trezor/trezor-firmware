from typing import TYPE_CHECKING

import storage.recovery as storage_recovery
import storage.recovery_shares as storage_recovery_shares
from trezor import TR, utils
from trezor.ui.layouts.recovery import (  # noqa: F401
    request_word_count,
    show_already_added,
    show_dry_run_result,
    show_group_share_success,
    show_group_threshold,
    show_identifier_mismatch,
    show_recovery_warning,
)

from apps.common import backup_types

from .recover import RecoveryAborted, load_slip39_state

if TYPE_CHECKING:
    from typing import Awaitable, Protocol

    from trezor.enums import BackupMethod, BackupType, RecoveryType

    # RemainingSharesInfo represents the data structure for remaining shares in SLIP-39 recovery:
    # - Set of tuples, each containing 2 or 3 words identifying a group
    # - List of remaining share counts for each group
    # - Group threshold (minimum number of groups required)
    RemainingSharesInfo = tuple[set[tuple[str, ...]], list[int], int]

    class RecoveryHandler(Protocol):
        @classmethod
        async def load(cls, recovery_type: RecoveryType) -> "RecoveryHandler": ...

        async def show_state(self, is_retry: bool) -> None: ...
        async def request_mnemonic(self) -> str | None: ...


async def request_mnemonic(
    word_count: int, backup_type: BackupType | None
) -> str | None:
    """
    Loops until a mnemonic is entered.

    Returns a space-separated mnemonic on success, None on cancellation.
    Raises `WordValidityResult` on share-related error.
    """
    from trezor.ui.layouts.recovery import request_word

    from . import word_validity

    send_button_request = True

    # Pre-allocate the list to enable going back and overwriting words.
    words: list[str] = [""] * word_count
    i = 0

    def all_words_entered() -> bool:
        return i >= word_count

    while not all_words_entered():
        # Prefilling the previously inputted word in case of going back
        word = await request_word(
            i,
            word_count,
            is_slip39=backup_types.is_slip39_word_count(word_count),
            send_button_request=send_button_request,
            prefill_word=words[i],
        )
        send_button_request = False

        if not word:
            # User has decided to go back
            if i == 0:
                # Already at the first word; treat as cancel.
                return None

            words[i] = ""
            i -= 1
            continue

        words[i] = word

        i += 1

        non_empty_words = [word for word in words if word]
        # Raises `WordValidityResult` on error.
        word_validity.check(backup_type, non_empty_words)

    return " ".join(words)


def enter_share(
    word_count: int | None = None,
    entered_remaining: tuple[int, int] | None = None,
    remaining_shares_info: RemainingSharesInfo | None = None,
) -> Awaitable[None]:
    from trezor import strings

    show_instructions = False

    if word_count is not None:
        # First-time entry. Show instructions and word count.
        text = TR.recovery__enter_any_share
        subtext = TR.recovery__word_count_template.format(word_count)
        show_instructions = True

    elif entered_remaining is not None:
        # Basic Shamir. There is only one group, we report entered/remaining count.
        entered, remaining = entered_remaining
        total = entered + remaining
        text = TR.recovery__x_of_y_entered_template.format(entered, total)
        subtext = strings.format_plural(
            TR.recovery__x_more_shares_needed_template_plural,
            remaining,
            TR.plurals__x_shares_needed,
        )

    else:
        # SuperShamir. We cannot easily show entered/remaining across groups,
        # the caller provided an info_func that has the details.
        text = TR.recovery__more_shares_needed
        subtext = None

    return homescreen_dialog(
        TR.buttons__enter_share,
        text,
        subtext,
        show_instructions,
        remaining_shares_info,
    )


async def homescreen_dialog(
    button_label: str,
    text: str,
    subtext: str | None = None,
    show_instructions: bool = False,
    remaining_shares_info: "RemainingSharesInfo | None" = None,
) -> None:
    import storage.recovery as storage_recovery
    from trezor.ui.layouts.recovery import continue_recovery

    recovery_type = storage_recovery.get_type()
    if not await continue_recovery(
        button_label,
        text,
        subtext,
        recovery_type,
        show_instructions,
        remaining_shares_info,
    ):
        raise RecoveryAborted


async def _request_share_first_screen(
    word_count: int, recovery_type: RecoveryType
) -> None:
    from trezor.enums import RecoveryType

    if backup_types.is_slip39_word_count(word_count):
        remaining = storage_recovery.fetch_slip39_remaining_shares()
        if remaining:
            group_count = storage_recovery.get_slip39_group_count()
            if group_count > 1:
                await enter_share(
                    remaining_shares_info=_get_remaining_groups_and_shares()
                )
            else:
                entered = len(storage_recovery_shares.fetch_group(0))
                await enter_share(entered_remaining=(entered, remaining[0]))
        else:
            if recovery_type == RecoveryType.UnlockRepeatedBackup:
                text = TR.recovery__enter_backup
                button_label = TR.buttons__continue
            else:
                text = TR.recovery__enter_any_share
                button_label = TR.buttons__enter_share
            await homescreen_dialog(
                button_label,
                text,
                TR.recovery__word_count_template.format(word_count),
                show_instructions=True,
            )
    else:  # BIP-39
        await homescreen_dialog(
            TR.buttons__continue,
            TR.recovery__enter_backup,
            TR.recovery__word_count_template.format(word_count),
            show_instructions=True,
        )


def _get_remaining_groups_and_shares() -> "RemainingSharesInfo":
    """
    Prepare data for Slip39 Advanced - what shares are to be entered.
    """
    from trezor.crypto import slip39

    shares_remaining = storage_recovery.fetch_slip39_remaining_shares()
    assert shares_remaining  # should be stored at this point

    groups = set()
    first_entered_index = -1
    for i, group_count in enumerate(shares_remaining):
        if group_count < slip39.MAX_SHARE_COUNT:
            first_entered_index = i
            break

    share = None
    for index, remaining in enumerate(shares_remaining):
        if 0 <= remaining < slip39.MAX_SHARE_COUNT:
            m = storage_recovery_shares.fetch_group(index)[0]
            if not share:
                share = slip39.decode_mnemonic(m)
            identifier = tuple(m.split(" ")[0:3])
            groups.add(identifier)
        elif remaining == slip39.MAX_SHARE_COUNT:  # no shares yet
            identifier = tuple(
                storage_recovery_shares.fetch_group(first_entered_index)[0].split(" ")[
                    0:2
                ]
            )
            groups.add(identifier)

    assert share  # share needs to be set
    return groups, shares_remaining, share.group_threshold


class _DisplayHandler:
    def __init__(
        self,
        recovery_type: RecoveryType,
        word_count: int,
        backup_type: BackupType | None,
    ) -> None:
        self.recovery_type = recovery_type
        self.word_count = word_count
        self.backup_type = backup_type

    @classmethod
    async def load(cls, recovery_type: RecoveryType) -> "RecoveryHandler":
        from trezor.wire import ActionCancelled

        # `slip39_state is None` indicates that we are (re)starting the first recovery step,
        # which includes word count selection.
        if (slip39_state := load_slip39_state()) is None:
            # If we are starting recovery, ask for word count first...
            try:
                word_count = await request_word_count(recovery_type)
            except ActionCancelled:
                raise RecoveryAborted
            # ...and only then show the starting screen with word count.
            # Backup type will be deduced from the first share.
            backup_type = None
        else:
            # SLIP-39 recovery is ongoing (at least one share was entered).
            word_count, backup_type = slip39_state

        return cls(recovery_type, word_count, backup_type)

    async def show_state(self, is_retry: bool) -> None:
        if is_retry and self.backup_type is not None:
            # skip showing recovery state on retries (if first share was entered)
            return
        await _request_share_first_screen(self.word_count, self.recovery_type)

    async def request_mnemonic(self) -> str | None:
        """Return the mnemonic or `None` on cancellation/validation error."""
        from .word_validity import WordValidityResult

        try:
            # returns `None` on cancellation
            return await request_mnemonic(self.word_count, self.backup_type)
        except WordValidityResult as exc:
            # if they were invalid or some checks failed we continue and request them again
            await exc.show_error()
            return None


if not utils.USE_N4W1:

    async def choose_handler(method: BackupMethod | None) -> type[RecoveryHandler]:
        from trezor.enums import BackupMethod

        if method is not BackupMethod.Display and __debug__:
            from trezor import log

            log.warning(__name__, "Unsupported backup method: %s", method)

        return _DisplayHandler

else:

    if TYPE_CHECKING:
        from trezor.messages import BackupMethod

        from .recover import Slip39State

    async def choose_handler(method: BackupMethod | None) -> type[RecoveryHandler]:
        from trezor.enums import BackupMethod

        if method is None:
            from trezor.ui.layouts.recovery import choose_method

            method = await choose_method(TR.recovery__title, TR.backup__type_have)

        if method is BackupMethod.N4W1:
            return _N4W1Handler

        if method not in (None, BackupMethod.Display):
            from trezor import log

            if __debug__:
                log.warning(__name__, "Unsupported backup method: %s", method)

        return _DisplayHandler

    class RetryRead(Exception):
        def __init__(self, msg: str) -> None:
            self.msg = msg

    async def _read_share() -> bytes:
        from apps.debug import n4w1_mock

        with n4w1_mock.ctx as ctx:
            # returns `None` on cancellation or retriable error.
            await ctx.confirm_connect(
                title=TR.recovery__title,
                description=TR.n4w1__hold_next,
                button=TR.n4w1__footer_next,
                br_name="backup_read",
            )
            # continue N4W1 communication (the tag is connected)

            # TODO: animate during read?
            if (blob := await ctx.read(key="mnemonic")) is None:
                raise RetryRead("This tag is empty. Continue to scan a different tag.")

            return bytes(blob)

    class _N4W1Handler:
        def __init__(
            self,
            recovery_type: RecoveryType,
            slip39_state: Slip39State | None,
        ) -> None:
            super().__init__()
            self.recovery_type = recovery_type
            # `slip39_state is None` indicates that we are (re)starting the first recovery step.
            self.slip39_state = slip39_state

        @classmethod
        async def load(cls, recovery_type: RecoveryType) -> "RecoveryHandler":
            return cls(recovery_type, load_slip39_state())

        async def show_state(self, is_retry: bool) -> None:
            if is_retry or self.slip39_state is None:
                # don't show recovery state on retries and before the first share is entered
                return
            word_count = self.slip39_state[0]
            await _request_share_first_screen(word_count, self.recovery_type)

        async def request_mnemonic(self) -> str | None:
            """Return the mnemonic or `None` on cancellation/validation error."""
            import trezorui_api
            from trezor.ui.layouts.common import raise_if_not_confirmed

            while True:
                try:
                    blob = await _read_share()
                    break
                except RetryRead as exc:
                    await raise_if_not_confirmed(
                        trezorui_api.show_warning(
                            title=TR.words__important,
                            button=TR.buttons__continue,
                            description=exc.msg,
                            danger=True,
                        ),
                        br_name="recovery_retry",
                    )
                    # wait for a new N4W1 tag
                    continue

            # TODO: use protobuf?
            share = blob.decode()
            return await self.check_words(share)

        async def check_words(self, share: str) -> str | None:
            from trezor.ui.layouts.progress import progress

            from .word_validity import WordValidityResult, check

            # Can be `None` when checking the first share.
            backup_type = self.slip39_state and self.slip39_state[1]
            share_words = share.split(" ")

            progress_obj = progress(description=TR.n4w1__reading)
            progress_obj.start()

            try:
                # Re-verify mnemonic prefixes:
                steps = len(share_words)
                for prefix_len in range(1, 1 + steps):
                    progress_obj.report((1000 * prefix_len) // steps)
                    check(backup_type, partial_mnemonic=share_words[:prefix_len])

                return share
            except WordValidityResult as exc:
                # if they were invalid or some checks failed we continue and request them again
                await exc.show_error()
                return None
            finally:
                progress_obj.stop()
