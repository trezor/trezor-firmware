from trezor import strings, ui
from trezor.enums import ButtonRequestType, StellarAssetType, StellarMemoType
from trezor.ui.layouts import (
    confirm_action,
    confirm_address,
    confirm_blob,
    confirm_metadata,
    confirm_properties,
)
from trezor.wire import DataError

from . import consts

if False:
    from trezor.wire import Context

    from trezor.messages import StellarAsset


async def require_confirm_init(
    ctx: Context,
    address: str,
    network_passphrase: str,
    accounts_match: bool,
) -> None:
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


async def require_confirm_timebounds(ctx: Context, start: int, end: int) -> None:
    await confirm_properties(
        ctx,
        "confirm_timebounds",
        title="Confirm timebounds",
        props=(
            (
                "Valid from (UTC)",
                strings.format_timestamp(start) if start > 0 else "[no restriction]",
            ),
            (
                "Valid to (UTC)",
                strings.format_timestamp(end) if end > 0 else "[no restriction]",
            ),
        ),
    )


async def require_confirm_memo(
    ctx: Context, memo_type: StellarMemoType, memo_text: str
) -> None:
    if memo_type == StellarMemoType.TEXT:
        description = "Memo (TEXT)"
    elif memo_type == StellarMemoType.ID:
        description = "Memo (ID)"
    elif memo_type == StellarMemoType.HASH:
        description = "Memo (HASH)"
    elif memo_type == StellarMemoType.RETURN:
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


async def require_confirm_final(ctx: Context, fee: int, num_operations: int) -> None:
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


def format_asset(asset: StellarAsset | None) -> str:
    if asset is None or asset.type == StellarAssetType.NATIVE:
        return "XLM"
    else:
        if asset.code is None:
            raise DataError("Stellar asset code is missing")
        return asset.code


def format_amount(amount: int, asset: StellarAsset | None = None) -> str:
    return (
        strings.format_amount(amount, consts.AMOUNT_DECIMALS)
        + " "
        + format_asset(asset)
    )


def get_network_warning(network_passphrase: str) -> str | None:
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        return None
    if network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        return "testnet network"
    return "private network"
