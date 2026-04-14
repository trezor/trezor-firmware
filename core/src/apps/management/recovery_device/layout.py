from typing import TYPE_CHECKING

from trezor import TR
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

from .recover import RecoveryAborted

if TYPE_CHECKING:
    from typing import Awaitable, Iterator

    from trezor.enums import BackupType
    from trezor.loop import Task

    # RemainingSharesInfo represents the data structure for remaining shares in SLIP-39 recovery:
    # - Set of tuples, each containing 2 or 3 words identifying a group
    # - List of remaining share counts for each group
    # - Group threshold (minimum number of groups required)
    RemainingSharesInfo = tuple[set[tuple[str, ...]], list[int], int]

if __debug__:
    from trezor import utils


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


if utils.USE_N4W1:
    from trezor.enums import BackupMethod
    from trezor.ui import Layout

    if TYPE_CHECKING:
        from apps.debug.n4w1_mock import N4W1Context

    async def _n4w1_read(
        ctx: N4W1Context, description: str, button: str
    ) -> bytes | None:
        from trezor.ui import Shutdown
        from trezor.ui.layouts.common import interact
        from trezorui_api import show_info

        class _LayoutRead(Layout):
            def create_tasks(self) -> Iterator[Task]:
                """Run N4W1 write operation in the backgroud of this layout."""

                async def _read_task() -> None:
                    res = await ctx.read(key="mnemonic")
                    try:
                        # emitting a message raises Shutdown exception
                        self._emit_message(res)
                    except Shutdown:
                        pass

                yield from super().create_tasks()
                yield _read_task()

        result = await interact(
            # TODO: disable button & add cancellation
            show_info(
                title=TR.recovery__title,
                description=description,
                button=(button, False),
            ),
            br_name="backup_read",
            confirm_only=True,
            layout_type=_LayoutRead,
        )

        # TODO: animate during read?
        # TODO: show empty tag warning
        if result is None or isinstance(result, bytes):
            return result

        raise RuntimeError

    async def _choose_method() -> BackupMethod:
        import trezorui_api
        from trezor.ui.layouts import interact

        index = await interact(
            trezorui_api.select_word(
                title=TR.recovery__title,
                description="Which type of wallet backup do you have?",
                words=("N4W1 backup", "Wordlist backup", ""),
            ),
            br_name="backup_retry",
        )
        return (BackupMethod.N4W1, BackupMethod.Display)[index]
