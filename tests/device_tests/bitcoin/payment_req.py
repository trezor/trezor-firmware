from collections import namedtuple
from hashlib import sha256

from ecdsa import SECP256k1, SigningKey

from trezorlib import btc, messages

TextMemo = namedtuple("TextMemo", "text")
RefundMemo = namedtuple("RefundMemo", "address_n")
CoinPurchaseMemo = namedtuple(
    "CoinPurchaseMemo", "amount, coin_name, slip44, address_n"
)

payment_req_signer = SigningKey.from_string(
    b"?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj",
    curve=SECP256k1,
)


def hash_bytes_prefixed(hasher, data):
    hasher.update(len(data).to_bytes(1, "little"))
    hasher.update(data)


def make_payment_request(
    client, recipient_name, outputs, change_addresses=None, memos=None, nonce=None
):
    slip44 = 1  # Testnet

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
            address_resp = btc.get_authenticated_address(
                client, "Testnet", memo.address_n
            )
            msg_memo = messages.RefundMemo(
                address=address_resp.address, mac=address_resp.mac
            )
            msg_memos.append(messages.PaymentRequestMemo(refund_memo=msg_memo))
            memo_type = 2
            h_pr.update(memo_type.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, address_resp.address.encode())
        elif isinstance(memo, CoinPurchaseMemo):
            address_resp = btc.get_authenticated_address(
                client, memo.coin_name, memo.address_n
            )
            msg_memo = messages.CoinPurchaseMemo(
                coin_type=memo.slip44,
                amount=memo.amount,
                address=address_resp.address,
                mac=address_resp.mac,
            )
            msg_memos.append(messages.PaymentRequestMemo(coin_purchase_memo=msg_memo))

            memo_type = 3
            h_pr.update(memo_type.to_bytes(4, "little"))
            h_pr.update(memo.slip44.to_bytes(4, "little"))
            hash_bytes_prefixed(h_pr, memo.amount.encode())
            hash_bytes_prefixed(h_pr, address_resp.address.encode())
        else:
            raise ValueError

    h_pr.update(slip44.to_bytes(4, "little"))

    change_address = iter(change_addresses or [])
    h_outputs = sha256()
    for txo in outputs:
        h_outputs.update(txo.amount.to_bytes(8, "little"))
        address = txo.address or next(change_address)
        h_outputs.update(len(address).to_bytes(1, "little"))
        h_outputs.update(address.encode())

    h_pr.update(h_outputs.digest())

    return messages.TxAckPaymentRequest(
        recipient_name=recipient_name,
        amount=sum(txo.amount for txo in outputs if txo.address),
        memos=msg_memos,
        nonce=nonce,
        signature=payment_req_signer.sign_digest_deterministic(h_pr.digest()),
    )
