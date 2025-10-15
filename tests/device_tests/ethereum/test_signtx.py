# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from __future__ import annotations

from itertools import product

import pytest

from trezorlib import ethereum, exceptions, messages, models
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.debuglink import message_filters
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path, unharden

from ...common import parametrize_using_common_fixtures
from ...definitions import encode_eth_network
from ...input_flows import (
    InputFlowConfirmAllWarnings,
    InputFlowEthereumSignTxDataGoBack,
    InputFlowEthereumSignTxDataScrollDown,
    InputFlowEthereumSignTxDataSkip,
    InputFlowEthereumSignTxGoBackFromSummary,
    InputFlowEthereumSignTxShowFeeInfo,
    InputFlowEthereumSignTxStaking,
)

TO_ADDR = "0x1d1c328764a41bda0492b66baa30c4a339ff85ef"


pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


def make_defs(parameters: dict) -> messages.EthereumDefinitions:
    # With removal of most built-in defs from firmware, we have test vectors
    # that no longer run. Because this is not the place to test the definitions,
    # we generate fake entries so that we can check the signing results.
    # However, we have the option to not generate the fake definitions,
    # in case what we want to test is signing a tx for an unknown chain
    # (which should be, well... not defined)!
    if parameters.get("fake_defs", True):
        address_n = parse_path(parameters["path"])
        slip44 = unharden(address_n[1])
        network = encode_eth_network(chain_id=parameters["chain_id"], slip44=slip44)

        return messages.EthereumDefinitions(encoded_network=network)
    else:
        return messages.EthereumDefinitions()


@parametrize_using_common_fixtures(
    "ethereum/sign_tx.json",
    "ethereum/sign_tx_eip155.json",
    "ethereum/sign_tx_erc20.json",
)
@pytest.mark.parametrize("chunkify", (True, False))
def test_signtx(session: Session, chunkify: bool, parameters: dict, result: dict):
    input_flow = (
        InputFlowConfirmAllWarnings(session).get()
        if not session.debug.legacy_debug
        else None
    )
    _do_test_signtx(session, parameters, result, input_flow, chunkify=chunkify)


def _do_test_signtx(
    session: Session,
    parameters: dict,
    result: dict,
    input_flow=None,
    chunkify: bool = False,
):
    with session.test_ctx as client:
        if input_flow:
            client.watch_layout()
            client.set_input_flow(input_flow)
        sig_v, sig_r, sig_s = ethereum.sign_tx(
            session,
            n=parse_path(parameters["path"]),
            nonce=int(parameters["nonce"], 16),
            gas_price=int(parameters["gas_price"], 16),
            gas_limit=int(parameters["gas_limit"], 16),
            to=parameters["to_address"],
            chain_id=parameters["chain_id"],
            value=int(parameters["value"], 16),
            tx_type=parameters["tx_type"],
            data=bytes.fromhex(parameters["data"]),
            definitions=make_defs(parameters),
            chunkify=chunkify,
            payment_req=parameters.get("payment_req"),
        )

    expected_v = 2 * parameters["chain_id"] + 35
    assert sig_v in (expected_v, expected_v + 1)
    assert sig_r.hex() == result["sig_r"]
    assert sig_s.hex() == result["sig_s"]
    assert sig_v == result["sig_v"]


# Data taken from sign_tx_eip1559.json["tests"][0]
example_input_data = {
    "parameters": {
        "chain_id": 1,
        "path": "m/44'/60'/0'/0/0",
        "nonce": "0x0",
        "gas_price": "0x4a817c800",
        "gas_limit": "0x5208",
        "value": "0x2540be400",
        "to_address": "0x8eA7a3fccC211ED48b763b4164884DDbcF3b0A98",
        "tx_type": None,
        "data": "",
    },
    "result": {
        "sig_v": 38,
        "sig_r": "6a6349bddb5749bb8b96ce2566a035ef87a09dbf89b5c7e3dfdf9ed725912f24",
        "sig_s": "4ae58ccd3bacee07cdc4a3e8540544fd009c4311af7048122da60f2054c07ee4",
    },
}


