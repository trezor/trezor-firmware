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
from itertools import product

import pytest

from trezorlib import btc, ethereum, messages, misc
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..payment_req import (
    CoinPurchaseMemo,
    RefundMemo,
    TextDetailsMemo,
    TextMemo,
    make_payment_request,
)
from .signtx import forge_prevtx

# address at seed "all all all..." path m/84h/1h/0h/0/0
INPUT_ADDRESS = "tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9"
PREV_HASH, PREV_TX = forge_prevtx([(INPUT_ADDRESS, 12_300_000)], network="testnet")
PREV_TXES = {PREV_HASH: PREV_TX}


pytestmark = [pytest.mark.models("core"), pytest.mark.experimental]


@pytest.mark.models(
    "core",
    skip="t2t1",
    reason="T1 does not support payment requests. Payment requests not yet implemented on model T.",
)
@pytest.mark.altcoin
@pytest.mark.parametrize("has_text,has_refund", list(product([True, False], repeat=2)))
def test_signtx_payment_req_swap_with_text_and_refund(
    session: Session, has_text: bool, has_refund: bool
):
    """The most basic use case for payment requests is a swap between two coins with an optional refund address and an optional text..."""
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
            payment_req_index=0,
        )
    ]

    swap_memo = CoinPurchaseMemo(
        amount="0.0636 ETH",
        coin_name="Ethereum",
        slip44=60,
        address_n=parse_path("m/44h/60h/0h/0/0"),
    )
    swap_memo.address_resp = ethereum.get_authenticated_address(
        session, swap_memo.address_n
    )

    memos = [swap_memo]

    if has_text:
        memos.append(
            TextDetailsMemo(
                title="But why ...", text="... would you swap your BTC for ETH?"
            )
        )

    if has_refund:
        refund_memo = RefundMemo(address_n=parse_path("m/44h/1h/0h/1/0"))
        refund_memo.address_resp = btc.get_authenticated_address(
            session, "Testnet", refund_memo.address_n
        )
        memos.append(refund_memo)

    nonce = misc.get_nonce(session)

    payment_req = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=1,
        outputs=[(o.amount, o.address) for o in outputs],
        memos=memos,
        nonce=nonce,
    )

    btc.sign_tx(
        session,
        "Testnet",
        inputs,
        [outputs[0]],
        prev_txes=PREV_TXES,
        payment_reqs=[payment_req],
    )


def case(id, *args, altcoin: bool = False, skip: str | None = None):
    marks = []
    if altcoin:
        marks.append(pytest.mark.altcoin)
    if skip:
        marks.append(pytest.mark.models(skip=skip))
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
        amount="15.9636 DOGE",
        coin_name="Dogecoin",
        slip44=3,
        address_n=parse_path("m/44h/3h/0h/1/0"),
    ),
]

memos2 = [
    CoinPurchaseMemo(
        amount="3.1896 DOGE",
        coin_name="Dogecoin",
        slip44=3,
        address_n=parse_path("m/44h/3h/0h/1/0"),
    ),
    CoinPurchaseMemo(
        amount="831.570802 BCH",
        coin_name="Bcash",
        slip44=145,
        address_n=parse_path("m/44h/145h/0h/0/3"),
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
            skip="t2t1",
        ),
        case(
            "out1",
            (PaymentRequestParams([1], memos2, get_nonce=True),),
            altcoin=True,
            skip="t2t1",
        ),
        case(
            "out2",
            (PaymentRequestParams([2], [], get_nonce=True),),
            skip="t2t1",
        ),
        case(
            "out0+out1",
            (
                PaymentRequestParams([0], [], get_nonce=False),
                PaymentRequestParams([1], [], get_nonce=True),
            ),
            skip="t2t1",
        ),
        case(
            "out01",
            (PaymentRequestParams([0, 1], memos3, get_nonce=True),),
            skip="t2t1",
        ),
        case(
            "out012",
            (PaymentRequestParams([0, 1, 2], [], get_nonce=True),),
            skip="t2t1",
        ),
        case(
            "out12",
            (PaymentRequestParams([1, 2], [], get_nonce=True),),
            skip="t2t1",
        ),
    ),
)
def test_payment_request(session: Session, payment_request_params):
    for txo in outputs:
        txo.payment_req_index = None

    payment_reqs = []
    for i, params in enumerate(payment_request_params):
        request_outputs = []
        for txo_index in params.txo_indices:
            output = outputs[txo_index]
            output.payment_req_index = i
            request_outputs.append((output.amount, output.address))
        nonce = misc.get_nonce(session) if params.get_nonce else None
        for memo in params.memos:
            if isinstance(memo, RefundMemo):
                memo.address_resp = btc.get_authenticated_address(
                    session, "Testnet", memo.address_n
                )
            elif isinstance(memo, CoinPurchaseMemo):
                memo.address_resp = btc.get_authenticated_address(
                    session, memo.coin_name, memo.address_n
                )
        payment_reqs.append(
            make_payment_request(
                session,
                recipient_name="trezor.io",
                slip44=1,
                outputs=request_outputs,
                change_addresses=["tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9"],
                memos=params.memos,
                nonce=nonce,
            )
        )

    _, serialized_tx = btc.sign_tx(
        session,
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
            session,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=payment_reqs,
        )


