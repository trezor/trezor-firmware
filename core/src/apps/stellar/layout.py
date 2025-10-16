from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings, wire
from trezor.enums import ButtonRequestType

from apps.common.paths import address_n_to_str

from . import consts

if TYPE_CHECKING:
    from trezor.enums import StellarMemoType
    from trezor.messages import PaymentRequest, StellarAsset

    from apps.common.paths import Bip32Path


async def require_confirm_tx_source(tx_source: str) -> None:
    await layouts.show_warning(
        br_name="confirm_tx_source",
        content=TR.stellar__transaction_source_diff_warning,
        br_code=ButtonRequestType.Warning,
    )

    await layouts.confirm_address(
        title=TR.stellar__transaction_source,
        address=tx_source,
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
        return await layouts.show_warning(
            br_name="confirm_memo",
            content=TR.stellar__exchanges_require_memo,
        )

    await layouts.confirm_text(
        "confirm_memo",
        TR.stellar__confirm_memo,
        memo_text,
        description,
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_payment_request(
    provider_address: str,
    verified_payment_request: PaymentRequest,
    address_n: Bip32Path | None,
    asset: StellarAsset,
) -> None:
    from trezor.ui.layouts import confirm_payment_request

    from apps.common.payment_request import parse_amount

    total_amount = format_amount(parse_amount(verified_payment_request), asset)

    texts: list[tuple[str | None, str]] = []
    refunds: list[tuple[str, str | None, str | None]] = []
    trades: list[tuple[str, str, str, str | None, str | None]] = []
    for memo in verified_payment_request.memos:
        if memo.text_memo is not None:
            texts.append((None, memo.text_memo.text))
        elif memo.text_details_memo is not None:
            texts.append((memo.text_details_memo.title, memo.text_details_memo.text))
        elif memo.refund_memo:
            refund_account_path = address_n_to_str(memo.refund_memo.address_n)
            refunds.append((memo.refund_memo.address, None, refund_account_path))
        elif memo.coin_purchase_memo:
            coin_purchase_account_path = address_n_to_str(
                memo.coin_purchase_memo.address_n
            )
            trades.append(
                (
                    f"-\u00a0{total_amount}",
                    f"+\u00a0{memo.coin_purchase_memo.amount}",
                    memo.coin_purchase_memo.address,
                    None,
                    coin_purchase_account_path,
                )
            )
        else:
            raise wire.DataError("Unrecognized memo type in payment request memo.")

    account_path = address_n_to_str(address_n) if address_n else None
    account_items = []
    if account_path:
        account_items.append((TR.address_details__derivation_path, account_path))

    await confirm_payment_request(
        verified_payment_request.recipient_name,
        provider_address,
        texts,
        refunds,
        trades,
        account_items,
        None,
        None,
        None,
    )


async def require_confirm_final(
    address_n: list[int],
    fee: int,
    timebounds: tuple[int, int],
    is_sending_from_trezor_account: bool,
) -> None:
    from trezor.wire import DataError

    from apps.common import paths

    from . import PATTERN, SLIP44_ID

    timebounds_start, timebounds_end = timebounds
    extra_items = [
        (
            TR.stellar__valid_from,
            (
                strings.format_timestamp(timebounds_start)
                if timebounds_start > 0
                else TR.stellar__no_restriction
            ),
            None,
        ),
        (
            TR.stellar__valid_to,
            (
                strings.format_timestamp(timebounds_end)
                if timebounds_end > 0
                else TR.stellar__no_restriction
            ),
            None,
        ),
    ]

    account_name = paths.get_account_name("Stellar", address_n, PATTERN, SLIP44_ID)
    account_path = paths.address_n_to_str(address_n)

    if account_name is None:
        raise DataError("Stellar: Invalid account name")

    await layouts.confirm_stellar_tx(
        format_amount(fee),
        account_name,
        account_path,
        is_sending_from_trezor_account,
        extra_items,
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
