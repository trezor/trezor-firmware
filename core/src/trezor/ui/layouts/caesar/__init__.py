from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui, utils
from trezor.enums import ButtonRequestType, RecoveryType
from trezor.wire import ActionCancelled

from ..common import interact, interact_simple, raise_if_not_confirmed
from ..properties import with_colon

if TYPE_CHECKING:
    from buffer_types import AnyBytes, StrOrBytes
    from collections.abc import Awaitable, Callable, Iterable, Sequence
    from typing import NoReturn

    from typing_extensions import TypeVar

    from apps.stellar.tokens import StellarToken

    from ..common import ExceptionType, PropertyType, StrPropertyType
    from ..menu import Menu, MenuLeaf
    from ..properties import AboveThreshold
    from ..slip24 import Refund, Trade

    R = TypeVar("R")


CONFIRMED = trezorui_api.CONFIRMED
CANCELLED = trezorui_api.CANCELLED

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


async def confirm_action(
    br_name: str,
    title: str,
    action: str | None = None,
    description: str | None = None,
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
) -> None:
    verb = verb or TR.buttons__confirm  # def_arg

    with trezorui_api.confirm_action(
        title=title,
        action=action,
        description=description,
        subtitle=subtitle,
        verb=verb,
        verb_cancel=verb_cancel,
        hold=hold,
        reverse=reverse,
    ) as layout:
        return await raise_if_not_confirmed(
            layout,
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


async def confirm_reset_device(recovery: bool = False) -> None:
    with trezorui_api.confirm_reset_device(recovery=recovery) as layout:
        return await raise_if_not_confirmed(
            layout,
            "recover_device" if recovery else "setup_device",
            (
                ButtonRequestType.ProtectCall
                if recovery
                else ButtonRequestType.ResetDevice
            ),
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
    from trezor.ui.layouts.menu import Menu, MenuLeaf, interact_with_menu

    br_name = "backup_device"
    br_code = ButtonRequestType.ResetDevice

    async def skip() -> bool:
        return True

    # skipping is in the menu
    menu = Menu([MenuLeaf(TR.buttons__skip, skip)])
    with trezorui_api.prompt_backup() as layout:
        result = await interact_with_menu(
            layout, menu, br_name, br_code, raise_on_cancel=None
        )
    if result is CONFIRMED:
        return True

    with trezorui_api.confirm_action(
        title=TR.backup__title_skip,
        action=None,
        description=TR.backup__want_to_skip,
        verb=TR.buttons__back_up,
        verb_cancel=TR.buttons__skip,
        hold=False,
    ) as layout:
        result = await interact(
            layout,
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


async def confirm_homescreen(image: AnyBytes) -> None:
    with trezorui_api.confirm_homescreen(
        title=TR.homescreen__title_set,
        image=image,
    ) as layout:
        return await raise_if_not_confirmed(
            layout,
            "set_homesreen",
            ButtonRequestType.ProtectCall,
        )


async def confirm_change_label(
    br_name: str, title: str, template: str, param: str
) -> None:

    await confirm_single(
        br_name=br_name,
        title=title,
        description=template,
        description_param=param,
        verb=TR.buttons__change,
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
    from trezor.ui.layouts.menu import Menu, MenuLeaf, cancel_leaf, confirm_with_menu

    mismatch_title = mismatch_title or TR.addr_mismatch__mismatch  # def_arg
    if title is None:
        # Will be a marquee in case of multisig
        title = TR.address__title_receive_address
        if multisig_index is not None:
            title = f"{title} (MULTISIG)"  # TODO translation?

    def xpub_title(i: int) -> str:
        # Will be marquee (cannot fit one line)
        result = TR.address__title_multisig_xpub_template.format(i + 1)
        result += (
            TR.address__title_yours
            if i == multisig_index
            else TR.address__title_cosigner
        )
        return result

    account_info: list[StrPropertyType] = []
    if account:
        account_info.append((with_colon(TR.words__account), account, False))
    if path:
        account_info.append(
            (with_colon(TR.address_details__derivation_path), path, False)
        )
    account_info.extend((xpub_title(i), xpub, True) for i, xpub in enumerate(xpubs))

    async def show_qr_code() -> None:
        with trezorui_api.show_address_details(
            qr_title="",  # unused on this model
            address=address if address_qr is None else address_qr,
            case_sensitive=case_sensitive,
            details_title="",  # unused on this model
            account=None,  # shown in the account info
            path=None,  # shown in the account info
            xpubs=(),  # shown in the account info
        ) as layout:
            await interact(layout, None, raise_on_cancel=None)

    menu_items: list[MenuLeaf[None]] = [MenuLeaf(TR.address__qr_code, show_qr_code)]
    if account_info:
        menu_items.append(
            create_info_menu_leaf(TR.address_details__account_info, account_info)
        )
    menu_items.append(
        cancel_leaf(
            TR.buttons__cancel,
            confirm=lambda: trezorui_api.show_mismatch(title=mismatch_title),
        )
    )

    # shown above the address
    address_label = "\n".join(line for line in (network, warning) if line)
    with trezorui_api.confirm_address(
        title=title,
        address=address,
        address_label=address_label or None,
        info_button=True,
        chunkify=chunkify,
    ) as layout:
        await confirm_with_menu(layout, Menu(menu_items), br_name, br_code)


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
        warning=warning,
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


async def show_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
    exc: ExceptionType | None = ActionCancelled,
) -> ui.UiResult:
    from trezor import translations

    button = button or TR.buttons__continue  # def_arg

    # Putting there a delimiter line in case of english, so it looks better
    # (we know it will fit one page)
    # TODO: figure out some better and non-intrusive way to do this
    # (check if the content fits one page with the newline, and if not, do not add it)
    if content and subheader and translations.get_language() == "en-US":
        content = content + "\n"

    with trezorui_api.show_warning(
        title="",
        button=button,
        value=content,
        description=subheader or "",
    ) as layout:
        return await interact(layout, br_name, br_code, raise_on_cancel=exc)


async def show_danger(
    br_name: str,
    content: str,
    title: str | None = None,
    verb_cancel: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    title = title or TR.words__warning
    verb_cancel = verb_cancel or TR.buttons__cancel
    with trezorui_api.show_danger(
        title=title,
        description=content,
    ) as layout:
        return await raise_if_not_confirmed(
            layout,
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
    recipient_address: str | None,
    texts: Iterable[tuple[str | None, str]],
    refunds: Iterable[Refund],
    trades: list[Trade],
    account_items: Sequence[StrPropertyType],
    transaction_fee: str | None,
    fee_info_items: Sequence[StrPropertyType] | None,
    extra_menu_items: list[tuple[str, str]] | None = None,
) -> None:
    from trezor.ui.layouts.menu import confirm_with_menu

    from ..properties import with_colon
    from ..slip24 import is_swap

    title = TR.words__swap if is_swap(trades) else TR.words__confirm

    for t, text in texts:
        with trezorui_api.confirm_value(
            title=t or title,
            value=text,
            description=None,
        ) as obj:
            await raise_if_not_confirmed(obj, "confirm_payment_request")

    async def _task() -> None:
        menu_items = []
        if recipient_address is not None:
            menu_items.append(
                create_info_menu_leaf(
                    TR.address__title_provider_address, recipient_address
                )
            )
        for refund in refunds:
            refund_account_items: list[StrPropertyType] = [("", refund.address, None)]
            if refund.account:
                refund_account_items.append((TR.words__account, refund.account, None))
            if refund.account_path:
                refund_account_items.append(
                    (TR.address_details__derivation_path, refund.account_path, None)
                )
            menu_items.append(
                create_info_menu_leaf(
                    TR.address__title_refund_address,
                    refund_account_items,
                )
            )
        with trezorui_api.confirm_properties(
            title=title,
            items=with_colon([(TR.words__provider, recipient_name, True)]),
            verb=TR.buttons__continue,
            external_menu=bool(menu_items),
        ) as main_layout:
            if menu_items:
                await confirm_with_menu(
                    main_layout,
                    _menu_with_cancel(menu_items, TR.buttons__cancel_sign),
                    "confirm_payment_request",
                )
            else:
                await raise_if_not_confirmed(main_layout, "confirm_payment_request")

    # Allow GC to free the objects allocated above.
    await _task()

    for trade in trades:
        await confirm_trade(
            f"{title} {TR.words__assets}",
            trade,
            extra_menu_items or [],
        )

    if transaction_fee is not None:
        assert fee_info_items is not None

        await _confirm_summary(
            "confirm_payment_request",
            fee=transaction_fee,
            fee_label=with_colon(TR.words__transaction_fee),
            title=TR.words__title_summary,
            info=(
                (TR.confirm_total__title_fee, fee_info_items),
                (TR.address_details__account_info, account_items),
            ),
            br_code=BR_CODE_OTHER,
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
    source_account: str | None = None,
    source_account_path: str | None = None,
) -> None:
    from trezor.ui.layouts.menu import interact_with_menu

    from ..common import confirm_linear_flow

    address_title = TR.words__recipient
    if output_index is not None:
        address_title += f" #{output_index + 1}"
    amount_title = TR.words__amount
    if output_index is not None:
        amount_title += f" #{output_index + 1}"

    account_items: list[StrPropertyType] = []
    if source_account:
        account_items.append((TR.words__wallet, source_account, None))
    if source_account_path and source_account_path != source_account:
        # the reason for this check is account_label in bitcoin/sign_tx/layout.py
        # which can return the derivation path instead of the account
        account_items.append(
            (TR.address_details__derivation_path, source_account_path, None)
        )
    menu_items = []
    if account_items:
        menu_items.append(
            create_info_menu_leaf(
                TR.address_details__account_info, with_colon(account_items)
            )
        )
    menu = _menu_with_cancel(menu_items)

    address_ctx = trezorui_api.confirm_address(
        title=address_title,
        address=address,
        address_label=address_label or None,
        verb=TR.buttons__continue,
        info_button=True,
        chunkify=chunkify,
    )
    # "Shift" + right button goes back to the address
    amount_ctx = trezorui_api.confirm_value(
        title=amount_title,
        value=amount,
        description=None,
        verb=TR.buttons__confirm,
        external_menu=True,
        back_button=True,
    )

    with address_ctx as address_layout, amount_ctx as amount_layout:
        await confirm_linear_flow(
            lambda: interact_with_menu(address_layout, menu, "confirm_output", br_code),
            lambda: interact_with_menu(amount_layout, menu, "confirm_output", br_code),
        )


async def tutorial(br_code: ButtonRequestType = BR_CODE_OTHER) -> ui.UiResult:
    """Showing users how to interact with the device."""
    with trezorui_api.tutorial() as layout:
        return await interact(layout, "tutorial", br_code)


async def should_show_more(
    title: str,
    para: Iterable[tuple[str, bool]],
    button_text: str | None = None,
    br_name: str = "should_show_more",
    br_code: ButtonRequestType = BR_CODE_OTHER,
    confirm: str | None = None,
    verb_cancel: str | None = None,
) -> bool:
    """Return True if the user wants to show more (they choose `button_text`
    from the menu, or scroll down if it is `DOWN_ARROW`) and False when the
    user wants to continue without showing details (`confirm`).

    Raises ActionCancelled if the user cancels.
    """
    from trezor.ui.layouts.menu import MenuLeaf, MenuResult, interact_with_menu

    confirm = confirm or TR.buttons__confirm  # def_arg

    # The right button continues, the other choice is in the menu.
    if button_text == DOWN_ARROW:
        verb, choice, show_more = DOWN_ARROW, confirm, False
    else:
        verb, choice, show_more = confirm, button_text, True
        if choice is None:
            choice = TR.buttons__show_all

    with trezorui_api.confirm_with_info(
        title=title,
        items=para,
        verb=verb,
        verb_info=choice,
    ) as layout:
        if not choice:
            # nothing to choose from, the left button cancels
            await raise_if_not_confirmed(layout, br_name, br_code)
            return False

        async def choose() -> bool:
            return show_more

        menu = _menu_with_cancel([MenuLeaf(choice, choose)])
        result = await interact_with_menu(layout, menu, br_name, br_code)

    if isinstance(result, MenuResult):
        return result.value
    assert result is CONFIRMED
    return not show_more


async def confirm_blob_intro(
    title: str,
    value: AnyBytes,
    *,
    subtitle: str,
    verb: str,
    verb_cancel: str,
    verb_view_all: str,
    br_name: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> bool:
    """Not needed for this layout - `confirm_blob_prefix` can skip confirmation."""
    return False


async def confirm_blob(
    br_name: str,
    title: str,
    data: StrOrBytes,
    description: str | None = None,
    subtitle: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,  # icon
    hold: bool = False,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    ask_pagination: bool = False,
    extra_confirmation_if_not_read: bool = False,
    chunkify: bool = False,
    prompt_screen: bool = True,
) -> None:
    if description:
        description = with_colon(description)

    with trezorui_api.confirm_value(
        title=title,
        description=description,
        value=data,
        verb=verb or TR.buttons__confirm,
        verb_cancel=verb_cancel or "",
        hold=hold,
        chunkify=chunkify,
    ) as layout:
        if not ask_pagination or layout.page_count() <= 1:
            return await raise_if_not_confirmed(layout, br_name, br_code)

    await _confirm_ask_pagination(
        br_name,
        title,
        data,
        description,
        verb=verb,
        hold=hold,
        br_code=br_code,
        chunkify=chunkify,
        # a text (not an icon) labels the cancel menu item
        cancel=verb_cancel if verb_cancel and len(verb_cancel) > 1 else None,
        extra_confirmation_if_not_read=extra_confirmation_if_not_read,
    )


async def _confirm_ask_pagination(
    br_name: str,
    title: str,
    data: StrOrBytes,
    description: str | None,
    *,
    verb: str | None,
    hold: bool,
    br_code: ButtonRequestType,
    chunkify: bool,
    cancel: str | None,
    extra_confirmation_if_not_read: bool,
) -> None:
    """Long content paginated on a single screen. Confirming it without reading
    all the pages is in the menu."""
    from trezor.ui.layouts.menu import MenuLeaf, MenuResult, interact_with_menu

    async def skip_review() -> bool:
        return True

    menu = _menu_with_cancel(
        [MenuLeaf(TR.sign_message__confirm_without_review, skip_review)], cancel
    )
    with trezorui_api.confirm_value(
        title=title,
        description=description,
        value=data,
        verb=verb or TR.buttons__confirm,
        hold=hold,
        chunkify=chunkify,
        info=True,  # menu with the choice to skip the review
    ) as layout:
        while True:
            result = await interact_with_menu(layout, menu, br_name, br_code)
            if not isinstance(result, MenuResult) or not extra_confirmation_if_not_read:
                return
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
                continue  # back to the content
            return


def confirm_address(
    title: str,
    address: str,
    subtitle: str | None = None,
    description: str | None = None,
    verb: str | None = None,
    footer: tuple[str, bool] | None = None,
    chunkify: bool = True,
    br_name: str | None = None,
    br_code: ButtonRequestType = BR_CODE_OTHER,
    info_items: Iterable[StrPropertyType] | None = None,
    info_title: str | None = None,
) -> Awaitable[None]:
    br_name = br_name or "confirm_address"  # def_arg
    if info_items:
        return _confirm_value_with_menu(
            br_name,
            br_code,
            subtitle or title,
            address,
            [
                create_info_menu_leaf(
                    info_title or TR.words__title_information,
                    with_colon(info_items),
                )
            ],
            description=with_colon(description),
            verb=verb or TR.buttons__confirm,
            chunkify=chunkify,
        )
    return confirm_blob(
        br_name,
        subtitle or title,
        address,
        description,
        verb=verb,
        br_code=br_code,
        chunkify=chunkify,
    )


def confirm_text(
    br_name: str,
    title: str,
    data: str,
    description: str | None = None,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> Awaitable[None]:
    if description and data:
        description = with_colon(description)

    return _placeholder_confirm(
        br_name,
        title,
        data,
        description,
        br_code=br_code,
    )


async def confirm_properties(
    br_name: str,
    title: str,
    props: Sequence[PropertyType],  # TODO: replace with StrPropertyType
    subtitle: str | None = None,
    hold: bool = False,
    br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
    verb: str | None = None,
) -> None:

    assert props
    from ..properties import with_colon

    items = with_colon(
        (
            prop[0],
            (utils.hexlify_if_bytes(prop[1]) if prop[1] else None),
            prop[2],
        )
        for prop in props
    )

    if subtitle:
        title += ": " + subtitle

    with trezorui_api.confirm_properties(
        title=title,
        items=items,
        hold=hold,
        verb=verb,
    ) as layout:
        return await raise_if_not_confirmed(
            layout,
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
    info_items: Iterable[StrPropertyType] | None = None,
    chunkify: bool = False,
    chunkify_info: bool = False,
    cancel: bool = False,
    cancel_text: str | None = None,
) -> None:
    """General confirmation dialog, used by many other confirm_* functions.

    `info_items` are shown in the menu, `cancel_text` labels its cancel item.
    """

    if description and value:
        description = with_colon(description)

    if not info_items:
        with trezorui_api.confirm_value(
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
        ) as layout:
            return await raise_if_not_confirmed(
                layout,
                br_name,
                br_code,
            )

    from trezor.ui.layouts.menu import leaf_from_layout

    def item_factory(
        info_title: str, info_value: str
    ) -> Callable[[], trezorui_api.LayoutContext]:
        return lambda: trezorui_api.confirm_value(
            title=info_title,
            value=info_value,
            description=None,
            verb="",
            verb_cancel="",
            is_data=is_data,
            chunkify=chunkify_info,
        )

    await _confirm_value_with_menu(
        br_name,
        br_code,
        title,
        value,
        [
            leaf_from_layout(name or "", item_factory(name or "", value or ""))
            for name, value, _is_data in info_items
        ],
        description=description,
        verb=verb or TR.buttons__confirm,
        is_data=is_data,
        chunkify=chunkify,
        cancel=cancel_text,
    )


async def confirm_total(
    total_amount: str,
    fee_amount: str,
    title: str | None = None,
    total_label: str | None = None,
    fee_label: str | None = None,
    account_title: str | None = None,
    account_items: Iterable[StrPropertyType] | None = None,
    fee_items: Iterable[StrPropertyType] | None = None,
    br_name: str = "confirm_total",
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    total_label = total_label or TR.send__total_amount  # def_arg
    fee_label = fee_label or TR.send__including_fee  # def_arg

    from ..properties import with_colon

    await _confirm_summary(
        br_name,
        amount=total_amount,
        amount_label=with_colon(total_label),
        fee=fee_amount,
        fee_label=with_colon(fee_label),
        info=(
            (TR.confirm_total__title_fee, with_colon(fee_items)),
            (
                account_title or TR.confirm_total__title_sending_from,
                with_colon(account_items),
            ),
        ),
        br_code=br_code,
    )


async def confirm_trade(
    title: str,
    trade: Trade,
    extra_menu_items: list[tuple[str, str]],
) -> None:
    from trezor.ui.layouts.menu import confirm_with_menu

    items = []
    if trade.sell_amount is not None:
        items.append(("", trade.sell_amount, True))
    items.append(("", trade.buy_amount, True))
    trade_ctx = trezorui_api.confirm_properties(
        title=title,
        items=items,
        verb=TR.buttons__continue,
        external_menu=True,
    )

    account_items: list[StrPropertyType] = [("", trade.address, None)]
    if trade.account:
        account_items.append((TR.words__account, trade.account, None))
    if trade.account_path:
        account_items.append(
            (TR.address_details__derivation_path, trade.account_path, None)
        )
    menu_items = [
        create_info_menu_leaf(TR.address__title_receive_address, account_items)
    ]
    for k, v in extra_menu_items:
        menu_items.append(create_info_menu_leaf(k, v))
    menu = _menu_with_cancel(menu_items, TR.buttons__cancel_sign)

    with trade_ctx as trade_layout:
        await confirm_with_menu(trade_layout, menu, "confirm_trade")


if not utils.BITCOIN_ONLY:

    async def confirm_blob_prefix(
        data: memoryview,
        *,
        total_len: int,
        confirmed_len: int,
        br_name: str,
        br_code: ButtonRequestType = BR_CODE_OTHER,
    ) -> int | None:
        """
        Returns the number of bytes confirmed, or `None` if confirmation should be skipped.
        """
        prefix = data[: 4 * 9]  # 4 rows x 18 hex digits
        confirmed_len += len(prefix)

        button_text = DOWN_ARROW if confirmed_len < total_len else ""

        show_more = await should_show_more(
            title=TR.ethereum__title_input_data_bytes.format(confirmed_len, total_len),
            para=[(utils.hexlify_if_bytes(prefix), True)],
            button_text=button_text,  # will return True
            confirm=TR.buttons__confirm_all,  # will return False
            br_name=br_name,
            br_code=br_code,
        )
        if show_more:
            return len(prefix)
        return None

    async def confirm_calldata_digest(digest: AnyBytes, size: int) -> None:
        pass

    def confirm_ethereum_unknown_contract_warning(
        _title: str | None,
    ) -> Awaitable[None]:
        return show_danger(
            "unknown_contract_warning",
            TR.words__know_what_your_doing,
            title=TR.ethereum__unknown_contract_address,
        )

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
        total_amount: str | AboveThreshold | None,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        fee_info_items: Iterable[StrPropertyType],
        chunkify: bool = False,
        native_amount: str | None = None,
    ) -> None:
        from ..properties import AboveThreshold, with_colon

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

        if isinstance(total_amount, AboveThreshold):
            await show_warning(
                "confirm_ethereum_approve",
                TR.ethereum__approve_unlimited_template.format(token_symbol),
                TR.words__continue_anyway_question,
            )

        if is_unknown_token:
            await confirm_value(
                TR.ethereum__title_token_contract,
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

        properties: list[StrPropertyType] = (
            [(TR.words__token, token_symbol, True)]
            if is_revoke
            else [
                (
                    TR.ethereum__approve_amount_allowance,
                    (
                        total_amount.message
                        if isinstance(total_amount, AboveThreshold)
                        else total_amount
                    ),
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

        account_items = _account_info_items(account, account_path)

        await _confirm_summary(
            "confirm_ethereum_approve",
            amount=native_amount,
            amount_label=with_colon(TR.words__amount) if native_amount else None,
            fee=maximum_fee,
            fee_label=with_colon(TR.send__maximum_fee),
            title=TR.words__title_summary,
            info=(
                (TR.confirm_total__title_fee, with_colon(fee_info_items)),
                (TR.address_details__account_info, account_items),
            ),
            br_code=BR_CODE_OTHER,
        )

    async def confirm_ethereum_clear_signing(
        contract_name: str,
        intent: str,
        properties: list[StrPropertyType],
        maximum_fee: str,
        contract_address: str,
        chain_info: StrPropertyType,
        amount: str | None = None,
        account: str | None = None,
        account_path: str | None = None,
    ) -> None:
        from trezor.ui.layouts.menu import confirm_with_menu

        from ..properties import with_colon

        br_name = "ethereum/clear_signing"

        account_properties: list[StrPropertyType] = []
        if account_path:
            assert account is not None
            account_properties.append((TR.words__account, account, None))
            account_properties.append(
                (TR.address_details__derivation_path, account_path, None)
            )

        contract_properties: list[StrPropertyType] = [
            (TR.words__address, contract_address, None),
            chain_info,
        ]

        def _menu() -> Menu[None]:
            menu_items: list[MenuLeaf[None]] = []
            if account_properties:
                menu_items.append(
                    create_info_menu_leaf(
                        TR.address_details__account_info,
                        with_colon(account_properties),
                    )
                )
            menu_items.append(
                create_info_menu_leaf(
                    TR.ethereum__contract_address, with_colon(contract_properties)
                )
            )
            return _menu_with_cancel(menu_items)

        await confirm_action(
            f"{br_name}/provider", TR.ethereum__contract_address, contract_name
        )
        await confirm_action(f"{br_name}/intent", TR.words__intent, intent)
        if properties:
            with trezorui_api.confirm_properties(
                title=TR.ethereum__confirm_contract,
                items=with_colon(properties),
                hold=False,
                external_menu=True,
            ) as layout:
                await confirm_with_menu(
                    layout, _menu(), br_name, ButtonRequestType.ConfirmOutput
                )

        # all the context goes into the menu
        with trezorui_api.confirm_summary(
            amount=amount,
            amount_label=with_colon(TR.words__amount) if amount is not None else None,
            fee=maximum_fee,
            fee_label=with_colon(TR.send__maximum_fee),
            external_menu=True,
        ) as layout:
            await confirm_with_menu(layout, _menu(), f"{br_name}/summary")

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
        info_items: Iterable[StrPropertyType],
        chunkify: bool = False,
        br_name: str = "confirm_ethereum_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        from ..properties import with_colon

        await _confirm_value_with_menu(
            br_name,
            br_code,
            title,
            intro_question,
            [create_info_menu_leaf(address_title, address)]
            + _account_info_leaves(account, account_path),
            verb=verb,
            is_data=False,
            cancel=TR.buttons__cancel_sign,
        )

        # confirmation
        if verb == TR.ethereum__staking_claim:
            amount_title = verb
            amount_value = ""
        else:
            amount_title = with_colon(TR.words__amount)
            amount_value = total_amount

        await _confirm_summary(
            br_name,
            amount=amount_value,
            amount_label=amount_title,
            fee=maximum_fee,
            fee_label=with_colon(TR.send__maximum_fee),
            info=((TR.confirm_total__title_fee, with_colon(info_items)),),
            br_code=br_code,
        )

    async def confirm_ethereum_vault_tx(
        title: str,
        intro_question: str,
        verb: str,
        vault_str: str,
        amount: str,
        amount_label: str,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        info_items: Iterable[StrPropertyType],
        chain: str,
        br_name: str = "ethereum/vault",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
        extra_data: str | None = None,
        receiver_address: str | None = None,
        owner_address: str | None = None,
        chunkify: bool = True,
        vault_is_address: bool = False,
    ) -> None:
        from ..properties import with_colon

        await _confirm_value_with_menu(
            f"{br_name}/intro",
            br_code,
            title,
            intro_question,
            _account_info_leaves(account, account_path),
            verb=TR.buttons__continue,
            is_data=False,
            cancel=TR.buttons__cancel_sign,
        )

        await confirm_value(
            title=title,
            value=vault_str,
            description=verb,
            verb=TR.buttons__continue,
            cancel=True,
            chunkify=chunkify and vault_is_address,
            br_name=f"{br_name}/vault",
            br_code=br_code,
        )

        await confirm_properties(
            f"{br_name}/amount",
            title,
            [
                (amount_label, amount, False),
                (TR.words__chain, chain, False),
            ],
        )

        if receiver_address is not None:
            await confirm_value(
                title=title,
                value=receiver_address,
                description=TR.words__recipient,
                br_name=f"{br_name}/receiver_address",
                br_code=br_code,
                verb=TR.buttons__continue,
                chunkify=chunkify,
                cancel=True,
            )

        if owner_address is not None:
            await confirm_value(
                title=title,
                value=owner_address,
                description=TR.ethereum__vault_owner_address,
                br_name=f"{br_name}/owner_address",
                br_code=br_code,
                verb=TR.buttons__continue,
                chunkify=chunkify,
                cancel=True,
            )

        if extra_data is not None:
            await confirm_value(
                title=title,
                value=extra_data,
                description=TR.ethereum__calldata_suffix,
                is_data=True,
                verb=TR.buttons__continue,
                cancel=True,
                br_name=f"{br_name}/extra_data",
                br_code=br_code,
            )

        await _confirm_summary(
            f"{br_name}/summary",
            fee=maximum_fee,
            fee_label=with_colon(TR.send__maximum_fee),
            title=title,
            info=((TR.confirm_total__title_fee, with_colon(info_items)),),
            br_code=br_code,
        )

    async def confirm_ethereum_vault_claim(
        title: str,
        intro_question: str,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        info_items: Iterable[StrPropertyType],
        token_list: str,
        br_name: str,
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:

        from ..properties import with_colon

        await _confirm_value_with_menu(
            f"{br_name}/intro",
            br_code,
            title,
            intro_question,
            _account_info_leaves(account, account_path),
            verb=TR.buttons__continue,
            is_data=False,
            cancel=TR.buttons__cancel_sign,
        )

        await confirm_properties(
            f"{br_name}/tokens",
            title,
            [
                (TR.ethereum__reward_tokens, token_list, False),
            ],
            br_code=br_code,
        )

        await _confirm_summary(
            f"{br_name}/summary",
            fee=maximum_fee,
            fee_label=with_colon(TR.send__maximum_fee),
            title=title,
            info=((TR.confirm_total__title_fee, with_colon(info_items)),),
            br_code=br_code,
        )

    async def confirm_ethereum_eip7702_auth(
        delegate_name: str,
        delegate_addr: str,
        network_item: StrPropertyType,
        account: str,
        account_path: str,
        nonce: int,
    ) -> None:
        from trezor.ui.layouts.menu import confirm_with_menu

        with trezorui_api.show_warning(
            title=TR.words__warning,
            button=TR.buttons__confirm,
            description=TR.ethereum__auth_warn,
            value=TR.words__know_what_your_doing,
            allow_cancel=True,
            danger=True,
        ) as layout:
            await raise_if_not_confirmed(layout, "ethereum/auth7702/warn")

        with trezorui_api.confirm_properties(
            title=TR.ethereum__auth_title,
            items=with_colon(
                (
                    (TR.ethereum__delegating, account, False),
                    (TR.ethereum__to, delegate_name, False),
                    network_item,
                )
            ),
            hold=False,
            external_menu=True,
        ) as layout:
            account_info = with_colon(
                (
                    (TR.words__account, account, False),
                    (TR.address_details__derivation_path, account_path, False),
                )
            )
            more_info = with_colon(
                (
                    (TR.ethereum__smart_info, delegate_addr, False),
                    # TODO: switch to non-Cardano specific string
                    (TR.cardano__nonce, str(nonce), False),
                )
            )
            children = [
                create_info_menu_leaf(TR.address_details__account_info, account_info),
                create_info_menu_leaf(TR.buttons__more_info, more_info),
            ]
            await confirm_with_menu(
                layout,
                _menu_with_cancel(children),
                "ethereum/auth7702/details",
                ButtonRequestType.SignTx,
            )

    async def confirm_ethereum_eip7702_revoke(
        network_item: StrPropertyType,
        account: str,
        account_path: str,
        nonce: int,
    ) -> None:
        from trezor.ui.layouts.menu import confirm_with_menu

        account_info = with_colon(
            (
                (TR.words__account, account, False),
                (TR.address_details__derivation_path, account_path, False),
            )
        )
        menu = _menu_with_cancel(
            [
                create_info_menu_leaf(TR.address_details__account_info, account_info),
                # TODO: switch to non-Cardano specific string
                create_info_menu_leaf(TR.cardano__nonce, str(nonce)),
            ]
        )

        with trezorui_api.confirm_action(
            title=TR.words__warning,
            description=TR.words__know_what_your_doing,
            action=TR.ethereum__revoke_warn.format(account),
            verb=TR.buttons__continue,
            external_menu=True,
            cancel=False,
        ) as layout:
            await confirm_with_menu(
                layout, menu, "ethereum/revoke7702/intro", ButtonRequestType.SignTx
            )

        with trezorui_api.confirm_properties(
            title=TR.ethereum__revoke_title,
            items=with_colon(
                (
                    (TR.ethereum__approve_revoke_from, account, False),
                    network_item,
                )
            ),
            verb=TR.buttons__confirm,
            hold=True,
            external_menu=True,
        ) as layout:
            await confirm_with_menu(
                layout, menu, "ethereum/revoke7702/details", ButtonRequestType.SignTx
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
        items: Iterable[StrPropertyType] = (),
        br_name: str = "confirm_solana_recipient",
        br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,
        chunkify: bool = False,
    ) -> Awaitable[None]:
        return confirm_value(
            title=title,
            value=recipient,
            description="",
            br_name=br_name,
            br_code=br_code,
            verb=TR.buttons__continue,
            info_items=items,
            chunkify=chunkify,
        )

    async def confirm_solana_tx(
        amount: str,
        fee: str,
        items: Iterable[StrPropertyType],
        amount_title: str | None = None,
        fee_title: str | None = None,
        br_name: str = "confirm_solana_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        from ..properties import with_colon

        amount_title = (
            amount_title if amount_title is not None else TR.words__amount
        )  # def_arg
        fee_title = fee_title or TR.words__fee  # def_arg
        await _confirm_summary(
            br_name,
            amount=amount,
            amount_label=with_colon(amount_title),
            fee=fee,
            fee_label=with_colon(fee_title),
            info=((TR.words__title_information, with_colon(items)),),
            br_code=br_code,
        )

    async def confirm_solana_staking_tx(
        title: str | None,
        description: str,
        account: str,
        account_path: str,
        vote_account: str,
        stake_item: StrPropertyType | None,
        amount_item: StrPropertyType | None,
        fee_item: StrPropertyType,
        fee_details: Iterable[StrPropertyType],
        blockhash_item: StrPropertyType,
        chunkify: bool,
        br_name: str = "confirm_solana_staking_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        from trezor.ui.layouts.menu import confirm_with_menu

        from ..properties import with_colon

        if not amount_item:
            amount_label, amount, _is_data = fee_item
            amount_label = f"\n\n{amount_label}"
            fee_label = ""
            fee = ""
        else:
            amount_label, amount, _is_data = amount_item
            fee_label, fee, _is_data = fee_item
            fee_label = fee_label or ""
            fee = fee or ""
        amount = amount or ""

        items: list[StrPropertyType] = []
        if stake_item is not None:
            items.append(stake_item)
        items.append(blockhash_item)

        if vote_account:
            description = f"{description}\n{TR.words__provider}:"
            title = None  # so the layout will fit in a single page
        else:
            description = f"\n{description}"

        main_ctx = trezorui_api.confirm_summary(
            title=title,
            amount=vote_account,
            amount_label=description,
            fee="",
            fee_label="",
            external_menu=True,
        )
        menu = _menu_with_cancel(
            (
                create_info_menu_leaf(name or "", value or "")
                for name, value, _is_data in items
            ),
            TR.buttons__cancel_sign,
        )
        with main_ctx as main:
            await confirm_with_menu(main, menu, br_name, br_code)

        main_ctx = trezorui_api.confirm_summary(
            amount=amount,
            amount_label=with_colon(amount_label),
            fee=fee,
            fee_label=with_colon(fee_label),
            external_menu=True,
        )
        account_details: list[StrPropertyType] = with_colon(
            (
                (TR.words__account, account, None),
                (TR.address_details__derivation_path, account_path, None),
            )
        )
        iter = [
            (TR.confirm_total__title_fee, fee_details),
            (TR.address_details__account_info, account_details),
        ]
        menu = _menu_with_cancel(
            create_info_menu_leaf(name, props) for name, props in iter
        )
        with main_ctx as main:
            await confirm_with_menu(main, menu, br_name, br_code)

    async def confirm_cardano_tx(
        amount: str,
        fee: str,
        items: Iterable[StrPropertyType],
        amount_title: str | None = None,
        fee_title: str | None = None,
    ) -> None:
        from ..properties import with_colon

        amount_title = TR.send__total_amount
        fee_title = TR.send__including_fee
        await _confirm_summary(
            "confirm_cardano_tx",
            amount=amount,
            amount_label=with_colon(amount_title),
            fee=fee,
            fee_label=with_colon(fee_title),
            info=((TR.words__title_information, with_colon(items)),),
        )

    async def confirm_ethereum_tx(
        recipient: str | None,
        total_amount: str,
        account: str | None,
        account_path: str | None,
        maximum_fee: str,
        fee_info_items: Iterable[StrPropertyType],
        is_send: bool,
        br_name: str = "confirm_ethereum_tx",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
        chunkify: bool = False,
        native_amount: str | None = None,
    ) -> None:
        from trezor.ui.layouts.menu import interact_with_menu

        from ..common import confirm_linear_flow
        from ..properties import with_colon

        if native_amount is not None:
            # A non-zero native ETH value carried alongside a token transfer;
            # show it next to the token amount so it can't be signed unseen.
            total_amount = f"{total_amount}\n{native_amount}"

        if is_send:
            title = TR.words__recipient
        else:
            title = TR.ethereum__contract_address if recipient else ""

        recipient_menu = _menu_with_cancel(
            _account_info_leaves(account, account_path), TR.buttons__cancel_sign
        )
        summary_menu = _menu_with_cancel(
            [
                create_info_menu_leaf(
                    TR.confirm_total__title_fee, with_colon(fee_info_items)
                )
            ]
        )

        async def _recipient() -> trezorui_api.UiResult:
            with trezorui_api.confirm_value(
                title=title,
                value=recipient or TR.ethereum__new_contract,
                description=None,
                is_data=bool(recipient),
                verb=TR.buttons__continue,
                chunkify=chunkify if recipient else False,
                external_menu=True,
            ) as layout:
                return await interact_with_menu(
                    layout, recipient_menu, br_name, br_code
                )

        async def _summary() -> trezorui_api.UiResult:
            # "Shift" + right button goes back to the recipient
            with trezorui_api.confirm_summary(
                amount=total_amount,
                amount_label=with_colon(TR.words__amount),
                fee=maximum_fee,
                fee_label=with_colon(TR.send__maximum_fee),
                back_button=True,
                external_menu=True,
            ) as layout:
                return await interact_with_menu(layout, summary_menu, br_name, br_code)

        await confirm_linear_flow(_recipient, _summary)

    async def confirm_stellar_tx(
        fee: str,
        account_name: str,
        account_path: str,
        is_sending_from_trezor_account: bool,
        extra_items: Iterable[StrPropertyType],
    ) -> None:
        from ..properties import with_colon

        await _confirm_summary(
            "confirm_stellar_tx",
            fee=fee,
            fee_label=with_colon(TR.send__maximum_fee),
            info=(
                (TR.words__title_information, with_colon(extra_items)),
                (
                    (
                        TR.send__send_from
                        if is_sending_from_trezor_account
                        else TR.stellar__sign_with
                    ),
                    with_colon(
                        (
                            (TR.words__account, account_name, None),
                            (TR.address_details__derivation_path, account_path, None),
                        )
                    ),
                ),
            ),
        )

    def _stellar_title(title: str, subtitle: str) -> str:
        # the layouts used here have no subtitle slot, join both parts into the title
        return f"{title}: {subtitle}" if subtitle else title

    async def confirm_stellar_address(
        title: str,
        subtitle: str,
        address: str,
        description: str,
        br_name: str,
    ) -> None:
        await confirm_address(
            _stellar_title(title, subtitle),
            address,
            description=description,
            verb=TR.buttons__continue,
            br_name=br_name,
        )

    async def confirm_stellar_valid_until(
        title: str,
        subtitle: str,
        live_until_ledger: int,
        br_name: str,
    ) -> None:
        await confirm_value(
            _stellar_title(title, subtitle),
            str(live_until_ledger),
            TR.stellar__valid_until_ledger,
            br_name,
            is_data=False,
            verb=TR.buttons__continue,
        )

    async def confirm_stellar_output_amount(
        title: str,
        subtitle: str,
        amount: str,
        token: StellarToken,
        description: str | None = None,
        token_contract: str | None = None,
    ) -> None:
        info_items = []
        if token.issuer is not None:
            info_items.append(
                (TR.stellar__issuer_template.format(token.symbol), token.issuer, None)
            )
        if token_contract:
            info_items.append((TR.stellar__token_contract, token_contract, None))

        await confirm_value(
            _stellar_title(title, subtitle),
            amount,
            description,
            br_name="confirm_output_amount",
            br_code=ButtonRequestType.ConfirmOutput,
            info_items=info_items,
            chunkify_info=True,
            chunkify=False,
            verb=TR.buttons__continue,
        )

    async def confirm_stellar_output(
        address: str,
        amount: str,
        output_index: int,
        token: StellarToken,
        address_description: str | None = None,
        amount_description: str | None = None,
        token_contract: str | None = None,
    ) -> None:
        await confirm_address(
            f"{TR.words__recipient} #{output_index + 1}",
            address,
            description=address_description,
            br_name="confirm_output_address",
            br_code=ButtonRequestType.ConfirmOutput,
            verb=TR.buttons__continue,
        )

        await confirm_stellar_output_amount(
            title=f"{TR.words__send} #{output_index + 1}",
            subtitle="",
            amount=amount,
            token=token,
            description=amount_description or TR.words__amount,
            token_contract=token_contract,
        )

    async def confirm_tron_claim(
        title: str,
        intro_question: str,
        account: str | None,
        account_path: str | None,
        br_name: str = "tron/claim",
        br_code: ButtonRequestType = ButtonRequestType.SignTx,
    ) -> None:
        await _confirm_value_with_menu(
            br_name,
            br_code,
            title,
            intro_question,
            _account_info_leaves(account, account_path),
            verb=TR.buttons__confirm,
            is_data=False,
            cancel=TR.buttons__cancel_sign,
        )

    async def confirm_tron_summary(
        title: str | None,
        amount: str | None,
        fee: str | None,
        account_details: tuple[str | None, str] | None = None,
    ) -> None:
        account_items = (
            [
                (TR.words__account, account_details[0], False),
                (TR.address_details__derivation_path, account_details[1], False),
            ]
            if account_details
            else None
        )
        # caesar's confirm_summary always displays the fee row; when there is no
        # fee but there is an amount, pass the amount into the fee slot so it
        # is shown correctly. When there is no amount, hide the amount row.
        if amount and not fee:
            display_amount, display_amount_label = None, None
            display_fee, display_fee_label = amount, TR.words__amount
        elif fee and not amount:
            display_amount, display_amount_label = None, None
            display_fee, display_fee_label = fee, TR.words__fee_limit
        else:
            display_amount, display_amount_label = (
                amount or "",
                (TR.words__amount if amount else ""),
            )
            display_fee, display_fee_label = (
                fee or "",
                (TR.words__fee_limit if fee else ""),
            )
        await _confirm_summary(
            "tron/summary",
            amount=display_amount,
            amount_label=display_amount_label,
            fee=display_fee,
            fee_label=display_fee_label,
            title=title or TR.words__title_summary,
            info=((TR.address_details__account_info, with_colon(account_items)),),
        )

    async def confirm_tron_send(
        amount: str | None,
        fee: str | None,
        account_details: tuple[str | None, str],
        address: str,
        chunkify: bool = False,
    ) -> None:
        await confirm_address(
            title=TR.words__send,
            subtitle=TR.words__recipient,
            address=address,
            verb=TR.buttons__continue,
            chunkify=chunkify,
            br_name="tron/send",
            info_items=[
                (TR.words__account, account_details[0], False),
                (TR.address_details__derivation_path, account_details[1], False),
            ],
            info_title=TR.address_details__account_info,
        )
        await confirm_tron_summary(
            TR.words__send,
            amount,
            fee,
            account_details,
        )

    async def confirm_tron_approve(
        recipient_addr: str,
        amount_str: str,
        is_revoke: bool,
        maximum_fee: str,
        native_amount_str: str | None = None,
        chunkify: bool = False,
    ) -> None:
        from ..properties import with_colon

        br_name = "tron/approve"
        if is_revoke:
            title = TR.ethereum__approve_intro_title_revoke
            action_subtitle = TR.ethereum__approve_intro_revoke
            value_subtitle = TR.ethereum__approve_revoke_from
            summary_view = (TR.words__token, amount_str[2:], True)
        else:
            title = TR.ethereum__approve_intro_title
            action_subtitle = TR.ethereum__approve_intro
            value_subtitle = TR.ethereum__approve_to
            summary_view = (
                TR.ethereum__approve_amount_allowance,
                amount_str,
                False,
            )

        await confirm_action(
            br_name,
            title,
            action_subtitle,
            verb=TR.buttons__continue,
        )
        await confirm_value(
            value_subtitle,
            recipient_addr,
            "",
            chunkify=chunkify,
            br_name=br_name,
            verb=TR.buttons__continue,
            cancel=True,
        )

        properties: list[StrPropertyType] = [
            summary_view,
            (TR.words__chain, "Tron", True),
        ]

        await confirm_properties(
            br_name,
            title,
            properties,
            None,
            False,
            verb=TR.buttons__continue,
        )

        with trezorui_api.confirm_summary(
            amount=native_amount_str,
            amount_label=with_colon(TR.words__amount) if native_amount_str else None,
            fee=maximum_fee,
            fee_label=with_colon(TR.words__fee_limit),
            title=title,
        ) as layout:
            await raise_if_not_confirmed(
                layout,
                br_name=br_name,
            )

    # TODO: #6364 Consider simplifying with confirm_tron_send like ETH flows.
    async def confirm_tron_transfer(
        recipient_addr: str,
        amount_str: str,
        maximum_fee: str,
        native_amount_str: str | None = None,
        chunkify: bool = False,
    ) -> None:
        from ..properties import with_colon

        br_name = "tron/transfer"
        title = TR.words__send

        await confirm_value(
            title,
            recipient_addr,
            "",
            chunkify=chunkify,
            br_name=br_name,
            verb=TR.buttons__continue,
            cancel=True,
        )

        properties: Iterable[StrPropertyType] = (
            (
                TR.words__amount,
                amount_str,
                False,
            ),
            (TR.words__chain, "Tron", True),
        )

        await confirm_properties(
            br_name,
            title,
            properties,
            None,
            False,
            verb=TR.buttons__continue,
        )

        with trezorui_api.confirm_summary(
            amount=native_amount_str,
            amount_label=with_colon(TR.words__amount) if native_amount_str else None,
            fee=maximum_fee,
            fee_label=with_colon(TR.words__fee_limit),
            title=title,
        ) as layout:
            await raise_if_not_confirmed(
                layout,
                br_name=br_name,
            )

    async def confirm_tron_voting(voting_list: list[tuple[int, str]]) -> None:
        with trezorui_api.confirm_properties(
            title=TR.words__review,
            subtitle=TR.words__voting,
            items=[
                (f"{TR.words__votes}: {vote[0]}", vote[1], True) for vote in voting_list
            ],
            hold=True,
        ) as layout:
            await raise_if_not_confirmed(
                layout,
                br_name="tron/vote",
                br_code=ButtonRequestType.SignTx,
            )


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
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
    hold: bool = False,
) -> Awaitable[None]:
    return _placeholder_confirm(
        br_name,
        title,
        description=content,
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
    address_ctx = trezorui_api.confirm_value(
        title=TR.modify_amount__title,
        value=address,
        verb=TR.buttons__continue,
        description=with_colon(TR.words__address),
    )

    modify_ctx = trezorui_api.confirm_modify_output(
        sign=sign,
        amount_change=amount_change,
        amount_new=amount_new,
    )

    with address_ctx as address_layout, modify_ctx as modify_layout:
        send_button_request = True
        while True:
            await raise_if_not_confirmed(
                address_layout,
                "modify_output" if send_button_request else None,
                ButtonRequestType.ConfirmOutput,
            )
            try:
                await raise_if_not_confirmed(
                    modify_layout,
                    "modify_output" if send_button_request else None,
                    ButtonRequestType.ConfirmOutput,
                )
            except ActionCancelled:
                send_button_request = False
                continue
            else:
                break


async def confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
    fee_rate_amount: str | None = None,
) -> None:
    from trezor.ui.layouts.menu import confirm_with_menu

    if sign < 0:
        description = TR.modify_fee__decrease_fee
    elif sign > 0:
        description = TR.modify_fee__increase_fee
    else:
        description, user_fee_change = TR.modify_fee__no_change, ""
    items: list[PropertyType] = [
        (description, user_fee_change or None, True),
        (TR.modify_fee__transaction_fee, total_fee_new, True),
    ]
    menu_items = []
    if fee_rate_amount:
        menu_items.append(
            create_info_menu_leaf(
                TR.confirm_total__title_fee,
                [(TR.modify_fee__fee_rate, fee_rate_amount, True)],
            )
        )

    with trezorui_api.confirm_properties(
        title=TR.modify_fee__title,
        items=items,
        external_menu=bool(menu_items),
    ) as layout:
        if menu_items:
            await confirm_with_menu(
                layout,
                _menu_with_cancel(menu_items),
                "modify_fee",
                ButtonRequestType.SignTx,
            )
        else:
            await raise_if_not_confirmed(layout, "modify_fee", ButtonRequestType.SignTx)


async def confirm_coinjoin(
    max_rounds: int, max_fee_per_vbyte: str, max_coordinator_fee_pct: str
) -> None:
    await confirm_properties(
        "coinjoin_final",
        TR.coinjoin__title,
        [
            (TR.coinjoin__max_rounds, str(max_rounds), True),
            (TR.coinjoin__max_mining_fee, max_fee_per_vbyte, True),
            (TR.coinjoin__max_coordinator_fee_pct, max_coordinator_fee_pct, True),
        ],
        hold=True,
        br_code=BR_CODE_OTHER,
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
    from trezor.ui.layouts.menu import Menu, cancel_leaf, confirm_with_menu

    if verify:
        address_title = TR.sign_message__verify_address
        br_name = "verify_message"
    else:
        address_title = TR.sign_message__confirm_address
        br_name = "sign_message"

    info_items: list[StrPropertyType] = []
    if account is not None:
        info_items.append((TR.words__account, account, False))
    if path is not None:
        info_items.append((TR.address_details__derivation_path, path, False))
    info_items.append(
        (
            TR.sign_message__message_size,
            TR.sign_message__bytes_template.format(len(message)),
            False,
        )
    )
    menu = Menu(
        [
            create_info_menu_leaf(TR.buttons__more_info, with_colon(info_items)),
            cancel_leaf(
                TR.buttons__cancel,
                confirm=lambda: trezorui_api.show_mismatch(
                    title=TR.addr_mismatch__mismatch
                ),
            ),
        ]
    )

    with trezorui_api.confirm_value(
        title=address_title,
        value=address,
        description=None,
        verb=TR.buttons__continue,
        chunkify=chunkify,
        external_menu=True,
    ) as address_layout:
        await confirm_with_menu(address_layout, menu, br_name, BR_CODE_OTHER)

    with trezorui_api.confirm_value(
        title=TR.sign_message__confirm_message,
        description=None,
        value=message,
        hold=not verify,
        external_menu=True,
    ) as message_layout:
        if message_layout.page_count() <= LONG_MSG_PAGE_THRESHOLD:
            await confirm_with_menu(message_layout, menu, br_name, BR_CODE_OTHER)
        else:
            await confirm_blob(
                br_name,
                TR.sign_message__confirm_message,
                message,
                br_code=BR_CODE_OTHER,
                hold=not verify,
                ask_pagination=True,
                # signing without reading the whole message is held to confirm
                extra_confirmation_if_not_read=not verify,
            )


def error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> trezorui_api.LayoutContext[trezorui_api.UiResult]:
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


async def request_passphrase_on_host() -> None:
    ctx = trezorui_api.show_simple(title=None, text=TR.passphrase__please_enter)
    await interact_simple(ctx)


async def request_passphrase_on_device(max_len: int) -> str:
    with trezorui_api.request_passphrase(
        prompt=TR.passphrase__title_enter,
        prompt_empty=TR.passphrase__continue_with_empty_passphrase,
        max_len=max_len,
    ) as layout:
        result = await interact(
            layout,
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
        attempts = ""
    elif attempts_remaining == 1:
        attempts = TR.pin__last_attempt
    else:
        attempts = f"{attempts_remaining} {TR.pin__tries_left}"

    with trezorui_api.request_pin(
        prompt=prompt,
        attempts=attempts,
        allow_cancel=allow_cancel,
        wrong_pin=wrong_pin,
    ) as layout:
        result = await interact(
            layout,
            "pin_device",
            ButtonRequestType.PinEntry,
            raise_on_cancel=wire.PinCancelled,
        )

    return result  # type: ignore ["UiResult" is not assignable to "str"]


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


async def _confirm_multiple_pages_texts(
    br_name: str,
    title: str,
    items: list[str],
    verb: str,
    br_code: ButtonRequestType = BR_CODE_OTHER,
) -> None:
    with trezorui_api.multiple_pages_texts(
        title=title, verb=verb, items=items
    ) as layout:
        return await raise_if_not_confirmed(layout, br_name, br_code)


async def pin_mismatch_popup(is_wipe_code: bool = False) -> None:
    description = TR.wipe_code__mismatch if is_wipe_code else TR.pin__mismatch
    br_name = "wipe_code_mismatch" if is_wipe_code else "pin_mismatch"
    # result is ignored
    await show_warning(
        br_name,
        description,
        TR.pin__please_check_again,
        TR.buttons__check_again,
        br_code=BR_CODE_OTHER,
    )


def wipe_code_same_as_pin_popup() -> Awaitable[None]:
    return confirm_action(
        "wipe_code_same_as_pin",
        TR.wipe_code__title_invalid,
        description=TR.wipe_code__diff_from_pin,
        verb=TR.buttons__try_again,
        verb_cancel=None,
        br_code=BR_CODE_OTHER,
    )


async def wipe_code_pin_not_set_popup(
    title: str, description: str, button: str
) -> NoReturn:
    await show_error_and_raise(
        "warning_pin_not_set",
        description,
        title,
        button,
    )


async def pin_wipe_code_exists_popup(
    title: str, description: str, button: str
) -> NoReturn:
    await show_error_and_raise(
        "wipe_code_exists",
        description,
        title,
        button,
    )


async def confirm_set_new_code(is_wipe_code: bool) -> None:
    if is_wipe_code:
        title = TR.wipe_code__title_settings
        description = TR.wipe_code__turn_on
        information = TR.wipe_code__info
        br_name = "set_wipe_code"
    else:
        title = TR.pin__title_settings
        description = TR.pin__turn_on
        information = TR.pin__info
        br_name = "set_pin"

    await _confirm_multiple_pages_texts(
        br_name,
        title,
        [description, information],
        TR.buttons__turn_on,
        BR_CODE_OTHER,
    )

    # Not showing extra info for wipe code
    if is_wipe_code:
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


async def confirm_firmware_update(description: str, fingerprint: str) -> None:
    from trezor.ui.layouts.menu import confirm_with_menu

    menu = _menu_with_cancel(
        [create_info_menu_leaf(TR.firmware_update__title_fingerprint, fingerprint)]
    )
    with trezorui_api.confirm_firmware_update(
        description=description, fingerprint=fingerprint
    ) as layout:
        await confirm_with_menu(layout, menu, "firmware_update", BR_CODE_OTHER)


def create_info_menu_leaf(
    name: str, value: Sequence[StrPropertyType] | str
) -> MenuLeaf[None]:
    from trezor.ui.layouts.menu import leaf_from_layout

    return leaf_from_layout(
        name, lambda: trezorui_api.show_properties(title=name, value=value)
    )


def _menu_with_cancel(
    items: Iterable[MenuLeaf[R]], cancel: str | None = None
) -> Menu[R]:
    """Context menu with the given items, and the last one cancelling the flow
    (labelled `cancel`, "Cancel" by default)."""
    from trezor.ui.layouts.menu import Menu, cancel_leaf

    items = list(items)
    items.append(cancel_leaf(cancel or TR.buttons__cancel))
    return Menu(items)


def _account_info_items(
    account: str | None, account_path: str | None
) -> list[StrPropertyType]:
    items: list[StrPropertyType] = []
    if account:
        items.append((TR.words__account, account, None))
    if account_path:
        items.append((TR.address_details__derivation_path, account_path, None))
    return with_colon(items)


def _account_info_leaves(
    account: str | None, account_path: str | None
) -> list[MenuLeaf[None]]:
    """ "Account info" menu item, if there is any."""
    items = _account_info_items(account, account_path)
    if not items:
        return []
    return [create_info_menu_leaf(TR.address_details__account_info, items)]


async def _confirm_value_with_menu(
    br_name: str,
    br_code: ButtonRequestType,
    title: str,
    value: str,
    menu_items: Iterable[MenuLeaf[None]],
    *,
    description: str | None = None,
    verb: str | None = None,
    is_data: bool = True,
    chunkify: bool = False,
    cancel: str | None = None,
) -> None:
    """Value confirmed by the right button, with `menu_items` and a cancel item
    in the menu."""
    from trezor.ui.layouts.menu import confirm_with_menu

    with trezorui_api.confirm_value(
        title=title,
        value=value,
        description=description,
        verb=verb or TR.buttons__confirm,
        is_data=is_data,
        chunkify=chunkify,
        external_menu=True,
    ) as layout:
        await confirm_with_menu(
            layout, _menu_with_cancel(menu_items, cancel), br_name, br_code
        )


async def _confirm_summary(
    br_name: str,
    *,
    fee: str,
    fee_label: str,
    amount: str | None = None,
    amount_label: str | None = None,
    title: str | None = None,
    info: Iterable[tuple[str, Sequence[StrPropertyType] | str | None]] = (),
    br_code: ButtonRequestType = ButtonRequestType.SignTx,
) -> None:
    """Summary confirmed by holding the right button. Each non-empty `info`
    (title and properties) is an item of the context menu."""
    from trezor.ui.layouts.menu import confirm_with_menu

    menu_items = [create_info_menu_leaf(name, value) for name, value in info if value]
    with trezorui_api.confirm_summary(
        amount=amount,
        amount_label=amount_label,
        fee=fee,
        fee_label=fee_label,
        title=title,
        external_menu=bool(menu_items),
    ) as layout:
        if menu_items:
            await confirm_with_menu(
                layout, _menu_with_cancel(menu_items), br_name, br_code
            )
        else:
            await raise_if_not_confirmed(layout, br_name, br_code)
