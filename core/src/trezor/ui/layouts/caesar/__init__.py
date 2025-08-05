from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui, utils
from trezor.enums import ButtonRequestType, RecoveryType
from trezor.wire import ActionCancelled

from ..common import draw_simple, interact, raise_if_cancelled

if TYPE_CHECKING:
    from typing import Awaitable, Callable, Iterable, List, NoReturn, Sequence

    from ..common import ExceptionType, PropertyType
    from ..menu import Details


CONFIRMED = trezorui_api.CONFIRMED
CANCELLED = trezorui_api.CANCELLED
INFO = trezorui_api.INFO

DOWN_ARROW = "V"
BR_CODE_OTHER = ButtonRequestType.Other  # global_import_cache


# Temporary function, so we know where it is used
# Should be gradually replaced by custom designs/layouts
def _placeholder_confirm(
    br_name: str,
    title: str,
    data: str | None = None,
    description: str | None = None,
    *,
    verb: str | None = None,
    verb_cancel: str | None = "",
    hold: bool = False,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    verb = verb or TR.buttons__confirm  # def_arg
    return confirm_action(
        br_name,
        title,
        data,
        description,
        verb=verb,
        verb_cancel=verb_cancel,
        hold=hold,
        reverse=True,
        br_code=br_code,
    )


def confirm_action(
    br_name: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = "",
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    exc: ExceptionType = ActionCancelled,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    prompt_screen: bool = False,  # unused on caesar
    prompt_title: str | None = None,
) -> Awaitable[None]:
    verb = verb or TR.buttons__confirm  # def_arg
    if description is not None and description_param is not None:
        description = description.format(description_param)

    return raise_if_cancelled(
        trezorui_api.confirm_action(
            title=title,
            action=action,
            description=description,
            subtitle=subtitle,
            verb=verb,
            verb_cancel=verb_cancel,
            hold=hold,
            reverse=reverse,
        ),
        br_name,
        br_code,
        exc,
    )


def confirm_single(
    br_name: str,
    title: str,
    description: str,
    description_param: str | None = None,
    verb: str | None = None,
) -> Awaitable[None]:
    description_param = description_param or ""

    # Placeholders are coming from translations in form of {0}
    template_str = "{0}"

    begin, _separator, end = description.partition(template_str)
    return confirm_action(
        br_name,
        title,
        description=begin + description_param + end,
        verb=verb or TR.buttons__confirm,
        br_code=ButtonRequestType.ProtectCall,
    )


def confirm_reset_device(
    recovery: bool = False,
) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.confirm_reset_device(recovery=recovery),
        "recover_device" if recovery else "setup_device",
        ButtonRequestType.ProtectCall if recovery else ButtonRequestType.ResetDevice,
    )


async def prompt_recovery_check(recovery_type: RecoveryType) -> None:
    assert recovery_type in (RecoveryType.DryRun, RecoveryType.UnlockRepeatedBackup)
    title = (
        TR.recovery__title_dry_run
        if recovery_type == RecoveryType.DryRun
        else TR.recovery__title_unlock_repeated_backup
    )
    await confirm_action(
        "confirm_seedcheck",
        title,
        description=TR.recovery__check_dry_run,
        br_code=ButtonRequestType.ProtectCall,
        verb=TR.buttons__check,
    )


async def show_wallet_created_success() -> None:
    # not shown on caesar UI
    return None


async def prompt_backup() -> bool:
    br_name = "backup_device"
    br_code = ButtonRequestType.ResetDevice

    result = await interact(
        trezorui_api.prompt_backup(),
        br_name,
        br_code,
        raise_on_cancel=None,
    )
    if result is CONFIRMED:
        return True

    result = await interact(
        trezorui_api.confirm_action(
            title=TR.backup__title_skip,
            action=None,
            description=TR.backup__want_to_skip,
            verb=TR.buttons__back_up,
            verb_cancel=TR.buttons__skip,
            hold=False,
        ),
        br_name,
        br_code,
        raise_on_cancel=None,
    )
    return result is CONFIRMED


