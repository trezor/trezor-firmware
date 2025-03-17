from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui, utils
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

from ..common import draw_simple, interact, raise_if_not_confirmed, with_info

if TYPE_CHECKING:
    from typing import Awaitable, Iterable, NoReturn, Sequence, TypeVar

    from ..common import ExceptionType, PropertyType

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
    return raise_if_not_confirmed(
        trezorui_api.confirm_emphasized(
            title=title,
            items=(begin, (True, description_param), end),
            verb=verb,
        ),
        br_name,
        ButtonRequestType.ProtectCall,
    )


def confirm_reset_device(recovery: bool = False) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.confirm_reset_device(recovery=recovery), None
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
        title=TR.words__pay_attention,
        menu_title=TR.words__receive,
        verb_cancel=TR.words__cancel_and_exit,
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def confirm_multisig_warning() -> Awaitable[None]:
    return show_danger(
        "warning_multisig",
        TR.send__receiving_to_multisig,
        title=TR.words__pay_attention,
        menu_title=TR.words__receive,
        verb_cancel=TR.words__cancel_and_exit,
    )


def confirm_multisig_different_paths_warning() -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.show_danger(
            title=TR.words__pay_attention,
            description="Using different paths for different XPUBs.",
            menu_title=TR.words__receive,
        ),
        "warning_multisig_different_paths",
        br_code=ButtonRequestType.Warning,
    )


def confirm_homescreen(
    image: bytes,
) -> Awaitable[None]:

    from trezor import workflow

    workflow.close_others()

    return raise_if_not_confirmed(
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
    address_qr: str | None = None,
    case_sensitive: bool = True,
    path: str | None = None,
    account: str | None = None,
    network: str | None = None,
    multisig_index: int | None = None,
    xpubs: Sequence[str] = (),
    mismatch_title: str | None = None,
    details_title: str | None = None,
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

    title_success = (
        TR.address__public_key_confirmed
        if title in ("XPUB", TR.address__public_key)
        else TR.address__confirmed
    )

    await raise_if_not_confirmed(
        trezorui_api.flow_get_address(
            address=address,
            title=title or TR.address__title_receive_address,
            description=network or "",
            extra=None,
            chunkify=chunkify,
            address_qr=address if address_qr is None else address_qr,
            case_sensitive=case_sensitive,
            account=account,
            path=path,
            xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
            title_success=title_success,
            br_name=br_name,
            br_code=br_code,
        ),
        None,
    )


def show_pubkey(
    pubkey: str,
    title: str | None = None,
    *,
    account: str | None = None,
    path: str | None = None,
    mismatch_title: str | None = None,
    br_name: str = "show_pubkey",
) -> Awaitable[None]:
    title = title or TR.address__public_key  # def_arg
    mismatch_title = mismatch_title or TR.addr_mismatch__key_mismatch  # def_arg
    return show_address(
        address=pubkey,
        title=title,
        account=account,
        path=path,
        br_name=br_name,
        br_code=ButtonRequestType.PublicKey,
        mismatch_title=mismatch_title,
        chunkify=False,
    )


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
    return raise_if_not_confirmed(
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
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    time_ms: int = 0,
) -> Awaitable[None]:
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
) -> None:
    if address_label is not None:
        title = address_label
    elif title is not None:
        pass
    elif output_index is not None:
        title = f"{TR.words__recipient} #{output_index + 1}"
    else:
        title = TR.send__title_sending_to

    # FIXME: not implemented
    # use `flow_confirm_output` or `TT/TR` style?
    raise NotImplementedError


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
    data: bytes | str,
    description: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    info: bool = True,
    hold: bool = False,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    ask_pagination: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = True,
) -> Awaitable[None]:
    if ask_pagination:
        main_layout = trezorui_api.confirm_value_intro(
            title=title,
            value=data,
            subtitle=description,
            verb=verb,
            verb_cancel=verb_cancel,
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
            hold=False,
            chunkify=chunkify,
            page_counter=True,
            prompt_screen=False,
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
    chunkify: bool = True,
    br_name: str = "confirm_address",
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    return confirm_value(
        title,
        address,
        description or "",
        br_name,
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
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    if not verb and not hold:
        raise ValueError("Either verb or hold=True must be set")

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
        ),
        info_layout,
        br_name,
        br_code,
    )


def confirm_properties(
    br_name: str,
    title: str,
    props: Iterable[PropertyType],
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
) -> Awaitable[None]:
    # Monospace flag for values that are bytes.
    items = [(prop[0], prop[1], isinstance(prop[1], bytes)) for prop in props]

    return raise_if_not_confirmed(
        trezorui_api.confirm_properties(
            title=title,
            items=items,
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
    amount: str,
    amount_label: str,
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

    return raise_if_not_confirmed(
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

    def confirm_ethereum_unknown_contract_warning() -> Awaitable[None]:
        return show_danger(
            "unknown_contract_warning",
            TR.ethereum__unknown_contract_address,
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
        # FIXME: not implemented
        # use `flow_confirm_output` or `TT/TR` style?
        raise NotImplementedError

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
        # FIXME: not implemented
        # use `confirm_output` or `TT/TR` style?
        raise NotImplementedError

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
            extra_items=items,
            br_name=br_name,
            br_code=br_code,
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
    # FIXME: not implemented
    raise NotImplementedError


def confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> Awaitable[None]:
    # FIXME: not implemented
    raise NotImplementedError


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


async def confirm_signverify(
    message: str,
    address: str,
    verify: bool,
    path: str | None = None,
    account: str | None = None,
    chunkify: bool = False,
) -> None:
    # FIXME: not implemented
    raise NotImplementedError


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
    """Not supported for Eckhart."""
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
    return raise_if_not_confirmed(
        trezorui_api.flow_confirm_set_new_pin(title=title, description=description),
        br_name,
        br_code,
    )


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
