from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui, utils, workflow
from trezor.enums import ButtonRequestType, RecoveryType
from trezor.wire import ActionCancelled

from ..common import draw_simple, interact, raise_if_not_confirmed, with_info

if TYPE_CHECKING:
    from buffer_types import AnyBytes, StrOrBytes
    from typing import Any, Awaitable, Coroutine, Iterable, NoReturn, Sequence, TypeVar

    from trezor.messages import StellarAsset
    from trezor.ui.layouts.menu import Details

    from ..common import ExceptionType, PropertyType
    from ..slip24 import Refund, Trade

    T = TypeVar("T")


BR_CODE_OTHER = ButtonRequestType.Other  # global_import_cache

CONFIRMED = trezorui_api.CONFIRMED
CANCELLED = trezorui_api.CANCELLED
BACK = trezorui_api.BACK
INFO = trezorui_api.INFO


def confirm_action(
    br_name: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
    description_param: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    hold_danger: bool = False,
    reverse: bool = False,
    exc: ExceptionType = ActionCancelled,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    prompt_screen: bool = False,
    prompt_title: str | None = None,
) -> Awaitable[None]:
    if description is not None and description_param is not None:
        description = description.format(description_param)

    return raise_if_not_confirmed(
        trezorui_api.confirm_action(
            title=title,
            action=action,
            description=description,
            subtitle=subtitle,
            verb=verb,
            verb_cancel=verb_cancel,
            hold=hold,
            hold_danger=hold_danger,
            reverse=reverse,
            prompt_screen=prompt_screen,
            prompt_title=prompt_title or title,
        ),
        br_name,
        br_code,
        exc,
    )


def confirm_reset_device(recovery: bool = False) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.confirm_reset_device(recovery=recovery), None
    )


async def prompt_recovery_check(recovery_type: RecoveryType) -> None:
    assert recovery_type in (RecoveryType.DryRun, RecoveryType.UnlockRepeatedBackup)
    title = (
        TR.reset__check_wallet_backup_title
        if recovery_type == RecoveryType.DryRun
        else TR.recovery__title_unlock_repeated_backup
    )
    await confirm_action(
        "confirm_seedcheck",
        title,
        description=TR.recovery__check_dry_run,
        br_code=ButtonRequestType.ProtectCall,
        verb=TR.buttons__continue,
    )


async def show_wallet_created_success() -> None:
    await interact(
        trezorui_api.show_success(
            title=TR.words__title_done,
            description=TR.backup__new_wallet_created,
            button=TR.buttons__continue,
            allow_cancel=False,
        ),
        "backup_device",
        ButtonRequestType.ResetDevice,
    )


async def prompt_backup() -> bool:
    result = await interact(
        trezorui_api.prompt_backup(),
        "backup_device",
        ButtonRequestType.ResetDevice,
        raise_on_cancel=None,
    )
    return result is CONFIRMED


def confirm_path_warning(
    path: str,
    path_type: str | None = None,
) -> Awaitable[None]:
    description = (
        TR.addr_mismatch__wrong_derivation_path
        if not path_type
        else f"{TR.words__unknown} {path_type.lower()}."
    )
    return show_danger(
        "path_warning",
        description,
        value=path,
        title=TR.words__important,
        menu_title=TR.words__receive,
        verb_cancel=TR.words__cancel_and_exit,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def confirm_multisig_warning() -> Awaitable[None]:
    return show_danger(
        "warning_multisig",
        TR.send__receiving_to_multisig,
        title=TR.words__important,
        menu_title=TR.words__receive,
        verb_cancel=TR.words__cancel_and_exit,
    )


def confirm_multisig_different_paths_warning() -> Awaitable[None]:
    return show_danger(
        "warning_multisig_different_paths",
        content=TR.send__multisig_different_paths,
        title=TR.words__important,
        menu_title=TR.words__receive,
        br_code=ButtonRequestType.Warning,
        verb_cancel=TR.words__cancel_and_exit,
    )


def confirm_multiple_accounts_warning() -> Awaitable[None]:
    return show_danger(
        "sending_from_multiple_accounts",
        TR.send__from_multiple_accounts,
        title=TR.words__important,
        verb_cancel=TR.send__cancel_transaction,
        br_code=ButtonRequestType.SignTx,
    )


def lock_time_disabled_warning() -> Awaitable[None]:
    return show_warning(
        "nondefault_locktime",
        TR.bitcoin__locktime_no_effect,
        br_code=ButtonRequestType.SignTx,
    )


def confirm_homescreen(
    image: AnyBytes,
) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.confirm_homescreen(
            title=TR.homescreen__title_set,
            image=image,
        ),
        "set_homesreen",
        ButtonRequestType.ProtectCall,
    )


async def confirm_change_label(
    br_name: str, title: str, template: str, param: str
) -> None:

    await confirm_action(
        br_name=br_name,
        title=title,
        description=template.format(param),
        verb=None,
    )


def confirm_change_passphrase(use: bool) -> Awaitable[None]:
    description = TR.passphrase__turn_on if use else TR.passphrase__turn_off

    return confirm_action(
        "set_passphrase",
        TR.passphrase__title_settings,
        description=description,
        br_code=ButtonRequestType.ProtectCall,
        verb=TR.buttons__confirm,
    )


