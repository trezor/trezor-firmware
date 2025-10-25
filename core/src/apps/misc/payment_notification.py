from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import PaymentNotification, Success

    from apps.common.keychain import Keychain

from trezor import strings

from apps.common.keychain import with_slip44_keychain
from apps.common.paths import PATTERN_SEP5, address_n_to_str

AMOUNT_DECIMALS = 2


@with_slip44_keychain(*[PATTERN_SEP5], slip44_id=0, slip21_namespaces=[[b"SLIP-0024"]])
async def payment_notification(msg: PaymentNotification, keychain: Keychain) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_payment_request
    from trezor.wire import DataError

    from apps.common.payment_request import PaymentRequestVerifier, parse_amount

    if msg.payment_req is None:
        raise DataError("Missing payment request.")

    PaymentRequestVerifier(msg.payment_req, 0, keychain).verify()

    verified_payment_request = msg.payment_req

    total_amount = strings.format_amount(
        parse_amount(verified_payment_request), AMOUNT_DECIMALS
    )

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
            raise DataError("Unrecognized memo type in payment request memo.")

    await confirm_payment_request(
        verified_payment_request.recipient_name,
        "",
        texts,
        refunds,
        trades,
        [],
        None,
        None,
        None,
    )

    return Success()
