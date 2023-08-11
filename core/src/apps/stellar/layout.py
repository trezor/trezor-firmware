from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings
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
    description = (
        TR.stellar__initialize_signing_with + TR.stellar__your_account
        if accounts_match
        else ""
    )
    await layouts.confirm_address(
        TR.stellar__confirm_stellar,
        address,
        description,
        "confirm_init",
    )

    # get_network_warning
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        network = None
    elif network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        network = TR.stellar__testnet_network
    else:
        network = TR.stellar__private_network

    if network:
        await layouts.confirm_metadata(
            "confirm_init_network",
            TR.stellar__confirm_network,
            TR.stellar__on_network_template,
            network,
            ButtonRequestType.ConfirmOutput,
        )


async def require_confirm_timebounds(start: int, end: int) -> None:
    await layouts.confirm_properties(
        "confirm_timebounds",
        TR.stellar__confirm_timebounds,
        (
            (
                TR.stellar__valid_from,
                strings.format_timestamp(start)
                if start > 0
                else TR.stellar__no_restriction,
            ),
            (
                TR.stellar__valid_to,
                strings.format_timestamp(end)
                if end > 0
                else TR.stellar__no_restriction,
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
            TR.stellar__confirm_memo,
            TR.stellar__no_memo_set,
            TR.stellar__exchanges_require_memo,
            br_code=ButtonRequestType.ConfirmOutput,
        )

    await layouts.confirm_blob(
        "confirm_memo",
        TR.stellar__confirm_memo,
        memo_text,
        description,
    )


async def require_confirm_final(fee: int, num_operations: int) -> None:
    op_str = strings.format_plural(
        "{count} {plural}", num_operations, TR.plurals__transaction_of_x_operations
    )
    text = (
        TR.stellar__sign_tx_count_template.format(op_str)
        + " "
        + TR.stellar__sign_tx_fee_template
    )
    await layouts.confirm_metadata(
        "confirm_final",
        TR.stellar__final_confirm,
        text,
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
