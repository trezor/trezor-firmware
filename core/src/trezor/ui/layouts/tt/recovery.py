from typing import TYPE_CHECKING, Callable

import trezorui2
from trezor import TR
from trezor.enums import ButtonRequestType, RecoveryType

from ..common import interact
from . import RustLayout, raise_if_not_confirmed

CONFIRMED = trezorui2.CONFIRMED  # global_import_cache
INFO = trezorui2.INFO  # global_import_cache

if TYPE_CHECKING:
    from apps.management.recovery_device.layout import RemainingSharesInfo


async def _homepage_with_info(
    dialog: RustLayout,
    info_func: Callable,
) -> trezorui2.UiResult:
    while True:
        result = await dialog

        if result is INFO:
            await info_func()
            dialog.request_complete_repaint()
        else:
            return result


async def request_word_count(recovery_type: RecoveryType) -> int:
    selector = RustLayout(trezorui2.select_word_count(recovery_type=recovery_type))
    count = await interact(selector, "word_count", ButtonRequestType.MnemonicWordCount)
    return int(count)


async def request_word(
    word_index: int, word_count: int, is_slip39: bool, prefill_word: str = ""
) -> str:
    prompt = TR.recovery__type_word_x_of_y_template.format(word_index + 1, word_count)
    can_go_back = word_index > 0
    if is_slip39:
        keyboard = RustLayout(
            trezorui2.request_slip39(
                prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
            )
        )
    else:
        keyboard = RustLayout(
            trezorui2.request_bip39(
                prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
            )
        )

    word: str = await keyboard
    return word


async def show_remaining_shares(
    groups: set[tuple[str, ...]],
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    from trezor import strings
    from trezor.crypto.slip39 import MAX_SHARE_COUNT

    pages: list[tuple[str, str]] = []
    completed_groups = shares_remaining.count(0)

    for group, remaining in zip(groups, shares_remaining):
        if 0 < remaining < MAX_SHARE_COUNT:
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                remaining,
                TR.plurals__x_shares_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))
        elif remaining == MAX_SHARE_COUNT and completed_groups < group_threshold:
            groups_remaining = group_threshold - completed_groups
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                groups_remaining,
                TR.plurals__x_groups_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))

    await raise_if_not_confirmed(
        interact(
            RustLayout(trezorui2.show_remaining_shares(pages=pages)),
            "show_shares",
            ButtonRequestType.Other,
        )
    )


async def show_group_share_success(share_index: int, group_index: int) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_group_share_success(
                    lines=[
                        TR.recovery__you_have_entered,
                        TR.recovery__share_num_template.format(share_index + 1),
                        TR.words__from,
                        TR.recovery__group_num_template.format(group_index + 1),
                    ],
                )
            ),
            "share_success",
            ButtonRequestType.Other,
        )
    )


async def _confirm_abort(dry_run: bool = False) -> None:
    from . import confirm_action

    if dry_run:
        await confirm_action(
            "abort_recovery",
            TR.recovery__title_cancel_dry_run,
            TR.recovery__cancel_dry_run,
            description=TR.recovery__wanna_cancel_dry_run,
            verb=TR.buttons__cancel,
            br_code=ButtonRequestType.ProtectCall,
        )
    else:
        await confirm_action(
            "abort_recovery",
            TR.recovery__title_cancel_recovery,
            TR.recovery__progress_will_be_lost,
            TR.recovery__wanna_cancel_recovery,
            verb=TR.buttons__cancel,
            reverse=True,
            br_code=ButtonRequestType.ProtectCall,
        )


async def continue_recovery(
    button_label: str,
    text: str,
    subtext: str | None,
    recovery_type: RecoveryType,
    show_info: bool = False,
    remaining_shares_info: "RemainingSharesInfo | None" = None,
) -> bool:
    from trezor.wire import ActionCancelled

    from ..common import button_request

    if show_info:
        # Show this just one-time
        description = TR.recovery__enter_each_word
    else:
        description = subtext or ""

    while True:
        homepage = RustLayout(
            trezorui2.confirm_recovery(
                title=text,
                description=description,
                button=button_label,
                recovery_type=recovery_type,
                info_button=remaining_shares_info is not None,
            )
        )

        await button_request("recovery", ButtonRequestType.RecoveryHomepage)

        if remaining_shares_info is None:
            result = await homepage
        else:
            groups, shares_remaining, group_threshold = remaining_shares_info
            result = await _homepage_with_info(
                homepage,
                lambda: show_remaining_shares(
                    groups, shares_remaining, group_threshold
                ),
            )

        if result is CONFIRMED:
            return True

        try:
            await _confirm_abort(recovery_type != RecoveryType.NormalRecovery)
        except ActionCancelled:
            pass
        else:
            return False


async def show_recovery_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    button = button or TR.buttons__try_again  # def_arg
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_warning(
                    title=content,
                    description=subheader or "",
                    button=button,
                    allow_cancel=False,
                )
            ),
            br_name,
            br_code,
        )
    )
