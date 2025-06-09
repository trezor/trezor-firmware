from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings
from trezor.enums import ButtonRequestType

from . import consts

if TYPE_CHECKING:
    from trezor.enums import StellarMemoType
    from trezor.messages import StellarAsset


async def require_confirm_tx_source(tx_source: str):
    await layouts.confirm_address(
        TR.stellar__confirm_transaction_source,
        tx_source,
        description=TR.stellar__transaction_source_diff_warning,
        br_name="confirm_tx_source",
        br_code=ButtonRequestType.ConfirmOutput,
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
            TR.stellar__confirm_memo,
            TR.stellar__no_memo_set,
            TR.stellar__exchanges_require_memo,
            br_code=ButtonRequestType.ConfirmOutput,
        )

    await layouts.confirm_text(
        "confirm_memo",
        TR.stellar__confirm_memo,
        memo_text,
        description,
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_final(
    fee: int,
    timebonuds: tuple[int, int],
    network_passphrase: str,
    account_index: int,
    account_id: str,
) -> None:
    extra_items = []

    # Add network info if it is not public
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        pass
    elif network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        extra_items.append(("Network", TR.stellar__testnet_network))
    else:
        extra_items.append(("Network", TR.stellar__private_network))

    # Add timebounds info if they are restricted
    timebonuds_start, timebonuds_end = timebonuds
    if timebonuds_start > 0:
        extra_items.append(
            (
                TR.stellar__valid_from,
                strings.format_timestamp(timebonuds_start),
            )
        )
    if timebonuds_end > 0:
        extra_items.append(
            (
                TR.stellar__valid_to,
                strings.format_timestamp(timebonuds_end),
            )
        )

    await layouts.confirm_stellar_tx(
        format_amount(fee), account_index, account_id, extra_items
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