example_input_data_long_value = {
    "parameters": {
        "chain_id": 1,
        "path": "m/44'/60'/0'/0/0",
        "nonce": "0x0",
        "gas_price": "0x4a817c800",
        "gas_limit": "0x125208",
        "value": "0x59b09a229d59205d2",  # 103.405359019777459666 ETH - a value that will not fit in 8 bytes, but ETH allows 32 bytes
        "to_address": "0x8eA7a3fccC211ED48b763b4164884DDbcF3b0A98",
        "tx_type": None,
        "data": "",
    },
    "result": {
        "sig_v": 37,
        "sig_r": "e398a281bab316c5d0192b8e1f6d7a9f1698f6ba2ada4efd8337d4dd2ac7fca4",
        "sig_s": "5e5caa4a8b51bd5d9b4d7ad4c2c5a62875fbbbf9dc71eb1fb2f76807e5aa23db",
    },
}

example_input_data_too_long_value = {
    "parameters": {
        "chain_id": 1,
        "path": "m/44'/60'/0'/0/0",
        "nonce": "0x0",
        "gas_price": "0x4a817c800",
        "gas_limit": "0x125208",
        "value": "0x10000000000000000000000000000000000000000000000000000000000000000",  # > 32 bytes
        "to_address": "0x8eA7a3fccC211ED48b763b4164884DDbcF3b0A98",
        "tx_type": None,
        "data": "",
    },
    "result": {
        "sig_v": 37,
        "sig_r": "e398a281bab316c5d0192b8e1f6d7a9f1698f6ba2ada4efd8337d4dd2ac7fca4",
        "sig_s": "5e5caa4a8b51bd5d9b4d7ad4c2c5a62875fbbbf9dc71eb1fb2f76807e5aa23db",
    },
}


@pytest.mark.models("core", reason="T1 does not support input flows")
def test_signtx_fee_info(session: Session):
    input_flow = InputFlowEthereumSignTxShowFeeInfo(session).get()
    _do_test_signtx(
        session,
        example_input_data["parameters"],
        example_input_data["result"],
        input_flow,
    )


@pytest.mark.models("core")
def test_signtx_go_back_from_summary(session: Session):
    input_flow = InputFlowEthereumSignTxGoBackFromSummary(session).get()
    _do_test_signtx(
        session,
        example_input_data["parameters"],
        example_input_data["result"],
        input_flow,
    )


@parametrize_using_common_fixtures("ethereum/sign_tx_eip1559.json")
@pytest.mark.parametrize("chunkify", (True, False))
def test_signtx_eip1559(
    session: Session, chunkify: bool, parameters: dict, result: dict
):
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            session,
            n=parse_path(parameters["path"]),
            nonce=int(parameters["nonce"], 16),
            gas_limit=int(parameters["gas_limit"], 16),
            max_gas_fee=int(parameters["max_gas_fee"], 16),
            max_priority_fee=int(parameters["max_priority_fee"], 16),
            to=parameters["to_address"],
            chain_id=parameters["chain_id"],
            value=int(parameters["value"], 16),
            data=bytes.fromhex(parameters["data"]),
            definitions=make_defs(parameters),
            chunkify=chunkify,
        )

    assert sig_r.hex() == result["sig_r"]
    assert sig_s.hex() == result["sig_s"]
    assert sig_v == result["sig_v"]


def test_sanity_checks(session: Session):
    """Is not vectorized because these are internal-only tests that do not
    need to be exposed to the public.
    """
    # contract creation without data should fail.
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx(
            session,
            n=parse_path("m/44h/60h/0h/0/0"),
            nonce=123_456,
            gas_price=20_000,
            gas_limit=20_000,
            to="",
            value=12_345_678_901_234_567_890,
            chain_id=1,
        )

    # gas overflow
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx(
            session,
            n=parse_path("m/44h/60h/0h/0/0"),
            nonce=123_456,
            gas_price=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            to=TO_ADDR,
            value=12_345_678_901_234_567_890,
            chain_id=1,
        )

    # bad chain ID
    with pytest.raises(TrezorFailure, match=r"Chain ID out of bounds"):
        ethereum.sign_tx(
            session,
            n=parse_path("m/44h/60h/0h/0/0"),
            nonce=123_456,
            gas_price=20_000,
            gas_limit=20_000,
            to=TO_ADDR,
            value=12_345_678_901_234_567_890,
            chain_id=0,
        )


