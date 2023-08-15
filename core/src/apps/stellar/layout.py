from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import strings
from trezor.enums import ButtonRequestType

from . import consts

if TYPE_CHECKING:
    from trezor.enums import StellarMemoType
    from trezor.messages import StellarAsset


async def require_confirm_init(
    address: str,
    network_passphrase: str,
    accounts_match: bool,
) -> None:
    description = "Initialize signing with" + " your account" if accounts_match else ""
    await layouts.confirm_address(
        "Confirm Stellar",
        address,
        description,
        "confirm_init",
    )

    # get_network_warning
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        network = None
    elif network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        network = "testnet network"
    else:
        network = "private network"

    if network:
        await layouts.confirm_metadata(
            "confirm_init_network",
            "Confirm network",
            "Transaction is on {}",
            network,
            ButtonRequestType.ConfirmOutput,
        )


async def require_confirm_timebounds(start: int, end: int) -> None:
    await layouts.confirm_properties(
        "confirm_timebounds",
        "Confirm timebounds",
        (
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


async def require_confirm_memo(memo_type: StellarMemoType, memo_text: str) -> None:
    from trezor.enums import StellarMemoType

    if memo_type == StellarMemoType.TEXT:
        description = "Memo (TEXT)"
    elif memo_type == StellarMemoType.ID:
        description = "Memo (ID)"
    elif memo_type == StellarMemoType.HASH:
        description = "Memo (HASH)"
    elif memo_type == StellarMemoType.RETURN:
        description = "Memo (RETURN)"
    else:
        return await layouts.confirm_action(
            "confirm_memo",
            "Confirm memo",
            "No memo set!",
            "Important: Many exchanges require a memo when depositing",
            br_code=ButtonRequestType.ConfirmOutput,
        )

    await layouts.confirm_blob(
        "confirm_memo",
        "Confirm memo",
        memo_text,
        description,
    )


async def require_confirm_final(fee: int, num_operations: int) -> None:
    op_str = strings.format_plural("{count} {plural}", num_operations, "operation")
    await layouts.confirm_metadata(
        "confirm_final",
        "Final confirm",
        "Sign this transaction made up of " + op_str + " and pay {}\nfor fee?",
        format_amount(fee),
        hold=True,
    )


def format_asset(asset: StellarAsset | None) -> str:
    from trezor.enums import StellarAssetType
    from trezor.wire import DataError

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
