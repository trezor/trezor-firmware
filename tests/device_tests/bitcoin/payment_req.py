from collections import namedtuple
from hashlib import sha256

from ecdsa import ECDH, SECP256k1, SigningKey

from trezorlib import btc, messages

from ...common import compact_size

SLIP44 = 1  # Testnet

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
    hasher.update(compact_size(len(data)))
    hasher.update(data)


def make_payment_request(
    client, recipient_name, outputs, change_addresses=None, memos=None, nonce=None
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

    h_pr.update(SLIP44.to_bytes(4, "little"))

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


def make_coinjoin_request(
    coordinator_name,
    inputs,
    input_script_pubkeys,
    outputs,
    output_script_pubkeys,
    no_fee_indices,
    fee_rate=500_000,  # 0.5 %
    no_fee_threshold=1_000_000,
    min_registrable_amount=5_000,
):
    # Reuse the signing key as the masking key to ensure deterministic behavior.
    # Note that in production the masking key should be generated randomly.
    ecdh = ECDH(curve=SECP256k1)
    ecdh.load_private_key(payment_req_signer)
    mask_public_key = ecdh.get_public_key().to_string("compressed")

    # Process inputs.
    h_prevouts = sha256()
    coinjoin_flags = bytearray()
    for i, (txi, script_pubkey) in enumerate(zip(inputs, input_script_pubkeys)):
        # Add input to prevouts hash.
        h_prevouts.update(bytes(reversed(txi.prev_hash)))
        h_prevouts.update(txi.prev_index.to_bytes(4, "little"))

        # Set signable flag in coinjoin_flags.
        if len(script_pubkey) == 34 and script_pubkey.startswith(b"\x51\x20"):
            ecdh.load_received_public_key_bytes(b"\x02" + script_pubkey[2:])
            shared_secret = ecdh.generate_sharedsecret_bytes()
            h_mask = sha256(shared_secret)
            h_mask.update(bytes(reversed(txi.prev_hash)))
            h_mask.update(txi.prev_index.to_bytes(4, "little"))
            mask = h_mask.digest()[0] & 1
            signable = bool(txi.address_n)
            txi.coinjoin_flags = signable ^ mask
        else:
            txi.coinjoin_flags = 0

        # Set no_fee flag in coinjoin_flags.
        txi.coinjoin_flags |= (i in no_fee_indices) << 1

        coinjoin_flags.append(txi.coinjoin_flags)

    # Process outputs.
    h_outputs = sha256()
    for txo, script_pubkey in zip(outputs, output_script_pubkeys):
        h_outputs.update(txo.amount.to_bytes(8, "little"))
        hash_bytes_prefixed(h_outputs, script_pubkey)

    # Hash the CoinJoin request.
    h_request = sha256(b"CJR1")
    hash_bytes_prefixed(h_request, coordinator_name.encode())
    h_request.update(SLIP44.to_bytes(4, "little"))
    h_request.update(fee_rate.to_bytes(4, "little"))
    h_request.update(no_fee_threshold.to_bytes(8, "little"))
    h_request.update(min_registrable_amount.to_bytes(8, "little"))
    h_request.update(mask_public_key)
    hash_bytes_prefixed(h_request, coinjoin_flags)
    h_request.update(h_prevouts.digest())
    h_request.update(h_outputs.digest())

    return messages.CoinJoinRequest(
        fee_rate=fee_rate,
        no_fee_threshold=no_fee_threshold,
        min_registrable_amount=min_registrable_amount,
        mask_public_key=mask_public_key,
        signature=payment_req_signer.sign_digest_deterministic(h_request.digest()),
    )
