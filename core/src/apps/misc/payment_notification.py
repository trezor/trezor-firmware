from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import PaymentNotification, Success

    from apps.common.keychain import Keychain

from apps.common.keychain import with_slip44_keychain


@with_slip44_keychain(slip44_id=0, slip21_namespaces=[[b"SLIP-0024"]])
async def payment_notification(msg: PaymentNotification, keychain: Keychain) -> Success:
    from trezor.messages import Success
    from trezor.wire import DataError

    from apps.common.payment_request import PaymentRequestVerifier

    if msg.payment_req is None:
        raise DataError("Missing payment request.")

    PaymentRequestVerifier(msg.payment_req, 0, keychain).verify()

    # TODO Show payment request memos.

    return Success()