def test_data_streaming(session: Session):
    """Only verifying the expected responses, the signatures are
    checked in vectorized function above.
    """
    with session.test_ctx as client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                message_filters.EthereumTxRequest(
                    data_length=1_024,
                    signature_r=None,
                    signature_s=None,
                    signature_v=None,
                ),
                message_filters.EthereumTxRequest(
                    data_length=1_024,
                    signature_r=None,
                    signature_s=None,
                    signature_v=None,
                ),
                message_filters.EthereumTxRequest(
                    data_length=1_024,
                    signature_r=None,
                    signature_s=None,
                    signature_v=None,
                ),
                message_filters.EthereumTxRequest(
                    data_length=3,
                    signature_r=None,
                    signature_s=None,
                    signature_v=None,
                ),
                message_filters.EthereumTxRequest(data_length=None),
            ]
        )

        ethereum.sign_tx(
            session,
            n=parse_path("m/44h/60h/0h/0/0"),
            nonce=0,
            gas_price=20_000,
            gas_limit=20_000,
            to=TO_ADDR,
            value=0,
            data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            chain_id=1,
        )


@pytest.mark.parametrize(
    "access_list,expected_sig",
    [
        pytest.param(
            [
                messages.EthereumAccessList(
                    address="0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000003"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000007"
                        ),
                    ],
                )
            ],
            (
                1,
                "9f8763f3ff8d4d409f6b96bc3f1d84dd504e2c667b162778508478645401f121",
                "51e30b68b9091cf8138c07380c4378c2711779b68b2e5264d141479f13a12f57",
            ),
            id="single_entry",
        ),
        pytest.param(
            [
                messages.EthereumAccessList(
                    address="0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000003"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000007"
                        ),
                    ],
                ),
                messages.EthereumAccessList(
                    address="0xbb9bc244d798123fde783fcc1c72d3bb8c189413",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000006"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000007"
                        ),
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000009"
                        ),
                    ],
                ),
            ],
            (
                1,
                "718a3a30827c979975c846d2f60495310c4959ee3adce2d89e0211785725465c",
                "7d0ea2a28ef5702ca763c1f340427c0020292ffcbb4553dd1c8ea8e2b9126dbc",
            ),
            id="larger_list",
        ),
        pytest.param(
            [
                messages.EthereumAccessList(
                    address=f"0xde0b295669a9fd93d5f28d9ec85e40f4cb697b{i:02x}",
                    storage_keys=[
                        bytes.fromhex(
                            "0000000000000000000000000000000000000000000000000000000000000003"
                        )
                    ]
                    * 12,
                )
                for i in range(12)
            ],
            None,  # Max count test - just verify signatures exist
            id="max_count",
        ),
    ],
)
def test_signtx_eip1559_access_list(
    session: Session,
    access_list,
    expected_sig: tuple[int, str, str] | None,
):
    with session.test_ctx:
        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            session,
            n=parse_path("m/44h/60h/0h/0/100"),
            nonce=0,
            gas_limit=20,
            to="0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
            access_list=access_list,
        )

    if expected_sig is not None:
        assert (sig_v, sig_r.hex(), sig_s.hex()) == expected_sig


