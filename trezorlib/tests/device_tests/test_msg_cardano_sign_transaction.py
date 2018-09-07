# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import binascii
import time

import pytest

from trezorlib import messages
from trezorlib.cardano import create_input, create_output

from .common import TrezorTest


@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgCardanoSignTx(TrezorTest):
    def test_cardano_sign_tx_mainnet(self):
        self.setup_mnemonic_allallall()

        transaction = {
            "inputs": [
                {
                    "path": "m/44'/1815'/0'/0/1",
                    "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
                    "prev_index": 0,
                    "type": 0,
                }
            ],
            "outputs": [
                {
                    "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
                    "amount": "3003112",
                }
            ],
            "transactions": [
                "839f8200d818582482582008abb575fac4c39d5bf80683f7f0c37e48f4e3d96e37d1f6611919a7241b456600ff9f8282d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a00305becffa0"
            ],
        }

        inputs = [create_input(input) for input in transaction["inputs"]]
        outputs = [create_output(output) for output in transaction["outputs"]]
        transactions = transaction["transactions"]

        self.client.transport.write(
            messages.CardanoSignTx(
                inputs=inputs,
                outputs=outputs,
                transactions_count=len(transactions),
                network=2,
            )
        )
        response = self.client.transport.read()

        assert isinstance(response, messages.CardanoTxRequest)
        assert response.tx_index == 0

        # Upload first transaction
        transaction_data = binascii.unhexlify(transactions[0])
        ack_message = messages.CardanoTxAck(transaction=transaction_data)
        self.client.transport.write(ack_message)

        # Confirm fee
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)

        # Confirm Network
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)

        # Confirm Output
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)
        self.client.debug.swipe_down()
        time.sleep(1)

        # Confirm amount
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())

        response = self.client.transport.read()
        assert isinstance(response, messages.CardanoSignedTx)

        assert (
            binascii.hexlify(response.tx_hash)
            == b"799c65e8a2c0b1dc4232611728c09d3f3eb0d811c077f8e9798f84605ef1b23d"
        )
        assert (
            binascii.hexlify(response.tx_body)
            == b"82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e8ffa0818200d818588582584089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a6355840312c01c27317415b0b8acc86aa789da877fe7e15c65b7ea4c4565d8739117f5f6d9d38bf5d058f7be809b2b9b06c1d79fc6b20f9a4d76d8c89bae333edf5680c"
        )

    def test_cardano_sign_tx_testnet(self):
        self.setup_mnemonic_allallall()

        transaction = {
            "inputs": [
                {
                    "path": "m/44'/1815'/0'/0/1",
                    "prev_hash": "1af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc",
                    "prev_index": 0,
                    "type": 0,
                }
            ],
            "outputs": [
                {
                    "address": "Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2",
                    "amount": "3003112",
                }
            ],
            "transactions": [
                "839f8200d818582482582008abb575fac4c39d5bf80683f7f0c37e48f4e3d96e37d1f6611919a7241b456600ff9f8282d818582183581cda4da43db3fca93695e71dab839e72271204d28b9d964d306b8800a8a0001a7a6916a51a00305becffa0"
            ],
        }

        inputs = [create_input(input) for input in transaction["inputs"]]
        outputs = [create_output(output) for output in transaction["outputs"]]
        transactions = transaction["transactions"]

        self.client.transport.write(
            messages.CardanoSignTx(
                inputs=inputs,
                outputs=outputs,
                transactions_count=len(transactions),
                network=1,
            )
        )
        response = self.client.transport.read()

        assert isinstance(response, messages.CardanoTxRequest)
        assert response.tx_index == 0

        # Upload first transaction
        transaction_data = binascii.unhexlify(transactions[0])
        ack_message = messages.CardanoTxAck(transaction=transaction_data)
        self.client.transport.write(ack_message)

        # Confirm fee
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)

        # Confirm Network
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)

        # Confirm Output
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)
        self.client.debug.swipe_down()
        time.sleep(1)

        # Confirm amount
        response = self.client.transport.read()
        assert isinstance(response, messages.ButtonRequest)
        assert response.code == messages.ButtonRequestType.Other

        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())

        response = self.client.transport.read()
        assert isinstance(response, messages.CardanoSignedTx)

        assert (
            binascii.hexlify(response.tx_hash)
            == b"799c65e8a2c0b1dc4232611728c09d3f3eb0d811c077f8e9798f84605ef1b23d"
        )
        assert (
            binascii.hexlify(response.tx_body)
            == b"82839f8200d81858248258201af8fa0b754ff99253d983894e63a2b09cbb56c833ba18c3384210163f63dcfc00ff9f8282d818582183581c9e1c71de652ec8b85fec296f0685ca3988781c94a2e1a5d89d92f45fa0001a0d0c25611a002dd2e8ffa0818200d818588582584089053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a63558403594ee7e2bfe4c84f886a8336cecb7c42983ce9a057345ebb6294a436087d8db93ca78cf514c7c48edff4c8435f690a5817951e2b55d2db729875ee7cc0f7d08"
        )
