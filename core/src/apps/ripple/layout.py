from typing import TYPE_CHECKING

from trezor import TR, wire
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount, format_amount_unit
from trezor.ui.layouts import confirm_metadata, confirm_total

from .helpers import DECIMALS

if TYPE_CHECKING:
    from trezor.messages import PaymentRequest

    from apps.common.paths import Bip32Path


async def require_confirm_total(total: int, fee: int) -> None:
    await confirm_total(
        format_amount_unit(format_amount(total, DECIMALS), "XRP"),
        format_amount_unit(format_amount(fee, DECIMALS), "XRP"),
    )


async def require_confirm_destination_tag(tag: int) -> None:
    from trezor import TR

    await confirm_metadata(
        "confirm_destination_tag",
        TR.ripple__confirm_tag,
        TR.ripple__destination_tag_template,
        str(tag),
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_tx(to: str, value: int, chunkify: bool = False) -> None:
    from trezor.ui.layouts import confirm_output

    await confirm_output(
        to, format_amount_unit(format_amount(value, DECIMALS), "XRP"), chunkify=chunkify
    )


async def require_confirm_payment_request(
    provider_address: str,
    verified_payment_request: PaymentRequest,
    address_n: Bip32Path | None,
) -> None:
    from trezor.ui.layouts import confirm_payment_request

    from apps.common.paths import address_n_to_str

    assert verified_payment_request.amount is not None  # required for non-CoinJoin
    total_amount = format_amount_unit(
        format_amount(verified_payment_request.amount, DECIMALS), "XRP"
    )

    texts = []
    refunds = []
    trades = []
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
                    f"-\u00A0{total_amount}",
                    f"+\u00A0{memo.coin_purchase_memo.amount}",
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