def test_sanity_checks_eip1559(session: Session):
    """Is not vectorized because these are internal-only tests that do not
    need to be exposed to the public.
    """
    # contract creation without data should fail.
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx_eip1559(
            session,
            n=parse_path("m/44h/60h/0h/0/100"),
            nonce=0,
            gas_limit=20,
            to="",
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
        )

    # max fee overflow
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx_eip1559(
            session,
            n=parse_path("m/44h/60h/0h/0/100"),
            nonce=0,
            gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            to=TO_ADDR,
            chain_id=1,
            value=10,
            max_gas_fee=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            max_priority_fee=1,
        )

    # priority fee overflow
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx_eip1559(
            session,
            n=parse_path("m/44h/60h/0h/0/100"),
            nonce=0,
            gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            to=TO_ADDR,
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
        )

    # bad chain ID
    with pytest.raises(TrezorFailure, match=r"Chain ID out of bounds"):
        ethereum.sign_tx_eip1559(
            session,
            n=parse_path("m/44h/60h/0h/0/100"),
            nonce=0,
            gas_limit=20,
            to=TO_ADDR,
            chain_id=0,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
        )


def input_flow_data_skip(client: Client | Session, cancel: bool = False):
    return InputFlowEthereumSignTxDataSkip(client, cancel).get()


def input_flow_data_scroll_down(client: Client | Session, cancel: bool = False):
    return InputFlowEthereumSignTxDataScrollDown(client, cancel).get()


def input_flow_data_go_back(client: Client | Session, cancel: bool = False):
    return InputFlowEthereumSignTxDataGoBack(client, cancel).get()


HEXDATA = "0123456789abcd000023456789abcd010003456789abcd020000456789abcd030000056789abcd040000006789abcd050000000789abcd060000000089abcd070000000009abcd080000000000abcd090000000001abcd0a0000000011abcd0b0000000111abcd0c0000001111abcd0d0000011111abcd0e0000111111abcd0f0000000002abcd100000000022abcd110000000222abcd120000002222abcd130000022222abcd140000222222abcd15"


@pytest.mark.parametrize(
    "flow", (input_flow_data_skip, input_flow_data_scroll_down, input_flow_data_go_back)
)
@pytest.mark.models("core")
def test_signtx_data_pagination(session: Session, flow):
    def _sign_tx_call():
        ethereum.sign_tx(
            session,
            n=parse_path("m/44h/60h/0h/0/0"),
            nonce=0x0,
            gas_price=0x14,
            gas_limit=0x14,
            to="0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
            chain_id=1,
            value=0xA,
            tx_type=None,
            data=bytes.fromhex(HEXDATA),
        )

    with session.test_ctx as client:
        client.watch_layout()
        client.set_input_flow(flow(client))
        _sign_tx_call()

    if flow is not input_flow_data_scroll_down:
        with client, pytest.raises(exceptions.Cancelled):
            client.watch_layout()
            client.set_input_flow(flow(session, cancel=True))
            _sign_tx_call()


@parametrize_using_common_fixtures("ethereum/sign_tx_staking.json")
@pytest.mark.parametrize("chunkify", (True, False))
def test_signtx_staking(
    session: Session, chunkify: bool, parameters: dict, result: dict
):
    input_flow = None
    if session.model is not models.T1B1:
        input_flow = InputFlowEthereumSignTxStaking(session).get()
    _do_test_signtx(
        session, parameters, result, input_flow=input_flow, chunkify=chunkify
    )


@parametrize_using_common_fixtures("ethereum/sign_tx_staking_data_error.json")
def test_signtx_staking_bad_inputs(session: Session, parameters: dict, result: dict):
    # result not needed
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx(
            session,
            n=parse_path(parameters["path"]),
            nonce=int(parameters["nonce"], 16),
            gas_price=int(parameters["gas_price"], 16),
            gas_limit=int(parameters["gas_limit"], 16),
            to=parameters["to_address"],
            value=int(parameters["value"], 16),
            data=bytes.fromhex(parameters["data"]),
            chain_id=parameters["chain_id"],
            tx_type=parameters["tx_type"],
            definitions=None,
            chunkify=False,
        )


