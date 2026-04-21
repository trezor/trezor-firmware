import typing as t
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional, Protocol, Union

from ecdsa import NIST256p, SigningKey

from .generated import messages as ethereum_messages
from trezorlib.client import Session
from trezorlib.testing.common import compact_size


class _HashLike(Protocol):
    """Protocol for hashlib hash objects."""

    def update(self, __data: bytes, /) -> None: ...
    def digest(self) -> bytes: ...


SLIP44_ID_UNDEFINED = 0xFFFF_FFFF


@dataclass
class TextMemo:
    text: str


@dataclass
class TextDetailsMemo:
    title: str
    text: str


@dataclass
class RefundMemo:
    address_n: list[int]
    address_resp: Optional[ethereum_messages.Address] = None


@dataclass
class CoinPurchaseMemo:
    amount: str
    coin_name: str
    slip44: int
    address_n: list[int]
    address_resp: Optional[ethereum_messages.Address] = None


payment_req_signer = SigningKey.from_string(
    b"\x05\x62\x35\xb0\x47\x6f\x05\x7f\x27\x65\x21\x97\x24\xf7\xf1\x80\x7d\x58\x80\x2b\x55\x0e\xd5\xbf\x6f\x73\x05\x0a\xf5\x45\x63\x00",
    curve=NIST256p,
)


def hash_bytes_prefixed(hasher: _HashLike, data: bytes) -> None:
    hasher.update(compact_size(len(data)))
    hasher.update(data)


def make_payment_request(
    session: Session,
    recipient_name: str,
    slip44: Optional[int] = None,
    outputs: Optional[list[tuple[int, Optional[str]]]] = None,
    change_addresses: Optional[list[str]] = None,
    memos: Optional[list[t.Any]] = None,
    nonce: Optional[bytes] = None,
    amount_size_bytes: int = 8,
) -> ethereum_messages.PaymentRequest:
    h_pr = sha256(b"SL\x00\x24")

    if nonce:
        hash_bytes_prefixed(h_pr, nonce)
    else:
        h_pr.update(b"\0")

    hash_bytes_prefixed(h_pr, recipient_name.encode())

    if memos is None:
        memos = []

    h_pr.update(len(memos).to_bytes(1, "little"))
    msg_memos = []
    for memo in memos:
        if isinstance(memo, TextMemo):
            msg_memo = ethereum_messages.TextMemo(text=memo.text)
            msg_memos.append(ethereum_messages.PaymentRequestMemo(text_memo=msg_memo))
            memo_type = 1
            h_pr.update(memo_type.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.text.encode())
        elif isinstance(memo, RefundMemo):
            assert memo.address_resp is not None
            assert isinstance(memo.address_resp.address, str)
            assert isinstance(memo.address_resp.mac, bytes)
            msg_memo = ethereum_messages.RefundMemo(
                address=memo.address_resp.address,
                address_n=memo.address_n,
                mac=memo.address_resp.mac,
            )
            msg_memos.append(ethereum_messages.PaymentRequestMemo(refund_memo=msg_memo))
            memo_type = 2
            h_pr.update(memo_type.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.address_resp.address.encode())
        elif isinstance(memo, CoinPurchaseMemo):
            assert memo.address_resp is not None
            assert isinstance(memo.address_resp.address, str)
            assert isinstance(memo.address_resp.mac, bytes)
            msg_memo = ethereum_messages.CoinPurchaseMemo(
                coin_type=memo.slip44,
                amount=memo.amount,
                address=memo.address_resp.address,
                address_n=memo.address_n,
                mac=memo.address_resp.mac,
            )
            msg_memos.append(
                ethereum_messages.PaymentRequestMemo(coin_purchase_memo=msg_memo)
            )

            memo_type = 3
            h_pr.update(memo_type.to_bytes(4, "little"))
            h_pr.update(memo.slip44.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.amount.encode())
            hash_bytes_prefixed(h_pr, memo.address_resp.address.encode())
        elif isinstance(memo, TextDetailsMemo):
            msg_memo = ethereum_messages.TextDetailsMemo(
                title=memo.title, text=memo.text
            )
            msg_memos.append(
                ethereum_messages.PaymentRequestMemo(text_details_memo=msg_memo)
            )
            memo_type = 4
            h_pr.update(memo_type.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.title.encode())
            hash_bytes_prefixed(h_pr, memo.text.encode())
        else:
            raise ValueError

    h_pr.update(
        (slip44 if slip44 is not None else SLIP44_ID_UNDEFINED).to_bytes(4, "little")
    )

    change_address = iter(change_addresses or [])
    h_outputs = sha256()
    for amount, address in outputs or []:
        h_outputs.update(amount.to_bytes(amount_size_bytes, "little"))
        if not address:
            address = next(change_address)
        h_outputs.update(len(address).to_bytes(1, "little"))
        h_outputs.update(address.encode())

    h_pr.update(h_outputs.digest())

    amount = (
        sum(amount for amount, address in outputs if address)
        if outputs is not None
        else None
    )

    return ethereum_messages.PaymentRequest(
        recipient_name=recipient_name,
        amount=(
            amount.to_bytes(amount_size_bytes, "little") if amount is not None else None
        ),
        memos=msg_memos,
        nonce=nonce,
        signature=payment_req_signer.sign_digest_deterministic(h_pr.digest()),
    )
