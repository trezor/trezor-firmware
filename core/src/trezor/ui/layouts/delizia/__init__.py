from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui, utils, workflow
from trezor.enums import ButtonRequestType, RecoveryType
from trezor.wire import ActionCancelled

from ..common import draw_simple, interact, raise_if_cancelled, with_info

if TYPE_CHECKING:
    from typing import Any, Awaitable, Coroutine, Iterable, NoReturn, Sequence, TypeVar

    from ..common import ExceptionType, PropertyType
    from ..menu import Details

    T = TypeVar("T")


BR_CODE_OTHER = ButtonRequestType.Other  # global_import_cache

CONFIRMED = trezorui_api.CONFIRMED
CANCELLED = trezorui_api.CANCELLED
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
    from trezor.ui.layouts.menu import Menu, confirm_with_menu

    if description is not None and description_param is not None:
        description = description.format(description_param)

    flow = trezorui_api.confirm_action(
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
        external_menu=not (prompt_screen or hold),
    )

    if prompt_screen or hold:
        # Note: multi-step confirm (prompt_screen/hold)
        # can't work with external menus yet
        return raise_if_cancelled(
            flow,
            br_name,
            br_code,
            exc,
        )
    else:
        menu = Menu.root(
            cancel=verb_cancel or TR.buttons__cancel,
        )

        return confirm_with_menu(
            flow,
            menu,
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
    assert template_str in description

    begin, _separator, end = description.partition(template_str)
    return raise_if_cancelled(
        trezorui_api.confirm_emphasized(
            title=title,
            items=(begin, (True, description_param), end),
            verb=verb,
        ),
        br_name,
        ButtonRequestType.ProtectCall,
    )


def confirm_reset_device(recovery: bool = False) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.confirm_reset_device(recovery=recovery), None
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
    await interact(
        trezorui_api.show_success(title=TR.backup__new_wallet_created, button=""),
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
        verb_cancel=TR.words__cancel_and_exit,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def confirm_multisig_warning() -> Awaitable[None]:
    return show_danger(
        "warning_multisig",
        TR.send__receiving_to_multisig,
        title=TR.words__important,
        verb_cancel=TR.words__cancel_and_exit,
    )


def confirm_multisig_different_paths_warning() -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.show_danger(
            title=f"{TR.words__important}!",
            description=TR.send__multisig_different_paths,
        ),
        "warning_multisig_different_paths",
        br_code=ButtonRequestType.Warning,
    )


def confirm_multiple_accounts_warning() -> Awaitable[None]:
    return show_danger(
        "sending_from_multiple_accounts",
        TR.send__from_multiple_accounts,
        verb_cancel=TR.send__cancel_transaction,
        br_code=ButtonRequestType.SignTx,
    )


def lock_time_disabled_warning() -> Awaitable[None]:
    return show_warning(
        "nondefault_locktime",
        TR.bitcoin__locktime_no_effect,
        TR.words__continue_anyway_question,
        button=TR.buttons__continue,
        br_code=ButtonRequestType.SignTx,
    )


def confirm_homescreen(
    image: bytes,
) -> Awaitable[None]:

    from trezor import workflow

    # Closing current homescreen workflow unlocks internal ImageBuffer,
    # in order to display the new homescreen image.
    workflow.close_others()

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

    return confirm_action(
        "set_passphrase",
        TR.passphrase__title_passphrase,
        subtitle=TR.words__settings,
        description=description,
        br_code=ButtonRequestType.ProtectCall,
        prompt_screen=True,
    )


def confirm_hide_passphrase_from_host() -> Awaitable[None]:
    return confirm_action(
        "set_hide_passphrase_from_host",
        TR.passphrase__title_passphrase,
        subtitle=TR.words__settings,
        description=TR.passphrase__hide,
        br_code=ButtonRequestType.ProtectCall,
        prompt_screen=True,
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
        TR.passphrase__title_passphrase,
        subtitle=TR.words__settings,
        description=description,
        br_code=ButtonRequestType.ProtectCall,
        prompt_screen=True,
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

    await raise_if_cancelled(
        trezorui_api.flow_get_address(
            address=address,
            title=title or TR.address__title_receive_address,
            subtitle=None,
            description=network or "",
            hint=None,
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

    await raise_if_cancelled(
        trezorui_api.flow_get_pubkey(
            pubkey=pubkey,
            title=title or title or TR.address__public_key,
            subtitle=None,
            description=None,
            hint=None,
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
    button = button or TR.buttons__continue  # def_arg
    return raise_if_cancelled(
        trezorui_api.show_warning(
            title=TR.words__important,
            value=content,
            button=subheader or TR.words__continue_anyway_question,
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
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    title = title or TR.words__warning
    verb_cancel = verb_cancel or TR.buttons__cancel
    return raise_if_cancelled(
        trezorui_api.show_danger(
            title=title,
            description=content,
            value=(value or ""),
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
    return raise_if_cancelled(
        trezorui_api.show_success(
            title=content,
            button=button or "",
            description=subheader or "",
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
    if address_label is not None:
        title = address_label
    elif title is not None:
        pass
    elif output_index is not None:
        title = f"{TR.words__recipient} #{output_index + 1}"
    else:
        title = TR.send__title_sending_to

    await raise_if_cancelled(
        trezorui_api.flow_confirm_output(
            title=TR.words__address,
            subtitle=title,
            message=address,
            extra=None,
            amount=amount,
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


async def should_show_payment_request_details(
    recipient_name: str,
    amount: str,
    memos: list[str],
) -> bool:
    """Return True if the user wants to show payment request details (they click a
    special button) and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """
    result = await interact(
        trezorui_api.confirm_with_info(
            title=TR.send__title_sending,
            items=[(f"{amount} to\n{recipient_name}", False)]
            + [(memo, False) for memo in memos],
            verb=TR.buttons__confirm,
            verb_info=TR.buttons__details,
        ),
        "confirm_payment_request",
        ButtonRequestType.ConfirmOutput,
    )

    if result is CONFIRMED:
        return False
    elif result is INFO:
        return True
    else:
        raise ActionCancelled


async def should_show_more(
    title: str,
    para: Iterable[tuple[str | bytes, bool]],
    button_text: str | None = None,
    br_name: str = "should_show_more",
    br_code: ButtonRequestType = BR_CODE_OTHER,
    confirm: str | None = None,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """
    button_text = button_text or TR.buttons__show_all  # def_arg

    result = await interact(
        trezorui_api.confirm_with_info(
            title=title,
            items=para,
            verb=confirm or TR.buttons__confirm,
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
    data: bytes | str,
    description: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    info: bool = True,
    hold: bool = False,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    ask_pagination: bool = False,
    verb_skip_pagination: str | None = None,
    chunkify: bool = False,
    prompt_screen: bool = True,
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
            title=title,
            value=data,
            subtitle=description,
            description=None,
            verb=None,
            verb_cancel=verb_cancel,
            info=False,
            hold=hold,
            chunkify=chunkify,
            page_counter=True,
            prompt_screen=prompt_screen,
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
            verb_cancel=verb_cancel,
            info=info,
            hold=hold,
            chunkify=chunkify,
            prompt_screen=prompt_screen,
        )
        return raise_if_cancelled(
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
        verb=(verb or TR.buttons__confirm),
        chunkify=chunkify,
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
        verb=TR.buttons__confirm,
    )


def confirm_amount(
    title: str,
    amount: str,
    description: str | None = None,
    br_name: str = "confirm_amount",
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    description = description or f"{TR.words__amount}:"  # def_arg
    return confirm_value(
        title,
        amount,
        description,
        br_name,
        br_code,
        verb=TR.buttons__confirm,
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
    info_items: Iterable[tuple[str, str]] | None = None,
    info_title: str | None = None,
    chunkify_info: bool = False,
    cancel: bool = False,
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    info_items = info_items or []
    info_layout = trezorui_api.show_info_with_cancel(
        title=info_title if info_title else TR.words__title_information,
        items=info_items,
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

    return raise_if_cancelled(
        trezorui_api.confirm_properties(
            title=title,
            subtitle=subtitle,
            items=list(props),
            hold=hold,
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
    title = title or TR.words__title_summary  # def_arg
    total_label = total_label or TR.send__total_amount  # def_arg
    fee_label = fee_label or TR.send__incl_transaction_fee  # def_arg

    fee_items = []
    account_items = []
    if source_account:
        account_items.append((TR.confirm_total__sending_from_account, source_account))
    if source_account_path:
        account_items.append((TR.address_details__derivation_path, source_account_path))
    if fee_rate_amount:
        fee_items.append((TR.confirm_total__fee_rate, fee_rate_amount))

    return raise_if_cancelled(
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
    account_items: Iterable[tuple[str, str]] | None = None,
    extra_items: Iterable[tuple[str, str]] | None = None,
    extra_title: str | None = None,
    br_name: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> Awaitable[None]:
    title = title or TR.words__title_summary  # def_arg

    return raise_if_cancelled(
        trezorui_api.confirm_summary(
            amount=amount,
            amount_label=amount_label,
            fee=fee,
            fee_label=fee_label,
            title=title,
            account_items=account_items or None,
            extra_items=extra_items or None,
            extra_title=extra_title or None,
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
            content=f"{TR.ethereum__unknown_contract_address}. {TR.words__know_what_your_doing}",
            verb_cancel=TR.send__cancel_sign,
        )

    async def confirm_ethereum_tx(
        recipient: str | None,
        total_amount: str,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        fee_info_items: Iterable[tuple[str, str]],
        is_contract_interaction: bool,
        br_name: str = "confirm_ethereum_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
        chunkify: bool = False,
    ) -> None:
        await raise_if_cancelled(
            trezorui_api.flow_confirm_output(
                title=TR.words__address,
                subtitle=(
                    TR.words__recipient
                    if not is_contract_interaction
                    else TR.ethereum__interaction_contract
                ),
                description=None,
                extra=None,
                message=(recipient or TR.ethereum__new_contract),
                amount=None,
                chunkify=(chunkify if recipient else False),
                text_mono=True,
                account_title=TR.send__send_from,
                account=account,
                account_path=account_path,
                address_item=None,
                extra_item=None,
                br_code=ButtonRequestType.SignTx,
                br_name="confirm_output",
                summary_items=(
                    (TR.words__amount, total_amount),
                    (TR.send__maximum_fee, maximum_fee),
                ),
                fee_items=fee_info_items,
                summary_title=TR.words__title_summary,
                summary_br_name="confirm_total",
                summary_br_code=ButtonRequestType.SignTx,
                cancel_text=TR.buttons__cancel,
            ),
            None,
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
        br_name = "confirm_ethereum_approve"
        br_code = ButtonRequestType.Other
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
            "",
            is_data=False,
            br_name=br_name,
        )

        title = (
            TR.ethereum__approve_revoke_from if is_revoke else TR.ethereum__approve_to
        )

        if recipient_str is None:
            await confirm_value(
                title,
                recipient_addr,
                "",
                chunkify=chunkify,
                br_name=br_name,
            )
        else:
            main_layout = trezorui_api.confirm_with_info(
                title=title,
                items=[(recipient_str, True)],
                verb="",
                verb_info=TR.ethereum__contract_address,
            )
            info_layout = trezorui_api.show_info_with_cancel(
                title=TR.ethereum__contract_address,
                items=[("", recipient_addr)],
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
                TR.words__address,
                token_address,
                "",
                subtitle=TR.ethereum__token_contract,
                chunkify=chunkify,
                br_name=br_name,
            )

        if is_unknown_network:
            assert is_unknown_token
            await confirm_value(
                TR.ethereum__approve_chain_id,
                chain_id,
                "",
                br_name=br_name,
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
            TR.ethereum__approve_revoke if is_revoke else TR.ethereum__approve,
            properties,
            None,
            False,
        )

        account_items = []
        if account_path:
            account_items.append((TR.address_details__derivation_path, account_path))

        await _confirm_summary(
            None,
            None,
            maximum_fee,
            TR.send__maximum_fee,
            TR.words__title_summary,
            account_items,
            fee_info_items,
            TR.confirm_total__title_fee,
        )

    async def confirm_trade(
        title: str,
        subtitle: str,
        sell_amount: str,
        buy_amount: str,
        address: str,
        account: str,
        account_path: str,
        token_address: str,
    ) -> None:
        from trezor.ui.layouts.menu import Menu, confirm_with_menu

        trade_layout = trezorui_api.confirm_trade(
            title=title,
            subtitle=subtitle,
            sell_amount=sell_amount,
            buy_amount=buy_amount,
        )

        menu = Menu.root(
            [
                create_details(
                    TR.address__title_receive_address,
                    [
                        ("", address),
                        (TR.words__account, account),
                        (TR.address_details__derivation_path, account_path),
                    ],
                ),
                create_details(TR.ethereum__token_contract, token_address),
            ],
            TR.send__cancel_sign,
        )

        await confirm_with_menu(trade_layout, menu, "confirm_trade")

    async def confirm_ethereum_payment_request(
        recipient_name: str,
        recipient: str,
        texts: Iterable[str],
        refunds: Iterable[tuple[str, str, str]],
        trades: Iterable[tuple[str, str, str, str, str]],
        account: str | None,
        account_path: str | None,
        chain_id: str,
        maximum_fee: str,
        fee_info_items: Iterable[tuple[str, str]],
        token_address: str,
    ) -> None:
        from trezor.ui.layouts.menu import Menu, confirm_with_menu

        for text in texts:
            await raise_if_cancelled(
                trezorui_api.confirm_value(
                    title=TR.words__confirm, value=text, description=None
                ),
                "confirm_payment_request",
            )

        main_layout = trezorui_api.confirm_value(
            title=TR.words__swap,
            subtitle=TR.words__provider,
            value=recipient_name,
            description=None,
            verb=TR.instructions__tap_to_continue,
            verb_cancel=None,
            chunkify=False,
            external_menu=True,
        )

        menu_items = [create_details(TR.address__title_provider_address, recipient)]
        for r_address, r_account, r_account_path in refunds:
            menu_items.append(
                create_details(
                    TR.address__title_refund_address,
                    [
                        ("", r_address),
                        (TR.words__account, r_account),
                        (TR.address_details__derivation_path, r_account_path),
                    ],
                )
            )
        menu = Menu.root(menu_items, TR.send__cancel_sign)

        await confirm_with_menu(main_layout, menu, "confirm_payment_request")

        for sell_amount, buy_amount, t_address, t_account, t_account_path in trades:
            await confirm_trade(
                TR.words__swap,
                TR.words__assets,
                sell_amount,
                buy_amount,
                t_address,
                t_account,
                t_account_path,
                token_address,
            )

        account_items = []
        if account:
            account_items.append((TR.words__account, account))
        if account_path:
            account_items.append((TR.address_details__derivation_path, account_path))
        account_items.append((TR.ethereum__approve_chain_id, chain_id))

        await _confirm_summary(
            None,
            None,
            maximum_fee,
            TR.words__transaction_fee,
            TR.words__title_summary,
            account_items,
            fee_info_items,
            TR.confirm_total__title_fee,
            "confirm_payment_request",
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
        info_items: Iterable[tuple[str, str]],
        chunkify: bool = False,
        br_name: str = "confirm_ethereum_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        if verb == TR.ethereum__staking_claim:
            summary_items = ((TR.send__maximum_fee, maximum_fee),)
        else:
            summary_items = (
                (TR.words__amount, total_amount),
                (TR.send__maximum_fee, maximum_fee),
            )
        await raise_if_cancelled(
            trezorui_api.flow_confirm_output(
                title=verb,
                subtitle=None,
                description=None,
                extra=None,
                message=intro_question,
                amount=None,
                chunkify=False,
                text_mono=False,
                account_title=TR.address_details__account_info,
                account=account,
                account_path=account_path,
                br_code=br_code,
                br_name=br_name,
                address_item=(address_title, address),
                extra_item=None,
                summary_items=summary_items,
                fee_items=info_items,
                summary_title=verb,
                summary_br_name="confirm_total",
                summary_br_code=ButtonRequestType.SignTx,
                cancel_text=TR.buttons__cancel,  # cancel staking
            ),
            br_name=None,
        )

    def confirm_solana_unknown_token_warning() -> Awaitable[None]:
        return show_danger(
            "unknown_token_warning",
            content=f"{TR.solana__unknown_token_address}. {TR.words__know_what_your_doing}",
            verb_cancel=TR.send__cancel_sign,
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
        return _confirm_summary(
            amount,
            amount_title,
            fee,
            fee_title,
            extra_title=TR.confirm_total__title_fee,
            extra_items=items,
            br_name=br_name,
            br_code=br_code,
        )

    async def confirm_solana_staking_tx(
        title: str,
        description: str,
        account: str,
        account_path: str,
        vote_account: str,
        stake_item: tuple[str, str] | None,
        amount_item: tuple[str, str] | None,
        fee_item: tuple[str, str],
        fee_details: Iterable[tuple[str, str]],
        blockhash_item: tuple[str, str],
        br_name: str = "confirm_solana_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        await raise_if_cancelled(
            trezorui_api.flow_confirm_output(
                title=title,
                subtitle=None,
                description=description,
                extra=f"\n{TR.words__provider}:" if vote_account else None,
                message=vote_account,
                amount=None,
                chunkify=True,
                text_mono=True,
                account_title=TR.address_details__account_info,
                account=account,
                account_path=account_path,
                br_code=br_code,
                br_name=br_name,
                address_item=stake_item,
                extra_item=blockhash_item,
                fee_items=fee_details,
                summary_title=title,
                summary_items=(amount_item, fee_item) if amount_item else (fee_item,),
                summary_br_name="confirm_total",
                summary_br_code=ButtonRequestType.SignTx,
                cancel_text=TR.buttons__cancel,
            ),
            br_name=None,
        )

    def confirm_cardano_tx(
        amount: str,
        fee: str,
        items: Iterable[tuple[str, str]],
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

    def confirm_tron_tx(
        amount: str,
        fee: str,
    ) -> Awaitable[None]:
        amount_title = TR.send__total_amount
        fee_title = TR.send__maximum_fee

        return _confirm_summary(
            amount,
            amount_title,
            fee,
            fee_title,
            extra_items=None,
            br_name="confirm_tron_tx",
            br_code=ButtonRequestType.SignTx,
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
        TR.send__transaction_id,
        verb=TR.buttons__continue,
        info=False,
        br_code=ButtonRequestType.SignTx,
        prompt_screen=False,
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
        verb_cancel=None,
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
    items: list[tuple[str, str]] = []
    if fee_rate_amount:
        items.append((TR.bitcoin__new_fee_rate, fee_rate_amount))
    info_layout = trezorui_api.show_info_with_cancel(
        title=TR.confirm_total__title_fee,
        items=items,
    )
    return with_info(fee_layout, info_layout, "modify_fee", ButtonRequestType.SignTx)


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
    return confirm_blob(
        "sign_identity",
        f"{TR.words__sign} {proto}",
        identity,
        challenge_visual,
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
        description="",
        verb=TR.buttons__continue,
        info=True,
        chunkify=chunkify,
    )

    items: list[tuple[str, str]] = []
    if account is not None:
        items.append((TR.words__account, account))
    if path is not None:
        items.append((TR.address_details__derivation_path, path))
    items.append(
        (
            TR.sign_message__message_size,
            TR.sign_message__bytes_template.format(len(message)),
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
        verb=TR.buttons__confirm,
    )

    if message_layout.page_count() <= LONG_MSG_PAGE_THRESHOLD:
        await interact(message_layout, br_name, BR_CODE_OTHER)
    else:
        await confirm_blob(
            br_name,
            TR.sign_message__confirm_message,
            message,
            verb="",
            br_code=BR_CODE_OTHER,
            hold=not verify,
            ask_pagination=True,
            verb_skip_pagination=TR.sign_message__confirm_without_review,
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
            prompt=TR.passphrase__title_enter, max_len=max_len
        ),
        "passphrase_device",
        ButtonRequestType.PassphraseEntry,
        raise_on_cancel=ActionCancelled("Passphrase entry cancelled"),
    )
    return result  # type: ignore ["UiResult" is incompatible with "str"]


def request_pin_on_device(
    prompt: str,
    attempts_remaining: int | None,
    allow_cancel: bool,
    wrong_pin: bool = False,
) -> Awaitable[str]:
    from trezor.wire import PinCancelled

    if attempts_remaining is None:
        subprompt = ""
    elif attempts_remaining == 1:
        subprompt = TR.pin__last_attempt
    else:
        subprompt = f"{attempts_remaining} {TR.pin__tries_left}"

    result = interact(
        trezorui_api.request_pin(
            prompt=prompt,
            subprompt=subprompt,
            allow_cancel=allow_cancel,
            wrong_pin=wrong_pin,
        ),
        "pin_device",
        ButtonRequestType.PinEntry,
        raise_on_cancel=PinCancelled,
    )
    return result  # type: ignore ["UiResult" is incompatible with "str"]


async def confirm_reenter_pin(is_wipe_code: bool = False) -> None:
    """Not supported for Delizia."""
    pass


def pin_mismatch_popup(is_wipe_code: bool = False) -> Awaitable[ui.UiResult]:
    title = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    description = TR.wipe_code__enter_new if is_wipe_code else TR.pin__reenter_new
    br_name = "wipe_code_mismatch" if is_wipe_code else "pin_mismatch"

    return interact(
        error_popup(
            title,
            description,
            button=TR.buttons__try_again,
        ),
        br_name,
        BR_CODE_OTHER,
    )


def wipe_code_same_as_pin_popup() -> Awaitable[ui.UiResult]:
    return interact(
        error_popup(
            TR.wipe_code__invalid,
            TR.wipe_code__diff_from_pin,
            button=TR.buttons__try_again,
        ),
        "wipe_code_same_as_pin",
        BR_CODE_OTHER,
    )


def confirm_set_new_pin(
    br_name: str,
    title: str,
    description: str,
    information: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    return raise_if_cancelled(
        trezorui_api.flow_confirm_set_new_pin(title=title, description=description),
        br_name,
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
        prompt_screen=False,
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


def set_brightness(current: int | None = None) -> Awaitable[None]:
    from trezor.ui.layouts.menu import Menu, confirm_with_menu

    return confirm_with_menu(
        trezorui_api.set_brightness(current=current),
        Menu.root(cancel=TR.buttons__cancel),
        "set_brightness",
        BR_CODE_OTHER,
    )


def tutorial(br_code: ButtonRequestType = BR_CODE_OTHER) -> Awaitable[None]:
    """Showing users how to interact with the device."""
    return raise_if_cancelled(
        trezorui_api.tutorial(),
        "tutorial",
        br_code,
    )


def create_details(name: str, value: list[tuple[str, str]] | str) -> Details:
    from trezor.ui.layouts.menu import Details

    return Details.from_layout(
        name, lambda: trezorui_api.show_properties(title=name, value=value)
    )
