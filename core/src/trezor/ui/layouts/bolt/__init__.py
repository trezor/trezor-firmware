from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui, utils
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

from ..common import draw_simple, interact, raise_if_not_confirmed, with_info

if TYPE_CHECKING:
    from typing import Awaitable, Iterable, NoReturn, Sequence

    from ..common import ExceptionType, PropertyType


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
    prompt_screen: bool = False,  # unused on bolt
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
        trezorui_api.confirm_reset_device(recovery=recovery),
        "recover_device" if recovery else "setup_device",
        (ButtonRequestType.ProtectCall if recovery else ButtonRequestType.ResetDevice),
    )


async def show_wallet_created_success() -> None:
    # not shown on model T
    return None


# TODO cleanup @ redesign
async def prompt_backup() -> bool:
    result = await interact(
        trezorui_api.confirm_action(
            title=TR.words__title_success,
            action=TR.backup__new_wallet_successfully_created,
            description=TR.backup__it_should_be_backed_up,
            verb=TR.buttons__back_up,
            verb_cancel=TR.buttons__skip,
        ),
        "backup_device",
        ButtonRequestType.ResetDevice,
        raise_on_cancel=None,
    )
    if result is CONFIRMED:
        return True

    result = await interact(
        trezorui_api.confirm_action(
            title=TR.words__warning,
            action=TR.backup__want_to_skip,
            description=TR.backup__can_back_up_anytime,
            verb=TR.buttons__back_up,
            verb_cancel=TR.buttons__skip,
        ),
        "backup_device",
        ButtonRequestType.ResetDevice,
        raise_on_cancel=None,
    )
    return result is CONFIRMED


def confirm_path_warning(path: str, path_type: str | None = None) -> Awaitable[None]:
    title = (
        TR.addr_mismatch__wrong_derivation_path
        if not path_type
        else f"{TR.words__unknown} {path_type.lower()}."
    )
    return raise_if_not_confirmed(
        trezorui_api.show_warning(
            title=title,
            value=path,
            description=TR.words__continue_anyway_question,
            button=TR.buttons__continue,
        ),
        "path_warning",
        br_code=ButtonRequestType.UnknownDerivationPath,
    )


def confirm_multisig_warning() -> Awaitable[None]:
    return show_warning(
        "warning_multisig",
        TR.send__receiving_to_multisig,
        TR.words__continue_anyway_question,
    )


def confirm_multisig_different_paths_warning() -> Awaitable[None]:
    return show_warning(
        "warning_multisig_different_paths",
        "Using different paths for different XPUBs.",
        TR.words__continue_anyway_question,
    )


def confirm_homescreen(image: bytes) -> Awaitable[None]:
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
    mismatch_title = mismatch_title or TR.addr_mismatch__mismatch  # def_arg
    send_button_request = True

    if title is None:
        title = TR.address__title_receive_address
        if multisig_index is not None:
            title = f"{title}\n(MULTISIG)"
        details_title = TR.send__title_receiving_to
    elif details_title is None:
        details_title = title

    while True:
        result = await interact(
            trezorui_api.confirm_address(
                title=title,
                address=address,
                address_label=network or None,
                info_button=True,
                chunkify=chunkify,
            ),
            br_name if send_button_request else None,
            br_code,
            raise_on_cancel=None,
        )

        send_button_request = False

        # User pressed right button.
        if result is CONFIRMED:
            break

        # User pressed corner button or swiped left, go to address details.
        elif result is INFO:

            def xpub_title(i: int) -> str:
                result = f"MULTISIG XPUB #{i + 1}\n"
                result += (
                    f"({TR.address__title_yours})"
                    if i == multisig_index
                    else f"({TR.address__title_cosigner})"
                )
                return result

            result = await interact(
                trezorui_api.show_address_details(
                    qr_title=title,
                    address=address if address_qr is None else address_qr,
                    case_sensitive=case_sensitive,
                    details_title=details_title,
                    account=account,
                    path=path,
                    xpubs=[(xpub_title(i), xpub) for i, xpub in enumerate(xpubs)],
                ),
                None,
                raise_on_cancel=None,
            )
            assert result is CANCELLED

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
    # always raise regardless of result
    raise exc


