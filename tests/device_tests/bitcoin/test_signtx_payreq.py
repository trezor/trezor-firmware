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

from collections import namedtuple

import pytest

from trezorlib import btc, messages, misc
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...input_flows import InputFlowPaymentRequestDetails
from .payment_req import CoinPurchaseMemo, RefundMemo, TextMemo, make_payment_request
from .signtx import forge_prevtx

# address at seed "all all all..." path m/84h/1h/0h/0/0
INPUT_ADDRESS = "tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9"
PREV_HASH, PREV_TX = forge_prevtx([(INPUT_ADDRESS, 12_300_000)], network="testnet")
PREV_TXES = {PREV_HASH: PREV_TX}


pytestmark = [pytest.mark.models("core"), pytest.mark.experimental]


def case(id, *args, altcoin: bool = False, models: str | None = None):
    marks = []
    if altcoin:
        marks.append(pytest.mark.altcoin)
    if models:
        marks.append(pytest.mark.models(models))
    return pytest.param(*args, id=id, marks=marks)


inputs = [
    messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=12_300_000,
        prev_hash=PREV_HASH,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
]

outputs = [
    messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=5_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    ),
    messages.TxOutputType(
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=2_000_000,
    ),
    messages.TxOutputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=12_300_000 - 5_000_000 - 2_000_000 - 11_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    ),
]

memos1 = [
    CoinPurchaseMemo(
        amount="15.9636 DASH",
        coin_name="Dash",
        slip44=5,
        address_n=parse_path("m/44h/5h/0h/1/0"),
    ),
]

memos2 = [
    CoinPurchaseMemo(
        amount="3.1896 DASH",
        coin_name="Dash",
        slip44=5,
        address_n=parse_path("m/44h/5h/0h/1/0"),
    ),
    CoinPurchaseMemo(
        amount="831.570802 GRS",
        coin_name="Groestlcoin",
        slip44=17,
        address_n=parse_path("m/44h/17h/0h/0/3"),
    ),
]

memos3 = [TextMemo("Invoice #87654321."), RefundMemo(parse_path("m/44h/1h/0h/0/1"))]

PaymentRequestParams = namedtuple(
    "PaymentRequestParams", ["txo_indices", "memos", "get_nonce"]
)

SERIALIZED_TX = "01000000000101e29305e85821ea86f2bca1fcfe45e7cb0c8de87b612479ee641e0d3d12a723b20000000000ffffffff03404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c98780841e0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f528b4500000000000160014b31dc2a236505a6cb9201fa0411ca38a254a7bf10247304402203ca28fc86a8947ccd11af2d80febfb592d3a29abcb0a8e0fc4924615a1307d89022051c1b41e0db900d90883c030da14f26a34b2bef6d2b289c5aac3097f3501005f012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000"


@pytest.mark.parametrize(
    "payment_request_params",
    (
        case(
            "out0",
            (PaymentRequestParams([0], memos1, get_nonce=True),),
            altcoin=True,
            models="t2t1",
        ),
        case(
            "out1",
            (PaymentRequestParams([1], memos2, get_nonce=True),),
            altcoin=True,
            models="t2t1",
        ),
        case("out2", (PaymentRequestParams([2], [], get_nonce=True),)),
        case(
            "out0+out1",
            (
                PaymentRequestParams([0], [], get_nonce=False),
                PaymentRequestParams([1], [], get_nonce=True),
            ),
        ),
        case(
            "out01",
            (PaymentRequestParams([0, 1], memos3, get_nonce=True),),
        ),
        case("out012", (PaymentRequestParams([0, 1, 2], [], get_nonce=True),)),
        case("out12", (PaymentRequestParams([1, 2], [], get_nonce=True),)),
    ),
)
def test_payment_request(client: Client, payment_request_params):
    for txo in outputs:
        txo.payment_req_index = None

    payment_reqs = []
    for i, params in enumerate(payment_request_params):
        request_outputs = []
        for txo_index in params.txo_indices:
            outputs[txo_index].payment_req_index = i
            request_outputs.append(outputs[txo_index])
        nonce = misc.get_nonce(client) if params.get_nonce else None
        payment_reqs.append(
            make_payment_request(
                client,
                recipient_name="trezor.io",
                outputs=request_outputs,
                change_addresses=["tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9"],
                memos=params.memos,
                nonce=nonce,
            )
        )

    _, serialized_tx = btc.sign_tx(
        client,
        "Testnet",
        inputs,
        outputs,
        prev_txes=PREV_TXES,
        payment_reqs=payment_reqs,
    )

    assert serialized_tx.hex() == SERIALIZED_TX

    # Ensure that the nonce has been invalidated.
    with pytest.raises(TrezorFailure, match="Invalid nonce in payment request"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=payment_reqs,
        )


