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
import pytest

from trezorlib import lisk, messages as proto
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.lisk
class TestMsgLiskSignTx(TrezorTest):
    def test_lisk_sign_tx_send(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "6c96202c2271971917f9d8b752d6aa097084931bae2f2c92d2eeb3956310fb29c5bebeadf5707558b847d75a7f437998b9940aa76fb0d7b4fe40f09b4809970f"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/134'/0'"),
                {
                    "amount": "10000000",
                    "recipientId": "9971262264659915921L",
                    "timestamp": 57525937,
                    "type": 0,
                    "fee": "10000000",
                    "asset": {},
                },
            )

    @pytest.mark.skip_t1
    def test_lisk_sign_tx_send_wrong_path(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(
                        code=proto.ButtonRequestType.UnknownDerivationPath
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "2cb9ce4b5e5add3b445272dd0def4719fcabfb169177ce705e856602ee414fc1a45e8ea0d1ae45bdc4e8283285b13d7a2e8776afb0e3ab50eeffe2c9ca67cc06"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/9999'/0'"),
                {
                    "amount": "10000000",
                    "recipientId": "9971262264659915921L",
                    "timestamp": 57525937,
                    "type": 0,
                    "fee": "10000000",
                    "asset": {},
                },
            )

    def test_lisk_sign_tx_send_with_data(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "8c36cbb03461cd574db2e9183b85f354f14f8a9b797a082b622bbd93c3504992e80bfcb20d93671843932c2d672e072ebcc139bb829bbdafedcc359230321b02"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/134'/0'"),
                {
                    "amount": "10000000",
                    "recipientId": "9971262264659915921L",
                    "timestamp": 57525937,
                    "type": 0,
                    "fee": "20000000",
                    "asset": {"data": "Test data"},
                },
            )

    def test_lisk_sign_tx_second_signature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.PublicKey),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "6b8d4af2f31d94c187dd7059c3bbbf0e98d0b0a5a278a1a71d3f42ed81c92d6e122b4bcf2e8829af081098adefca990972b7765cecca70745030e07f61de7909"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/134'/0'"),
                {
                    "amount": "0",
                    "timestamp": 57525937,
                    "type": 1,
                    "fee": "500000000",
                    "asset": {
                        "signature": {
                            "publicKey": "5d036a858ce89f844491762eb89e2bfbd50a4a0a0da658e4b2628b25b117ae09"
                        }
                    },
                },
            )

    def test_lisk_sign_tx_delegate_registration(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "9187f8156e8fc0bfe934002f0630cf9e9ef94f8880c796b8680b67ddeb15421f2a7880c0e23fa405cf3ed06459b856b9004aec916df58654b025bf5167e5dc0f"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/134'/0'"),
                {
                    "amount": "0",
                    "timestamp": 57525937,
                    "type": 2,
                    "fee": "2500000000",
                    "asset": {"delegate": {"username": "trezor_t"}},
                },
            )

    def test_lisk_sign_tx_cast_votes(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "dfe9a12e14a12e6d411dba6eab91f69f7389eb3b04055f57218b997ccf72059fe151dd065d055e4c11205aa357f9b733958502ad7e8ab97cfeeda9b2edfa6a0b"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/134'/0'"),
                {
                    "amount": "0",
                    "timestamp": 57525937,
                    "type": 3,
                    "fee": "100000000",
                    "asset": {
                        "votes": [
                            "+b002f58531c074c7190714523eec08c48db8c7cfc0c943097db1a2e82ed87f84",
                            "-ec111c8ad482445cfe83d811a7edd1f1d2765079c99d7d958cca1354740b7614",
                        ]
                    },
                },
            )

    def test_lisk_sign_tx_multisignature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "c97c94a4e6426e0d280e8279833110c5d5204beabde49865d73e21866ee9764da7f654257977e68ec6a9c5aa71214dec29ca331e64ae70853968c25b730ca403"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                self.client,
                parse_path("m/44'/134'/0'"),
                {
                    "amount": "0",
                    "timestamp": 57525937,
                    "type": 4,
                    "fee": "1500000000",
                    "asset": {
                        "multisignature": {
                            "min": 2,
                            "lifetime": 5,
                            "keysgroup": [
                                "+5d036a858ce89f844491762eb89e2bfbd50a4a0a0da658e4b2628b25b117ae09",
                                "+922fbfdd596fa78269bbcadc67ec2a1cc15fc929a19c462169568d7a3df1a1aa",
                            ],
                        }
                    },
                },
            )