def confirm_hide_passphrase_from_host() -> Awaitable[None]:
    return confirm_action(
        "set_hide_passphrase_from_host",
        TR.passphrase__title_settings,
        description=TR.passphrase__hide,
        br_code=ButtonRequestType.ProtectCall,
        prompt_screen=True,
    )


async def confirm_hidden_passphrase_from_host() -> None:
    await confirm_action(
        "passphrase_host1_hidden",
        TR.passphrase__hidden_wallet,
        description=TR.passphrase__from_host_not_shown,
        verb=TR.passphrase__access_hidden_wallet,
    )


async def show_passphrase_from_host(passphrase: str | None) -> None:
    await confirm_action(
        "passphrase_host1",
        TR.passphrase__hidden_wallet,
        description=TR.passphrase__next_screen_will_show_passphrase,
        verb=TR.passphrase__show,
    )

    await confirm_value(
        TR.passphrase__hidden_wallet,
        passphrase or "",
        description="",
        br_name="passphrase_host2",
        verb=TR.passphrase__title_confirm,
        cancel=True,
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
        TR.passphrase__title_settings,
        description=description,
        br_code=ButtonRequestType.ProtectCall,
        verb=TR.buttons__confirm,
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
    details_title: str | None = None,
    warning: str | None = None,
    br_name: str = "show_address",
    br_code: ButtonRequestType = ButtonRequestType.Address,
    chunkify: bool = False,
) -> None:
    def xpub_title(i: int) -> str:
        result = f"Multisig XPUB #{i + 1}\n"
        result += (
            f"({TR.address__title_yours.lower()})"
            if i == multisig_index
            else f"({TR.address__title_cosigner.lower()})"
        )
        return result

    if warning is None and multisig_index is not None:
        warning = TR.send__receiving_to_multisig
    await raise_if_not_confirmed(
        trezorui_api.flow_get_address(
            address=address,
            title=title or TR.words__receive,
            subtitle=subtitle,
            description=network or "",
            hint=warning,
            chunkify=chunkify,
            address_qr=address if address_qr is None else address_qr,
            case_sensitive=case_sensitive,
            account=account,
            path=path,
            xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
            br_name=br_name,
            br_code=br_code,
        ),
        None,
    )

    show_continue_in_app(TR.address__confirmed)


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

    await raise_if_not_confirmed(
        trezorui_api.flow_get_pubkey(
            pubkey=pubkey,
            title=title or TR.address__public_key,
            subtitle=account,
            description=None,
            hint=warning,
            chunkify=False,
            pubkey_qr=pubkey,
            case_sensitive=True,
            account=account,
            path=path,
            br_name=br_name,
            br_code=ButtonRequestType.PublicKey,
        ),
        None,
    )

    show_continue_in_app(TR.address__public_key_confirmed)


async def show_error_and_raise(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    exc: ExceptionType = ActionCancelled,
) -> NoReturn:
    button = button or TR.buttons__try_again  # def_arg
    await interact(
        trezorui_api.show_error(
            title=subheader or "",
            description=content,
            button=button,
            allow_cancel=False,
        ),
        br_name,
        BR_CODE_OTHER,
        raise_on_cancel=None,
    )
    raise exc


def show_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    button = button or TR.words__continue_anyway  # def_arg
    return raise_if_not_confirmed(
        trezorui_api.show_warning(
            title=TR.words__important,
            button=button,
            description=content,
            value=subheader or "",
            danger=True,
        ),
        br_name,
        br_code,
    )


