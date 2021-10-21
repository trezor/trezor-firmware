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

from trezorlib import ethereum, exceptions, messages
from trezorlib.debuglink import message_filters
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

TO_ADDR = "0x1d1c328764a41bda0492b66baa30c4a339ff85ef"
SHOW_ALL = (143, 167)
GO_BACK = (16, 220)

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
            nonce=int(parameters["nonce"], 16),
            gas_price=int(parameters["gas_price"], 16),
            gas_limit=int(parameters["gas_limit"], 16),
            to=parameters["to_address"],
            chain_id=parameters["chain_id"],
            value=int(parameters["value"], 16),
            tx_type=parameters["tx_type"],
            data=bytes.fromhex(parameters["data"]),
        )

    expected_v = 2 * parameters["chain_id"] + 35
    assert sig_v in (expected_v, expected_v + 1)
    assert sig_r.hex() == result["sig_r"]
    assert sig_s.hex() == result["sig_s"]
    assert sig_v == result["sig_v"]


@parametrize_using_common_fixtures("ethereum/sign_tx_eip1559.json")
def test_signtx_eip1559(client, parameters, result):
    with client:
        sig_v, sig_r, sig_s = ethereum.sign_tx_eip1559(
            client,
            n=parse_path(parameters["path"]),
            nonce=int(parameters["nonce"], 16),
            gas_limit=int(parameters["gas_limit"], 16),
            max_gas_fee=int(parameters["max_gas_fee"], 16),
            max_priority_fee=int(parameters["max_priority_fee"], 16),
            to=parameters["to_address"],
            chain_id=parameters["chain_id"],
            value=int(parameters["value"], 16),
            data=bytes.fromhex(parameters["data"]),
        )

    assert sig_r.hex() == result["sig_r"]
    assert sig_s.hex() == result["sig_s"]
    assert sig_v == result["sig_v"]


def test_sanity_checks(client):
    """Is not vectorized because these are internal-only tests that do not
    need to be exposed to the public.
    """
    # contract creation without data should fail.
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=123456,
            gas_price=20000,
            gas_limit=20000,
            to="",
            value=12345678901234567890,
            chain_id=1,
        )

    # gas overflow
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=123456,
            gas_price=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            gas_limit=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
            to=TO_ADDR,
            value=12345678901234567890,
            chain_id=1,
        )

    # bad chain ID
    with pytest.raises(TrezorFailure, match=r"Chain ID out of bounds"):
        ethereum.sign_tx(
            client,
            n=parse_path("44'/60'/0'/0/0"),
            nonce=123456,
            gas_price=20000,
            gas_limit=20000,
            to=TO_ADDR,
            value=12345678901234567890,
            chain_id=0,
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


def test_sanity_checks_eip1559(client):
    """Is not vectorized because these are internal-only tests that do not
    need to be exposed to the public.
    """
    # contract creation without data should fail.
    with pytest.raises(TrezorFailure, match=r"DataError"):
        ethereum.sign_tx_eip1559(
            client,
            n=parse_path("44'/60'/0'/0/100"),
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
            client,
            n=parse_path("44'/60'/0'/0/100"),
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
            client,
            n=parse_path("44'/60'/0'/0/100"),
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
            client,
            n=parse_path("44'/60'/0'/0/100"),
            nonce=0,
            gas_limit=20,
            to=TO_ADDR,
            chain_id=0,
            value=10,
            max_gas_fee=20,
            max_priority_fee=1,
        )


def input_flow_skip(client, cancel=False):
    yield  # confirm sending
    client.debug.press_yes()

    yield  # confirm data
    if cancel:
        client.debug.press_no()
    else:
        client.debug.press_yes()
        yield
        client.debug.press_yes()


def input_flow_scroll_down(client, cancel=False):
    yield  # confirm sending
    client.debug.wait_layout()
    client.debug.press_yes()

    yield  # confirm data
    client.debug.wait_layout()
    client.debug.click(SHOW_ALL)

    br = yield  # paginated data
    for i in range(br.pages):
        client.debug.wait_layout()
        if i < br.pages - 1:
            client.debug.swipe_up()

    client.debug.press_yes()
    yield  # confirm data
    if cancel:
        client.debug.press_no()
    else:
        client.debug.press_yes()
        yield  # hold to confirm
        client.debug.press_yes()


def input_flow_go_back(client, cancel=False):
    br = yield  # confirm sending
    client.debug.wait_layout()
    client.debug.press_yes()

    br = yield  # confirm data
    client.debug.wait_layout()
    client.debug.click(SHOW_ALL)

    br = yield  # paginated data
    for i in range(br.pages):
        client.debug.wait_layout()
        if i == 2:
            client.debug.click(GO_BACK)
            yield  # confirm data
            client.debug.wait_layout()
            if cancel:
                client.debug.press_no()
            else:
                client.debug.press_yes()
                yield  # hold to confirm
                client.debug.wait_layout()
                client.debug.press_yes()
            return

        elif i < br.pages - 1:
            client.debug.swipe_up()


HEXDATA = "0123456789abcd000023456789abcd010003456789abcd020000456789abcd030000056789abcd040000006789abcd050000000789abcd060000000089abcd070000000009abcd080000000000abcd090000000001abcd0a0000000011abcd0b0000000111abcd0c0000001111abcd0d0000011111abcd0e0000111111abcd0f0000000002abcd100000000022abcd110000000222abcd120000002222abcd130000022222abcd140000222222abcd15"


@pytest.mark.parametrize(
    "flow", (input_flow_skip, input_flow_scroll_down, input_flow_go_back)
)
@pytest.mark.skip_t1
def test_signtx_data_pagination(client, flow):
    with client:
        client.watch_layout()
        client.set_input_flow(flow(client))
        ethereum.sign_tx(
            client,
            n=parse_path("m/44'/60'/0'/0/0"),
            nonce=0x0,
            gas_price=0x14,
            gas_limit=0x14,
            to="0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
            chain_id=1,
            value=0xA,
            tx_type=None,
            data=bytes.fromhex(HEXDATA),
        )

    with client, pytest.raises(exceptions.Cancelled):
        client.watch_layout()
        client.set_input_flow(flow(client, cancel=True))
        ethereum.sign_tx(
            client,
            n=parse_path("m/44'/60'/0'/0/0"),
            nonce=0x0,
            gas_price=0x14,
            gas_limit=0x14,
            to="0x1d1c328764a41bda0492b66baa30c4a339ff85ef",
            chain_id=1,
            value=0xA,
            tx_type=None,
            data=bytes.fromhex(HEXDATA),
        )
