from dataclasses import dataclass
from hashlib import sha256

from ecdsa import SECP256k1, SigningKey

from trezorlib import messages

from ..common import compact_size


@dataclass
class TextMemo:
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
    b"?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj",
    curve=SECP256k1,
)


def hash_bytes_prefixed(hasher, data):
    hasher.update(compact_size(len(data)))
    hasher.update(data)


def make_payment_request(
    client,
    recipient_name,
    slip44,
    outputs,
    change_addresses=None,
    memos=None,
    nonce=None,
):
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
        else:
            raise ValueError

    h_pr.update(slip44.to_bytes(4, "little"))

    change_address = iter(change_addresses or [])
    h_outputs = sha256()
    for amount, address in outputs:
        h_outputs.update(amount.to_bytes(8, "little"))
        if not address:
            address = next(change_address)
        h_outputs.update(len(address).to_bytes(1, "little"))
        h_outputs.update(address.encode())

    h_pr.update(h_outputs.digest())

    return messages.PaymentRequest(
        recipient_name=recipient_name,
        amount=sum(amount for amount, address in outputs if address),
        memos=msg_memos,
        nonce=nonce,
        signature=payment_req_signer.sign_digest_deterministic(h_pr.digest()),
    )