@parametrize_using_common_fixtures("ethereum/sign_tx_staking_eip1559.json")
def test_signtx_staking_eip1559(session: Session, parameters: dict, result: dict):
    with session.test_ctx:
        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            session,
            n=parse_path(parameters["path"]),
            nonce=int(parameters["nonce"], 16),
            max_gas_fee=int(parameters["max_gas_fee"], 16),
            max_priority_fee=int(parameters["max_priority_fee"], 16),
            gas_limit=int(parameters["gas_limit"], 16),
            to=parameters["to_address"],
            value=int(parameters["value"], 16),
            data=bytes.fromhex(parameters["data"]),
            chain_id=parameters["chain_id"],
            definitions=None,
            chunkify=True,
        )
    assert sig_r.hex() == result["sig_r"]
    assert sig_s.hex() == result["sig_s"]
    assert sig_v == result["sig_v"]


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "has_refund,has_text,has_multiple_purchases",
    list(product([True, False], repeat=3)),
)
def test_signtx_payment_req(
    session: Session, has_refund: bool, has_text: bool, has_multiple_purchases: bool
):
    from trezorlib import btc, ethereum, misc

    from ..payment_req import (
        CoinPurchaseMemo,
        RefundMemo,
        TextDetailsMemo,
        TextMemo,
        make_payment_request,
    )

    purchase_memo_1 = CoinPurchaseMemo(
        amount="0.0636 BTC",
        coin_name="Bitcoin",
        slip44=0,
        address_n=parse_path("m/44h/0h/0h/0/0"),
    )
    purchase_memo_1.address_resp = btc.get_authenticated_address(
        session, purchase_memo_1.coin_name, purchase_memo_1.address_n
    )

    memos = [purchase_memo_1]

    if has_refund:
        refund_memo = RefundMemo(address_n=parse_path("m/44h/60h/0h/0/0"))
        refund_memo.address_resp = ethereum.get_authenticated_address(
            session, refund_memo.address_n
        )
        memos.append(refund_memo)

    if has_text:
        memos.append(TextMemo(text="We will confirm some text"))
        memos.append(TextDetailsMemo(title="Please confirm", text="Here is the text"))

    if has_multiple_purchases:
        purchase_memo_2 = CoinPurchaseMemo(
            amount="0.0123 BTC",
            coin_name="Bitcoin",
            slip44=0,
            address_n=parse_path("m/44h/0h/0h/0/0"),
        )
        purchase_memo_2.address_resp = btc.get_authenticated_address(
            session, purchase_memo_2.coin_name, purchase_memo_2.address_n
        )

        memos.append(purchase_memo_2)

    nonce = misc.get_nonce(session)

    params = dict(example_input_data["parameters"])
    params["payment_req"] = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=60,
        outputs=[(int(params["value"], 16), params["to_address"])],
        memos=memos,
        nonce=nonce,
        amount_size_bytes=32,
    )

    _do_test_signtx(
        session,
        params,
        example_input_data["result"],
    )


@pytest.mark.models("core")
def test_signtx_payment_req_long_value(
    session: Session,
):
    from trezorlib import btc, misc

    from ..payment_req import CoinPurchaseMemo, make_payment_request

    purchase_memo = CoinPurchaseMemo(
        amount="0.0123456789123456789 BTC",
        coin_name="Bitcoin",
        slip44=0,
        address_n=parse_path("m/44h/0h/0h/0/0"),
    )
    purchase_memo.address_resp = btc.get_authenticated_address(
        session, purchase_memo.coin_name, purchase_memo.address_n
    )

    memos = [purchase_memo]

    nonce = misc.get_nonce(session)

    params = dict(example_input_data_long_value["parameters"])
    params["payment_req"] = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=60,
        outputs=[(int(params["value"], 16), params["to_address"])],
        memos=memos,
        nonce=nonce,
        amount_size_bytes=32,
    )

    _do_test_signtx(
        session,
        params,
        example_input_data_long_value["result"],
    )

    params = dict(example_input_data_too_long_value["parameters"])
    params["payment_req"] = make_payment_request(
        session,
        recipient_name="trezor.io",
        slip44=60,
        outputs=[(int(params["value"], 16), params["to_address"])],
        memos=memos,
        nonce=nonce,
        amount_size_bytes=64,
    )

    with pytest.raises(exceptions.TrezorFailure) as e:
        _do_test_signtx(
            session,
            params,
            example_input_data_long_value["result"],
        )
    assert str(e.value.message) == "amount must be exactly 32 bytes"
