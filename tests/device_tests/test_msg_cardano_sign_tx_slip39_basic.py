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

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6
from .test_msg_cardano_sign_transaction import (
    SAMPLE_INPUTS,
    SAMPLE_OUTPUTS,
    InputAction,
)

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
        [
            [InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "73e09bdebf98a9e0f17f86a2d11e0f14f4f8dae77cdf26ff1678e821f20c8db6",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018182582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e802182a030aa1028184582024c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c584055c179ff2beca2c6a78d66de3dea5a6e3134ca3430447c9b73ede73d9b6ae524cde73db59d93a4dfccbbd42b4f4dbacbb655b27171d0f248fdd2d0dc16e0130458206f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b41a0f6",
    ),
    # Mainnet transaction with change
    (
        # protocol magic (mainnet)
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
            [InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "4c43ce4c72f145b145ae7add414722735e250d048f61c4585a5becafcbffa6ae",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018282582b82d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e882582b82d818582183581c2ea63b3db3a1865f59c11762a5aede800ed8f2dc0605d75df2ed7c9ca0001ae82668161a000f424002182a030aa1028184582024c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c5840594c986290cc5cddf3c242f2d650fcbfd0705949c9990569798c29e42ca7b0d6e92a589be6962dcce9c53c63de973d84c38cf53374b5329e20973a280abec00d58206f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b41a0f6",
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
        [SAMPLE_OUTPUTS["testnet_output"], SAMPLE_OUTPUTS["byron_change_output"]],
        # fee
        42,
        # ttl
        10,
        # input flow
        [
            [InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
            [InputAction.YES],
            [InputAction.SWIPE, InputAction.YES],
        ],
        # tx hash
        "93a2c3cfb67ef1e4bae167b0f443c3370664bdb9171bc9cd41bad98e5cc049b2",
        # serialized tx
        "83a400818258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00018282582f82d818582583581cc817d85b524e3d073795819a25cdbb84cff6aa2bbb3a081980d248cba10242182a001a0fb6fc611a002dd2e882582f82d818582583581c709bfb5d9733cbdd72f520cd2c8b9f8f942da5e6cd0b6994e1803b0aa10242182a001aef14e76d1a000f424002182a030aa1028184582024c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c5840552d1d66972598532fa539faa98cdc7889c8dce00577626a62fb22d0e244d9f49732b6ab65593352a7486123077b7e36308c5048cc8ee6dc465e576f065cb70558206f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b45a10242182af6",
    ),
]


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase=True)
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
    certificates = []
    withdrawals = []
    metadata = bytes()

    expected_responses = [
        messages.PassphraseRequest(),
    ]
    expected_responses += [
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

    client.use_passphrase("TREZOR")
    with client:
        client.set_expected_responses(expected_responses)
        client.set_input_flow(input_flow)
        response = cardano.sign_tx(
            client=client,
            inputs=inputs,
            outputs=outputs,
            fee=fee,
            ttl=ttl,
            certificates=certificates,
            withdrawals=withdrawals,
            metadata=metadata,
            protocol_magic=protocol_magic,
            network_id=network_id,
        )
        assert response.tx_hash.hex() == tx_hash
        assert response.serialized_tx.hex() == serialized_tx
