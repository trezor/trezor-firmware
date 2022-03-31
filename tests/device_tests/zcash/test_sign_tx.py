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

from trezorlib import btc, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..bitcoin.signtx import request_finished, request_input, request_output

B = messages.ButtonRequestType

TXHASH_aaf51e = bytes.fromhex(
    "aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc"
)
TXHASH_e38206 = bytes.fromhex(
    "e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368"
)

pytestmark = [pytest.mark.altcoin, pytest.mark.zcash, pytest.mark.skip_t1]


def test_version_group_id_missing(client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300000000 - 1940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure, match="Version group ID must be set."):
        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1],
            version=5,
        )


def test_one_one(client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300000000 - 1940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_finished(),
            ]
        )

        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1],
            version=5,
            version_group_id=0x892F2085,
            branch_id=0x76B809BB,
        )

        # TODO: send tx to testnet
        # TODO: check serialized_tx


def test_one_two(client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="tmNvfeKR5PkcQazLEqddTskFr6Ev9tsovfQ",
        amount=100000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=200000000 - 2000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )

        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1, out2],
            version=5,
            version_group_id=0x892F2085,
            branch_id=0x76B809BB,
        )

        # TODO: send tx to testnet
        # TODO: check serialized_tx


def test_external_presigned(client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )

    inp2 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        # address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_aaf51e,
        prev_index=1,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a914a579388225827d9f2fe9014add644487808c695d88ac"
        ),
        script_sig=bytes.fromhex(
            "48304502210090020ba5d1c945145f04e940c4b6026a24d2b9e58e7ae53834eca6f606e457e4022040d214cb7ad2bd2cff14bac8d7b8eab0bb603c239a962ecd8535ea49ca25071e0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        ),
    )

    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300000000 + 300000000 - 1940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(1),
                request_input(0),
                request_input(1),
                request_output(0),
                request_finished(),
            ]
        )

        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1, inp2],
            [out1],
            version=5,
            version_group_id=0x892F2085,
            branch_id=0x76B809BB,
        )

    # TODO: send tx to testnet
    # TODO: check serialized


def test_refuse_replacement_tx(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/4"),
        amount=174998,
        prev_hash=bytes.fromhex(
            "beafc7cbd873d06dbee88a7002768ad5864228639db514c81cfb29f108bb1e7a"
        ),
        prev_index=0,
        orig_hash=bytes.fromhex(
            "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
        ),
        orig_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/2"),
        amount=174998 - 50000 - 1111,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=bytes.fromhex(
            "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
        ),
        orig_index=0,
    )

    out2 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=50000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=bytes.fromhex(
            "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
        ),
        orig_index=1,
    )

    with pytest.raises(
        TrezorFailure, match="Replacement transactions are not supported."
    ):
        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1, out2],
            version=5,
            version_group_id=0x892F2085,
            branch_id=0x76B809BB,
        )