def confirm_path_warning(
    path: str,
    path_type: str | None = None,
) -> Awaitable[None]:
    title = f"{TR.words__unknown} {path_type if path_type else 'path'}"
    return _placeholder_confirm(
        "path_warning",
        title,
        description=path,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def confirm_multisig_warning() -> Awaitable[ui.UiResult]:
    return show_warning(
        "warning_multisig",
        TR.send__receiving_to_multisig,
        TR.words__continue_anyway_question,
    )


def confirm_multisig_different_paths_warning() -> Awaitable[ui.UiResult]:
    return show_warning(
        "warning_multisig_different_paths",
        TR.send__multisig_different_paths,
        TR.words__continue_anyway_question,
    )


def confirm_multiple_accounts_warning() -> Awaitable[ui.UiResult]:
    return show_warning(
        "sending_from_multiple_accounts",
        TR.send__from_multiple_accounts,
        TR.words__continue_anyway_question,
        button=TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


def lock_time_disabled_warning() -> Awaitable[ui.UiResult]:
    return show_warning(
        "nondefault_locktime",
        TR.bitcoin__locktime_no_effect,
        TR.words__continue_anyway_question,
        button=TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


def confirm_homescreen(image: bytes) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.confirm_homescreen(
            title=TR.homescreen__title_set,
            image=image,
        ),
        "set_homesreen",
        ButtonRequestType.ProtectCall,
    )


def confirm_change_passphrase(use: bool) -> Awaitable[None]:
    description = TR.passphrase__turn_on if use else TR.passphrase__turn_off
    verb = TR.buttons__turn_on if use else TR.buttons__turn_off

    return confirm_action(
        "set_passphrase",
        TR.passphrase__title_settings,
        description=description,
        verb=verb,
        br_code=ButtonRequestType.ProtectCall,
    )


def confirm_hide_passphrase_from_host() -> Awaitable[None]:
    return confirm_action(
        "set_hide_passphrase_from_host",
        TR.passphrase__title_hide,
        description=TR.passphrase__hide,
        br_code=ButtonRequestType.ProtectCall,
    )


async def confirm_hidden_passphrase_from_host() -> None:
    await confirm_action(
        "passphrase_host1_hidden",
        TR.passphrase__wallet,
        description=TR.passphrase__from_host_not_shown,
        prompt_screen=True,
        prompt_title=TR.passphrase__access_wallet,
    )


async def show_passphrase_from_host(passphrase: str | None) -> None:
    await confirm_action(
        "passphrase_host1",
        TR.passphrase__wallet,
        description=TR.passphrase__next_screen_will_show_passphrase,
        verb=TR.buttons__continue,
    )

    await confirm_blob(
        "passphrase_host2",
        TR.passphrase__title_confirm,
        passphrase or "",
        info=False,
    )


def confirm_change_passphrase_source(
    passphrase_always_on_device: bool,
) -> Awaitable[None]:
    description = (
        TR.passphrase__always_on_device
        if passphrase_always_on_device
        else TR.passphrase__revoke_on_device
    )
    return confirm_action(
        "set_passphrase_source",
        TR.passphrase__title_source,
        description=description,
        br_code=ButtonRequestType.ProtectCall,
    )


async def show_address(
    address: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    address_qr: str | None = None,
    case_sensitive: bool = True,
    path: str | None = None,
    account: str | None = None,
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    mismatch_title: str | None = None,
    warning: str | None = None,
    br_name: str = "show_address",
    br_code: ButtonRequestType = ButtonRequestType.Address,
    chunkify: bool = False,
) -> None:
    mismatch_title = mismatch_title or TR.addr_mismatch__mismatch  # def_arg
    send_button_request = True
    if title is None:
        # Will be a marquee in case of multisig
        title = TR.address__title_receive_address
        if multisig_index is not None:
            title = f"{title} (MULTISIG)"  # TODO translation?

    while True:
        result = await interact(
            trezorui_api.confirm_address(
                title=title,
                address=address,
                address_label=None,
                info_button=True,
                chunkify=chunkify,
            ),
            br_name if send_button_request else None,
            br_code,
            raise_on_cancel=None,
        )
        send_button_request = False

        # User confirmed with middle button.
        if result is CONFIRMED:
            break

        # User pressed right button, go to address details.
        elif result is INFO:

            def xpub_title(i: int) -> str:
                # Will be marquee (cannot fit one line)
                result = f"MULTISIG XPUB #{i + 1}"
                result += (
                    f" ({TR.address__title_yours})"
                    if i == multisig_index
                    else f" ({TR.address__title_cosigner})"
                )
                return result

            result = await interact(
                trezorui_api.show_address_details(
                    qr_title="",  # unused on this model
                    address=address if address_qr is None else address_qr,
                    case_sensitive=case_sensitive,
                    details_title="",  # unused on this model
                    account=account,
                    path=path,
                    xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
                ),
                None,
                raise_on_cancel=None,
            )
            # Can only go back from the address details.
            assert result is CANCELLED

        # User pressed left cancel button, show mismatch dialogue.
        else:
            result = await interact(
                trezorui_api.show_mismatch(title=mismatch_title),
                None,
                raise_on_cancel=None,
            )
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise ActionCancelled


async def show_pubkey(
    pubkey: str,
    title: str | None = None,
    *,
    account: str | None = None,
    path: str | None = None,
    mismatch_title: str | None = None,
    warning: str | None = None,
    br_name: str = "show_pubkey",
) -> None:
    title = title or TR.address__public_key  # def_arg
    mismatch_title = mismatch_title or TR.addr_mismatch__key_mismatch  # def_arg
    await show_address(
        address=pubkey,
        title=title,
        account=account,
        path=path,
        br_name=br_name,
        br_code=ButtonRequestType.PublicKey,
        mismatch_title=mismatch_title,
        chunkify=False,
    )


def _show_modal(
    br_name: str,
    header: str,
    subheader: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
    br_code: ButtonRequestType,
    exc: ExceptionType = ActionCancelled,
) -> Awaitable[None]:
    return confirm_action(
        br_name,
        header,
        subheader,
        content,
        verb=button_confirm or "",
        verb_cancel=button_cancel,
        exc=exc,
        br_code=br_code,
    )


async def show_error_and_raise(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    exc: ExceptionType = ActionCancelled,
) -> NoReturn:
    button = button or TR.buttons__try_again  # def_arg
    await show_warning(
        br_name,
        subheader or "",
        content,
        button=button,
        br_code=BR_CODE_OTHER,
        exc=None,
    )
    # always raise regardless of result
    raise exc


def show_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
    exc: ExceptionType | None = ActionCancelled,
) -> Awaitable[ui.UiResult]:
    from trezor import translations

    button = button or TR.buttons__continue  # def_arg

    # Putting there a delimiter line in case of english, so it looks better
    # (we know it will fit one page)
    # TODO: figure out some better and non-intrusive way to do this
    # (check if the content fits one page with the newline, and if not, do not add it)
    if content and subheader and translations.get_language() == "en-US":
        content = content + "\n"

    return interact(
        trezorui_api.show_warning(
            title="",
            button=button,
            value=content,
            description=subheader or "",
        ),
        br_name,
        br_code,
        raise_on_cancel=exc,
    )


def show_danger(
    br_name: str,
    content: str,
    title: str | None = None,
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    title = title or TR.words__warning
    verb_cancel = verb_cancel or TR.buttons__cancel
    return raise_if_cancelled(
        trezorui_api.show_danger(
            title=title,
            description=content,
        ),
        br_name,
        br_code,
    )


def show_success(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
) -> Awaitable[None]:
    button = button or TR.buttons__continue  # def_arg
    title = TR.words__title_success

    # In case only subheader is supplied, showing it
    # in regular font, not bold.
    if not content and subheader:
        content = subheader
        subheader = None

    # Special case for Shamir backup - to show everything just on one page
    # in regular font.
    if TR.words__continue_with in content:
        content = f"{subheader}\n\n{content}"
        subheader = None
        title = ""

    return _show_modal(
        br_name,
        title,
        subheader,
        content,
        button_confirm=button,
        button_cancel=None,
        br_code=ButtonRequestType.Success,
    )


def show_continue_in_app(content: str) -> None:
    return


async def confirm_payment_request(
    recipient_name: str,
    recipient: str,
    texts: Iterable[tuple[str | None, str]],
    refunds: Iterable[tuple[str, str | None, str | None]],
    trades: List[tuple[str, str, str, str | None, str | None]],
    account_items: List[tuple[str, str]],
    transaction_fee: str | None,
    fee_info_items: Iterable[tuple[str, str]] | None,
    token_address: str | None,
) -> None:
    from trezor.ui.layouts.menu import Menu, confirm_with_menu

    # Note: we don't support "sales" (swap to fiat) yet,
    # so if there is any trade, we assume it must be a swap
    is_swap = len(trades) != 0

    for title, text in texts:
        await raise_if_cancelled(
            trezorui_api.confirm_value(
                title=title or (TR.words__swap if is_swap else TR.words__confirm),
                value=text,
                description=None,
            ),
            "confirm_payment_request",
        )

    main_layout = trezorui_api.confirm_with_info(
        title=(TR.words__swap if is_swap else TR.words__confirm),
        items=[(TR.words__provider, True), (recipient_name, False)],
        verb=TR.buttons__continue,
        verb_info=TR.buttons__info,
        external_menu=True,
    )

    menu_items = [create_details(TR.address__title_provider_address, recipient)]
    for r_address, r_account, r_account_path in refunds:
        refund_account_items: list[tuple[str, str]] = [("", r_address)]
        if r_account:
            refund_account_items.append((TR.words__account, r_account))
        if r_account_path:
            refund_account_items.append(
                (TR.address_details__derivation_path, r_account_path)
            )
        menu_items.append(
            create_details(
                TR.address__title_refund_address,
                refund_account_items,
            )
        )
    menu = Menu.root(menu_items)

    await confirm_with_menu(main_layout, menu, "confirm_payment_request")

    for sell_amount, buy_amount, t_address, t_account, t_account_path in trades:
        await confirm_trade(
            f"{TR.words__swap} {TR.words__assets}",
            sell_amount,
            buy_amount,
            t_address,
            t_account,
            t_account_path,
            token_address,
        )

    if transaction_fee is not None:
        assert fee_info_items is not None

        summary_layout = trezorui_api.confirm_summary(
            amount=None,
            amount_label=None,
            fee=transaction_fee,
            fee_label=TR.words__transaction_fee,
            title=TR.words__title_summary,
            external_menu=True,
        )

        summary_menu_items = [
            create_details(TR.confirm_total__title_fee, list(fee_info_items)),
            create_details(TR.address_details__account_info, account_items),
        ]

        summary_menu = Menu.root(summary_menu_items)

        await confirm_with_menu(
            summary_layout, summary_menu, br_name="confirm_payment_request"
        )


async def confirm_output(
    address: str,
    amount: str,
    title: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    address_label: str | None = None,
    output_index: int | None = None,
    chunkify: bool = False,
    source_account: str | None = None,  # ignored on safe 3
    source_account_path: str | None = None,  # ignored on safe 3
) -> None:
    title = title or TR.send__confirm_sending  # def_arg
    address_title = TR.words__recipient
    if output_index is not None:
        address_title += f" #{output_index + 1}"
    amount_title = TR.words__amount
    if output_index is not None:
        amount_title += f" #{output_index + 1}"

    while True:
        await interact(
            trezorui_api.confirm_address(
                title=address_title,
                address=address,
                address_label=address_label or None,
                verb=TR.buttons__continue,
                info_button=False,
                chunkify=chunkify,
            ),
            "confirm_output",
            br_code,
        )

        try:
            await interact(
                trezorui_api.confirm_value(
                    title=amount_title,
                    value=amount,
                    description=None,
                    verb_cancel="^",
                    verb=TR.buttons__confirm,
                ),
                "confirm_output",
                br_code,
            )
        except ActionCancelled:
            # if the user cancels here, go back to confirm_value
            continue
        else:
            return


def tutorial(br_code: ButtonRequestType = BR_CODE_OTHER) -> Awaitable[ui.UiResult]:
    """Showing users how to interact with the device."""
    return interact(trezorui_api.tutorial(), "tutorial", br_code)


async def should_show_more(
    title: str,
    para: Iterable[tuple[str, bool]],
    button_text: str | None = None,
    br_name: str = "should_show_more",
    br_code: ButtonRequestType = BR_CODE_OTHER,
    confirm: str | None = None,
    verb_cancel: str | None = None,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """

    result = await interact(
        trezorui_api.confirm_with_info(
            title=title,
            items=para,
            verb=confirm or TR.buttons__confirm,
            verb_cancel=verb_cancel,
            verb_info=button_text or TR.buttons__show_all,  # unused on caesar
        ),
        br_name,
        br_code,
    )

    if result is CONFIRMED:
        return False
    elif result is INFO:
        return True
    else:
        raise ActionCancelled


def confirm_blob(
    br_name: str,
    title: str,
    data: bytes | str,
    description: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,  # icon
    info: bool = True,
    hold: bool = False,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    ask_pagination: bool = False,
    extra_confirmation_if_not_read: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = True,
) -> Awaitable[None]:
    if description and ":" not in description:
        description += ":"

    layout = trezorui_api.confirm_value(
        title=title,
        description=description,
        value=data,
        verb=verb or TR.buttons__confirm,
        verb_cancel=verb_cancel or "",
        hold=hold,
        chunkify=chunkify,
    )

    if ask_pagination and layout.page_count() > 1:
        assert not hold
        return _confirm_ask_pagination(
            br_name,
            title,
            data,
            description or "",
            br_code,
            extra_confirmation_if_not_read,
        )
    else:
        return raise_if_cancelled(layout, br_name, br_code)


async def _confirm_ask_pagination(
    br_name: str,
    title: str,
    data: bytes | str,
    description: str,
    br_code: ButtonRequestType,
    extra_confirmation_if_not_read: bool = False,
) -> None:
    data = utils.hexlify_if_bytes(data)

    confirm_more_layout = trezorui_api.confirm_more(
        title=title,
        button=TR.buttons__confirm,
        items=[(description, False), (data, True)],
    )

    while True:
        if not await should_show_more(
            title,
            para=[(description, False), (data, True)],
            br_name=br_name,
            br_code=br_code,
        ):
            if extra_confirmation_if_not_read:
                try:
                    await confirm_value(
                        title,
                        TR.sign_message__confirm_without_review,
                        None,
                        br_name=br_name,
                        br_code=br_code,
                        verb=TR.buttons__confirm,
                        verb_cancel="^",
                        hold=True,
                        is_data=False,
                    )
                except ActionCancelled:
                    continue
            return

        result = await interact(confirm_more_layout, br_name, br_code, None)
        if result is trezorui_api.CANCELLED:
            continue
        else:
            break


def confirm_address(
    title: str,
    address: str,
    subtitle: str | None = None,
    description: str | None = None,
    verb: str | None = None,
    warning_footer: str | None = None,
    chunkify: bool = True,
    br_name: str | None = None,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    return confirm_blob(
        br_name or "confirm_address",
        subtitle or title,
        address,
        description,
        verb=verb,
        br_code=br_code,
    )


def confirm_text(
    br_name: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    if description and data:
        description += ":"

    return _placeholder_confirm(
        br_name,
        title,
        data,
        description,
        br_code=br_code,
    )


def confirm_amount(
    title: str,
    amount: str,
    description: str | None = None,
    br_name: str = "confirm_amount",
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    description = description or f"{TR.words__amount}:"  # def_arg
    return confirm_blob(
        br_name,
        title,
        amount,
        description,
        br_code=br_code,
    )


def confirm_properties(
    br_name: str,
    title: str,
    props: Iterable[PropertyType],
    subtitle: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    verb: str | None = None,
) -> Awaitable[None]:

    items: list[tuple[str | None, str | bytes | None, bool | None]] = [
        (
            prop[0],
            (utils.hexlify_if_bytes(prop[1]) if prop[1] else None),
            prop[2],
        )
        for prop in props
    ]

    if subtitle:
        title += ": " + subtitle

    return raise_if_cancelled(
        trezorui_api.confirm_properties(
            title=title,
            items=items,
            hold=hold,
        ),
        br_name,
        br_code,
    )


async def confirm_value(
    title: str,
    value: str,
    description: str | None,
    br_name: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    *,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    is_data: bool = True,
    info_items: Iterable[tuple[str, str]] | None = None,
    chunkify: bool = False,
    chunkify_info: bool = False,
    cancel: bool = False,
) -> None:
    """General confirmation dialog, used by many other confirm_* functions."""

    if description and value:
        description += ":"

    if not info_items:
        return await raise_if_cancelled(
            trezorui_api.confirm_value(
                title=title,
                value=value,
                description=description,
                verb=verb or TR.buttons__hold_to_confirm,
                verb_cancel=verb_cancel or "",
                info=False,
                hold=hold,
                is_data=is_data,
                chunkify=chunkify,
                cancel=cancel,
            ),
            br_name,
            br_code,
        )

    from trezor.ui.layouts.menu import Details, Menu, confirm_with_menu

    main = trezorui_api.confirm_with_info(
        title=title,
        items=((value, False),),
        verb=verb or TR.buttons__confirm,
        verb_info=TR.buttons__info,
        external_menu=True,
    )

    def item_factory(
        info_title: str, info_value: str
    ) -> Callable[[], trezorui_api.LayoutObj]:
        return lambda: trezorui_api.confirm_value(
            title=info_title,
            value=info_value,
            description=description,
            verb="",
            verb_cancel="",
            is_data=is_data,
            chunkify=chunkify_info,
        )

    menu = Menu.root(
        Details.from_layout(name, item_factory(name, value))
        for name, value in info_items
    )
    await confirm_with_menu(main, menu, br_name, br_code)


def confirm_total(
    total_amount: str,
    fee_amount: str,
    fee_rate_amount: str | None = None,
    title: str | None = None,
    total_label: str | None = None,
    fee_label: str | None = None,
    source_account: str | None = None,
    source_account_path: str | None = None,
    br_name: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> Awaitable[None]:
    total_label = total_label or f"{TR.send__total_amount}:"  # def_arg
    fee_label = fee_label or TR.send__including_fee  # def_arg

    fee_info_items = []
    if fee_rate_amount:
        fee_info_items.append((TR.confirm_total__fee_rate_colon, fee_rate_amount))
    account_info_items = []
    if source_account:
        account_info_items.append((TR.words__account_colon, source_account))

    return raise_if_cancelled(
        trezorui_api.confirm_summary(
            amount=total_amount,
            amount_label=total_label,
            fee=fee_amount,
            fee_label=fee_label,
            account_items=account_info_items or None,
            extra_items=fee_info_items or None,
            extra_title=TR.confirm_total__title_fee,
        ),
        br_name,
        br_code,
    )


if not utils.BITCOIN_ONLY:

    def confirm_ethereum_unknown_contract_warning(
        _title: str | None,
    ) -> Awaitable[None]:
        return show_danger(
            "unknown_contract_warning",
            TR.words__know_what_your_doing,
            title=TR.ethereum__unknown_contract_address,
        )

    def ethereum_address_title() -> str:
        """Return the title for the Ethereum address confirmation."""
        return TR.words__address

    async def confirm_ethereum_approve(
        recipient_addr: str,
        recipient_str: str | None,
        is_unknown_token: bool,
        token_address: str,
        token_symbol: str,
        is_unknown_network: bool,
        chain_id: str,
        network_name: str,
        is_revoke: bool,
        total_amount: str | None,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        fee_info_items: Iterable[tuple[str, str]],
        chunkify: bool = False,
    ) -> None:
        await confirm_value(
            (
                TR.ethereum__approve_intro_title_revoke
                if is_revoke
                else TR.ethereum__approve_intro_title
            ),
            (
                TR.ethereum__approve_intro_revoke
                if is_revoke
                else TR.ethereum__approve_intro
            ),
            None,
            verb=TR.buttons__continue,
            hold=False,
            is_data=False,
            br_name="confirm_ethereum_approve",
        )

        await confirm_value(
            TR.ethereum__approve_revoke_from if is_revoke else TR.ethereum__approve_to,
            recipient_str or recipient_addr,
            None,
            verb=TR.buttons__continue,
            hold=False,
            br_name="confirm_ethereum_approve",
            chunkify=False if recipient_str else chunkify,
        )

        if total_amount is None:
            await show_warning(
                "confirm_ethereum_approve",
                TR.ethereum__approve_unlimited_template.format(token_symbol),
                TR.words__continue_anyway_question,
            )

        if is_unknown_token:
            await confirm_value(
                TR.ethereum__token_contract + " | " + TR.words__address,
                token_address,
                None,
                verb=DOWN_ARROW,
                hold=False,
                br_name="confirm_ethereum_approve",
                chunkify=chunkify,
            )

        if is_unknown_network:
            assert is_unknown_token
            await confirm_value(
                TR.ethereum__approve_chain_id,
                chain_id,
                None,
                verb=DOWN_ARROW,
                hold=False,
                br_name="confirm_ethereum_approve",
            )

        properties: list[PropertyType] = (
            [(TR.words__token, token_symbol, True)]
            if is_revoke
            else [
                (
                    TR.ethereum__approve_amount_allowance,
                    total_amount or TR.words__unlimited,
                    False,
                )
            ]
        )
        if not is_unknown_network:
            properties.append((TR.words__chain, network_name, True))
        await confirm_properties(
            "confirm_ethereum_approve",
            TR.ethereum__approve_revoke if is_revoke else TR.ethereum__approve,
            properties,
            None,
            False,
        )

        account_items = []
        if account_path:
            account_items.append((TR.address_details__derivation_path, account_path))

        await raise_if_cancelled(
            trezorui_api.confirm_summary(
                amount=None,
                amount_label=None,
                fee=maximum_fee,
                fee_label=f"{TR.send__maximum_fee}:",
                title=TR.words__title_summary,
                account_items=[(f"{k}:", v) for (k, v) in account_items],
                account_title=TR.address_details__account_info,
                extra_items=fee_info_items,
                extra_title=TR.confirm_total__title_fee,
            ),
            br_name="confirm_ethereum_approve",
        )

    async def confirm_trade(
        title: str,
        sell_amount: str,
        buy_amount: str,
        address: str,
        account: str | None,
        account_path: str | None,
        token_address: str | None,
    ) -> None:
        from trezor.ui.layouts.menu import Menu, confirm_with_menu

        trade_layout = trezorui_api.confirm_properties(
            title=title,
            items=[("", sell_amount, True), ("", buy_amount, True)],
            verb=TR.buttons__continue,
            external_menu=True,
        )

        account_items: list[tuple[str, str]] = [("", address)]
        if account:
            account_items.append((TR.words__account, account))
        if account_path:
            account_items.append((TR.address_details__derivation_path, account_path))
        menu_items = [create_details(TR.address__title_receive_address, account_items)]
        if token_address is not None:
            menu_items.append(
                create_details(TR.ethereum__token_contract, token_address)
            )
        menu = Menu.root(menu_items)

        await confirm_with_menu(trade_layout, menu, "confirm_trade")

    async def confirm_ethereum_staking_tx(
        title: str,
        intro_question: str,
        verb: str,
        total_amount: str,
        _account: str | None,
        _account_path: str | None,
        maximum_fee: str,
        address: str,
        address_title: str,
        info_items: Iterable[tuple[str, str]],
        chunkify: bool = False,
        br_name: str = "confirm_ethereum_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        # intro
        await confirm_value(
            title,
            intro_question,
            "",
            br_name,
            br_code,
            verb=verb,
            info_items=((address_title, address),),
            chunkify_info=chunkify,
        )

        # confirmation
        if verb == TR.ethereum__staking_claim:
            amount_title = verb
            amount_value = ""
        else:
            amount_title = f"{TR.words__amount}:"
            amount_value = total_amount
        await raise_if_cancelled(
            trezorui_api.confirm_summary(
                amount=amount_value,
                amount_label=amount_title,
                fee=maximum_fee,
                fee_label=f"{TR.send__maximum_fee}:",
                extra_items=[(f"{k}:", v) for (k, v) in info_items],
                extra_title=TR.confirm_total__title_fee,
            ),
            br_name=br_name,
            br_code=br_code,
        )

    def confirm_solana_unknown_token_warning() -> Awaitable[None]:
        return show_danger(
            "unknown_token_warning",
            content=TR.words__know_what_your_doing,
            title=TR.solana__unknown_token_address,
        )

    def confirm_solana_recipient(
        recipient: str,
        title: str,
        items: Iterable[tuple[str, str]] = (),
        br_name: str = "confirm_solana_recipient",
        br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    ) -> Awaitable[None]:
        return confirm_value(
            title=title,
            value=recipient,
            description="",
            br_name=br_name,
            br_code=br_code,
            verb=TR.buttons__continue,
            info_items=items,
        )

    def confirm_solana_tx(
        amount: str,
        fee: str,
        items: Iterable[tuple[str, str]],
        amount_title: str | None = None,
        fee_title: str | None = None,
        br_name: str = "confirm_solana_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> Awaitable[None]:
        amount_title = (
            amount_title if amount_title is not None else f"{TR.words__amount}:"
        )  # def_arg
        fee_title = fee_title or TR.words__fee  # def_arg
        return raise_if_cancelled(
            trezorui_api.confirm_summary(
                amount=amount,
                amount_label=amount_title,
                fee=fee,
                fee_label=fee_title,
                extra_items=items,  # TODO: extra_title here?
                extra_title=TR.words__title_information,
            ),
            br_name=br_name,
            br_code=br_code,
        )

    async def confirm_solana_staking_tx(
        title: str | None,
        description: str,
        account: str,
        account_path: str,
        vote_account: str,
        stake_item: tuple[str, str] | None,
        amount_item: tuple[str, str] | None,
        fee_item: tuple[str, str],
        fee_details: list[tuple[str, str]],
        blockhash_item: tuple[str, str],
        br_name: str = "confirm_solana_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        from trezor.ui.layouts.menu import Menu, confirm_with_menu

        if not amount_item:
            amount_label, amount = fee_item
            amount_label = f"\n\n{amount_label}"
            fee_label = ""
            fee = ""
        else:
            amount_label, amount = amount_item
            fee_label, fee = fee_item

        items = []
        if stake_item is not None:
            items.append(stake_item)
        items.append(blockhash_item)

        if vote_account:
            description = f"{description}\n{TR.words__provider}:"
            title = None  # so the layout will fit in a single page
        else:
            description = f"\n{description}"

        main = trezorui_api.confirm_summary(
            title=title,
            amount=vote_account,
            amount_label=description,
            fee="",
            fee_label="",
            external_menu=True,
        )
        menu = Menu.root(create_details(name, value) for name, value in items)
        await confirm_with_menu(main, menu, br_name, br_code)

        main = trezorui_api.confirm_summary(
            amount=amount,
            amount_label=amount_label,
            fee=fee,
            fee_label=fee_label,
            external_menu=True,
        )
        account_details = [
            (f"{TR.words__account}:", account),
            (TR.address_details__derivation_path_colon, account_path),
        ]
        items = [
            (TR.confirm_total__title_fee, fee_details),
            (TR.address_details__account_info, account_details),
        ]
        menu = Menu.root(create_details(name, value) for name, value in items)
        await confirm_with_menu(main, menu, br_name, br_code)

    def confirm_cardano_tx(
        amount: str,
        fee: str,
        items: Iterable[tuple[str, str]],
        amount_title: str | None = None,
        fee_title: str | None = None,
    ) -> Awaitable[None]:
        amount_title = f"{TR.send__total_amount}:"
        fee_title = TR.send__including_fee

        return raise_if_cancelled(
            trezorui_api.confirm_summary(
                amount=amount,
                amount_label=amount_title,
                fee=fee,
                fee_label=fee_title,
                extra_items=items,
            ),
            br_name="confirm_cardano_tx",
            br_code=ButtonRequestType.SignTx,
        )

    async def confirm_ethereum_tx(
        recipient: str | None,
        total_amount: str,
        _account: str | None,
        _account_path: str | None,
        maximum_fee: str,
        fee_info_items: Iterable[tuple[str, str]],
        is_contract_interaction: bool,
        br_name: str = "confirm_ethereum_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
        chunkify: bool = False,
    ) -> None:
        summary_layout = trezorui_api.confirm_summary(
            amount=total_amount,
            amount_label=f"{TR.words__amount}:",
            fee=maximum_fee,
            fee_label=f"{TR.send__maximum_fee}:",
            extra_items=[(f"{k}:", v) for (k, v) in fee_info_items],
            extra_title=TR.confirm_total__title_fee,
            verb_cancel="^",
        )

        if not is_contract_interaction:
            title = TR.words__recipient
        else:
            title = TR.ethereum__interaction_contract if recipient else ""

        while True:
            # Allowing going back and forth between recipient and summary/details
            await confirm_blob(
                br_name,
                title,
                recipient or TR.ethereum__new_contract,
                verb=TR.buttons__continue,
                br_code=br_code,
                chunkify=(chunkify if recipient else False),
            )

            try:
                await raise_if_cancelled(
                    summary_layout,
                    br_name,
                    br_code,
                )
                break
            except ActionCancelled:
                continue


def confirm_joint_total(spending_amount: str, total_amount: str) -> Awaitable[None]:
    return confirm_properties(
        "confirm_joint_total",
        TR.joint__title,
        [
            (TR.joint__you_are_contributing, spending_amount, False),
            (TR.joint__to_the_total_amount, total_amount, False),
        ],
        hold=True,
        br_code=ButtonRequestType.SignTx,
    )


def confirm_metadata(
    br_name: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hold: bool = False,
) -> Awaitable[None]:
    return _placeholder_confirm(
        br_name,
        title,
        description=content.format(param),
        hold=hold,
        br_code=br_code,
    )


def confirm_replacement(description: str, txid: str) -> Awaitable[None]:
    return confirm_value(
        description,
        txid,
        TR.send__transaction_id,
        "confirm_replacement",
        ButtonRequestType.SignTx,
        verb=TR.buttons__continue,
    )


async def confirm_modify_output(
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    address_layout = trezorui_api.confirm_value(
        title=TR.modify_amount__title,
        value=address,
        verb=TR.buttons__continue,
        description=f"{TR.words__address}:",
    )

    modify_layout = trezorui_api.confirm_modify_output(
        sign=sign,
        amount_change=amount_change,
        amount_new=amount_new,
    )

    send_button_request = True
    while True:
        await raise_if_cancelled(
            address_layout,
            "modify_output" if send_button_request else None,
            ButtonRequestType.ConfirmOutput,
        )
        try:
            await raise_if_cancelled(
                modify_layout,
                "modify_output" if send_button_request else None,
                ButtonRequestType.ConfirmOutput,
            )
        except ActionCancelled:
            send_button_request = False
            continue
        else:
            break


def confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.confirm_modify_fee(
            title=title,
            sign=sign,
            user_fee_change=user_fee_change,
            total_fee_new=total_fee_new,
            fee_rate_amount=fee_rate_amount,
        ),
        "modify_fee",
        ButtonRequestType.SignTx,
    )


def confirm_coinjoin(max_rounds: int, max_fee_per_vbyte: str) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.confirm_coinjoin(
            max_rounds=str(max_rounds),
            max_feerate=max_fee_per_vbyte,
        ),
        "coinjoin_final",
        BR_CODE_OTHER,
    )


# TODO cleanup @ redesign
def confirm_sign_identity(
    proto: str, identity: str, challenge_visual: str | None
) -> Awaitable[None]:
    text = ""
    if challenge_visual:
        text += f"{challenge_visual}\n\n"
    text += identity

    return _placeholder_confirm(
        "confirm_sign_identity",
        f"{TR.words__sign} {proto}",
        text,
        br_code=BR_CODE_OTHER,
    )


LONG_MSG_PAGE_THRESHOLD = 5


async def confirm_signverify(
    message: str,
    address: str,
    verify: bool,
    path: str | None = None,
    account: str | None = None,
    chunkify: bool = False,
) -> None:
    br_name = "verify_message" if verify else "sign_message"

    message_layout = trezorui_api.confirm_value(
        title=TR.sign_message__confirm_message,
        description=None,
        value=message,
        verb=None,
        verb_cancel="^",
        hold=not verify,
        chunkify=chunkify,
    )

    # Allowing to go back from the second screen
    while True:
        await confirm_blob(
            br_name,
            TR.sign_message__confirm_address,
            address,
            verb=TR.buttons__continue,
            br_code=BR_CODE_OTHER,
        )
        try:
            if message_layout.page_count() <= LONG_MSG_PAGE_THRESHOLD:
                await raise_if_cancelled(
                    message_layout,
                    br_name,
                    BR_CODE_OTHER,
                )
            else:
                await confirm_blob(
                    br_name,
                    TR.sign_message__confirm_message,
                    message,
                    verb=None,
                    verb_cancel="^",
                    ask_pagination=True,
                    extra_confirmation_if_not_read=not verify,
                )
        except ActionCancelled:
            continue
        else:
            break


def error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> trezorui_api.LayoutObj[trezorui_api.UiResult]:
    if button:
        raise NotImplementedError("Button not implemented")

    description = description.format(description_param)
    if subtitle:
        description = f"{subtitle}\n{description}"
    return trezorui_api.show_info(
        title=title,
        description=description,
        time_ms=timeout_ms,
    )


def request_passphrase_on_host() -> None:
    draw_simple(
        trezorui_api.show_simple(
            title=None,
            text=TR.passphrase__please_enter,
        )
    )


def show_wait_text(message: str) -> None:
    draw_simple(trezorui_api.show_wait_text(message))


async def request_passphrase_on_device(max_len: int) -> str:
    result = await interact(
        trezorui_api.request_passphrase(
            prompt=TR.passphrase__title_enter,
            max_len=max_len,
        ),
        "passphrase_device",
        ButtonRequestType.PassphraseEntry,
        raise_on_cancel=ActionCancelled("Passphrase entry cancelled"),
    )
    assert isinstance(result, str)
    return result


async def request_pin_on_device(
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
    wrong_pin: bool = False,
) -> str:
    from trezor import wire

    # Not showing the prompt in case user did not enter it badly yet
    # (has full 16 attempts left)
    if attempts_remaining is None or attempts_remaining == 16:
        subprompt = ""
    elif attempts_remaining == 1:
        subprompt = TR.pin__last_attempt
    else:
        subprompt = f"{attempts_remaining} {TR.pin__tries_left}"

    result = await interact(
        trezorui_api.request_pin(
            prompt=prompt,
            subprompt=subprompt,
            allow_cancel=allow_cancel,
            wrong_pin=wrong_pin,
        ),
        "pin_device",
        ButtonRequestType.PinEntry,
        raise_on_cancel=wire.PinCancelled,
    )

    assert isinstance(result, str)
    return result


def confirm_reenter_pin(is_wipe_code: bool = False) -> Awaitable[None]:
    br_name = "reenter_wipe_code" if is_wipe_code else "reenter_pin"
    title = TR.wipe_code__title_check if is_wipe_code else TR.pin__title_check_pin
    description = (
        TR.wipe_code__reenter_to_confirm if is_wipe_code else TR.pin__reenter_to_confirm
    )
    return confirm_action(
        br_name,
        title,
        description=description,
        verb=TR.buttons__continue,
        verb_cancel=None,
        br_code=BR_CODE_OTHER,
    )


def _confirm_multiple_pages_texts(
    br_name: str,
    title: str,
    items: list[str],
    verb: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.multiple_pages_texts(
            title=title,
            verb=verb,
            items=items,
        ),
        br_name,
        br_code,
    )


def pin_mismatch_popup(is_wipe_code: bool = False) -> Awaitable[None]:
    description = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    br_name = "wipe_code_mismatch" if is_wipe_code else "pin_mismatch"
    layout = show_warning(
        br_name,
        description,
        TR.pin__please_check_again,
        TR.buttons__check_again,
        br_code=BR_CODE_OTHER,
    )
    return layout  # type: ignore ["UiResult" is incompatible with "None"]


def wipe_code_same_as_pin_popup() -> Awaitable[None]:
    return confirm_action(
        "wipe_code_same_as_pin",
        TR.wipe_code__title_invalid,
        description=TR.wipe_code__diff_from_pin,
        verb=TR.buttons__try_again,
        verb_cancel=None,
        br_code=BR_CODE_OTHER,
    )


async def confirm_set_new_pin(
    br_name: str,
    title: str,
    description: str,
    information: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> None:
    await _confirm_multiple_pages_texts(
        br_name,
        title,
        [description, information],
        TR.buttons__turn_on,
        br_code,
    )

    # Not showing extra info for wipe code
    if "wipe_code" in br_name:
        return

    # Additional information for the user to know about PIN
    next_info = [
        TR.pin__should_be_long,
        TR.pin__cursor_will_change,
    ]
    await _confirm_multiple_pages_texts(
        br_name,
        title,
        next_info,
        TR.buttons__continue,
        br_code,
    )


def confirm_change_pin(
    br_name: str,
    title: str,
    description: str,
) -> Awaitable[None]:
    return confirm_action(
        br_name,
        title,
        description=description,
        verb=TR.buttons__change,
    )


def confirm_remove_pin(
    br_name: str,
    title: str,
    description: str,
) -> Awaitable[None]:
    return confirm_action(
        br_name,
        title,
        description=description,
        verb=TR.buttons__turn_off,
    )


async def success_pin_change(curpin: str | None, newpin: str | None) -> None:
    if newpin:
        if curpin:
            msg_screen = TR.pin__changed
        else:
            msg_screen = TR.pin__enabled
    else:
        msg_screen = TR.pin__disabled

    await show_success("success_pin", msg_screen)


def confirm_firmware_update(description: str, fingerprint: str) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.confirm_firmware_update(
            description=description, fingerprint=fingerprint
        ),
        "firmware_update",
        BR_CODE_OTHER,
    )


def create_details(name: str, value: list[tuple[str, str]] | str) -> Details:
    from trezor.ui.layouts.menu import Details

    return Details.from_layout(
        name, lambda: trezorui_api.show_properties(title=name, value=value)
    )
