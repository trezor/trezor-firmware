from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError

from .. import writers

if TYPE_CHECKING:
    from trezor.messages import TxAckPaymentRequest, TxOutput

    from apps.common import coininfo
    from apps.common.keychain import Keychain

_MEMO_TYPE_TEXT = const(1)
_MEMO_TYPE_REFUND = const(2)
_MEMO_TYPE_COIN_PURCHASE = const(3)


class PaymentRequestVerifier:
    if __debug__:
        # secp256k1 public key of m/0h for "all all ... all" seed.
        PUBLIC_KEY = b"\x03\x0f\xdf^(\x9bZ\xefSb\x90\x95:\xe8\x1c\xe6\x0e\x84\x1f\xf9V\xf3f\xac\x12?\xa6\x9d\xb3\xc7\x9f!\xb0"
    else:
        PUBLIC_KEY = b""

    def __init__(
        self, msg: TxAckPaymentRequest, coin: coininfo.CoinInfo, keychain: Keychain
    ) -> None:
        from storage import cache
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from apps.common.address_mac import check_address_mac

        from .. import writers  # pylint: disable=import-outside-toplevel

        self.h_outputs = HashWriter(sha256())
        self.amount = 0
        self.expected_amount = msg.amount
        self.signature = msg.signature
        self.h_pr = HashWriter(sha256())

        if msg.nonce:
            nonce = bytes(msg.nonce)
            if cache.get(cache.APP_COMMON_NONCE) != nonce:
                raise DataError("Invalid nonce in payment request.")
            cache.delete(cache.APP_COMMON_NONCE)
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
                writers.write_uint32(self.h_pr, _MEMO_TYPE_TEXT)
                writers.write_bytes_prefixed(self.h_pr, memo.text.encode())
            elif m.refund_memo is not None:
                memo = m.refund_memo
                # Unlike in a coin purchase memo, the coin type is implied by the payment request.
                check_address_mac(memo.address, memo.mac, coin.slip44, keychain)
                writers.write_uint32(self.h_pr, _MEMO_TYPE_REFUND)
                writers.write_bytes_prefixed(self.h_pr, memo.address.encode())
            elif m.coin_purchase_memo is not None:
                memo = m.coin_purchase_memo
                check_address_mac(memo.address, memo.mac, memo.coin_type, keychain)
                writers.write_uint32(self.h_pr, _MEMO_TYPE_COIN_PURCHASE)
                writers.write_uint32(self.h_pr, memo.coin_type)
                writers.write_bytes_prefixed(self.h_pr, memo.amount.encode())
                writers.write_bytes_prefixed(self.h_pr, memo.address.encode())

        writers.write_uint32(self.h_pr, coin.slip44)

    def verify(self) -> None:
        from trezor.crypto.curve import secp256k1

        if self.expected_amount is not None and self.amount != self.expected_amount:
            raise DataError("Invalid amount in payment request.")

        hash_outputs = writers.get_tx_hash(self.h_outputs)
        writers.write_bytes_fixed(self.h_pr, hash_outputs, 32)

        if not secp256k1.verify(
            self.PUBLIC_KEY, self.signature, self.h_pr.get_digest()
        ):
            raise DataError("Invalid signature in payment request.")

    def _add_output(self, txo: TxOutput) -> None:
        # For change outputs txo.address filled in by output_derive_script().
        assert txo.address is not None
        writers.write_uint64(self.h_outputs, txo.amount)
        writers.write_bytes_prefixed(self.h_outputs, txo.address.encode())

    def add_external_output(self, txo: TxOutput) -> None:
        self._add_output(txo)
        self.amount += txo.amount

    def add_change_output(self, txo: TxOutput) -> None:
        self._add_output(txo)
