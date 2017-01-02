import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException
from trezorlib.tx_api import TxApiTestnet

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
                              #address_n=self.client.expand_path("49'/1'/0'/1/0"),
                              #script_type=proto_types.PAYTOP2SHWITNESS,
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
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1, ], [out1, out2 ])

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
                              #address_n=self.client.expand_path("49'/1'/0'/1/0"),
                              #script_type=proto_types.PAYTOWITNESS,
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
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1, ], [out1, out2 ])

        self.assertEqual(binascii.hexlify(serialized_tx), b'010000000001018a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f502483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000')


if __name__ == '__main__':
    unittest.main()
