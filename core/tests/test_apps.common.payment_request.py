# flake8: noqa: F403,F405
from common import *  # isort:skip

from typing import TYPE_CHECKING

from mock import patch
from trezor import wire
from trezor.crypto import bip39
from trezor.messages import (
    CoinPurchaseMemo,
    PaymentRequest,
    PaymentRequestMemo,
    RefundMemo,
    TextMemo,
)

from apps.common import coins
from apps.common.keychain import Keychain
from apps.common.paths import AlwaysMatchingSchema
from apps.common.payment_request import PaymentRequestVerifier

if TYPE_CHECKING:
    from typing import Callable, ParamSpec

    P = ParamSpec("P")


# Decorator that replaces DEBUG version of `verify_payment_request_is_supported` and PUBLIC_KEY
# by the PROD versions
def patch_prod(func: Callable[P, None]) -> Callable[P, None]:

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> bytes:
        with patch(
            PaymentRequestVerifier,
            "_use_debug_key",
            lambda self: None,
        ):
            with patch(
                PaymentRequestVerifier,
                "_use_debug_verification",
                lambda self: None,
            ):
                return func(*args, **kwargs)

    return wrapper


# Get keychain for SLIP-24
def _get_test_keychain() -> Keychain:
    coin = coins.by_name("Bitcoin")
    seed = bip39.seed(" ".join(["all"] * 12), "")
    keychain = Keychain(
        seed,
        coin.curve_name,
        [AlwaysMatchingSchema],
        slip21_namespaces=[[b"SLIP-0024"]],
    )
    return keychain


# Payment request helpers
def _get_request_without_memos() -> PaymentRequest:
    debug_signature = (
        "208cd919f3c6544f390b402394570fd6d1279962c13d0cb1b8180dfe0bc614ee1"
        "e55efcc85de5ab52a57a8ecf675d8454d6204c98298f93faf71c668fec9340070"
    )
    return PaymentRequest(
        recipient_name="TEST Recipient", signature=unhexlify(debug_signature), memos=[]
    )


def _get_request_with_text_memo() -> PaymentRequest:
    text_memo = TextMemo(text="text memo text")

    return PaymentRequest(
        recipient_name="TEST Recipient",
        signature=b"\x01",
        memos=[PaymentRequestMemo(text_memo=text_memo)],
    )


def _get_request_with_coin_purchase_memo() -> PaymentRequest:
    coin_purchase_memo = CoinPurchaseMemo(
        coin_type=0, amount="AMOUNT", address="ADDRESS", mac=b"\xde\xad\xbe\xef"
    )
    return PaymentRequest(
        recipient_name="TEST Recipient",
        signature=b"\x01",
        memos=[PaymentRequestMemo(coin_purchase_memo=coin_purchase_memo)],
    )


def _get_sell_payment_request() -> PaymentRequest:
    text_memo = TextMemo(text="text memo text")
    mac = "a7594205d318491c7335d460acfebadc3c862b803abfd5a0fcf7ea6082bff1dc"
    refund_memo = RefundMemo(address="ADDRESS", mac=unhexlify(mac))
    debug_signature = (
        "20b638bff2341f526ee99faa7afb28f72c54c535db69b25451ce7471dd8866fd1"
        "8644a89effcc7dfb07a281bd5c516045180341c813536563ff50725f4221df5f8"
    )
    return PaymentRequest(
        recipient_name="TEST Recipient",
        signature=unhexlify(debug_signature),
        memos=[
            PaymentRequestMemo(text_memo=text_memo),
            PaymentRequestMemo(refund_memo=refund_memo),
        ],
    )


