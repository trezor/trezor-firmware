from typing import TYPE_CHECKING, Awaitable, Iterable

import trezorui2
from trezor import TR, ui
from trezor.enums import ButtonRequestType

from ..common import interact

if TYPE_CHECKING:
    from ..common import InfoFunc


async def request_word_count(dry_run: bool) -> int:
    count = await interact(
        trezorui2.select_word_count(dry_run=dry_run),
        "word_count",
        ButtonRequestType.MnemonicWordCount,
    )
    return int(count)


async def request_word(
    word_index: int,
    word_count: int,
    is_slip39: bool,
    send_button_request: bool,
    prefill_word: str = "",
) -> str:
    prompt = TR.recovery__type_word_x_of_y_template.format(word_index + 1, word_count)
    can_go_back = word_index > 0
    if is_slip39:
        keyboard = trezorui2.request_slip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    else:
        keyboard = trezorui2.request_bip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    word: str = await interact(
        keyboard,
        "mnemonic" if send_button_request else None,
        ButtonRequestType.MnemonicInput,
    )
    return word


def show_remaining_shares(
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> Awaitable[trezorui2.UiResult]:
    from trezor import strings
    from trezor.crypto.slip39 import MAX_SHARE_COUNT

    pages: list[tuple[str, str]] = []
    for remaining, group in groups:
        if 0 < remaining < MAX_SHARE_COUNT:
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                remaining,
                TR.plurals__x_shares_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))
        elif (
            remaining == MAX_SHARE_COUNT and shares_remaining.count(0) < group_threshold
        ):
            groups_remaining = group_threshold - shares_remaining.count(0)
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                groups_remaining,
                TR.plurals__x_groups_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))

    return interact(
        trezorui2.show_remaining_shares(pages=pages),
        "show_shares",
        ButtonRequestType.Other,
    )


def show_group_share_success(
    share_index: int, group_index: int
) -> Awaitable[ui.UiResult]:
    return interact(
        trezorui2.show_group_share_success(
            lines=[
                TR.recovery__you_have_entered,
                TR.recovery__share_num_template.format(share_index + 1),
                TR.words__from,
                TR.recovery__group_num_template.format(group_index + 1),
            ],
        ),
        "share_success",
        ButtonRequestType.Other,
    )


async def continue_recovery(
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: InfoFunc | None,
    dry_run: bool,
    show_instructions: bool = False,
) -> bool:
    if show_instructions:
        # Show this just one-time
        description = TR.recovery__only_first_n_letters
    else:
        description = subtext or ""

    homepage = trezorui2.confirm_recovery(
        title=text,
        description=description,
        button=button_label.upper(),
        info_button=info_func is not None,
        dry_run=dry_run,
    )

    send_button_request = True
    while True:
        result = await interact(
            homepage,
            "recovery" if send_button_request else None,
            ButtonRequestType.RecoveryHomepage,
            raise_on_cancel=None,
        )
        send_button_request = False

        if info_func is not None and result is trezorui2.INFO:
            await info_func()
        else:
            return result is trezorui2.CONFIRMED


def show_recovery_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[ui.UiResult]:
    button = button or TR.buttons__try_again  # def_arg

    return interact(
        trezorui2.show_warning(
            title=content,
            description=subheader or "",
            button=button.upper(),
            allow_cancel=False,
        ),
        br_type,
        br_code,
    )
