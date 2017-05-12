# This file is part of the TREZOR project.
#
# Copyright (C) 2017 Jochen Hoenicke <hoenicke@gmail.com>
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

import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException
from trezorlib.tx_api import TxApiTestnet
from trezorlib.ckd_public import deserialize

class TestMsgSigntxSegwit(common.TrezorTest):
    def test_send_p2sh(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("49'/1'/0'/1/0"),
                             # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
                             amount=123456789,
                             prev_hash=binascii.unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                             prev_index=0,
                             script_type=proto_types.SPENDP2SHWITNESS,
                             )
        out1 = proto_types.TxOutputType(address='QWywnqNMsMNavbCgMYiQLa91ApvsVRoaqt1i',
                              amount=12300000,
                              script_type=proto_types.PAYTOADDRESS,
                              )
        out2 = proto_types.TxOutputType(
                              address='2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX',
                              script_type=proto_types.PAYTOADDRESS,
                              amount=123456789 - 11000 - 12300000,
                              )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1, out2])

        self.assertEqual(binascii.hexlify(serialized_tx), b'0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100bd3d8b8ad35c094e01f6282277300e575f1021678fc63ec3f9945d6e35670da3022052e26ef0dd5f3741c9d5939d1dec5464c15ab5f2c85245e70a622df250d4eb7c012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000')

    def test_send_p2sh_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("49'/1'/0'/1/0"),
                             # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
                             amount=123456789,
                             prev_hash=binascii.unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                             prev_index=0,
                             script_type=proto_types.SPENDP2SHWITNESS,
                             )
        out1 = proto_types.TxOutputType(address='QWywnqNMsMNavbCgMYiQLa91ApvsVRoaqt1i',
                              amount=12300000,
                              script_type=proto_types.PAYTOADDRESS,
                              )
        out2 = proto_types.TxOutputType(
                              address_n=self.client.expand_path("49'/1'/0'/1/0"),
                              script_type=proto_types.PAYTOP2SHWITNESS,
                              amount=123456789 - 11000 - 12300000,
                              )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1, out2])

        self.assertEqual(binascii.hexlify(serialized_tx), b'0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100bd3d8b8ad35c094e01f6282277300e575f1021678fc63ec3f9945d6e35670da3022052e26ef0dd5f3741c9d5939d1dec5464c15ab5f2c85245e70a622df250d4eb7c012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000')

    def test_send_native(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("49'/1'/0'/0/0"),
                             # QWywnqNMsMNavbCgMYiQLa91ApvsVRoaqt1i
                             amount=12300000,
                             prev_hash=binascii.unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
                             prev_index=0,
                             script_type=proto_types.SPENDWITNESS,
                             )
        out1 = proto_types.TxOutputType(address='2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp',
                             amount=5000000,
                             script_type=proto_types.PAYTOADDRESS,
                             )
        out2 = proto_types.TxOutputType(
                              address='QWzGpyMkAEvmkSVprBzRRVQMP6UPp17q4kQn',
                              script_type=proto_types.PAYTOADDRESS,
                              amount=12300000 - 11000 - 5000000,
                              )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1, out2 ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'010000000001018a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f502483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000')

    def test_send_native_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("49'/1'/0'/0/0"),
                             # QWywnqNMsMNavbCgMYiQLa91ApvsVRoaqt1i
                             amount=12300000,
                             prev_hash=binascii.unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
                             prev_index=0,
                             script_type=proto_types.SPENDWITNESS,
                             )
        out1 = proto_types.TxOutputType(address='2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp',
                             amount=5000000,
                             script_type=proto_types.PAYTOADDRESS,
                             )
        out2 = proto_types.TxOutputType(
                              address_n=self.client.expand_path("49'/1'/0'/1/0"),
                              script_type=proto_types.PAYTOWITNESS,
                              amount=12300000 - 11000 - 5000000,
                              )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1, out2 ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'010000000001018a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f502483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000')

    def test_send_both(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("49'/1'/0'/1/0"),
                             # 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
                             amount=111145789,
                             prev_hash=binascii.unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
                             prev_index=1,
                             script_type=proto_types.SPENDP2SHWITNESS,
                             )
        inp2 = proto_types.TxInputType(address_n=self.client.expand_path("49'/1'/0'/1/0"),
                             # QWzGpyMkAEvmkSVprBzRRVQMP6UPp17q4kQn
                             amount=7289000,
                             prev_hash=binascii.unhexlify('65b811d3eca0fe6915d9f2d77c86c5a7f19bf66b1b1253c2c51cb4ae5f0c017b'),
                             prev_index=1,
                             script_type=proto_types.SPENDWITNESS,
                             )
        out1 = proto_types.TxOutputType(address='QWzCpc1NeTN7hNDzK9sQQ9yrTQP8zh5Hef5J',
                              amount=12300000,
                              script_type=proto_types.PAYTOADDRESS,
                              )
        out2 = proto_types.TxOutputType(
                              #address_n=self.client.expand_path("44'/1'/0'/0/0"),
                              #script_type=proto_types.PAYTOP2SHWITNESS,
                              address='2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc',
                              script_type=proto_types.PAYTOADDRESS,
                              amount=45600000,
                              )
        out3 = proto_types.TxOutputType(address='mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q',
                              amount=111145789 + 7289000 - 11000 - 12300000 - 45600000,
                              script_type=proto_types.PAYTOADDRESS,
                              )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=2)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=2)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1, inp2], [out1, out2, out3 ])

        # 0e480a97c7a545c85e101a2f13c9af0e115d43734e1448f0cac3e55fe8e7399d
        self.assertEqual(binascii.hexlify(serialized_tx), b'010000000001028a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090100000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff7b010c5faeb41cc5c253121b6bf69bf1a7c5867cd7f2d91569fea0ecd311b8650100000000ffffffff03e0aebb0000000000160014a579388225827d9f2fe9014add644487808c695d00cdb7020000000017a91491233e24a9bf8dbb19c1187ad876a9380c12e787870d859b03000000001976a914a579388225827d9f2fe9014add644487808c695d88ac02483045022100ead79ee134f25bb585b48aee6284a4bb14e07f03cc130253e83450d095515e5202201e161e9402c8b26b666f2b67e5b668a404ef7e57858ae9a6a68c3837e65fdc69012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7902483045022100b4099ec4c7b3123795b3c080a86f4b745f3784eb3f77de79bef1d8da319cbee5022039766865d448a4a3e435a95d0df3ff56ebc6532bf538988a7e8a679b40ec41b6012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000')

    def test_send_multisig_1(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        nodes = map(lambda index : self.client.get_public_node(self.client.expand_path("999'/1'/"+str(index)+"'")), range(1,4))
        multisig = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=deserialize(n.xpub), address_n=[2,0]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )

        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("999'/1'/1'/2/0"),
                                       prev_hash=binascii.unhexlify('9c31922be756c06d02167656465c8dc83bb553bf386a3f478ae65b5c021002be'),
                                       prev_index=1,
                                       script_type=proto_types.SPENDP2SHWITNESS,
                                       multisig=multisig,
                                       amount=1610436
        )

        out1 = proto_types.TxOutputType(address='T7nZJt6QbGJy6Hok4EF2LqtJPcT7z7VFSrSysGS3tEqCfDPwizqy4',
                                        amount=1605000,
                                        script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures1, _) = self.client.sign_tx('Testnet', [inp1], [out1 ])
            # store signature
            inp1.multisig.signatures[0] = signatures1[0]
            # sign with third key
            inp1.address_n[2] = 0x80000003
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures2, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1 ])

        # f41cbedd8becee05a830f418d13aa665125464547db5c7a6cd28f21639fe1228
        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000000101be0210025c5be68a473f6a38bf53b53bc88d5c46567616026dc056e72b92319c01000000232200201e8dda334f11171190b3da72e526d441491464769679a319a2f011da5ad312a1ffffffff01887d180000000000220020c5f4a0a4ea7c0392efe0a9670a73264cffa90b19107cd8a8e9750ff93c77fdfb0400483045022100a9b681f324ff4cf419ab06820d07248cc4e359c77334bf448ae7b5cdf3995ddf022039811f91f55b602368b4ba08a217b82bfd62d1a97dc635deb1457e7cfcc1550b0147304402201ad86a795c3d26881d696fa0a0619c24c4d505718132a82965cc2a609c9d8798022067cd490ce1366cde77e307ced5b13040bbc04991619ea6f49e06cece9a83268b01695221038e81669c085a5846e68e03875113ddb339ecbb7cb11376d4163bca5dc2e2a0c1210348c5c3be9f0e6cf1954ded1c0475beccc4d26aaa9d0cce2dd902538ff1018a112103931140ebe0fbbb7df0be04ed032a54e9589e30339ba7bbb8b0b71b15df1294da53ae00000000')

    def test_send_multisig_2(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        nodes = map(lambda index : self.client.get_public_node(self.client.expand_path("999'/1'/"+str(index)+"'")), range(1,4))
        multisig = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=deserialize(n.xpub), address_n=[2,1]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )

        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("999'/1'/2'/2/1"),
                                       prev_hash=binascii.unhexlify('f41cbedd8becee05a830f418d13aa665125464547db5c7a6cd28f21639fe1228'),
                                       prev_index=0,
                                       script_type=proto_types.SPENDWITNESS,
                                       multisig=multisig,
                                       amount=1605000
        )

        out1 = proto_types.TxOutputType(address='T7nY3A3kewpDKumsdhonP4TBDfTXFSc2RNhZxkqmeeszRDHjM5yUn',
                                        amount=1604000,
                                        script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures1, _) = self.client.sign_tx('Testnet', [inp1], [out1 ])
            # store signature
            inp1.multisig.signatures[1] = signatures1[0]
            # sign with first key
            inp1.address_n[2] = 0x80000001
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures2, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1 ])

        # c9348040bbc2024e12dcb4a0b4806b0398646b91acf314da028c3f03dd0179fc
        self.assertEqual(binascii.hexlify(serialized_tx), b'010000000001012812fe3916f228cda6c7b57d5464541265a63ad118f430a805eeec8bddbe1cf40000000000ffffffff01a0791800000000002200201e8dda334f11171190b3da72e526d441491464769679a319a2f011da5ad312a10400483045022100cc97f21a7cabc543a9b4ac52424e8f7e420622903f2417a1c08a6af68058ec4a02200baca0b222fc825078d94e8e1b55f174c4828bed16697e4281cda2a0c799eecf01473044022009b8058dc30fa7a13310dd8f1a99c4341c4cd95f771c5a41c4381f956e2344c102205e829c560c0184fd4b4db8971f99711e2a87409afa4df0840b4f12a87b2c8afc0169522102740ec30d0af8591a0dd4a3e3b274e57f3f73bdc0638a9603f9ee6ade0475ba57210311aada919974e882abf0c67b5c0fba00000b26997312ca00345027d22359443021029382591271a79d4b12365fa27c67fad3753150d8eaa987e5a12dc5ba1bb2fa1653ae00000000')

    def test_send_multisig_3_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        nodes = map(lambda index : self.client.get_public_node(self.client.expand_path("999'/1'/"+str(index)+"'")), range(1,4))
        multisig = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=deserialize(n.xpub), address_n=[2,0]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )
        multisig2 = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=deserialize(n.xpub), address_n=[1,1]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )

        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("999'/1'/1'/2/0"),
                                       prev_hash=binascii.unhexlify('c9348040bbc2024e12dcb4a0b4806b0398646b91acf314da028c3f03dd0179fc'),
                                       prev_index=0,
                                       script_type=proto_types.SPENDWITNESS,
                                       multisig=multisig,
                                       amount=1604000
        )

        out1 = proto_types.TxOutputType(address_n=self.client.expand_path("999'/1'/1'/1/1"),
                                        amount=1603000,
                                        multisig=multisig2,
                                        script_type=proto_types.PAYTOP2SHWITNESS)

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures1, _) = self.client.sign_tx('Testnet', [inp1], [out1 ])
            # store signature
            inp1.multisig.signatures[0] = signatures1[0]
            # sign with third key
            inp1.address_n[2] = 0x80000003
            out1.address_n[2] = 0x80000003
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures2, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1 ])

        # 31bc1c88ce6ae337a6b3057a16d5bad0b561ad1dfc047d0a7fbb8814668f91e5
        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000000101fc7901dd033f8c02da14f3ac916b6498036b80b4a0b4dc124e02c2bb408034c90000000000ffffffff01b87518000000000017a914a8655acf68f785125561158b0f4db9b5d0044047870400473044022057b571986c07f8ccb231811334ad06ee6f87b722495def2e9511c1da46f3433202207b6e95bdd99e7fc7d319486437cb930d40a4af3cd753c4cb960b330badbf7f35014730440220517ecc6d0a2544276921d8fc2077aec4285ab83b1b21f5eb73cdb6187a0583e4022043fb5ab942f8981c04a54c66a57c4d291fad8514d4a8afea09f01f2db7a8f32901695221038e81669c085a5846e68e03875113ddb339ecbb7cb11376d4163bca5dc2e2a0c1210348c5c3be9f0e6cf1954ded1c0475beccc4d26aaa9d0cce2dd902538ff1018a112103931140ebe0fbbb7df0be04ed032a54e9589e30339ba7bbb8b0b71b15df1294da53ae00000000')

    def test_send_multisig_4_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        nodes = map(lambda index : self.client.get_public_node(self.client.expand_path("999'/1'/"+str(index)+"'")), range(1,4))
        multisig = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=deserialize(n.xpub), address_n=[1,1]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )
        multisig2 = proto_types.MultisigRedeemScriptType(
            pubkeys=map(lambda n : proto_types.HDNodePathType(node=deserialize(n.xpub), address_n=[1,2]), nodes),
            signatures=[b'', b'', b''],
            m=2,
        )

        inp1 = proto_types.TxInputType(address_n=self.client.expand_path("999'/1'/1'/1/1"),
                                       prev_hash=binascii.unhexlify('31bc1c88ce6ae337a6b3057a16d5bad0b561ad1dfc047d0a7fbb8814668f91e5'),
                                       prev_index=0,
                                       script_type=proto_types.SPENDP2SHWITNESS,
                                       multisig=multisig,
                                       amount=1603000
        )

        out1 = proto_types.TxOutputType(address_n=self.client.expand_path("999'/1'/1'/1/2"),
                                        amount=1602000,
                                        multisig=multisig2,
                                        script_type=proto_types.PAYTOWITNESS)

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures1, _) = self.client.sign_tx('Testnet', [inp1], [out1 ])
            # store signature
            inp1.multisig.signatures[0] = signatures1[0]
            # sign with third key
            inp1.address_n[2] = 0x80000003
            out1.address_n[2] = 0x80000003
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures2, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1 ])

        # c0bf56060a109624b4635222696d94a7d533cacea1b3f8245417a4348c045829
        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000000101e5918f661488bb7f0a7d04fc1dad61b5d0bad5167a05b3a637e36ace881cbc3100000000232200205b9824093eaf5cdcf8247c00dc0b557a7720957828fcde8384ac11f80a91f403ffffffff01d071180000000000220020e77caf5fbef07b1e461475c02afd4aed877693263d69c81e14617304349b629a040047304402204832553b0da1009da496881e58e8e2e41010cfe5c0161623048093f1b1a817b7022020dad8bf887acf574af80bfe4b39cd24e95019fd5e6b8ae967471e21ddc67354014830450221009e5d60847e7275edcf4619ed8ee462c56a042eef75d17da2d44e6b13d78e50e50220665195492900ef87a5eb8a924fa0ac9afc4fc75ca704ff356dc3a213979970c80169522103f4040006e3561b3e76c6d4113225c84748ab9d55ffd23f9578ab4c18fb0c3b9721020975f2e6922897ff6b80da6412a8d6ebd67e33c9611d081656a53ef967964e5021026b0546f23a6ce6b756c2c30b4176ce6f1c3268744f7aca82668d5116c4f764e453ae00000000')

if __name__ == '__main__':
    unittest.main()