def show_danger(
    br_name: str,
    content: str,
    value: str | None = None,
    title: str | None = None,
    menu_title: str | None = None,
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    title = title or TR.words__warning
    verb_cancel = verb_cancel or TR.buttons__cancel
    return raise_if_not_confirmed(
        trezorui_api.show_danger(
            title=title,
            description=content,
            value=(value or ""),
            menu_title=menu_title,
            verb_cancel=verb_cancel,
        ),
        br_name,
        br_code,
    )


def show_success(
    br_name: str | None,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    time_ms: int = 0,
) -> Coroutine[Any, Any, None]:
    button = button or TR.buttons__continue  # def_arg
    return raise_if_not_confirmed(
        trezorui_api.show_success(
            title=subheader if subheader else TR.words__title_done,
            button=button,
            description=content,
            allow_cancel=False,
            time_ms=time_ms,
        ),
        br_name,
        ButtonRequestType.Success,
    )


def show_continue_in_app(content: str) -> None:
    task = show_success(
        content=content,
        button=TR.instructions__continue_in_app,
        time_ms=3200,
        br_name=None,
    )
    workflow.spawn(task)


async def confirm_payment_request(
    recipient_name: str,
    recipient_address: str | None,
    texts: Iterable[tuple[str | None, str]],
    refunds: Iterable[Refund],
    trades: list[Trade],
    account_items: list[PropertyType],
    transaction_fee: str | None,
    fee_info_items: Iterable[PropertyType] | None,
    extra_menu_items: list[tuple[str, str]] | None = None,
) -> None:
    from trezor.ui.layouts.menu import Menu, confirm_with_menu

    from ..slip24 import is_swap

    (title, summary_title) = (
        (TR.words__swap, TR.words__swap)
        if is_swap(trades)
        else (TR.words__confirm, TR.words__title_summary)
    )

    for t, text in texts:
        await raise_if_not_confirmed(
            trezorui_api.confirm_value(
                title=t or title,
                value=text,
                description=None,
                verb=TR.buttons__confirm,
            ),
            "confirm_payment_request",
        )

    main_layout = trezorui_api.confirm_value(
        title=title,
        subtitle=TR.words__provider,
        value=recipient_name,
        description=None,
        verb=TR.buttons__continue,
        verb_cancel=None,
        chunkify=False,
        external_menu=True,
    )

    menu_items = []
    if recipient_address is not None:
        menu_items.append(
            create_details(TR.address__title_provider_address, recipient_address)
        )
    for refund in refunds:
        refund_account_info: list[PropertyType] = [(str(""), refund.address, True)]
        if refund.account:
            refund_account_info.append((TR.words__account, refund.account, True))
        if refund.account_path:
            refund_account_info.append(
                (TR.address_details__derivation_path, refund.account_path, True)
            )
        menu_items.append(
            create_details(
                TR.address__title_refund_address,
                refund_account_info,
            )
        )
    menu = Menu.root(menu_items, TR.send__cancel_sign)

    while True:
        back_from_confirm_trade = False
        await confirm_with_menu(main_layout, menu, "confirm_payment_request")

        while True:
            back_from_confirm_trade = False

            # HACK: if we have multiple trades to confirm, we disable the back button
            # to simplify the mechanism we use here to handle it.
            # In practice, this should never happen, since normally there is only one trade in a transaction,
            # but in theory it can (since SLIP-24 supports multiple CoinPurchaseMemos...)
            can_go_back_from_trade = len(trades) == 1

            for trade in trades:
                res = await confirm_trade(
                    title,
                    TR.words__assets,
                    trade,
                    extra_menu_items or [],
                    can_go_back_from_trade,
                )
                if res is BACK:
                    back_from_confirm_trade = True
                    break

            if back_from_confirm_trade:
                break

            if transaction_fee is not None:
                res = await _confirm_summary(
                    amount=None,
                    amount_label=None,
                    fee=transaction_fee,
                    fee_label=TR.words__transaction_fee,
                    title=summary_title,
                    account_items=account_items,
                    extra_items=fee_info_items,
                    extra_title=TR.confirm_total__title_fee,
                    back_button=True,
                    br_name="confirm_payment_request",
                )
                if res is BACK:
                    continue
                else:
                    break
            else:
                break
        if back_from_confirm_trade:
            continue
        else:
            break


async def confirm_output(
    address: str,
    amount: str | None = None,
    title: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    address_label: str | None = None,
    output_index: int | None = None,
    chunkify: bool = False,
    source_account: str | None = None,
    source_account_path: str | None = None,
    cancel_text: str | None = None,
    description: str | None = None,
) -> None:
    from trezor.ui.layouts.menu import Menu, confirm_with_menu, interact_with_menu

    if address_label is not None:
        title = address_label
    elif title is not None:
        pass
    elif output_index is not None:
        title = f"{TR.words__recipient} #{output_index + 1}"
    else:
        title = TR.send__title_sending_to

    if amount is not None:
        account_properties: list[PropertyType] = []
        if source_account:
            account_properties.append((TR.words__wallet, source_account, None))
        if source_account_path:
            account_properties.append(
                (
                    TR.address_details__derivation_path,
                    source_account_path,
                    None,
                )
            )
        if account_properties:
            menu_items = [
                create_details(
                    TR.address_details__account_info,
                    account_properties,
                    title=TR.address_details__account_info,
                    subtitle=TR.send__send_from,
                )
            ]
        else:
            menu_items = []
        menu = Menu.root(
            menu_items,
            cancel=TR.buttons__cancel,
        )
        while True:
            address_layout = trezorui_api.confirm_value(
                title=TR.words__send,
                value=address,
                description=description,
                subtitle=title,
                verb=TR.buttons__continue,
                chunkify=chunkify,
                page_counter=True,  # TODO: this is for test_cardano_sign_tx_show_details - maybe we can do without?
                external_menu=True,
            )
            await confirm_with_menu(address_layout, menu, "confirm_output", br_code)

            amount_layout = trezorui_api.confirm_value(
                title=TR.words__send,
                value=amount,
                description=TR.words__amount,
                is_data=False,
                subtitle=title,
                external_menu=True,
                back_button=True,
            )
            if (
                await interact_with_menu(amount_layout, menu, "confirm_output", br_code)
                is BACK
            ):
                continue
            else:
                break
    else:
        await raise_if_not_confirmed(
            trezorui_api.flow_confirm_output(
                title=TR.words__send,
                subtitle=title,
                message=address,
                extra=None,
                chunkify=chunkify,
                text_mono=True,
                account_title=TR.send__send_from,
                account=source_account,
                account_path=source_account_path,
                address_item=None,
                extra_item=None,
                br_code=br_code,
                br_name="confirm_output",
                summary_items=None,
                fee_items=None,
                summary_title=None,
                summary_br_name=None,
                summary_br_code=None,
                cancel_text=cancel_text,
                description=description,
            ),
            br_name=None,
        )


async def should_show_more(
    title: str,
    para: Iterable[tuple[str | bytes, bool]],
    button_text: str | None = None,
    br_name: str = "should_show_more",
    br_code: ButtonRequestType = BR_CODE_OTHER,
    confirm: str | bytes | None = None,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """
    button_text = button_text or TR.buttons__show_all  # def_arg
    if confirm is None or not isinstance(confirm, str):
        confirm = TR.buttons__confirm

    result = await interact(
        trezorui_api.confirm_with_info(
            title=title,
            items=para,
            verb=confirm,
            verb_info=button_text,
        ),
        br_name,
        br_code,
    )

    if result is CONFIRMED:
        return False
    elif result is INFO:
        return True
    else:
        assert result is CANCELLED
        raise ActionCancelled


def confirm_blob(
    br_name: str,
    title: str,
    data: StrOrBytes,
    description: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    ask_pagination: bool = False,
    verb_skip_pagination: str | None = None,
    chunkify: bool = False,
    _prompt_screen: bool = True,
) -> Awaitable[None]:

    if ask_pagination:
        main_layout = trezorui_api.confirm_value_intro(
            title=title,
            value=data,
            subtitle=description,
            verb=verb_skip_pagination or verb,
            verb_cancel=verb_cancel,
            hold=hold,
            chunkify=chunkify,
        )
        info_layout = trezorui_api.confirm_value(
            title=subtitle or title,
            description=None,
            value=data,
            info=False,
            hold=hold,
            chunkify=chunkify,
            page_counter=True,
            cancel=True,
        )

        return with_info(
            main_layout,
            info_layout,
            br_name,
            br_code,
            repeat_button_request=True,
            info_layout_can_confirm=True,
        )
    else:
        layout = trezorui_api.confirm_value(
            title=title,
            value=data,
            description=description,
            subtitle=subtitle,
            verb=verb,
            hold=hold,
            chunkify=chunkify,
            cancel=True,
        )
        return raise_if_not_confirmed(
            layout,
            br_name,
            br_code,
        )


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
    return confirm_value(
        title,
        address,
        description or "",
        br_name or "confirm_address",
        br_code,
        subtitle=subtitle,
        verb=verb,
        chunkify=chunkify,
        warning_footer=warning_footer,
        cancel=True,
    )


def confirm_text(
    br_name: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    return confirm_value(
        title,
        data,
        description or "",
        br_name,
        br_code,
    )


def confirm_amount(
    title: str,
    amount: str,
    description: str | None = None,
    br_name: str = "confirm_amount",
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    description = description or f"{TR.words__send}:"  # def_arg
    return confirm_value(
        title,
        amount,
        description,
        br_name,
        br_code,
    )


def confirm_value(
    title: str,
    value: str,
    description: str,
    br_name: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    *,
    verb: str | None = None,
    subtitle: str | None = None,
    hold: bool = False,
    is_data: bool = True,
    chunkify: bool = False,
    info_items: Iterable[PropertyType] | None = None,
    info_title: str | None = None,
    chunkify_info: bool = False,
    warning_footer: str | None = None,
    cancel: bool = False,
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    items: list[PropertyType] = list(info_items) if info_items else []
    info_layout = trezorui_api.show_info_with_cancel(
        title=info_title if info_title else TR.words__title_information,
        items=items,
        chunkify=chunkify_info,
    )

    return with_info(
        trezorui_api.confirm_value(
            title=title,
            value=value,
            is_data=is_data,
            description=description,
            subtitle=subtitle,
            verb=verb,
            info=bool(info_items),
            hold=hold,
            chunkify=chunkify,
            warning_footer=warning_footer,
            cancel=cancel,
        ),
        info_layout,
        br_name,
        br_code,
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

    if subtitle:
        title += ": " + subtitle

    return raise_if_not_confirmed(
        trezorui_api.confirm_properties(
            title=title,
            items=list(props),
            hold=hold,
            verb=verb,
        ),
        br_name,
        br_code,
    )


def confirm_total(
    total_amount: str,
    fee_amount: str,
    title: str | None = None,
    total_label: str | None = None,
    fee_label: str | None = None,
    source_account: str | None = None,
    source_account_path: str | None = None,
    fee_rate_amount: str | None = None,
    br_name: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> Awaitable[None]:
    title = title or TR.words__send  # def_arg
    total_label = total_label or TR.send__total_amount  # def_arg
    fee_label = fee_label or TR.send__incl_transaction_fee  # def_arg

    fee_items: list[PropertyType] = []
    account_items: list[PropertyType] = []
    if source_account:
        account_items.append((TR.words__account, source_account, True))
    if source_account_path:
        account_items.append(
            (TR.address_details__derivation_path, source_account_path, True)
        )
    if fee_rate_amount:
        fee_items.append((TR.confirm_total__fee_rate, fee_rate_amount, True))

    return raise_if_not_confirmed(
        trezorui_api.confirm_summary(
            amount=total_amount,
            amount_label=total_label,
            fee=fee_amount,
            fee_label=fee_label,
            title=title,
            account_items=account_items or None,
            extra_items=fee_items or None,
            extra_title=TR.confirm_total__title_fee,
        ),
        br_name,
        br_code,
    )


def _confirm_summary(
    amount: str | None,
    amount_label: str | None,
    fee: str,
    fee_label: str,
    title: str | None = None,
    account_items: Iterable[PropertyType] | None = None,
    account_title: str | None = None,
    extra_items: Iterable[PropertyType] | None = None,
    extra_title: str | None = None,
    back_button: bool = False,
    br_name: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> Awaitable[None]:
    title = title or TR.words__send  # def_arg
    account_props: list[PropertyType] | None = (
        list(account_items) if account_items else None
    )
    extra_props: list[PropertyType] | None = list(extra_items) if extra_items else None
    return raise_if_not_confirmed(
        trezorui_api.confirm_summary(
            amount=amount,
            amount_label=amount_label,
            fee=fee,
            fee_label=fee_label,
            title=title,
            account_items=account_props,
            account_title=account_title,
            extra_items=extra_props,
            extra_title=extra_title or None,
            back_button=back_button,
        ),
        br_name,
        br_code,
    )


def confirm_trade(
    title: str,
    subtitle: str,
    trade: Trade,
    extra_menu_items: list[tuple[str, str]],
    back_button: bool,
) -> Awaitable[ui.UiResult]:
    from trezor.ui.layouts.menu import Menu, interact_with_menu

    trade_layout = trezorui_api.confirm_trade(
        title=title,
        subtitle=subtitle,
        sell_amount=trade.sell_amount,
        buy_amount=trade.buy_amount,
        back_button=back_button,
    )

    account_info: list[PropertyType] = [("", trade.address, True)]
    if trade.account:
        account_info.append((TR.words__account, trade.account, True))
    if trade.account_path:
        account_info.append(
            (TR.address_details__derivation_path, trade.account_path, True)
        )
    menu_items = [create_details(TR.address__title_receive_address, account_info)]
    for k, v in extra_menu_items:
        menu_items.append(create_details(k, v))
    menu = Menu.root(menu_items, TR.send__cancel_sign)

    return interact_with_menu(trade_layout, menu, "confirm_trade")


if not utils.BITCOIN_ONLY:

    def confirm_ethereum_unknown_contract_warning(title: str | None) -> Awaitable[None]:
        return show_danger(
            "unknown_contract_warning",
            f"{TR.ethereum__unknown_contract_address} {TR.words__know_what_your_doing}",
            title=TR.words__important,
            menu_title=title,
            verb_cancel=TR.send__cancel_sign,
        )

    def confirm_solana_unknown_token_warning() -> Awaitable[None]:
        return show_danger(
            "unknown_token_warning",
            content=f"{TR.solana__unknown_token_address}. {TR.words__know_what_your_doing}",
            verb_cancel=TR.send__cancel_sign,
        )

    async def confirm_ethereum_tx(
        recipient: str | None,
        total_amount: str,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        fee_info_items: Iterable[PropertyType],
        is_contract_interaction: bool,
        br_name: str = "confirm_total",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
        chunkify: bool = False,
    ) -> None:
        subtitle = (
            None
            if is_contract_interaction and recipient is None
            else (
                TR.ethereum__interaction_contract
                if is_contract_interaction
                else TR.words__recipient
            )
        )
        title = TR.words__send
        fee_items: list[PropertyType] | None = (
            list(fee_info_items) if fee_info_items else None
        )
        await raise_if_not_confirmed(
            trezorui_api.flow_confirm_output(
                title=title,
                subtitle=subtitle,
                description=None,
                extra=None,
                message=(recipient or TR.ethereum__new_contract),
                chunkify=(chunkify if recipient else False),
                text_mono=(True if recipient else False),
                account_title=TR.send__send_from,
                account=account,
                account_path=account_path,
                address_item=None,
                extra_item=None,
                br_code=br_code,
                br_name="confirm_output",
                summary_items=[
                    (TR.words__amount, total_amount, True),
                    (TR.send__maximum_fee, maximum_fee, True),
                ],
                fee_items=fee_items,
                summary_title=title,
                summary_br_name=br_name,
                summary_br_code=br_code,
                cancel_text=TR.buttons__cancel,
            ),
            None,
        )

    def ethereum_address_title() -> str:
        """Return the title for the Ethereum address confirmation."""
        return TR.words__send

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
        fee_info_items: Iterable[PropertyType],
        chunkify: bool = False,
    ) -> None:

        br_name = "confirm_ethereum_approve"
        br_code = ButtonRequestType.Other
        title = (
            TR.ethereum__approve_intro_title_revoke
            if is_revoke
            else TR.ethereum__approve_intro_title
        )

        await confirm_action(
            br_name,
            title,
            (
                TR.ethereum__approve_intro_revoke
                if is_revoke
                else TR.ethereum__approve_intro
            ),
            verb=TR.buttons__continue,
        )

        if recipient_str is None:
            await confirm_value(
                title,
                recipient_addr,
                "",
                subtitle=(
                    TR.ethereum__approve_revoke_from
                    if is_revoke
                    else TR.ethereum__approve_to
                ),
                chunkify=chunkify,
                br_name=br_name,
                verb=TR.buttons__continue,
                cancel=True,
            )
        else:
            main_layout = trezorui_api.confirm_with_info(
                title=title,
                subtitle=(
                    TR.ethereum__approve_revoke_from
                    if is_revoke
                    else TR.ethereum__approve_to
                ),
                items=[(recipient_str, True)],
                verb=TR.buttons__continue,
                verb_info=TR.ethereum__contract_address,
            )
            items: list[PropertyType] = [("", recipient_addr, True)]
            info_layout = trezorui_api.show_info_with_cancel(
                title=title,
                items=items,
                chunkify=chunkify,
            )
            await with_info(main_layout, info_layout, br_name, br_code)

        if total_amount is None:
            await show_warning(
                br_name,
                TR.ethereum__approve_unlimited_template.format(token_symbol),
            )

        if is_unknown_token:
            await confirm_value(
                TR.words__send,
                token_address,
                "",
                subtitle=TR.ethereum__token_contract,
                chunkify=chunkify,
                br_name=br_name,
                cancel=True,
            )

        if is_unknown_network:
            assert is_unknown_token
            await confirm_value(
                title,
                chain_id,
                TR.ethereum__approve_chain_id,
                br_name=br_name,
                cancel=True,
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
            br_name,
            title,
            properties,
            None,
            False,
            verb=TR.buttons__continue,
        )

        account_items: list[PropertyType] | None = (
            [(TR.address_details__derivation_path, account_path, True)]
            if account_path
            else None
        )

        await _confirm_summary(
            None,
            None,
            maximum_fee,
            TR.send__maximum_fee,
            title,
            account_items,
            None,
            fee_info_items,
            TR.confirm_total__title_fee,
        )

    async def confirm_ethereum_staking_tx(
        title: str,
        intro_question: str,
        verb: str,
        total_amount: str,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        address: str,
        address_title: str,
        info_items: Iterable[PropertyType],
        chunkify: bool = False,
        br_name: str = "confirm_ethereum_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        summary_items: list[PropertyType] = []
        if verb == TR.ethereum__staking_claim:
            summary_items.extend([(TR.send__maximum_fee, maximum_fee, True)])
        else:
            summary_items.extend(
                [
                    (TR.words__amount, total_amount, True),
                    (TR.send__maximum_fee, maximum_fee, True),
                ]
            )
        fee_items: list[PropertyType] | None = list(info_items) if info_items else None
        await raise_if_not_confirmed(
            trezorui_api.flow_confirm_output(
                title=verb,
                subtitle=None,
                description=None,
                extra=None,
                message=intro_question,
                chunkify=False,
                text_mono=False,
                account_title=TR.address_details__account_info,
                account=account,
                account_path=account_path,
                br_code=br_code,
                br_name=br_name,
                address_item=(address_title, address, True),
                extra_item=None,
                summary_items=summary_items,
                fee_items=fee_items,
                summary_title=verb,
                summary_br_name="confirm_total",
                summary_br_code=ButtonRequestType.SignTx,
                cancel_text=TR.buttons__cancel,  # cancel staking
            ),
            br_name=None,
        )

    def confirm_solana_recipient(
        recipient: str,
        title: str,
        items: Iterable[PropertyType] = (),
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
            cancel=True,
        )

    def confirm_solana_tx(
        amount: str,
        fee: str,
        items: Iterable[PropertyType],
        amount_title: str | None = None,
        fee_title: str | None = None,
        br_name: str = "confirm_solana_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> Awaitable[None]:
        amount_title = (
            amount_title if amount_title is not None else f"{TR.words__amount}:"
        )  # def_arg
        fee_title = fee_title or TR.words__fee  # def_arg
        return _confirm_summary(
            amount,
            amount_title,
            fee,
            fee_title,
            extra_items=list(items) if items else None,
            br_name=br_name,
            br_code=br_code,
        )

    async def confirm_solana_staking_tx(
        title: str,
        description: str,
        account: str,
        account_path: str,
        vote_account: str,
        stake_item: PropertyType | None,
        amount_item: PropertyType | None,
        fee_item: PropertyType,
        fee_details: Iterable[PropertyType],
        blockhash_item: PropertyType,
        br_name: str = "confirm_solana_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        summary_items: list[PropertyType] = [fee_item]
        if amount_item:
            summary_items.append(amount_item)
        await raise_if_not_confirmed(
            trezorui_api.flow_confirm_output(
                title=title,
                subtitle=None,
                description=description,
                extra=TR.words__provider if vote_account else None,
                message=vote_account,
                chunkify=True,
                text_mono=True,
                account_title=TR.address_details__account_info,
                account=account,
                account_path=account_path,
                br_code=br_code,
                br_name=br_name,
                address_item=stake_item,
                extra_item=blockhash_item,
                fee_items=list(fee_details) if fee_details else None,
                summary_title=title,
                summary_items=summary_items,
                summary_br_name="confirm_total",
                summary_br_code=ButtonRequestType.SignTx,
                cancel_text=TR.buttons__cancel,
            ),
            br_name=None,
        )

    def confirm_cardano_tx(
        amount: str,
        fee: str,
        items: Iterable[PropertyType],
    ) -> Awaitable[None]:
        amount_title = TR.send__total_amount
        fee_title = TR.send__incl_transaction_fee
        return _confirm_summary(
            amount,
            amount_title,
            fee,
            fee_title,
            extra_items=items,
            br_name="confirm_cardano_tx",
            br_code=ButtonRequestType.SignTx,
        )

    def confirm_stellar_tx(
        fee: str,
        account_name: str,
        account_path: str,
        is_sending_from_trezor_account: bool,
        extra_items: Iterable[PropertyType],
    ) -> Awaitable[None]:
        return _confirm_summary(
            None,
            None,
            fee,
            TR.send__maximum_fee,
            account_items=[
                (TR.words__account, account_name, None),
                (TR.address_details__derivation_path, account_path, None),
            ],
            account_title=(
                TR.send__send_from
                if is_sending_from_trezor_account
                else TR.stellar__sign_with
            ),
            extra_items=extra_items,
            extra_title=TR.stellar__timebounds,
            br_name="confirm_stellar_tx",
            br_code=ButtonRequestType.SignTx,
        )

    async def confirm_stellar_output(
        address: str,
        amount: str,
        output_index: int,
        asset: StellarAsset,
    ) -> None:
        from trezor.enums import StellarAssetType

        subtitle = f"{TR.words__recipient} #{output_index + 1}"
        await confirm_address(
            TR.words__address,
            address,
            subtitle=subtitle,
            br_name="confirm_output_address",
            br_code=ButtonRequestType.ConfirmOutput,
        )

        info_items = []
        if asset.type != StellarAssetType.NATIVE:
            info_items = [
                (
                    TR.stellar__issuer_template.format(asset.code),
                    asset.issuer or "",
                    None,
                )
            ]

        await confirm_value(
            TR.words__amount,
            amount,
            description="",
            subtitle=subtitle,
            br_name="confirm_output_amount",
            br_code=ButtonRequestType.ConfirmOutput,
            info_items=info_items,
            info_title=TR.stellar__token_info,
            is_data=False,
            chunkify_info=True,
            chunkify=False,
        )


def confirm_joint_total(spending_amount: str, total_amount: str) -> Awaitable[None]:
    return _confirm_summary(
        spending_amount,
        TR.send__you_are_contributing,
        total_amount,
        TR.send__to_the_total_amount,
        title=TR.send__title_joint_transaction,
        br_name="confirm_joint_total",
        br_code=ButtonRequestType.SignTx,
    )


def confirm_metadata(
    br_name: str,
    title: str,
    content: str,
    param: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hold: bool = False,
    verb: str | None = None,
) -> Awaitable[None]:
    verb = verb or TR.buttons__continue  # def_arg
    return confirm_action(
        br_name,
        title=title,
        action="",
        description=content,
        description_param=param,
        verb=verb,
        hold=hold,
        br_code=br_code,
    )


def confirm_replacement(title: str, txid: str) -> Awaitable[None]:
    return confirm_blob(
        "confirm_replacement",
        title,
        txid,
        subtitle=TR.send__transaction_id,
        verb=TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_modify_output(
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    address_layout = trezorui_api.confirm_value(
        title=TR.modify_amount__title,
        subtitle=TR.words__address,
        value=address,
        verb=TR.buttons__continue,
        cancel=True,
        is_data=True,
        description=None,
    )
    modify_layout = trezorui_api.confirm_modify_output(
        sign=sign,
        amount_change=amount_change,
        amount_new=amount_new,
    )

    send_button_request = True
    while True:
        await raise_if_not_confirmed(
            address_layout,
            "modify_output" if send_button_request else None,
            ButtonRequestType.ConfirmOutput,
        )
        result = await interact(
            modify_layout,
            "modify_output" if send_button_request else None,
            ButtonRequestType.ConfirmOutput,
            raise_on_cancel=None,
        )
        send_button_request = False

        if result is CONFIRMED:
            break


def confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> Awaitable[None]:
    fee_layout = trezorui_api.confirm_modify_fee(
        title=title,
        sign=sign,
        user_fee_change=user_fee_change,
        total_fee_new=total_fee_new,
        fee_rate_amount=fee_rate_amount,
    )
    items: list[PropertyType] = []
    if fee_rate_amount:
        items.append((TR.bitcoin__new_fee_rate, fee_rate_amount, True))
    info_layout = trezorui_api.show_info_with_cancel(
        title=TR.confirm_total__title_fee,
        items=items,
    )
    return with_info(fee_layout, info_layout, "modify_fee", ButtonRequestType.SignTx)


def confirm_coinjoin(max_rounds: int, max_fee_per_vbyte: str) -> Awaitable[None]:
    return raise_if_not_confirmed(
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
    return confirm_blob(
        "sign_identity",
        f"{TR.words__sign} {proto}",
        identity,
        challenge_visual + "\n" if challenge_visual else "",
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
    if verify:
        address_title = TR.sign_message__verify_address
        br_name = "verify_message"
    else:
        address_title = TR.sign_message__confirm_address
        br_name = "sign_message"

    address_layout = trezorui_api.confirm_value(
        title=address_title,
        value=address,
        description=None,
        is_data=True,
        verb=TR.buttons__continue,
        info=True,
        chunkify=chunkify,
        cancel=True,
    )

    items: list[PropertyType] = []
    if account is not None:
        items.append((TR.words__account, account, True))
    if path is not None:
        items.append((TR.address_details__derivation_path, path, True))
    items.append(
        (
            TR.sign_message__message_size,
            TR.sign_message__bytes_template.format(len(message)),
            True,
        )
    )

    info_layout = trezorui_api.show_info_with_cancel(
        title=TR.words__title_information,
        items=items,
        horizontal=True,
    )

    while True:
        try:
            await with_info(address_layout, info_layout, br_name, br_code=BR_CODE_OTHER)
        except ActionCancelled:
            result = await interact(
                trezorui_api.show_mismatch(title=TR.addr_mismatch__mismatch),
                None,
                raise_on_cancel=None,
            )
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise
            continue
        else:
            break

    message_layout = trezorui_api.confirm_value(
        title=TR.sign_message__confirm_message,
        description=None,
        value=message,
        extra=None,
        prompt_screen=True,
        hold=not verify,
        info=False,
        cancel=True,
    )

    if message_layout.page_count() <= LONG_MSG_PAGE_THRESHOLD:
        await interact(message_layout, br_name, BR_CODE_OTHER)
    else:
        await confirm_blob(
            br_name,
            TR.sign_message__confirm_message,
            message,
            br_code=BR_CODE_OTHER,
            hold=not verify,
            ask_pagination=True,
            verb_skip_pagination=TR.buttons__confirm,
        )


def error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> ui.LayoutObj[ui.UiResult]:
    if not button and not timeout_ms:
        raise ValueError("Either button or timeout_ms must be set")

    if subtitle:
        title += f"\n{subtitle}"
    return trezorui_api.show_error(
        title=title,
        description=description.format(description_param),
        button=button,
        time_ms=timeout_ms,
        allow_cancel=False,
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


def request_passphrase_on_device(max_len: int) -> Awaitable[str]:
    result = interact(
        trezorui_api.request_passphrase(
            prompt=TR.passphrase__title_enter,
            prompt_empty=TR.passphrase__continue_with_empty_passphrase,
            max_len=max_len,
        ),
        "passphrase_device",
        ButtonRequestType.PassphraseEntry,
        raise_on_cancel=ActionCancelled("Passphrase entry cancelled"),
    )
    return result  # type: ignore ["UiResult" is not assignable to "str"]


def request_pin_on_device(
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
    wrong_pin: bool = False,
) -> Awaitable[str]:
    from trezor.wire import PinCancelled

    if attempts_remaining is None:
        attempts = ""
        last_attempt = False
    elif attempts_remaining == 1:
        attempts = TR.pin__last_attempt
        last_attempt = True
    else:
        attempts = f"{attempts_remaining}\n{TR.pin__tries_left}"
        last_attempt = False

    result = interact(
        trezorui_api.request_pin(
            prompt=prompt,
            attempts=attempts,
            allow_cancel=allow_cancel,
            wrong_pin=wrong_pin,
            last_attempt=last_attempt,
        ),
        "pin_device",
        ButtonRequestType.PinEntry,
        raise_on_cancel=PinCancelled,
    )
    return result  # type: ignore ["UiResult" is not assignable to "str"]


async def confirm_reenter_pin(is_wipe_code: bool = False) -> None:
    """Not supported for Eckhart."""
    pass


def pin_mismatch_popup(is_wipe_code: bool = False) -> Awaitable[ui.UiResult]:
    description = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    button = TR.wipe_code__enter_new if is_wipe_code else TR.pin__reenter
    br_name = "wipe_code_mismatch" if is_wipe_code else "pin_mismatch"

    return interact(
        error_popup(
            TR.words__important,
            description,
            button=button,
        ),
        br_name,
        BR_CODE_OTHER,
    )


def wipe_code_same_as_pin_popup() -> Awaitable[ui.UiResult]:
    return interact(
        error_popup(
            TR.words__important,
            TR.wipe_code__diff_from_pin,
            button=TR.buttons__try_again,
        ),
        "wipe_code_same_as_pin",
        BR_CODE_OTHER,
    )


async def wipe_code_pin_not_set_popup(
    title: str, description: str, button: str
) -> NoReturn:
    await show_error_and_raise(
        "warning_pin_not_set",
        description,
        TR.words__important,
        button,
    )


async def pin_wipe_code_exists_popup(
    title: str, description: str, button: str
) -> NoReturn:
    await show_error_and_raise(
        "wipe_code_exists",
        description,
        TR.words__important,
        button,
    )


def confirm_set_new_code(
    is_wipe_code: bool,
) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.flow_confirm_set_new_code(is_wipe_code=is_wipe_code),
        "set_wipe_code" if is_wipe_code else "set_pin",
        BR_CODE_OTHER,
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
        verb=TR.buttons__continue,
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
        verb=TR.buttons__continue,
    )


async def success_pin_change(curpin: str | None, newpin: str | None) -> None:
    if newpin:
        if curpin:
            msg_screen = TR.pin__changed
        else:
            msg_screen = TR.pin__setup_completed
    else:
        msg_screen = TR.pin__disabled

    await show_success("success_pin", msg_screen, button=TR.buttons__close)


def confirm_firmware_update(description: str, fingerprint: str) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.confirm_firmware_update(
            description=description, fingerprint=fingerprint
        ),
        "firmware_update",
        BR_CODE_OTHER,
    )


def set_brightness(current: int | None = None) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.set_brightness(current=current),
        "set_brightness",
        BR_CODE_OTHER,
    )


def tutorial(br_code: ButtonRequestType = BR_CODE_OTHER) -> Awaitable[None]:
    """Showing users how to interact with the device."""
    return raise_if_not_confirmed(
        trezorui_api.tutorial(),
        "tutorial",
        br_code,
    )


def create_details(
    name: str,
    value: list[PropertyType] | str,
    title: str | None = None,
    subtitle: str | None = None,
) -> Details:
    from trezor.ui.layouts.menu import Details

    return Details.from_layout(
        name,
        lambda: trezorui_api.show_properties(
            title=(title or name), subtitle=subtitle, value=value
        ),
    )
