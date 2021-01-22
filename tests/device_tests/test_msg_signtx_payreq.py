# This file is part of the Trezor project.
#
# Copyright (C) 2020 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from hashlib import sha256

import pytest
from ecdsa import SECP256k1, SigningKey

from trezorlib import btc, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..tx_cache import TxCache

B = messages.ButtonRequestType
TX_API = TxCache("Testnet")

TXHASH_091446 = bytes.fromhex(
    "09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a"
)

payment_req_signer = SigningKey.from_string(
    b"?S\ti\x8b\xc5o{,\xab\x03\x194\xea\xa8[_:\xeb\xdf\xce\xef\xe50\xf17D\x98`\xb9dj",
    curve=SECP256k1,
)


def make_payment_request(outputs, hash_outputs, memos=[], nonce=None):
    recipient_name = "trezor.io"
    slip44 = 1  # Testnet

    h_pr = sha256(b"Payment request:")
    h_pr.update(bytes([len(recipient_name)]))
    h_pr.update(recipient_name.encode())
    h_pr.update(slip44.to_bytes(4, "little"))
    h_pr.update(hash_outputs)
    h_pr.update(bytes([len(memos)]))
    for memo in memos:
        h_pr.update(memo.type.to_bytes(4, "little"))
        h_pr.update(bytes([len(memo.data)]))
        h_pr.update(memo.data)

    if nonce:
        h_pr.update(bytes([len(nonce)]))
        h_pr.update(nonce)
    else:
        h_pr.update(b"\0")

    return messages.TxAckPaymentRequest(
        recipient_name=recipient_name,
        memos=memos,
        nonce=nonce,
        signature=payment_req_signer.sign_digest_deterministic(h_pr.digest()),
    )


def case(id, *args, altcoin=False):
    if altcoin:
        marks = pytest.mark.altcoin
    else:
        marks = ()
    return pytest.param(*args, id=id, marks=marks)


inputs = [
    messages.TxInput(
        address_n=parse_path("84'/1'/0'/0/0"),
        amount=12300000,
        prev_hash=TXHASH_091446,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
]

outputs = [
    messages.TxOutput(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=5000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        payment_request=0,
    ),
    messages.TxOutput(
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=2000000,
    ),
    messages.TxOutput(
        address_n=parse_path("84h/1h/0h/0/0"),
        amount=12300000 - 5000000 - 2000000 - 11000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    ),
]

memos1 = [
    messages.Memo(type=1, data=b"Buying 15.9636 DASH."),
    messages.Memo(
        type=0x80000005,
        data=bytes.fromhex("76a914fd61dd017dad1f505c0511142cc9ac51ef3a5beb88ac"),
        address_n=parse_path("44'/5'/0'/1/0"),
        coin_name="Dash",
        script_type=messages.InputScriptType.SPENDADDRESS,
    ),
]

memos2 = [
    messages.Memo(type=1, data=b"Buying 3.1896 DASH and 831.57080247 GRS."),
    messages.Memo(
        type=0x80000005,
        data=bytes.fromhex("76a914fd61dd017dad1f505c0511142cc9ac51ef3a5beb88ac"),
        address_n=parse_path("44'/5'/0'/1/0"),
        coin_name="Dash",
        script_type=messages.InputScriptType.SPENDADDRESS,
    ),
    messages.Memo(
        type=0x80000011,
        data=bytes.fromhex("76a914fe40329c95c5598ac60752a5310b320cb52d18e688ac"),
        address_n=parse_path("44'/17'/0'/0/3"),
        coin_name="Groestlcoin",
        script_type=messages.InputScriptType.SPENDADDRESS,
    ),
]


@pytest.mark.skip_t1
@pytest.mark.parametrize(
    "payment_request_params",
    (
        case(
            "out0",
            (
                (
                    [0],
                    "30181c1811618206cb6656ae4fa77e9e95459e85be295a63ea6d034bda39d507",
                    memos1,
                ),
            ),
            altcoin=True,
        ),
        case(
            "out1",
            (
                (
                    [1],
                    "ab1f485f678a4176b5d77f5f6316321cb90d34e53c4503a5d7931211512e4e7d",
                    memos2,
                ),
            ),
            altcoin=True,
        ),
        case(
            "out2",
            (
                (
                    [2],
                    "b5b957549c9756b4b9a4521f49db96b77bac9fba6e0d4b47f875374beadb1276",
                    [],
                ),
            ),
        ),
        case(
            "out0+out1",
            (
                (
                    [0],
                    "30181c1811618206cb6656ae4fa77e9e95459e85be295a63ea6d034bda39d507",
                    [],
                ),
                (
                    [1],
                    "ab1f485f678a4176b5d77f5f6316321cb90d34e53c4503a5d7931211512e4e7d",
                    [],
                ),
            ),
        ),
        case(
            "out01",
            (
                (
                    [0, 1],
                    "4615b15d83d31d8250c5c078896b4186a02b6cd201fe211e2adf9793452f290d",
                    [],
                ),
            ),
        ),
        case(
            "out012",
            (
                (
                    [0, 1, 2],
                    "7e53bc48fb6cf8e8b4ea8416c523cb6a6a35e24effac335a1d5384a1f0b63df0",
                    [],
                ),
            ),
        ),
        case(
            "out02+out1",
            (
                (
                    [0, 2],
                    "31e0436be0ad5fe5a1b81f0f8278f57d401eedea60cd48df49281c99eb415878",
                    [],
                ),
                (
                    [1],
                    "ab1f485f678a4176b5d77f5f6316321cb90d34e53c4503a5d7931211512e4e7d",
                    [],
                ),
            ),
        ),
        case(
            "out12",
            (
                (
                    [1, 2],
                    "75d0a1389303f3334e838e0d8ed046741a1ae6bfdd523835331f61fa8247ad53",
                    [],
                ),
            ),
        ),
    ),
)
def test_payment_request(client, payment_request_params):
    for txo in outputs:
        txo.payment_request = None

    payment_reqs = []
    for i, (txo_indices, hash_outputs, memos) in enumerate(payment_request_params):
        request_outputs = []
        for txo_index in txo_indices:
            outputs[txo_index].payment_request = i
            request_outputs.append(outputs[txo_index])
        payment_reqs.append(
            make_payment_request(
                outputs=request_outputs,
                hash_outputs=bytes.fromhex(hash_outputs),
                memos=memos,
                nonce=btc.get_nonce(client),
            )
        )

    _, serialized_tx = btc.sign_tx(
        client,
        "Testnet",
        inputs,
        outputs,
        prev_txes=TX_API,
        payment_reqs=payment_reqs,
    )

    assert (
        serialized_tx.hex()
        == "010000000001018a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff03404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c98780841e0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f528b4500000000000160014b31dc2a236505a6cb9201fa0411ca38a254a7bf10247304402204adea8ae600878c5912310f546d600359f6cde8087ebd23f20f8acc7ecb2ede70220603334476c8fb478d8c539f027f9bff5f126e4438df757f9b4ba528adcb56c48012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000"
    )

    # Ensure that the nonce has been invalidated.
    with pytest.raises(TrezorFailure, match="Invalid nonce in payment request"):
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_API,
            payment_reqs=payment_reqs,
        )