def show_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[None]:
    button = button or TR.buttons__continue  # def_arg
    return raise_if_not_confirmed(
        trezorui_api.show_warning(
            title=content,
            description=subheader or "",
            button=button,
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
    return show_warning(
        br_name,
        content,
        TR.words__continue_anyway_question,
        br_code=br_code,
    )


def show_success(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
) -> Awaitable[None]:
    button = button or TR.buttons__continue  # def_arg
    return raise_if_not_confirmed(
        trezorui_api.show_success(
            title=content,
            description=subheader or "",
            button=button,
            allow_cancel=False,
        ),
        br_name,
        ButtonRequestType.Success,
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
    source_account: str | None = None,  # ignored on model t
    source_account_path: str | None = None,  # ignored on model t
) -> None:
    if title is not None:
        # TODO: handle translation:
        if title.upper().startswith("CONFIRM "):
            title = title[len("CONFIRM ") :]
        amount_title = title
        recipient_title = title
    elif output_index is not None:
        amount_title = f"{TR.words__amount} #{output_index + 1}"
        recipient_title = f"{TR.words__recipient} #{output_index + 1}"
    else:
        amount_title = TR.send__confirm_sending
        recipient_title = TR.send__title_sending_to

    while True:
        # if the user cancels here, raise ActionCancelled (by default)
        await interact(
            trezorui_api.confirm_address(
                title=recipient_title,
                address=address,
                address_label=address_label,
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
                    subtitle=None,
                    verb=None if hold else TR.buttons__confirm,
                    verb_cancel="^",
                    info=False,
                    hold=hold,
                ),
                "confirm_output",
                br_code,
            )
        except ActionCancelled:
            # if the user cancels here, go back to confirm_value
            continue
        else:
            return


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
    items: Iterable[tuple[str | bytes, bool]],
    button_text: str | None = None,
    br_name: str = "should_show_more",
    br_code: ButtonRequestType = BR_CODE_OTHER,
    confirm: str | None = None,
) -> bool:
    """Return True if the user wants to show more (they click a special button)
    and False when the user wants to continue without showing details.

    Raises ActionCancelled if the user cancels.
    """

    result = await interact(
        trezorui_api.confirm_with_info(
            title=title,
            items=items,
            verb=confirm or TR.buttons__confirm,
            verb_info=button_text or TR.buttons__show_all,
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


async def _confirm_ask_pagination(
    br_name: str,
    title: str,
    data: bytes | str,
    description: str,
    br_code: ButtonRequestType,
    extra_confirmation_if_not_read: bool = False,
    hold: bool = False,
) -> None:
    # TODO: make should_show_more/confirm_more accept bytes directly
    if isinstance(data, (bytes, bytearray, memoryview)):
        from ubinascii import hexlify

        data = hexlify(data).decode()

    confirm_more_layout = trezorui_api.confirm_more(
        title=title,
        button=TR.buttons__confirm,
        button_style_confirm=True,
        items=[(data, True)],
        hold=hold,
    )
    while True:
        if not await should_show_more(
            title,
            [(description, False), (data, True)],
            br_name=br_name,
            br_code=br_code,
            confirm="V" if extra_confirmation_if_not_read else None,
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

        result = await interact(
            confirm_more_layout, br_name, br_code, raise_on_cancel=None
        )
        if result is CONFIRMED:
            return

    assert False


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
    extra_confirmation_if_not_read: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = True,
) -> Awaitable[None]:
    if description and ":" not in description:
        description += ":"

    verb = verb or TR.buttons__confirm  # def_arg
    layout = trezorui_api.confirm_value(
        title=title,
        subtitle=subtitle,
        description=description,
        value=data,
        hold=hold,
        verb=verb,
        verb_cancel=None,
        chunkify=chunkify,
    )

    if ask_pagination and layout.page_count() > 1:
        return _confirm_ask_pagination(
            br_name,
            title,
            data,
            description or "",
            br_code,
            extra_confirmation_if_not_read,
            hold,
        )
    else:
        assert not extra_confirmation_if_not_read
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
        description or subtitle or "",
        br_name,
        br_code,
        subtitle=None,
        verb=(verb or TR.buttons__confirm),
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
    description: str | None,
    br_name: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    *,
    verb: str | None = None,
    verb_cancel: str | None = None,
    subtitle: str | None = None,
    hold: bool = False,
    is_data: bool = True,
    info_items: Iterable[tuple[str, str]] | None = None,
    info_title: str | None = None,
    chunkify_info: bool = False,
) -> Awaitable[None]:
    """General confirmation dialog, used by many other confirm_* functions."""

    if description and value:
        description += ":"

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
            description=description,
            is_data=is_data,
            subtitle=subtitle,
            verb=verb,
            verb_cancel=verb_cancel,
            info=bool(info_items),
            hold=hold,
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
    total_label = total_label or f"{TR.send__total_amount}:"  # def_arg
    fee_label = fee_label or TR.send__including_fee  # def_arg

    account_info_items = []
    extra_info_items = []
    if source_account:
        account_info_items.append(
            (TR.confirm_total__sending_from_account, source_account)
        )
    if fee_rate_amount:
        extra_info_items.append((f"{TR.confirm_total__fee_rate}:", fee_rate_amount))

    return _confirm_summary(
        total_amount,
        total_label,
        fee_amount,
        fee_label,
        title=title,
        account_items=account_info_items,
        extra_items=extra_info_items,
        extra_title=TR.words__title_information,
        br_name=br_name,
        br_code=br_code,
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

    total_layout = trezorui_api.confirm_summary(
        amount=amount,
        amount_label=amount_label,
        fee=fee,
        fee_label=fee_label,
        title=title,
        account_items=account_items or None,
        extra_items=extra_items or None,
    )

    # TODO: use `_info` params directly in this^ layout instead of using `with_info`
    info_items = []
    if account_items:
        info_items.extend(account_items)
    if extra_items:
        info_items.extend(extra_items)
    info_layout = trezorui_api.show_info_with_cancel(
        title=extra_title if extra_title else TR.words__title_information,
        items=info_items,
    )
    return with_info(total_layout, info_layout, br_name, br_code)


if not utils.BITCOIN_ONLY:

    def confirm_ethereum_unknown_contract_warning() -> Awaitable[None]:
        return show_danger(
            "unknown_contract_warning", TR.ethereum__unknown_contract_address_short
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
        if not is_contract_interaction:
            description = f"{TR.words__recipient}:"
        else:
            description = f"{TR.ethereum__interaction_contract}:" if recipient else None

        address_layout = trezorui_api.confirm_value(
            title=TR.words__address,
            description=description,
            value=recipient or TR.ethereum__new_contract,
            verb=TR.buttons__continue,
            verb_cancel=None,
            info=True,
            chunkify=(chunkify if recipient else False),
        )

        account_info_layout = trezorui_api.show_info_with_cancel(
            title=TR.send__send_from,
            items=[
                (f"{TR.words__account}:", account or ""),
                (f"{TR.address_details__derivation_path}:", account_path or ""),
            ],
        )

        total_layout = trezorui_api.confirm_summary(
            amount=total_amount,
            amount_label=f"{TR.words__amount}:",
            fee=maximum_fee,
            fee_label=f"{TR.send__maximum_fee}:",
            title=TR.words__title_summary,
            extra_items=fee_info_items,  # used so that info button is shown
            extra_title=TR.confirm_total__title_fee,
            verb_cancel="^",
        )

        fee_info_layout = trezorui_api.show_info_with_cancel(
            title=TR.confirm_total__title_fee,
            items=[(f"{k}:", v) for (k, v) in fee_info_items],
        )

        while True:
            await with_info(address_layout, account_info_layout, br_name, br_code)

            try:
                await with_info(total_layout, fee_info_layout, br_name, br_code)
            except ActionCancelled:
                # Allowing going back and forth between recipient and summary
                continue
            else:
                break

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
            is_data=False,
            info_items=(("", address),),
            info_title=address_title,
            chunkify_info=chunkify,
        )

        # confirmation
        if verb == TR.ethereum__staking_claim:
            amount = ""
            amount_label = ""
            fee_label = f"{TR.send__maximum_fee}:"
            fee = maximum_fee
        else:
            amount_label = f"{TR.words__amount}:"
            amount = total_amount
            fee_label = f"{TR.send__maximum_fee}:"
            fee = maximum_fee
        await _confirm_summary(
            amount,
            amount_label,
            fee,
            fee_label,
            title=title,
            extra_items=[(f"{k}:", v) for (k, v) in info_items],
            extra_title=TR.confirm_total__title_fee,
            br_name=br_name,
            br_code=br_code,
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
        amount_item: tuple[str, str],
        fee_item: tuple[str, str],
        fee_details: Iterable[tuple[str, str]],
        blockhash_item: tuple[str, str],
        br_name: str = "confirm_solana_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        (amount_label, amount) = amount_item
        (fee_label, fee) = fee_item

        confirm_layout = trezorui_api.confirm_value(
            title=title,
            description=description,
            extra=f"{TR.solana__stake_provider}:" if vote_account else None,
            value=vote_account,
            verb=TR.buttons__continue,
            info=True,
        )

        items = [
            (f"{TR.words__account}:", account),
            (f"{TR.address_details__derivation_path}:", account_path),
        ]
        if stake_item is not None:
            items.append(stake_item)
        items.append(blockhash_item)

        info_layout = trezorui_api.show_info_with_cancel(
            title=title,
            items=items,
            horizontal=True,
        )

        await with_info(confirm_layout, info_layout, br_name, br_code)

        await _confirm_summary(
            amount=amount,
            amount_label=amount_label,
            fee=fee,
            fee_label=fee_label,
            account_items=None,
            title=title,
            extra_title=TR.confirm_total__title_fee,
            extra_items=fee_details,
            br_name=br_name,
            br_code=br_code,
        )

    def confirm_cardano_tx(
        amount: str,
        fee: str,
        items: Iterable[tuple[str, str]],
    ) -> Awaitable[None]:
        amount_title = f"{TR.send__total_amount}:"
        fee_title = TR.send__including_fee
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
    return raise_if_not_confirmed(
        # FIXME: arguments for amount/fee are misused here
        trezorui_api.confirm_summary(
            amount=spending_amount,
            amount_label=TR.send__you_are_contributing,
            fee=total_amount,
            fee_label=TR.send__to_the_total_amount,
            title=TR.send__title_joint_transaction,
        ),
        "confirm_joint_total",
        ButtonRequestType.SignTx,
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
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_modify_output(
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> None:
    send_button_request = True
    while True:
        # if the user cancels here, raise ActionCancelled (by default)
        await interact(
            trezorui_api.confirm_value(
                title="MODIFY AMOUNT",
                value=address,
                verb="CONTINUE",
                verb_cancel=None,
                description="Address:",
            ),
            "modify_output" if send_button_request else None,
            ButtonRequestType.ConfirmOutput,
        )

        try:
            await interact(
                trezorui_api.confirm_modify_output(
                    sign=sign,
                    amount_change=amount_change,
                    amount_new=amount_new,
                ),
                "modify_output" if send_button_request else None,
                ButtonRequestType.ConfirmOutput,
            )
        except ActionCancelled:
            # if the user cancels here, go back to confirm_blob
            send_button_request = False
            continue
        else:
            return


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

    address_layout = trezorui_api.confirm_address(
        title=address_title,
        address=address,
        address_label=None,
        verb=TR.buttons__continue,
        info_button=True,
        chunkify=chunkify,
    )

    items: list[tuple[str, str]] = []
    if account is not None:
        items.append((f"{TR.words__account}:", account))
    if path is not None:
        items.append((f"{TR.address_details__derivation_path}:", path))
    items.append(
        (
            f"{TR.sign_message__message_size}:",
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
            break
        except ActionCancelled:
            result = await interact(
                trezorui_api.show_mismatch(title=TR.addr_mismatch__mismatch),
                None,
                raise_on_cancel=None,
            )
            assert result in (CONFIRMED, CANCELLED)
            # Right button aborts action, left goes back to showing address.
            if result is CONFIRMED:
                raise ActionCancelled
            else:
                continue

    message_layout = trezorui_api.confirm_value(
        title=TR.sign_message__confirm_message,
        description=None,
        value=message,
        hold=not verify,
        verb=TR.buttons__confirm,
    )

    while True:
        if message_layout.page_count() <= LONG_MSG_PAGE_THRESHOLD:
            result = await interact(message_layout, br_name, BR_CODE_OTHER)
            if result is CONFIRMED:
                break
        else:
            await confirm_blob(
                br_name,
                TR.sign_message__confirm_message,
                message,
                verb=TR.buttons__confirm,
                hold=not verify,
                br_code=BR_CODE_OTHER,
                ask_pagination=True,
                extra_confirmation_if_not_read=not verify,
            )

            break


def error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> ui.LayoutObj[None]:
    if not button and not timeout_ms:
        raise ValueError("Either button or timeout_ms must be set")

    if subtitle:
        title += f"\n{subtitle}"
    layout = trezorui_api.show_error(
        title=title,
        description=description.format(description_param),
        button=button,
        time_ms=timeout_ms,
        allow_cancel=False,
    )
    return layout  # type: ignore [Expression of type "LayoutObj[UiResult]" is incompatible with return type "LayoutObj[None]"]


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
            prompt=TR.passphrase__title_enter, max_len=max_len
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
    from trezor.wire import PinCancelled

    if attempts_remaining is None:
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
        raise_on_cancel=PinCancelled,
    )
    assert isinstance(result, str)
    return result


async def confirm_reenter_pin(is_wipe_code: bool = False) -> None:
    """Not supported for Bolt."""
    pass


def pin_mismatch_popup(is_wipe_code: bool = False) -> Awaitable[None]:
    title = TR.wipe_code__wipe_code_mismatch if is_wipe_code else TR.pin__pin_mismatch
    br_name = "wipe_code_mismatch" if is_wipe_code else "pin_mismatch"
    description = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    return interact(
        error_popup(
            title,
            description,
            button=TR.buttons__try_again,
        ),
        br_name,
        BR_CODE_OTHER,
        raise_on_cancel=None,
    )


def wipe_code_same_as_pin_popup() -> Awaitable[None]:
    return interact(
        error_popup(
            TR.wipe_code__invalid,
            TR.wipe_code__diff_from_pin,
            button=TR.buttons__try_again,
        ),
        "wipe_code_same_as_pin",
        BR_CODE_OTHER,
        raise_on_cancel=None,
    )


def confirm_set_new_pin(
    br_name: str,
    title: str,
    description: str,
    information: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    return raise_if_not_confirmed(
        trezorui_api.confirm_emphasized(
            title=title,
            items=(
                (True, description + "\n\n"),
                information,
            ),
            verb=TR.buttons__turn_on,
        ),
        br_name,
        br_code,
    )


async def confirm_firmware_update(description: str, fingerprint: str) -> None:
    main = trezorui_api.confirm_value(
        title=TR.firmware_update__title,
        description=description,
        value="",
        verb=TR.buttons__install,
        info=True,
    )
    info = trezorui_api.show_info_with_cancel(
        title=TR.firmware_update__title_fingerprint,
        items=(("", fingerprint),),
        chunkify=True,
    )
    await with_info(
        main,
        info,
        br_name="firmware_update",
        br_code=BR_CODE_OTHER,
    )


async def set_brightness(current: int | None = None) -> None:
    await interact(
        trezorui_api.set_brightness(current=current),
        "set_brightness",
        BR_CODE_OTHER,
    )
