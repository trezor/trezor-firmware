from trezor import strings, ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_action,
    confirm_address,
    confirm_blob,
    confirm_metadata,
)
from trezor.ui.layouts.tt.altcoin import confirm_timebounds_stellar

from . import consts

if False:
    from trezor.messages import StellarAssetType


async def require_confirm_init(
    ctx, address: str, network_passphrase: str, accounts_match: bool
):
    if accounts_match:
        description = "Initialize signing with your account"
    else:
        description = "Initialize signing with"
    await confirm_address(
        ctx,
        title="Confirm Stellar",
        address=address,
        br_type="confirm_init",
        description=description,
        icon=ui.ICON_SEND,
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

    await confirm_blob(
        ctx,
        "confirm_memo",
        title="Confirm memo",
        description=description,
        data=memo_text,
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


def format_asset(asset: StellarAssetType | None = None) -> str:
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        return "XLM"
    else:
        return asset.code


def format_amount(amount: int, asset: StellarAssetType | None = None) -> str:
    return (
        strings.format_amount(amount, consts.AMOUNT_DECIMALS)
        + " "
        + format_asset(asset)
    )


def get_network_warning(network_passphrase: str):
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        return None
    if network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        return "testnet network"
    return "private network"
