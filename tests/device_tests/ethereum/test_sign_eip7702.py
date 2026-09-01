# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import pytest

from trezorlib import device, ethereum
from trezorlib._rlp import encode
from trezorlib.debuglink import DebugSession as Session
from trezorlib.ethereum import decode_hex
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import Capability, EthereumAuth7702, PaymentRequest
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from .test_signtx import make_defs

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ethereum,
    pytest.mark.capabilities(Capability.Ethereum_EIP7702),
]


# Test vectors validated with Foundry
# cast wallet sign-auth $ADDRESS --mnemonic $MNEMONIC --mnemonic-derivation-path "m/44'/60'/0'/0/0" --nonce $NONCE --chain $CHAINID
# To evaluate signature parts: cast from-rlp <result_from_above>
# format: [chain_id, address, nonce, v, r, s]


@parametrize_using_common_fixtures("ethereum/sign_auth_eip7702.json")
def test_sign_eip7702(session: Session, parameters: dict, result: dict):
    defs = make_defs(parameters)

    addr = ethereum.get_address(
        session,
        n=parse_path(parameters["path"]),
    )

    def _sign() -> ethereum.SignTxResult:
        return ethereum.sign_tx_eip1559(
            session,
            n=parse_path(parameters["path"]),
            chain_id=parameters["chain_id"],
            auth7702=EthereumAuth7702(delegate=parameters["delegate"]),
            nonce=parameters["tuple_nonce"] - 1,  # compute tx nonce
            definitions=defs,
            to=addr,
            value=0,
            max_priority_fee=0,
            max_gas_fee=0,
            gas_limit=0,
        )

    with pytest.raises(TrezorFailure, match="Experimental features are disabled"):
        _sign()

    device.apply_settings(session, experimental_features=True)

    res = _sign()
    [auth7702_tuple] = res.auth7702_list
    chain_id, delegate, nonce, y_parity, r, s = auth7702_tuple
    assert int.from_bytes(chain_id, "big") == parameters["chain_id"]
    assert delegate == decode_hex(parameters["delegate"])
    assert int.from_bytes(nonce, "big") == parameters["tuple_nonce"]
    assert int.from_bytes(y_parity, "big") == result["sig_v"]
    assert r.hex() == result["sig_r"]
    assert s.hex() == result["sig_s"]


@parametrize_using_common_fixtures("ethereum/sign_auth_eip7702_errors.json")
def test_sign_eip7702_errors(session: Session, parameters, result):
    device.apply_settings(session, experimental_features=True)

    assert result["error"]  # make sure it's not an empty string
    with pytest.raises(TrezorFailure, match=result["error"]):
        payment_req = None
        if parameters.get("payment_req"):
            # Fake payment request - not supported by EIP-7702 transactions
            payment_req = PaymentRequest(
                recipient_name="Fake name", signature=b"FAKE SIG"
            )

        ethereum.sign_tx_eip1559(
            session,
            n=parse_path(parameters["path"]),
            chain_id=parameters["chain_id"],
            auth7702=EthereumAuth7702(delegate=parameters["delegate"]),
            nonce=parameters["tuple_nonce"] - 1,  # compute tx nonce
            to=parameters["to_address"],
            value=parameters["value"],
            data=bytes.fromhex(parameters["data"]),
            max_priority_fee=0,
            max_gas_fee=0,
            gas_limit=0,
            payment_req=payment_req,
        )


@parametrize_using_common_fixtures("ethereum/sign_tx_eip7702_mainnet.json")
def test_sign_eip7702_mainnet(session: Session, parameters: dict, result: dict):
    device.apply_settings(session, experimental_features=True)

    res = ethereum.sign_tx_eip1559(
        session,
        n=parse_path(parameters["path"]),
        chain_id=parameters["chain_id"],
        nonce=parameters["nonce"],
        to=parameters["to_address"],
        value=parameters["value"],
        max_priority_fee=parameters["max_priority_fee"],
        max_gas_fee=parameters["max_gas_fee"],
        gas_limit=parameters["gas_limit"],
        auth7702=EthereumAuth7702(delegate=parameters["delegate"]),
    )
    auth7702_list = [
        [i.hex() for i in auth7702_tuple] for auth7702_tuple in res.auth7702_list
    ]
    assert auth7702_list == result["auth7702_list_hex"]
    items = (
        parameters["chain_id"],
        parameters["nonce"],
        parameters["max_priority_fee"],
        parameters["max_gas_fee"],
        parameters["gas_limit"],
        decode_hex(parameters["to_address"]),
        parameters["value"],
        b"",  # data
        [],  # access list
        res.auth7702_list,
        res.v,
        res.r,
        res.s,
    )
    serialized = b"\x04" + encode(items)
    assert serialized.hex() == result["tx_bytes_hex"]
