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
        out1 = proto_types.TxOutputType(address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
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

        self.assertEqual(binascii.hexlify(serialized_tx), b'0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000')

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
        out1 = proto_types.TxOutputType(address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
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

        self.assertEqual(binascii.hexlify(serialized_tx), b'0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000')

    def test_send_multisig_1(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        nodes = map(lambda index : self.client.get_public_node(self.client.expand_path("999'/1'/%d'" % index)), range(1,4))
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

        out1 = proto_types.TxOutputType(address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
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

        self.assertEqual(binascii.hexlify(serialized_tx), b'01000000000101be0210025c5be68a473f6a38bf53b53bc88d5c46567616026dc056e72b92319c01000000232200201e8dda334f11171190b3da72e526d441491464769679a319a2f011da5ad312a1ffffffff01887d1800000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac040047304402205b44c20cf2681690edaaf7cd2e30d4704124dd8b7eb1fb7f459d3906c3c374a602205ca359b6544ce2c101c979899c782f7d141c3b0454ea69202b1fb4c09d3b715701473044022052fafa64022554ae436dbf781e550bf0d326fef31eea1438350b3ff1940a180102202851bd19203b7fe8582a9ef52e82aa9f61cd52d4bcedfe6dcc0cf782468e6a8e01695221038e81669c085a5846e68e03875113ddb339ecbb7cb11376d4163bca5dc2e2a0c1210348c5c3be9f0e6cf1954ded1c0475beccc4d26aaa9d0cce2dd902538ff1018a112103931140ebe0fbbb7df0be04ed032a54e9589e30339ba7bbb8b0b71b15df1294da53ae00000000')

if __name__ == '__main__':
    unittest.main()
