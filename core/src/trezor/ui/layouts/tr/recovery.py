from typing import TYPE_CHECKING, Awaitable, Iterable

import trezorui2
from trezor import TR, ui
from trezor.enums import ButtonRequestType

from ..common import interact
from . import show_warning

if TYPE_CHECKING:
    from ..common import InfoFunc


async def request_word_count(dry_run: bool) -> int:
    count = await interact(
        trezorui2.select_word_count(dry_run=dry_run),
        "recovery_word_count",
        ButtonRequestType.MnemonicWordCount,
    )
    # It can be returning a string (for example for __debug__ in tests)
    return int(count)


async def request_word(
    word_index: int,
    word_count: int,
    is_slip39: bool,
    send_button_request: bool,
    prefill_word: str = "",
) -> str:
    prompt = TR.recovery__word_x_of_y_template.format(word_index + 1, word_count)

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


async def show_remaining_shares(
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    raise NotImplementedError


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
    # TODO: implement info_func?
    # There is very limited space on the screen
    # (and having middle button would mean shortening the right button text)

    # Never showing info for dry-run, user already saw it and it is disturbing
    if dry_run:
        show_instructions = False

    if subtext:
        text += f"\n\n{subtext}"

    homepage = trezorui2.confirm_recovery(
        title="",
        description=text,
        button=button_label.upper(),
        info_button=False,
        dry_run=dry_run,
        show_instructions=show_instructions,
    )
    result = await interact(
        homepage,
        "recovery",
        ButtonRequestType.RecoveryHomepage,
        raise_on_cancel=None,
    )
    return result is trezorui2.CONFIRMED


def show_recovery_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[ui.UiResult]:
    button = button or TR.buttons__try_again  # def_arg
    return show_warning(br_type, content, subheader, button, br_code)
