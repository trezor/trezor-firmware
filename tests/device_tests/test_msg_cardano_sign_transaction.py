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
from trezorlib.cardano import NETWORK_IDS, PROTOCOL_MAGICS
from trezorlib.exceptions import TrezorFailure


class InputAction:
    """
    Test cases don't use the same input flows. These constants are used to define
    the expected input flows for each test case. Corresponding input actions
    are then executed on the device to simulate user inputs.
    """

    SWIPE = 0
    YES = 1


SAMPLE_INPUTS = {
    "byron_input": {
        "path": "m/44'/1815'/0'/0/1",
        "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
        "prev_index": 0,
    },
    "shelley_input": {
        "path": "m/1852'/1815'/0'/0/0",
        "prev_hash": "3b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7",
        "prev_index": 0,
    },
}

SAMPLE_OUTPUTS = {
    "simple_byron_output": {
        "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
        "amount": "3003112",
    },
    "byron_change_output": {
        "addressType": 8,
        "path": "m/44'/1815'/0'/0/1",
        "amount": "1000000",
    },
    "simple_shelley_output": {
        "address": "addr1q84sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hlsd5tq5r",
        "amount": "1",
    },
    "base_address_with_script_output": {
        "address": "addr1z90z7zqwhya6mpk5q929ur897g3pp9kkgalpreny8y304r2dcrtx0sf3dluyu4erzr3xtmdnzvcyfzekkuteu2xagx0qeva0pr",
        "amount": "7120787",
    },
    "base_address_change_output": {
        "addressType": 0,
        "path": "m/1852'/1815'/0'/0/0",
        "stakingPath": "m/1852'/1815'/0'/2/0",
        "amount": "7120787",
    },
    "staking_key_hash_output": {
        "addressType": 0,
        "path": "m/1852'/1815'/0'/0/0",
        "stakingKeyHash": "32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc",
        "amount": "7120787",
    },
    "pointer_address_output": {
        "addressType": 4,
        "path": "m/1852'/1815'/0'/0/0",
        "blockIndex": 1,
        "txIndex": 2,
        "certificateIndex": 3,
        "amount": "7120787",
    },
    "enterprise_address_output": {
        "addressType": 6,
        "path": "m/1852'/1815'/0'/0/0",
        "amount": "7120787",
    },
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
    "invalid_address_too_short": {
        "address": "addr1q89s8py7y68e3x66sscs0wkhlg5ssfrfs65084jry45scvehcr",
        "amount": "3003112",
    },
    "invalid_address_too_long": {
        "address": "addr1q89s8py7y68e3x66sscs0wkhlg5ssfrfs65084jrlrqcfqqj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfm5z3vcwsfrvkr5zglq4rxu",
        "amount": "3003112",
    },
    "large_simple_byron_output": {
        "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
        "amount": "449999999199999999",
    },
    # address type 10
    "unsupported_address_type": {
        "address": "addr1590z7zqwhya6mpk5q929ur897g3pp9kkgalpreny8y304r2dcrtx0sf3dluyu4erzr3xtmdnzvcyfzekkuteu2xagx0qt7gvvj",
        "amount": "3003112",
    },
    "testnet_output": {
        "address": "2657WMsDfac7BteXkJq5Jzdog4h47fPbkwUM49isuWbYAr2cFRHa3rURP236h9PBe",
        "amount": "3003112",
    },
    "shelley_testnet_output": {
        "address": "addr_test1vr9s8py7y68e3x66sscs0wkhlg5ssfrfs65084jrlrqcfqqtmut0e",
        "amount": "1",
    },
}

