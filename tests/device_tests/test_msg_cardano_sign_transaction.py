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

from trezorlib import cardano, messages
from trezorlib.cardano import PROTOCOL_MAGICS
from trezorlib.exceptions import TrezorFailure

SAMPLE_INPUT = {
    "path": "m/44'/1815'/0'/0/1",
    "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
    "prev_index": 0,
}

SAMPLE_OUTPUTS = {
    "simple_output": {
        "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
        "amount": "3003112",
    },
    "change_output": {"path": "m/44'/1815'/0'/0/1", "amount": "1000000"},
    "invalid_address": {
        "address": "jsK75PTH2esX8k4Wvxenyz83LJJWToBbVmGrWUer2CHFHanLseh7r3sW5X5q",
        "amount": "3003112",
    },
    "invalid_cbor": {
        "address": "5dnY6xgRcNUSLGa4gfqef2jGAMHb7koQs9EXErXLNC1LiMPUnhn8joXhvEJpWQtN3F4ysATcBvCn5tABgL3e4hPWapPHmcK5GJMSEaET5JafgAGwSrznzL1Mqa",
        "amount": "3003112",
    },
    "invalid_crc": {
        "address": "Ae2tdPwUPEZ5YUb8sM3eS8JqKgrRLzhiu71crfuH2MFtqaYr5ACNRZR3Mbm",
        "amount": "3003112",
    },
    "large_simple_output": {
        "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
        "amount": "449999999199999999",
    },
    "testnet_output": {
        "address": "2657WMsDfac5vydkak9a7BqGrsLqBzB7K3vT55rucZKYDmVnUCf6hXAFkZSTcUx7r",
        "amount": "3003112",
    },
}

VALID_VECTORS = [
    # Mainnet transaction without change
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        42,
        # ttl
        10,
        # tx hash
        "73e09bdebf98a9e0f17f86a2d11e0f14f4f8dae77cdf26ff1678e821f20c8db6",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018182582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e802182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840da07ac5246e3f20ebd1276476a4ae34a019dd4b264ffc22eea3c28cb0f1a6bb1c7764adeecf56bcb0bc6196fd1dbe080f3a7ef5b49f56980fe5b2881a4fdfa00582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63541a0f6",
    ),
    # Mainnet transaction with change
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"], SAMPLE_OUTPUTS["change_output"]],
        # fee
        42,
        # ttl
        10,
        # tx hash
        "81b14b7e62972127eb33c0b1198de6430540ad3a98eec621a3194f2baac43a43",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018282582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e882582b82d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a000f424002182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840d909b16038c4fd772a177038242e6793be39c735430b03ee924ed18026bd28d06920b5846247945f1204276e4b759aa5ac05a4a73b49ce705ab0e5e54a3a170e582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63541a0f6",
    ),
    # Testnet transaction
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["testnet_output"], SAMPLE_OUTPUTS["change_output"]],
        # fee
        42,
        # ttl
        10,
        # tx hash
        "5dd03fb44cb88061b2a1c246981bb31adfe4f57be69b58badb5ae8f448450932",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018282582f82d818582583581c586b90cf80c021db288ce1c18ecfd3610acf64f8748768b0eb7335b1a10242182a001aae3129311a002dd2e882582f82d818582583581c98c3a558f39d1d993cc8770e8825c70a6d0f5a9eb243501c4526c29da10242182a001aa8566c011a000f424002182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840fc30afdd0d4a6d8581e0f6abe895994d208fd382f2b23ff1553d711477a4fedbd1f68a76e7465c4816d5477f4287f7360acf71fca3b3d5902e4448e48c447106582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63545a10242182af6",
    ),
]

INVALID_VECTORS = [
    # Output address is a valid CBOR but invalid Cardano address
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["invalid_address"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Output address is invalid CBOR
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["invalid_cbor"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Output address has invalid CRC
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["invalid_crc"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Fee is too high
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        45000000000000001,
        # ttl
        10,
        # error message
        "Fee is out of range!",
    ),
    # Output total is too high
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["large_simple_output"], SAMPLE_OUTPUTS["change_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Total transaction amount is out of range!",
    ),
    # Mainnet transaction with testnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["testnet_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
    # Testnet transaction with mainnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # inputs
        [SAMPLE_INPUT],
        # outputs
        [SAMPLE_OUTPUTS["simple_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
]


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,inputs,outputs,fee,ttl,tx_hash,serialized_tx", VALID_VECTORS
)
def test_cardano_sign_tx(
    client, protocol_magic, inputs, outputs, fee, ttl, tx_hash, serialized_tx
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [
        messages.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.CardanoSignedTx(),
    ]

    def input_flow():
        yield
        client.debug.swipe_up()
        client.debug.press_yes()
        yield
        client.debug.swipe_up()
        client.debug.press_yes()

    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(client, inputs, outputs, fee, ttl, protocol_magic)
        assert response.tx_hash.hex() == tx_hash
        assert response.serialized_tx.hex() == serialized_tx


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,inputs,outputs,fee,ttl,expected_error_message", INVALID_VECTORS
)
def test_cardano_sign_tx_validation(
    client, protocol_magic, inputs, outputs, fee, ttl, expected_error_message
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [messages.Failure()]

    with client:
        client.set_expected_responses(expected_responses)

        with pytest.raises(TrezorFailure, match=expected_error_message):
            cardano.sign_tx(client, inputs, outputs, fee, ttl, protocol_magic)
