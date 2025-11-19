from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import PaymentNotification, Success

    from apps.common.keychain import Keychain

from apps.common.keychain import with_slip44_keychain
from apps.common.paths import address_n_to_str

# this module implements SLIP-0024 payment requests for crypto purchases using fiat


@with_slip44_keychain(slip21_namespaces=[[b"SLIP-0024"]])
async def payment_notification(msg: PaymentNotification, keychain: Keychain) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_payment_request
    from trezor.ui.layouts.slip24 import Trade
    from trezor.wire import DataError

    from apps.common.payment_request import SLIP44_ID_UNDEFINED, PaymentRequestVerifier

    if msg.payment_req is None:
        raise DataError("Missing payment request.")

    if msg.payment_req.amount is not None:
        raise DataError("Payment request amount must be missing")

    PaymentRequestVerifier(msg.payment_req, SLIP44_ID_UNDEFINED, keychain).verify()

    verified_payment_request = msg.payment_req

    texts: list[tuple[str | None, str]] = []
    trades = []
    for memo in verified_payment_request.memos:
        # Note: we do not process RefundMemo here:
        # if the swap fails, the fiat amount just remains in your custodial account, it does not get refunded anywhere
        if memo.text_memo is not None:
            texts.append((None, memo.text_memo.text))
        elif memo.text_details_memo is not None:
            texts.append((memo.text_details_memo.title, memo.text_details_memo.text))
        elif memo.coin_purchase_memo:
            coin_purchase_account_path = address_n_to_str(
                memo.coin_purchase_memo.address_n
            )
            trades.append(
                Trade(
                    None,  # if we later decide to somehow pass the fiat amount (and currency!) as part of the payment request in a more structured fashion,
                    # we should include it here so it gets shown on the trade screen, but for now we just have the fiat amount ad-hoc as part of a text memo.
                    f"+\u00a0{memo.coin_purchase_memo.amount}",  # amount of crypto purchased
                    memo.coin_purchase_memo.address,
                    None,
                    coin_purchase_account_path,
                )
            )
        else:
            raise DataError("Unrecognized memo type in payment request memo.")

    await confirm_payment_request(
        recipient_name=verified_payment_request.recipient_name,
        recipient_address=None,  # no address for the fiat being spent
        texts=texts,
        refunds=[],
        trades=trades,
        account_items=[],
        transaction_fee=None,
        fee_info_items=None,
    )

    return Success()