VALID_VECTORS = [
    # Mainnet transaction without change
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        42,
        # ttl
        10,
        # input flow
        [[InputAction.SWIPE, InputAction.YES], [InputAction.SWIPE, InputAction.YES]],
        # tx hash
        "73e09bdebf98a9e0f17f86a2d11e0f14f4f8dae77cdf26ff1678e821f20c8db6",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018182582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e802182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840da07ac5246e3f20ebd1276476a4ae34a019dd4b264ffc22eea3c28cb0f1a6bb1c7764adeecf56bcb0bc6196fd1dbe080f3a7ef5b49f56980fe5b2881a4fdfa00582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63541a0f6",
    ),
    # Mainnet transaction with change
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"], SAMPLE_OUTPUTS["byron_change_output"]],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "81b14b7e62972127eb33c0b1198de6430540ad3a98eec621a3194f2baac43a43",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018282582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e882582b82d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a000f424002182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840d909b16038c4fd772a177038242e6793be39c735430b03ee924ed18026bd28d06920b5846247945f1204276e4b759aa5ac05a4a73b49ce705ab0e5e54a3a170e582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63541a0f6",
    ),
    # simple transaction with base address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["base_address_change_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [[InputAction.SWIPE, InputAction.YES], [InputAction.SWIPE, InputAction.YES]],
        # tx hash
        "16fe72bb198be423677577e6326f1f648ec5fc11263b072006382d8125a6edda",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282583901eb0baa5e570cffbe2934db29df0b6a3d7c0430ee65d4c3a7ab2fefb91bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff018258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b42771a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c158406a78f07836dcf4a303448d2b16b217265a9226be3984a69a04dba5d04f4dbb2a47b5e1cbb345f474c0b9634a2f37b921ab26e6a65d5dfd015dacb4455fb8430af6",
    ),
    # simple transaction with base script address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["base_address_with_script_output"],
            SAMPLE_OUTPUTS["base_address_change_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [[InputAction.SWIPE, InputAction.YES], [InputAction.SWIPE, InputAction.YES]],
        # tx hash
        "5ddbb530b8a89e2b08fc91db03950c876c4a9c1c3fb6e628c4cab638b1c97648",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b7000182825839115e2f080eb93bad86d401545e0ce5f2221096d6477e11e6643922fa8d4dc0d667c1316ff84e572310e265edb31330448b36b7179e28dd419e1a006ca7938258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b42771a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c15840e0bdaa59016f2a521d31179b60364eacdcb53c34ae01c56b339afa62d312f5f89783579691cac777e3d5f2e7810aa8fe554ba545a8d1578c55405af5ae51b30ff6",
    ),
    # simple transaction with base address change output with staking key hash
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["staking_key_hash_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "d1610bb89bece22ed3158738bc1fbb31c6af0685053e2993361e3380f49afad9",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282583901eb0baa5e570cffbe2934db29df0b6a3d7c0430ee65d4c3a7ab2fefb91bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff018258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc1a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c15840622f22d03bc9651ddc5eb2f5dc709ac4240a64d2b78c70355dd62106543c407d56e8134c4df7884ba67c8a1b5c706fc021df5c4d0ff37385c30572e73c727d00f6",
    ),
    # simple transaction with pointer address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["pointer_address_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "40535fa8f88515f1da008d3cdf544cf9dbf1675c3cb0adb13b74b9293f1b7096",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282583901eb0baa5e570cffbe2934db29df0b6a3d7c0430ee65d4c3a7ab2fefb91bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff018258204180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa0102031a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c15840dbbf050cc13d0696b1884113613318a275e6f0f8c7cb3e7828c4f2f3c158b2622a5d65ea247f1eed758a0f6242a52060c319d6f37c8460f5d14be24456cd0b08f6",
    ),
    # simple transaction with enterprise address change output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["simple_shelley_output"],
            SAMPLE_OUTPUTS["enterprise_address_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "d3570557b197604109481a80aeb66cd2cfabc57f802ad593bacc12eb658e5d72",
        # tx body
        "83a400818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282583901eb0baa5e570cffbe2934db29df0b6a3d7c0430ee65d4c3a7ab2fefb91bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff0182581d6180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa1a006ca79302182a030aa100818258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c15840c5996650c438c4493b2c8a94229621bb9b151b8d61d75fb868c305e917031e9a1654f35023f7dbf5d1839ab9d57b153c7f79c2666af51ecf363780397956e00af6",
    ),
    # Testnet transaction
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["testnet_output"],
            SAMPLE_OUTPUTS["shelley_testnet_output"],
            SAMPLE_OUTPUTS["byron_change_output"],
        ],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "47cf79f20c6c62edb4162b3b232a57afc1bd0b57c7fd8389555276408a004776",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018382582f82d818582583581cc817d85b524e3d073795819a25cdbb84cff6aa2bbb3a081980d248cba10242182a001a0fb6fc611a002dd2e882581d60cb03849e268f989b5a843107bad7fa2908246986a8f3d643f8c184800182582f82d818582583581c98c3a558f39d1d993cc8770e8825c70a6d0f5a9eb243501c4526c29da10242182a001aa8566c011a000f424002182a030aa1028184582089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea5840cc11adf81cb3c3b75a438325f8577666f5cbb4d5d6b73fa6dbbcf5ab36897df34eecacdb54c3bc3ce7fc594ebb2c7aa4db4700f4290facad9b611a035af8710a582026308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63545a10242182af6",
    ),
]