@pytest.mark.models(skip="safe3")
def test_payment_request_details(client: Client):
    # Test that payment request details are shown when requested.
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    nonce = misc.get_nonce(client)
    payment_reqs = [
        make_payment_request(
            client,
            recipient_name="trezor.io",
            outputs=outputs[:2],
            memos=[TextMemo("Invoice #87654321.")],
            nonce=nonce,
        )
    ]

    with client:
        IF = InputFlowPaymentRequestDetails(client, outputs)
        client.set_input_flow(IF.get())

        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=payment_reqs,
        )

    assert serialized_tx.hex() == SERIALIZED_TX


def test_payment_req_wrong_amount(client: Client):
    # Test wrong total amount in payment request.
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        client,
        recipient_name="trezor.io",
        outputs=outputs[:2],
        nonce=misc.get_nonce(client),
    )

    # Decrease the total amount of the payment request.
    payment_req.amount -= 1

    with pytest.raises(TrezorFailure, match="Invalid amount in payment request"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )


def test_payment_req_wrong_mac_refund(client: Client):
    # Test wrong MAC in payment request memo.
    memo = RefundMemo(parse_path("m/44h/1h/0h/1/0"))
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        client,
        recipient_name="trezor.io",
        outputs=outputs[:2],
        memos=[memo],
        nonce=misc.get_nonce(client),
    )

    # Corrupt the MAC value.
    mac = bytearray(payment_req.memos[0].refund_memo.mac)
    mac[0] ^= 1
    payment_req.memos[0].refund_memo.mac = mac

    with pytest.raises(TrezorFailure, match="Invalid address MAC"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )


@pytest.mark.altcoin
@pytest.mark.models("t2t1", reason="Dash not supported on Safe family")
def test_payment_req_wrong_mac_purchase(client: Client):
    # Test wrong MAC in payment request memo.
    memo = CoinPurchaseMemo(
        amount="22.34904 DASH",
        coin_name="Dash",
        slip44=5,
        address_n=parse_path("m/44h/5h/0h/1/0"),
    )
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        client,
        recipient_name="trezor.io",
        outputs=outputs[:2],
        memos=[memo],
        nonce=misc.get_nonce(client),
    )

    # Corrupt the MAC value.
    mac = bytearray(payment_req.memos[0].coin_purchase_memo.mac)
    mac[0] ^= 1
    payment_req.memos[0].coin_purchase_memo.mac = mac

    with pytest.raises(TrezorFailure, match="Invalid address MAC"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )


def test_payment_req_wrong_output(client: Client):
    # Test wrong output in payment request.
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        client,
        recipient_name="trezor.io",
        outputs=outputs[:2],
        nonce=misc.get_nonce(client),
    )

    # Use a different address in the second output.
    fake_outputs = [
        outputs[0],
        messages.TxOutputType(
            address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
            script_type=outputs[1].script_type,
            amount=outputs[1].amount,
            payment_req_index=outputs[1].payment_req_index,
        ),
        outputs[2],
    ]

    with pytest.raises(TrezorFailure, match="Invalid signature in payment request"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            fake_outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )
