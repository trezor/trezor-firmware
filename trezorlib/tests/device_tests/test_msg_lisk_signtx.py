# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from binascii import unhexlify
import pytest

from .common import TrezorTest
from trezorlib import messages as proto

PUBLIC_KEY = unhexlify('eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294')


@pytest.mark.xfail  # drop when trezor-core PR #90 is merged
@pytest.mark.skip_t1
class TestMsgLiskSignTx(TrezorTest):

    def test_lisk_sign_tx_send(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.LiskSignedTx(
                    signature=unhexlify('b62717d581e5713bca60b758b661e6cfa091addc6caedd57534e06cda805943ee80797b9fb9a1e1b2bd584e292d2a7f832a4d1b3f15f00e1ee1b72de7e195a08')
                )
            ])

            self.client.lisk_sign_tx(self.client.expand_path("m/44'/134'/0'/0'"), {
                "amount": "10000000",
                "recipientId": "9971262264659915921L",
                "timestamp": 57525937,
                "type": 0,
                "fee": "10000000",
                "asset": {}
            })

    def test_lisk_sign_tx_send_with_data(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.LiskSignedTx(
                    signature=unhexlify('5dd0dbb87ee46f3e985b1ef2df85cb0bec481e8601d150388f73e198cdd57a698eab076c7cd5b281fbb6a83dd3dc64d91a6eccd1614dffd46f101194ffa3a004')
                )
            ])

            self.client.lisk_sign_tx(self.client.expand_path("m/44'/134'/0'/0'"), {
                "amount": "10000000",
                "recipientId": "9971262264659915921L",
                "timestamp": 57525937,
                "type": 0,
                "fee": "20000000",
                "asset": {
                    "data": "Test data"
                }
            })

    def test_lisk_sign_tx_second_signature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.PublicKey),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.LiskSignedTx(
                    signature=unhexlify('f02bdc40a7599c21d29db4080ff1ff8934f76eedf5b0c4fa695c8a64af2f0b40a5c4f92db203863eebbbfad8f0611a23f451ed8bb711490234cdfb034728fd01')
                )
            ])

            self.client.lisk_sign_tx(self.client.expand_path("m/44'/134'/0'/0'"), {
                "amount": "0",
                "timestamp": 57525937,
                "type": 1,
                "fee": "500000000",
                "asset": {
                    "signature": {
                        "publicKey": "5d036a858ce89f844491762eb89e2bfbd50a4a0a0da658e4b2628b25b117ae09"
                    }
                }
            })

    def test_lisk_sign_tx_delegate_registration(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.LiskSignedTx(
                    signature=unhexlify('5ac02b2882b9d7d0f944e48baadc27de1296cc08c3533f7c8e380fbbb9fb4a6ac81b5dc57060d7d8c68912eea24eb6e39024801bccc0d55020e2052b0c2bb701')
                )
            ])

            self.client.lisk_sign_tx(self.client.expand_path("m/44'/134'/0'/0'"), {
                "amount": "0",
                "timestamp": 57525937,
                "type": 2,
                "fee": "2500000000",
                "asset": {
                    "delegate": {
                        "username": "trezor_t"
                    }
                }
            })

    def test_lisk_sign_tx_cast_votes(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.LiskSignedTx(
                    signature=unhexlify('1d0599a8387edaa4a6d309b8a78accd1ceaff20ff9d87136b01cba0efbcb9781c13dc2b0bab5a1ea4f196d8dcc9dbdbd2d56dbffcc088fc77686b2e2c2fe560f')
                )
            ])

            self.client.lisk_sign_tx(self.client.expand_path("m/44'/134'/0'/0'"), {
                "amount": "0",
                "timestamp": 57525937,
                "type": 3,
                "fee": "100000000",
                "asset": {
                    "votes": [
                        "+b002f58531c074c7190714523eec08c48db8c7cfc0c943097db1a2e82ed87f84",
                        "-ec111c8ad482445cfe83d811a7edd1f1d2765079c99d7d958cca1354740b7614"
                    ]
                }
            })

    def test_lisk_sign_tx_multisignature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.LiskSignedTx(
                    signature=unhexlify('88923866c2d500a6927715699ab41a0f58ea4b52e552d90e923bc24ac9da240f2328c93f9ce043a1da4937d4b61c7f57c02fc931f9824d06b24731e7be23c506')
                )
            ])

            self.client.lisk_sign_tx(self.client.expand_path("m/44'/134'/0'/0'"), {
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
                            "+922fbfdd596fa78269bbcadc67ec2a1cc15fc929a19c462169568d7a3df1a1aa"
                        ]
                    }
                }
            })
