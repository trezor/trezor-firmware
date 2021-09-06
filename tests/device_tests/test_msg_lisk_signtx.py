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

from trezorlib import lisk, messages as proto
from trezorlib.tools import parse_path

NETWORK_ID = bytes.fromhex(
    "4c09e6a781fc4c7bdb936ee815de8f94190f8a7519becd9de2081832be309a99"
)


@pytest.mark.altcoin
@pytest.mark.lisk
class TestMsgLiskSignTx:
    def test_lisk_sign_tx_send(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)
        NB: recipientAddress is the address hash derived from the publick key

        const tx = {
            moduleID: 2,
            assetID: 0,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: Buffer.from('68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c', 'hex'),
            asset: {
                amount: BigInt(133700000000),
                recipientAddress: Buffer.from('36642e496362253373f03a7b04978b36e6ae3216', 'hex'),
                data: '',
            }
        }
        """
        tx = "08021000180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c321f0880b29089f2031214453d1100d88c7959610ec3a30e6188f48ac0f7471a00"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "a853c462bd25abcb85170b39f2fc163acb61f04ee7ea1605ccda92ef23bd2a018d3a6f78eb93dc5826b655f1e207b0631e4e6d843509b33039468f8dc389cc0c"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )

    def test_lisk_sign_tx_send_with_data(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)
        NB: recipientAddress is the address hash derived from the publick key

        const tx = {
            moduleID: 2,
            assetID: 0,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: Buffer.from('68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c', 'hex'),
            asset: {
                amount: BigInt(133700000000),
                recipientAddress: Buffer.from('36642e496362253373f03a7b04978b36e6ae3216', 'hex'),
                data: 'hello from trezor!!',
            }
        }
        """
        tx = "08021000180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c32320880b29089f2031214453d1100d88c7959610ec3a30e6188f48ac0f7471a1368656c6c6f2066726f6d207472657a6f722121"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.Other),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "2aa387a293443c9fc2a8e1e11f42f29548d8e84b8a5649f2cd37ac187dd0dfc109a30203fca12deac486e60a35b4607645230576dcd382d929813054dd5cd507"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )

    def test_lisk_sign_tx_delegate_registration(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)

        const tx = {
            moduleID: 5,
            assetID: 0,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: Buffer.from('68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c', 'hex'),
            asset: {
                username: 'hirish_trezor'
            }
        }
        """
        tx = "08051000180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c320f0a0d6869726973685f7472657a6f72"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "16d372fa6f24157338a9244f6e814712ac275df77be0ed7b58b01e495ea389a5096a053373b23aa16d73276c58b05582931b0fee6f78dcb9607ed417498b9307"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )

    def test_lisk_sign_tx_cast_votes(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)
        NB: delegateAddress is the address hash derived from the publick key of the delegate

        const addressHash = Buffer.from('36642e496362253373f03a7b04978b36e6ae3216', 'hex'),
        const tx = {
            moduleID: 5,
            assetID: 1,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: Buffer.from('68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c', 'hex'),
            asset: {
                votes: [
                    { amount: BigInt(100004235000), delegateAddress: addressHash },
                    { amount: BigInt(-100004235000), delegateAddress: addressHash }
                ],
            }
        }
        """
        tx = "08051001180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c323e0a1d0a14453d1100d88c7959610ec3a30e6188f48ac0f74710f09bbc8be9050a1d0a14453d1100d88c7959610ec3a30e6188f48ac0f74710ef9bbc8be905"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "3f6bff7b575dfe0471dd9ac0f330388ce15c0e876a2e9d020a1190bf5d44dbe5843524dc2e54b4be04d30ce9ef924352a1cfcc2ebc1601f61e5925303261ea09"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )

    def test_lisk_sign_tx_unlock_tokens(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)
        NB: delegateAddress is the address hash derived from the publick key of the delegate

        const addressHash = Buffer.from('36642e496362253373f03a7b04978b36e6ae3216', 'hex'),
        const tx = {
            moduleID: 5,
            assetID: 2,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: Buffer.from('68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c', 'hex'),
            asset: {
                unlockObjects: [
                    { amount: BigInt(100004235000), delegateAddress: addressHash, unvoteHeight: 100 },
                    { amount: BigInt(100004235000), delegateAddress: addressHash, unvoteHeight: 100 }
                ],
            }
        }
        """
        tx = "08051002180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c32420a1f0a14453d1100d88c7959610ec3a30e6188f48ac0f74710f88ddec5f40218640a1f0a14453d1100d88c7959610ec3a30e6188f48ac0f74710f88ddec5f4021864"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "eb2e95a4aa4c03a1b1a9271019fec38c30a653d4d47246e2cbb4487c9301059ca626d95379c916f87bb5a5641ad8781a6a8267f66e3e3b93c8e2da1e18752e0c"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )

    def test_lisk_sign_tx_reclaim(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)

        const tx = {
            moduleID: 1000,
            assetID: 0,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: Buffer.from('68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c', 'hex'),
            asset: {
                amount: BigInt(133700000000),
            }
        }
        """
        tx = "08e8071000180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c32070880b29089f203"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "553b2604b01d1b008b03662a4649bc57ae6c65dd407bb60548d3a9a87cc9891e1ff33da00e7eb3b0679d96df8b478791b9ace90b6ffc17767b58e3b211c73e02"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )

    def test_lisk_sign_tx_multisignature(self, client):
        """
        tx is the serialization of this transaction (by using lisk-sdk library in NodeJS)

        const tx = {
            moduleID: 4,
            assetID: 0,
            nonce: BigInt(3),
            fee: BigInt(100000),
            senderPublicKey: newPubKey, // If not provided, it will be set automatically
            asset: {
                numberOfSignatures: 4,
                mandatoryKeys: [
                    Buffer.from(publicKey1, "hex"),
                    Buffer.from(publicKey2, "hex"),
                ],
                optionalKeys: [
                    Buffer.from(publicKeyOpt1, "hex"),
                    Buffer.from(publicKeyOpt2, "hex"),
                ],
            },
        }
        """
        tx = "08041000180320a08d062a2068ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c328a010804122065b616bd60eb9ed63d583a7101c0579b291fd65d3114416db434f5794a12bc88122065b616bd60eb9ed63d583a7101c0579b291fd65d3114416db434f5794a12bc881a2065b616bd60eb9ed63d583a7101c0579b291fd65d3114416db434f5794a12bc881a2065b616bd60eb9ed63d583a7101c0579b291fd65d3114416db434f5794a12bc88"
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.LiskSignedTx(
                        signature=bytes.fromhex(
                            "2766e62060a449fbf89bf27b957c7aebc34ca90b54a49b0ba62a5268b9c9cb490d009872aa23aecad41b8adfa3c9ab96d1e3985102ca1a27ccacd48a4a69ab0c"
                        )
                    ),
                ]
            )

            lisk.sign_tx(
                client, parse_path("m/44'/134'/0'"), NETWORK_ID, bytes.fromhex(tx)
            )