def _get_coin_swap_request() -> PaymentRequest:
    mac = "08f2e807b9932596dd15831958cb1172ae5bb3c8bc8c6476b089bc045ca4d8b8"
    mac2 = "1394db3333b67a73b9abb6f5c9afe37c2a5f8fb92aa17baf9c696ec85d2523c1"
    debug_signature = (
        "20a5500e61eafdfbb83643f5b2c139757f760e32a7416b92a1b07a4f1a6c307a4"
        "149fbda45fdb98e051f3b839e63eb67bb167f32a85f8c6864a60785e304b703b1"
    )
    coin_purchase_memo = CoinPurchaseMemo(
        coin_type=0, amount="AMOUNT", address="ADDRESS", mac=unhexlify(mac)
    )
    refund_memo = RefundMemo(address="Refund address", mac=unhexlify(mac2))
    return PaymentRequest(
        recipient_name="TEST Recipient",
        signature=unhexlify(debug_signature),
        memos=[
            PaymentRequestMemo(coin_purchase_memo=coin_purchase_memo),
            PaymentRequestMemo(refund_memo=refund_memo),
        ],
    )


class TestPaymentRequestVerfier(unittest.TestCase):

    @patch_prod
    def test_payment_requests_unsupported_in_prod_without_memos(self):

        # Unsupported - without memos
        with self.assertRaises(wire.DataError) as e:
            PaymentRequestVerifier(
                payment_request=_get_request_without_memos(),
                slip44_id=1,
                keychain=_get_test_keychain(),
                amount_size_bytes=12345,
            )
        self.assertEqual(
            e.value.message, "Payment request must contain at least one memo."
        )

    @patch_prod
    def test_payment_requests_unsupported_in_prod_sell(self):
        with self.assertRaises(wire.DataError) as e:
            PaymentRequestVerifier(
                payment_request=_get_sell_payment_request(),
                slip44_id=1,
                keychain=_get_test_keychain(),
                amount_size_bytes=12345,
            )
        self.assertEqual(
            e.value.message, "Only COIN SWAP payment requests are supported."
        )

    @patch_prod
    def test_payment_requests_unsupported_in_prod_coin_purchase_memo_only(self):
        with self.assertRaises(wire.DataError) as e:
            PaymentRequestVerifier(
                payment_request=_get_request_with_coin_purchase_memo(),
                slip44_id=1,
                keychain=_get_test_keychain(),
                amount_size_bytes=12345,
            )
        self.assertEqual(
            e.value.message, "Only COIN SWAP payment requests are supported."
        )

    @patch_prod
    def test_payment_requests_unsupported_in_prod_text_memo_only(self):
        with self.assertRaises(wire.DataError) as e:
            PaymentRequestVerifier(
                payment_request=_get_request_with_text_memo(),
                slip44_id=1,
                keychain=_get_test_keychain(),
                amount_size_bytes=12345,
            )
        self.assertEqual(
            e.value.message, "Only COIN SWAP payment requests are supported."
        )

    @patch_prod
    def test_payment_requests_supported_in_prod_coin_swap(self):
        verifier = PaymentRequestVerifier(
            payment_request=_get_coin_swap_request(),
            slip44_id=1,
            keychain=_get_test_keychain(),
            amount_size_bytes=12345,
        )

        # Verify signature - should fail, as PROD key should be used for verification
        with self.assertRaises(wire.DataError) as e:
            verifier.verify()
        self.assertEqual(e.value.message, "Invalid signature in payment request.")

    def test_payment_requests_supported_in_debug_without_memos(self):

        verifier = PaymentRequestVerifier(
            payment_request=_get_request_without_memos(),
            slip44_id=1,
            keychain=_get_test_keychain(),
            amount_size_bytes=12345,
        )

        # Verify signature
        verifier.verify()

    def test_payment_requests_supported_in_debug_sell(self):

        verifier = PaymentRequestVerifier(
            payment_request=_get_sell_payment_request(),
            slip44_id=1,
            keychain=_get_test_keychain(),
            amount_size_bytes=12345,
        )

        # Verify signature
        verifier.verify()

    def test_payment_requests_supported_in_debug_coin_swap(self):

        verifier = PaymentRequestVerifier(
            payment_request=_get_coin_swap_request(),
            slip44_id=1,
            keychain=_get_test_keychain(),
            amount_size_bytes=12345,
        )

        # Verify signature
        verifier.verify()


if __name__ == "__main__":
    unittest.main()
