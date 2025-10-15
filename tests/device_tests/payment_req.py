from dataclasses import dataclass
from hashlib import sha256

from ecdsa import NIST256p, SigningKey

from trezorlib import messages
from trezorlib.client import Session

from ..common import compact_size

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
    address_resp: messages.Address | messages.EthereumAddress | None = None


@dataclass
class CoinPurchaseMemo:
    amount: int
    coin_name: str
    slip44: int
    address_n: list[int]
    address_resp: messages.Address | messages.EthereumAddress | None = None


payment_req_signer = SigningKey.from_string(
    b"\x05\x62\x35\xb0\x47\x6f\x05\x7f\x27\x65\x21\x97\x24\xf7\xf1\x80\x7d\x58\x80\x2b\x55\x0e\xd5\xbf\x6f\x73\x05\x0a\xf5\x45\x63\x00",
    curve=NIST256p,
)


def hash_bytes_prefixed(hasher, data) -> None:
    hasher.update(compact_size(len(data)))
    hasher.update(data)


def make_payment_request(
    session: Session,
    recipient_name,
    slip44,
    outputs,
    change_addresses=None,
    memos=None,
    nonce=None,
    amount_size_bytes=8,
) -> messages.PaymentRequest:
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
            msg_memo = messages.TextMemo(text=memo.text)
            msg_memos.append(messages.PaymentRequestMemo(text_memo=msg_memo))
            memo_type = 1
            h_pr.update(memo_type.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.text.encode())
        elif isinstance(memo, RefundMemo):
            msg_memo = messages.RefundMemo(
                address=memo.address_resp.address,
                address_n=memo.address_n,
                mac=memo.address_resp.mac,
            )
            msg_memos.append(messages.PaymentRequestMemo(refund_memo=msg_memo))
            memo_type = 2
            h_pr.update(memo_type.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.address_resp.address.encode())
        elif isinstance(memo, CoinPurchaseMemo):
            msg_memo = messages.CoinPurchaseMemo(
                coin_type=memo.slip44,
                amount=memo.amount,
                address=memo.address_resp.address,
                address_n=memo.address_n,
                mac=memo.address_resp.mac,
            )
            msg_memos.append(messages.PaymentRequestMemo(coin_purchase_memo=msg_memo))

            memo_type = 3
            h_pr.update(memo_type.to_bytes(4, "little"))
            h_pr.update(memo.slip44.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.amount.encode())
            hash_bytes_prefixed(h_pr, memo.address_resp.address.encode())
        elif isinstance(memo, TextDetailsMemo):
            msg_memo = messages.TextDetailsMemo(title=memo.title, text=memo.text)
            msg_memos.append(messages.PaymentRequestMemo(text_details_memo=msg_memo))
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

    return messages.PaymentRequest(
        recipient_name=recipient_name,
        amount=(
            amount.to_bytes(amount_size_bytes, "little") if amount is not None else None
        ),
        memos=msg_memos,
        nonce=nonce,
        signature=payment_req_signer.sign_digest_deterministic(h_pr.digest()),
    )
