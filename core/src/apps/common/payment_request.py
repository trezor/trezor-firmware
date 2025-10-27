from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError, context

from . import writers

if TYPE_CHECKING:
    from typing import Literal

    from trezor.messages import PaymentRequest

    from apps.common.keychain import Keychain


_MEMO_TYPE_TEXT = const(1)
_MEMO_TYPE_REFUND = const(2)
_MEMO_TYPE_COIN_PURCHASE = const(3)
_MEMO_TYPE_TEXT_DETAILS = const(4)


def parse_amount(payment_request: PaymentRequest) -> int:
    assert payment_request.amount is not None
    return int.from_bytes(payment_request.amount, "little")


def _sanitize_payment_request(payment_request: PaymentRequest) -> PaymentRequest:
    for memo in payment_request.memos:
        if (
            memo.text_memo,
            memo.text_details_memo,
            memo.refund_memo,
            memo.coin_purchase_memo,
        ).count(None) != 3:
            raise DataError(
                "Exactly one memo type must be specified in each PaymentRequestMemo."
            )
    return payment_request


def _is_coin_swap(payment_request: PaymentRequest) -> bool:
    has_coin_purchase = any(m.coin_purchase_memo for m in payment_request.memos)
    has_refund = any(m.refund_memo for m in payment_request.memos)

    return has_coin_purchase and has_refund


class PaymentRequestVerifier:
    PUBLIC_KEY = b""

    def verify_payment_request_is_supported(
        self, payment_request: PaymentRequest
    ) -> None:
        if not payment_request.memos:
            raise DataError("Payment request must contain at least one memo.")

        if not _is_coin_swap(payment_request):
            raise DataError("Only COIN SWAP payment requests are supported.")

    if __debug__:

        def _use_debug_key(self) -> None:
            # nist256p1 public key of m/0h for "all all ... all" seed.
            self.PUBLIC_KEY = b"\x03\xd9\xd9\x3f\x89\xc6\x96\x3b\x94\xbb\xd7\xa5\x11\x88\x28\xe4\x4c\x1c\x39\x59\x15\xac\xe8\x48\x88\x71\x7f\x56\x8c\xb0\x19\x74\xc3"

        def _use_debug_verification(self) -> None:
            self.verify_payment_request_is_supported = lambda payment_request: None

    def __init__(
        self,
        payment_request: PaymentRequest,
        slip44_id: int,
        keychain: Keychain,
        amount_size_bytes: Literal[
            8, 32
        ] = 8,  # amount is normally 8 bytes, but for EVM assets it is 32 bytes
    ) -> None:
        from storage.cache_common import APP_COMMON_NONCE
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from apps.common.address_mac import check_address_mac

        from . import writers  # pylint: disable=import-outside-toplevel

        if __debug__:
            self._use_debug_key()
            self._use_debug_verification()

        payment_request = _sanitize_payment_request(payment_request)
        self.verify_payment_request_is_supported(payment_request)

        self.h_outputs = HashWriter(sha256())
        self.amount = 0
        self.h_pr = HashWriter(sha256())

        if payment_request.amount is None:
            self.expected_amount = None
        else:
            if len(payment_request.amount) != amount_size_bytes:
                raise DataError(f"amount must be exactly {amount_size_bytes} bytes")
            self.expected_amount = parse_amount(payment_request)
        self.amount_size_bytes = amount_size_bytes
        self.signature = payment_request.signature

        if payment_request.nonce:
            nonce = bytes(payment_request.nonce)
            if context.cache_get(APP_COMMON_NONCE) != nonce:
                raise DataError("Invalid nonce in payment request.")
            context.cache_delete(APP_COMMON_NONCE)
        else:
            nonce = b""
            if payment_request.memos:
                DataError("Missing nonce in payment request.")

        writers.write_bytes_fixed(self.h_pr, b"SL\x00\x24", 4)
        writers.write_bytes_prefixed(self.h_pr, nonce)
        writers.write_bytes_prefixed(self.h_pr, payment_request.recipient_name.encode())
        writers.write_compact_size(self.h_pr, len(payment_request.memos))
        for m in payment_request.memos:
            if m.text_memo is not None:
                memo = m.text_memo
                writers.write_uint32_le(self.h_pr, _MEMO_TYPE_TEXT)
                writers.write_bytes_prefixed(self.h_pr, memo.text.encode())
            elif m.refund_memo is not None:
                memo = m.refund_memo
                # Unlike in a coin purchase memo, the coin type is implied by the payment request.
                check_address_mac(
                    memo.address, memo.mac, slip44_id, memo.address_n, keychain
                )
                writers.write_uint32_le(self.h_pr, _MEMO_TYPE_REFUND)
                writers.write_bytes_prefixed(self.h_pr, memo.address.encode())
            elif m.coin_purchase_memo is not None:
                memo = m.coin_purchase_memo
                check_address_mac(
                    memo.address, memo.mac, memo.coin_type, memo.address_n, keychain
                )
                writers.write_uint32_le(self.h_pr, _MEMO_TYPE_COIN_PURCHASE)
                writers.write_uint32_le(self.h_pr, memo.coin_type)
                writers.write_bytes_prefixed(self.h_pr, memo.amount.encode())
                writers.write_bytes_prefixed(self.h_pr, memo.address.encode())
            elif m.text_details_memo is not None:
                memo = m.text_details_memo
                writers.write_uint32_le(self.h_pr, _MEMO_TYPE_TEXT_DETAILS)
                writers.write_bytes_prefixed(self.h_pr, memo.title.encode())
                writers.write_bytes_prefixed(self.h_pr, memo.text.encode())
            else:
                DataError("Unrecognized memo type in payment request.")

        writers.write_uint32_le(self.h_pr, slip44_id)

    def verify(self) -> None:
        from trezor.crypto.curve import nist256p1

        if self.expected_amount is not None and self.amount != self.expected_amount:
            raise DataError("Invalid amount in payment request.")

        hash_outputs = self.h_outputs.get_digest()
        writers.write_bytes_fixed(self.h_pr, hash_outputs, 32)

        if not nist256p1.verify(
            self.PUBLIC_KEY, self.signature, self.h_pr.get_digest()
        ):
            raise DataError("Invalid signature in payment request.")

    def add_output(self, amount: int, address: str, change: bool = False) -> None:
        encoded_amount = amount.to_bytes(self.amount_size_bytes, "little")
        # Ensure that the amount fits on amount_size_bytes.
        # Note that Micropython's int.to_bytes() doesn't raise OverflowError!
        assert int.from_bytes(encoded_amount, "little") == amount
        writers.write_bytes_unchecked(self.h_outputs, encoded_amount)
        writers.write_bytes_prefixed(self.h_outputs, address.encode())
        if not change:
            self.amount += amount
