from trezor import strings, ui
from trezor.enums import ButtonRequestType
from trezor.ui.constants import MONO_ADDR_PER_LINE
from trezor.ui.layouts import (
    confirm_action,
    confirm_hex,
    confirm_metadata,
    confirm_timebounds_stellar,
)

from . import consts


async def require_confirm_init(
    ctx, address: str, network_passphrase: str, accounts_match: bool
):
    if accounts_match:
        description = "Initialize signing with\nyour account"
    else:
        description = "Initialize signing with"
    await require_confirm_op(
        ctx,
        "confirm_init",
        title="Confirm Stellar",
        subtitle=None,
        description=description,
        data=address,
        icon=ui.ICON_SEND,
        is_account=True,
    )

    network = get_network_warning(network_passphrase)
    if network:
        await confirm_metadata(
            ctx,
            "confirm_init_network",
            title="Confirm network",
            content="Transaction is on {}",
            param=network,
            icon=ui.ICON_CONFIRM,
            br_code=ButtonRequestType.ConfirmOutput,
            hide_continue=True,
        )


async def require_confirm_timebounds(ctx, start: int, end: int):
    await confirm_timebounds_stellar(ctx, start, end)


async def require_confirm_memo(ctx, memo_type: int, memo_text: str):
    if memo_type == consts.MEMO_TYPE_TEXT:
        description = "Memo (TEXT)"
    elif memo_type == consts.MEMO_TYPE_ID:
        description = "Memo (ID)"
    elif memo_type == consts.MEMO_TYPE_HASH:
        description = "Memo (HASH)"
    elif memo_type == consts.MEMO_TYPE_RETURN:
        description = "Memo (RETURN)"
    else:
        return await confirm_action(
            ctx,
            "confirm_memo",
            title="Confirm memo",
            action="No memo set!",
            description="Important: Many exchanges require a memo when depositing",
            icon=ui.ICON_CONFIRM,
            icon_color=ui.GREEN,
            br_code=ButtonRequestType.ConfirmOutput,
        )

    await require_confirm_op(
        ctx,
        "confirm_memo",
        title="Confirm memo",
        subtitle=description,
        data=memo_text,
        split=False,
    )


async def require_confirm_final(ctx, fee: int, num_operations: int):
    op_str = strings.format_plural("{count} {plural}", num_operations, "operation")
    await confirm_metadata(
        ctx,
        "confirm_final",
        title="Final confirm",
        content="Sign this transaction made up of " + op_str + " and pay {}\nfor fee?",
        param=format_amount(fee),
        hide_continue=True,
        hold=True,
    )


async def require_confirm_op(
    ctx,
    br_type: str,
    subtitle: str | None,
    data: str,
    title: str = "Confirm operation",
    description: str = None,
    icon=ui.ICON_CONFIRM,
    split: bool = True,
    is_account: bool = False,
):
    await confirm_hex(
        ctx,
        br_type,
        title=title,
        subtitle=subtitle,
        description=description,
        data=data,
        width=MONO_ADDR_PER_LINE if split else None,
        icon=icon,
        truncate=True,
        truncate_ellipsis=".." if is_account else "",
        br_code=ButtonRequestType.ConfirmOutput,
    )


def format_amount(amount: int, ticker=True) -> str:
    t = ""
    if ticker:
        t = " XLM"
    return strings.format_amount(amount, consts.AMOUNT_DECIMALS) + t


def get_network_warning(network_passphrase: str):
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        return None
    if network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        return "testnet network"
    return "private network"
