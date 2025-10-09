from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError, context

from . import writers

if TYPE_CHECKING:
    from trezor.messages import PaymentRequest

    from apps.common.keychain import Keychain

_MEMO_TYPE_TEXT = const(1)
_MEMO_TYPE_REFUND = const(2)
_MEMO_TYPE_COIN_PURCHASE = const(3)
_MEMO_TYPE_TEXT_DETAILS = const(4)


class PaymentRequestVerifier:
    if __debug__:
        # nist256p1 public key of m/0h for "all all ... all" seed.
        PUBLIC_KEY = b"\x03\xd9\xd9\x3f\x89\xc6\x96\x3b\x94\xbb\xd7\xa5\x11\x88\x28\xe4\x4c\x1c\x39\x59\x15\xac\xe8\x48\x88\x71\x7f\x56\x8c\xb0\x19\x74\xc3"
    else:
        PUBLIC_KEY = b""

    def __init__(self, msg: PaymentRequest, slip44_id: int, keychain: Keychain) -> None:
        from storage.cache_common import APP_COMMON_NONCE
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from apps.common.address_mac import check_address_mac

        from . import writers  # pylint: disable=import-outside-toplevel

        self.h_outputs = HashWriter(sha256())
        self.amount = 0
        self.expected_amount = msg.amount
        self.signature = msg.signature
        self.h_pr = HashWriter(sha256())

        if msg.nonce:
            nonce = bytes(msg.nonce)
            if context.cache_get(APP_COMMON_NONCE) != nonce:
                raise DataError("Invalid nonce in payment request.")
            context.cache_delete(APP_COMMON_NONCE)
        else:
            nonce = b""
            if msg.memos:
                DataError("Missing nonce in payment request.")

        writers.write_bytes_fixed(self.h_pr, b"SL\x00\x24", 4)
        writers.write_bytes_prefixed(self.h_pr, nonce)
        writers.write_bytes_prefixed(self.h_pr, msg.recipient_name.encode())
        writers.write_compact_size(self.h_pr, len(msg.memos))
        for m in msg.memos:
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
        writers.write_uint64_le(self.h_outputs, amount)
        writers.write_bytes_prefixed(self.h_outputs, address.encode())
        if not change:
            self.amount += amount