@pytest.mark.models(skip="t2t1")
def test_payment_req_wrong_amount(session: Session):
    # Test wrong total amount in payment request.
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=1,
        outputs=[(txo.amount, txo.address) for txo in outputs[:2]],
        nonce=misc.get_nonce(session),
    )

    # Decrease the total amount of the payment request.
    payment_req.amount -= 1

    with pytest.raises(TrezorFailure, match="Invalid amount in payment request"):
        btc.sign_tx(
            session,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )


@pytest.mark.models(skip="t2t1")
def test_payment_req_wrong_mac_refund(session: Session):
    # Test wrong MAC in payment request memo.
    memo = RefundMemo(parse_path("m/44h/1h/0h/1/0"))
    memo.address_resp = btc.get_authenticated_address(
        session, "Testnet", memo.address_n
    )
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=1,
        outputs=[(txo.amount, txo.address) for txo in outputs[:2]],
        memos=[memo],
        nonce=misc.get_nonce(session),
    )

    # Corrupt the MAC value.
    mac = bytearray(payment_req.memos[0].refund_memo.mac)
    mac[0] ^= 1
    payment_req.memos[0].refund_memo.mac = mac

    with pytest.raises(TrezorFailure, match="Invalid address MAC"):
        btc.sign_tx(
            session,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )


@pytest.mark.models(skip="t2t1")
@pytest.mark.altcoin
def test_payment_req_wrong_mac_purchase(session: Session):
    # Test wrong MAC in payment request memo.
    memo = CoinPurchaseMemo(
        amount="22.34904 DOGE",
        coin_name="Dogecoin",
        slip44=3,
        address_n=parse_path("m/44h/3h/0h/1/0"),
    )
    memo.address_resp = btc.get_authenticated_address(
        session, memo.coin_name, memo.address_n
    )
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=1,
        outputs=[(txo.amount, txo.address) for txo in outputs[:2]],
        memos=[memo],
        nonce=misc.get_nonce(session),
    )

    # Corrupt the MAC value.
    mac = bytearray(payment_req.memos[0].coin_purchase_memo.mac)
    mac[0] ^= 1
    payment_req.memos[0].coin_purchase_memo.mac = mac

    with pytest.raises(TrezorFailure, match="Invalid address MAC"):
        btc.sign_tx(
            session,
            "Testnet",
            inputs,
            outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )


@pytest.mark.models(skip="t2t1")
def test_payment_req_wrong_output(session: Session):
    # Test wrong output in payment request.
    outputs[0].payment_req_index = 0
    outputs[1].payment_req_index = 0
    outputs[2].payment_req_index = None
    payment_req = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=1,
        outputs=[(txo.amount, txo.address) for txo in outputs[:2]],
        nonce=misc.get_nonce(session),
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
            session,
            "Testnet",
            inputs,
            fake_outputs,
            prev_txes=PREV_TXES,
            payment_reqs=[payment_req],
        )