INVALID_VECTORS = [
    # Output address is a valid CBOR but invalid Cardano address
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
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
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
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
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["invalid_crc"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Output address is too short
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["invalid_address_too_short"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Output address is too long
    (
        # protocol magic (mainnet)
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["invalid_address_too_long"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Fee is too high
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        45000000000000001,
        # ttl
        10,
        # error message
        "Fee is out of range!",
    ),
    # Output total is too high
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [
            SAMPLE_OUTPUTS["large_simple_byron_output"],
            SAMPLE_OUTPUTS["byron_change_output"],
        ],
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
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
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
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["byron_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Output address network mismatch!",
    ),
    # Shelley mainnet transaction with testnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["shelley_testnet_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Shelley testnet transaction with mainnet output
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_shelley_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
    # Testnet protocol magic with mainnet network id
    (
        # protocol magic
        PROTOCOL_MAGICS["testnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_shelley_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid network id/protocol magic combination!",
    ),
    # Mainnet protocol magic with testnet network id
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["testnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["simple_byron_output"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid network id/protocol magic combination!",
    ),
    # Unsupported address type
    (
        # protocol magic
        PROTOCOL_MAGICS["mainnet"],
        # network id
        NETWORK_IDS["mainnet"],
        # inputs
        [SAMPLE_INPUTS["shelley_input"]],
        # outputs
        [SAMPLE_OUTPUTS["unsupported_address_type"]],
        # fee
        42,
        # ttl
        10,
        # error message
        "Invalid address",
    ),
]


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,network_id,inputs,outputs,fee,ttl,input_flow_sequences,tx_hash,serialized_tx",
    VALID_VECTORS,
)
def test_cardano_sign_tx(
    client,
    protocol_magic,
    network_id,
    inputs,
    outputs,
    fee,
    ttl,
    input_flow_sequences,
    tx_hash,
    serialized_tx,
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [
        messages.ButtonRequest(code=messages.ButtonRequestType.Other)
        for i in range(len(input_flow_sequences))
    ]
    expected_responses.append(messages.CardanoSignedTx())

    def input_flow():
        for sequence in input_flow_sequences:
            yield
            for action in sequence:
                if action == InputAction.SWIPE:
                    client.debug.swipe_up()
                elif action == InputAction.YES:
                    client.debug.press_yes()
                else:
                    raise ValueError("Invalid input action")

    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client, inputs, outputs, fee, ttl, protocol_magic, network_id
        )
        assert response.tx_hash.hex() == tx_hash
        assert response.serialized_tx.hex() == serialized_tx


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "protocol_magic,network_id,inputs,outputs,fee,ttl,expected_error_message",
    INVALID_VECTORS,
)
def test_cardano_sign_tx_validation(
    client,
    protocol_magic,
    network_id,
    inputs,
    outputs,
    fee,
    ttl,
    expected_error_message,
):
    inputs = [cardano.create_input(i) for i in inputs]
    outputs = [cardano.create_output(o) for o in outputs]

    expected_responses = [messages.Failure()]

    with client:
        client.set_expected_responses(expected_responses)

        with pytest.raises(TrezorFailure, match=expected_error_message):
            cardano.sign_tx(
                client, inputs, outputs, fee, ttl, protocol_magic, network_id
            )
