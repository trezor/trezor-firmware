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

import pytest

from trezorlib import ethereum, messages
from trezorlib.debuglink import message_filters
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

TO_ADDR = "0x1d1c328764a41bda0492b66baa30c4a339ff85ef"

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


@parametrize_using_common_fixtures(
    "ethereum/sign_tx.json",
    "ethereum/sign_tx_eip155.json",
)
def test_signtx(client, parameters, result):
    with client:
        sig_v, sig_r, sig_s = ethereum.sign_tx(
            client,
            n=parse_path(parameters["path"]),
            nonce=parameters["nonce"],
            gas_price=parameters["gas_price"],
            gas_limit=parameters["gas_limit"],
            to=parameters["to_address"],
            chain_id=parameters["chain_id"],
            value=parameters["value"],
            tx_type=parameters["tx_type"],
            data=bytes.fromhex(parameters["data"]),
        )

    expected_v = 2 * parameters["chain_id"] + 35
    assert sig_v in (expected_v, expected_v + 1)
    assert sig_r.hex() == result["sig_r"]
    assert sig_s.hex() == result["sig_s"]
    assert sig_v == result["sig_v"]


@parametrize_using_common_fixtures(
    "ethereum/sign_tx_eip1559.json",
)
@pytest.mark.skip_t1
def test_signtx_eip1559(client, parameters, result):
    with client:
        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path(parameters["path"]),
            nonce=parameters["nonce"],
            gas_limit=parameters["gas_limit"],
            max_gas_fee=parameters["max_gas_fee"],
            max_priority_fee=parameters["max_priority_fee"],
            to=parameters["to_address"],
            chain_id=parameters["chain_id"],
            value=parameters["value"],
            data=bytes.fromhex(parameters["data"]),
        )

    assert sig_r.hex() == result["sig_r_hex"]
    assert sig_s.hex() == result["sig_s_hex"]
    assert sig_v == result["sig_v"]


def test_sanity_checks(client):
    """Is not vectorized because these are internal-only tests that do not
    need to be exposed to the public.
    """
    # contract creation without data should fail.
    with pytest.raises(Exception):
        ethereum.sign_tx(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=123456,
            gas_price=20000,
            gas_limit=20000,
            to="",
            value=12345678901234567890,
        )

    # gas overflow
    with pytest.raises(TrezorFailure):
        ethereum.sign_tx(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=123456,
            gas_price=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            to=TO_ADDR,
            value=12345678901234567890,
        )


def test_data_streaming(client):
    """Only verifying the expected responses, the signatures are
    checked in vectorized function above.
    """
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                messages.ButtonRequest(code=messages.ButtonRequestType.SignTx),
                message_filters.EthereumTxRequest(
                    data_length=1024,
                    signature_r=None,
                    signature_s=None,
                    signature_v=None,
                ),
                message_filters.EthereumTxRequest(
                    data_length=1024,
                    signature_r=None,
                    signature_s=None,
                    signature_v=None,
                ),
                message_filters.EthereumTxRequest(
                    data_length=1024,
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
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=0,
            gas_price=20000,
            gas_limit=20000,
            to=TO_ADDR,
            value=0,
            data=b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            chain_id=1,
        )


@pytest.mark.skip_t1
def test_signtx_eip1559_access_list(client):
    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to="0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
            access_list=[
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
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "9f8763f3ff8d4d409f6b96bc3f1d84dd504e2c667b162778508478645401f121"
    )
    assert (
        sig_s.hex()
        == "51e30b68b9091cf8138c07380c4378c2711779b68b2e5264d141479f13a12f57"
    )


@pytest.mark.skip_t1
def test_signtx_eip1559_access_list_larger(client):
    with client:

        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to="0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
            chain_id=1,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
            access_list=[
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
        )

    assert sig_v == 1
    assert (
        sig_r.hex()
        == "718a3a30827c979975c846d2f60495310c4959ee3adce2d89e0211785725465c"
    )
    assert (
        sig_s.hex()
        == "7d0ea2a28ef5702ca763c1f340427c0020292ffcbb4553dd1c8ea8e2b9126dbc"
    )
