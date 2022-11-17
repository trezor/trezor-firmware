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

from trezorlib import messages, zcash
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import (
    ButtonRequest,
    OutputScriptType,
    RequestType as T,
    TxInputType,
    TxOutputType,
    TxRequest,
    TxRequestDetailsType,
    ZcashOrchardInput,
    ZcashOrchardOutput,
    ZcashSignatureType,
)
from trezorlib.tools import parse_path

from ..bitcoin.signtx import request_finished, request_input, request_output

# from ..bitcoin.signtx import request_finished, request_input, request_output

B = messages.ButtonRequestType


def request_orchard_input(i: int):
    return TxRequest(
        request_type=T.TXORCHARDINPUT,
        details=messages.TxRequestDetailsType(request_index=i),
    )


def request_orchard_output(i: int):
    return TxRequest(
        request_type=T.TXORCHARDOUTPUT,
        details=messages.TxRequestDetailsType(request_index=i),
    )


def request_no_op():
    return TxRequest(request_type=T.NO_OP)


def test_z2t(client: Client) -> None:
    t_out_0 = TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=990000,
        script_type=OutputScriptType.PAYTOADDRESS,
    )
    # note a86810a5b052fb69b3c76887f381241cea060017314e9a9418876e02cda63c03
    o_inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex(
            "160618e7e57eb29bfc1182108a933ae1dbf8ccc148d3cfa6c0a15a04de09e3c8844cd07be822332eaa2900"
        ),
        value=1000000,
        rho=bytes.fromhex(
            "bd6361c35b8363554f9c0b3612e67f4c65beae3aa71305e84d3827137497563d"
        ),
        rseed=bytes.fromhex(
            "5c7ea612f6f66f50f961d7c98c2c60f3d0223c4ad6bdb876a3b8225bce526361"
        ),
    )

    anchor = bytes.fromhex(
        "a6e3b9c237886caa6ca8614428dc9a0ca5e2e54691c68f682348a41f489abf1f"
    )
    expected_shielding_seed = bytes.fromhex(
        "a3db28e1855c5bd8670f234150ea4d8f2d22a97662e5e3cf765aa6abf5b5579e"
    )
    expected_sighash = bytes.fromhex(
        "791f8985d5c21e9738b4556274109aa1a468f57079d8cd1b3ae83bac371eabfd"
    )
    expected_serialized_tx = bytes.fromhex(
        "050000800a27a726b4d0d6c200000000000000000001301b0f00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000002"
    )

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_output(0),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_input(0),
                request_output(0),
                request_finished(),  # returns o-signature of o-input 0 in action 0
            ]
        )

        protocol = zcash.sign_tx(
            client,
            t_inputs=[],
            t_outputs=[t_out_0],
            o_inputs=[o_inp_0],
            o_outputs=[],
            anchor=anchor,
            coin_name="Zcash Testnet",
        )

        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                0: bytes.fromhex(
                    "6a5b6db66413490272cdcc55efca8c2d85ce493fa46a3624675e9760f78f98206761087f847266839c9d9534a5e39cedb90e628ee48c7fdc88089faf692ab42e"
                ),
            },
        }

        # Accepted by network as fdab1e37ac3be83a1bcdd87970f568a4a19a10746255b438971ec2d585891f79
        # link: https://sochain.com/tx/ZECTEST/fdab1e37ac3be83a1bcdd87970f568a4a19a10746255b438971ec2d585891f79


def test_z2z(client: Client) -> None:
    # note 8eb09c03fcddd0011fcbeee17518d378f02c3be3cbf210c69fbae5c111da0e16
    o_inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex(
            "160618e7e57eb29bfc1182108a933ae1dbf8ccc148d3cfa6c0a15a04de09e3c8844cd07be822332eaa2900"
        ),
        value=1000000,
        rho=bytes.fromhex(
            "3bf2d24afd84071efbbf3175afba9971cc8aa21ea1da5629379e2d51b39aeb28"
        ),
        rseed=bytes.fromhex(
            "74e4ab56513d4587d716d864a9c6e05b289e67c16096a6a4df8737d8253f442d"
        ),
    )

    o_out_0 = ZcashOrchardOutput(
        address=None,
        amount=990000,
        memo=None,
    )
    anchor = bytes.fromhex(
        "a6e3b9c237886caa6ca8614428dc9a0ca5e2e54691c68f682348a41f489abf1f"
    )
    expected_shielding_seed = bytes.fromhex(
        "e14ee85dac66bbc5dbc0e8cf9a73a5b5feba978dc8c96a7d8d83af971b43f943"
    )
    expected_sighash = bytes.fromhex(
        "8b7a1b8bcae057c9389a7743d05e3ac45fd4088b1f4f34427903eae140f13196"
    )
    expected_serialized_tx = bytes.fromhex(
        "050000800a27a726b4d0d6c200000000000000000000000002"
    )

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_orchard_output(0),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_input(0),
                request_orchard_output(0),
                request_finished(),  # returns o-signature of o-input 0 in action 0
            ]
        )

        protocol = zcash.sign_tx(
            client,
            t_inputs=[],
            t_outputs=[],
            o_inputs=[o_inp_0],
            o_outputs=[o_out_0],
            anchor=anchor,
            coin_name="Zcash Testnet",
        )

        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                0: bytes.fromhex(
                    "23215cda85de918473b83f6f53a7817817286692a69ffd74c12468adeb4cc5a4dbb1990672b24bdd7c3f5ebee8f86a56c707493b9f5d34707bd639a3191a4c04"
                ),
            },
        }

        # Accepted by network as 9631f140e1ea037942344f1f8b08d45fc43a5ed043779a38c957e0ca8b1b7a8b
        # link: https://sochain.com/tx/ZECTEST/9631f140e1ea037942344f1f8b08d45fc43a5ed043779a38c957e0ca8b1b7a8b


def test_t2z(client: Client) -> None:
    t_inp_0 = TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=1000000,
        prev_hash=bytes.fromhex(
            "f81bfe926afee9f463f9c7ab0a68e29b78718b42798b48f4227094b3cbe8c3e7"
        ),
        prev_index=0,
    )
    o_out_0 = ZcashOrchardOutput(
        address=None,
        amount=990000,
        memo=None,
    )
    anchor = bytes.fromhex(
        "a6e3b9c237886caa6ca8614428dc9a0ca5e2e54691c68f682348a41f489abf1f"
    )
    expected_shielding_seed = bytes.fromhex(
        "a8f354bff75e1607f80868aaa408e776ce097f8adcbc5074ac603774cb9462e2"
    )
    expected_sighash = bytes.fromhex(
        "c7a2978fe65e8d7742358f542ae2f031aa1a3441af161079237509ee4e74112d"
    )
    expected_serialized_tx = bytes.fromhex(
        "050000800a27a726b4d0d6c2000000000000000001e7c3e8cbb3947022f4488b79428b71789be2680aabc7f963f4e9fe6a92fe1bf8000000006a473044022054e06e576036b6b83f7c676ed1e97810710a50eed52bd6e393ac93084a7a62b602201a5dcf95242b174a9510741692a8666b4f305abff7f2a0b153bd00470a77b66c0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff00000002"
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_orchard_output(0),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_output(0),
                request_input(0),
                request_finished(),  # t-signature {i}
            ]
        )

        protocol = zcash.sign_tx(
            client,
            t_inputs=[t_inp_0],
            t_outputs=[],
            o_inputs=[],
            o_outputs=[o_out_0],
            anchor=anchor,
            coin_name="Zcash Testnet",
        )

        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [
                bytes.fromhex(
                    "3044022054e06e576036b6b83f7c676ed1e97810710a50eed52bd6e393ac93084a7a62b602201a5dcf95242b174a9510741692a8666b4f305abff7f2a0b153bd00470a77b66c"
                ),
            ],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {},
        }

        # Accepted by network as 57cb5b7194583d3d4073d8825668762872dd1b4b3ad88fed5e24bc26b500ea44
        # link: https://sochain.com/tx/ZECTEST/57cb5b7194583d3d4073d8825668762872dd1b4b3ad88fed5e24bc26b500ea44
