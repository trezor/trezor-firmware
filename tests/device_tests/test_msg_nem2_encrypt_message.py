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

from trezorlib import nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2GetPublicKey:

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_encrypt_message(self, client):

        test_payloads = [
            "Test Payload",
            "",
            "Another message",
            "message with a \\s character",
            "message ending with a \r",
            "1232221232123123232333323121112112",
            "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        ]

        for test_payload in test_payloads:
            ensure_encrypted_message_is_correct(test_payload, client)

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_descrypt_nem2_sdk_message(self, client):

        decrypted_message = nem2.decrypt_message(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            {
                "senderPublicKey": "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297",
                "payload": "50E316DE03F1D52C9DB9CBA6F11F84EAC05D78FD55F3668E5FDF0733A299C27BE9F50ADD3EA02A8BE7413D072E8A2936"
            }
        )

        assert (
            bytes("Encrypted by nem2-sdk", "ascii")
            == decrypted_message.payload
        )

def ensure_encrypted_message_is_correct(payload, client):
    encrypted_message = nem2.encrypt_message(
        client,
        parse_path("m/44'/43'/0'/0'/0'"),
        {
            "recipientPublicKey": "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297",
            "payload": payload
        }
    )

    decrypted_message = nem2.decrypt_message(
        client,
        parse_path("m/44'/43'/0'/0'/0'"),
        {
            "senderPublicKey": "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297",
            "payload": encrypted_message.payload.hex()
        }
    )

    assert (
        bytes(payload, "ascii")
        == decrypted_message.payload
    )
