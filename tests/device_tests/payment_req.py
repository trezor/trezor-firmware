from collections import namedtuple
from hashlib import sha256

from ecdsa import SECP256k1, SigningKey

from trezorlib import btc, messages

TextMemo = namedtuple("TextMemo", ["text"])
CoinPurchaseMemo = namedtuple(
    "CoinPurchaseMemo", ["amount", "coin_name", "slip44", "address_n"]
)

payment_req_signer = SigningKey.from_string(
    b"?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj",
    curve=SECP256k1,
)


def make_payment_request(
    client, recipient_name, outputs, hash_outputs, memos=[], nonce=None
):
    slip44 = 1  # Testnet

    h_pr = sha256(b"Payment request:")

    if nonce:
        h_pr.update(bytes([len(nonce)]))
        h_pr.update(nonce)
    else:
        h_pr.update(b"\0")

    h_pr.update(bytes([len(recipient_name)]))
    h_pr.update(recipient_name.encode())

    h_pr.update(bytes([len(memos)]))
    msg_memos = []
    for memo in memos:
        if isinstance(memo, CoinPurchaseMemo):
            address_resp = btc.get_authenticated_address(
                client, memo.coin_name, memo.address_n
            )
            msg_memo = messages.PaymentRequestMemo(
                type=messages.MemoType.COIN_PURCHASE,
                data=address_resp.address.encode(),
                amount=memo.amount,
                coin_name=memo.coin_name,
                mac=address_resp.mac,
            )
            h_pr.update(msg_memo.type.to_bytes(4, "little"))
            h_pr.update(bytes([len(msg_memo.data)]))
            h_pr.update(msg_memo.data)
            h_pr.update(memo.amount.to_bytes(8, "little"))
            h_pr.update(memo.slip44.to_bytes(4, "little"))
        else:
            msg_memo = messages.PaymentRequestMemo(
                type=messages.MemoType.UTF8_TEXT,
                data=memo.text.encode(),
            )
            h_pr.update(msg_memo.type.to_bytes(4, "little"))
            h_pr.update(bytes([len(msg_memo.data)]))
            h_pr.update(msg_memo.data)
        msg_memos.append(msg_memo)

    h_pr.update(slip44.to_bytes(4, "little"))
    h_pr.update(hash_outputs)

    return messages.TxAckPaymentRequest(
        recipient_name=recipient_name,
        amount=sum(txo.amount for txo in outputs if txo.address),
        memos=msg_memos,
        nonce=nonce,
        signature=payment_req_signer.sign_digest_deterministic(h_pr.digest()),
    )
