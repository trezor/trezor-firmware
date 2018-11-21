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
        self.setup_mnemonic_allallall()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "f48532d43e8c5abadf50bb7b82098b31eec3e67747e5328c0675203e86441899c246fa3aea6fc91043209431ce710c5aa34aa234546b85b88299d5a379bff202"
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
        self.setup_mnemonic_allallall()

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
                            "87b9789ed10fb93311b77d23e34484ee653b43206a7e416da70f8dd6b15231a8dfe05c66bcbca62ba841fdde8affdb04b3ee18300caa8560cd15f6a4942a870a"
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
        self.setup_mnemonic_allallall()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "4e83a651e82f2f787a71a5f44a2911dd0429ee4001b80c79fb7d174ea63ceeefdfba55aa3a9f31fa14b8325a39ad973dcd7eadbaa77b0447a9893f84b60f210e"
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
        self.setup_mnemonic_allallall()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.PublicKey),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "e27d8997d0bdbc9ab4ad928fcf140edb25a217007987447270085c0872e4178c018847d1378a949ad2aa913692f10aeec340810fd9de02da9d4461c63b6b6c06"
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
        self.setup_mnemonic_allallall()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "e9f68b9961198f4e0d33d6ae95cbd90ab243c2c1f9fcc51db54eb54cc1491db53d237131e12da9485bfbfbd02255c431d08095076f926060c434edb01cf25807"
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
        self.setup_mnemonic_allallall()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "18d7cb27276a83178427aab2abcb5ee1c8ae9e8e2d1231585dcae7a83dd7d5167eea5baca890169bc80dcaf187320cab47c2f65a20c6483fede0f059919e4106"
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
        self.setup_mnemonic_allallall()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "b84438ae3d419d270eacd0414fc8818d8f2c721602be54c3d705cf4cb3305de44e674f6dac9aac87379cce006cc97f2f635f296a48ab6a6adf62e2c11e08e409"
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
