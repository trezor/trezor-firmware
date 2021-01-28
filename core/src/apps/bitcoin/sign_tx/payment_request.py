from micropython import const

from storage import cache
from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.utils import HashWriter

from apps.common.paths import validate_path

from .. import addresses, writers
from ..keychain import get_keychain_for_coin, validate_path_against_script_type
from ..scripts import output_derive_script

if False:
    from typing import List
    from trezor.messages.TxOutput import TxOutput
    from trezor.messages.TxAckPaymentRequest import TxAckPaymentRequest
    from trezor.messages.PaymentRequestMemo import PaymentRequestMemo
    from apps.common.coininfo import CoinInfo

MEMO_TYPE_UTF8 = const(1)
MEMO_TYPE_COIN_FLAG = const(0x8000_0000)
MEMO_TYPE_COIN_MASK = const(0x7FFF_FFFF)


class PaymentRequestVerifier:
    if __debug__:
        # secp256k1 public key of m/0h for "all all ... all" seed.
        PUBLIC_KEY = b"\x03\x0f\xdf^(\x9bZ\xefSb\x90\x95:\xe8\x1c\xe6\x0e\x84\x1f\xf9V\xf3f\xac\x12?\xa6\x9d\xb3\xc7\x9f!\xb0"
    else:
        PUBLIC_KEY = b""

    def __init__(self) -> None:
        self.h_outputs = HashWriter(sha256())
        self.amount = 0

    def verify(self, tx_ack: TxAckPaymentRequest, coin: CoinInfo) -> None:
        hash_outputs = writers.get_tx_hash(self.h_outputs, double=True)
        h_pr = HashWriter(sha256())
        writers.write_bytes_fixed(h_pr, b"Payment request:", 16)
        writers.write_bytes_prefixed(h_pr, tx_ack.recipient_name.encode())
        writers.write_uint32(h_pr, coin.slip44)
        writers.write_bytes_fixed(h_pr, hash_outputs, 32)
        writers.write_bitcoin_varint(h_pr, len(tx_ack.memos))
        for memo in tx_ack.memos:
            writers.write_uint32(h_pr, memo.type)
            writers.write_bytes_prefixed(h_pr, memo.data)

        if tx_ack.nonce:
            nonce = bytes(tx_ack.nonce)
            nonces: List[bytes] = cache.get(cache.APP_COMMON_NONCES)
            try:
                nonces.remove(nonce)
            except (AttributeError, ValueError):
                raise wire.DataError("Invalid nonce in payment request.")
            writers.write_bytes_prefixed(h_pr, nonce)
        else:
            writers.write_bytes_prefixed(h_pr, b"")

        if not secp256k1.verify(self.PUBLIC_KEY, tx_ack.signature, h_pr.get_digest()):
            raise wire.DataError("Invalid signature in payment request.")

    def add_external_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        writers.write_tx_output(self.h_outputs, txo, script_pubkey)
        self.amount += txo.amount

    def add_change_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        writers.write_tx_output(self.h_outputs, txo, script_pubkey)


async def verify_memos(ctx: wire.Context, memos: List[PaymentRequestMemo]) -> None:
    for memo in memos:
        if memo.type & MEMO_TYPE_COIN_FLAG:
            keychain, coin = await get_keychain_for_coin(ctx, memo.coin_name)
            if coin.slip44 != memo.type & MEMO_TYPE_COIN_MASK:
                raise wire.DataError("Coin type mismatch in payment request.")
            with keychain:
                assert memo.script_type is not None
                await validate_path(
                    ctx,
                    keychain,
                    memo.address_n,
                    validate_path_against_script_type(coin, memo),
                )
                node = keychain.derive(memo.address_n)
                address = addresses.get_address(memo.script_type, coin, node)
                if memo.data != output_derive_script(address, coin):
                    raise wire.DataError("Invalid sciptPubKey in payment request.")
