import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException
from trezorlib.tx_api import TXAPIZcashTestnet

class TestMsgSigntx(common.TrezorTest):

    def test_one_one_fee(self):
        self.setup_mnemonic_allallall()

        # tx: 83fc9d26e90ed70f161cbd4b6af6c4cf5d27525dedd5477d054b9a4935cf01d9
        # input 0: 2.1 TAZ

        inp1 = proto_types.TxInputType(address_n=[2147483692, 2147483649, 2147483648, 0, 0],  # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
                             # amount=210000000,
                             prev_hash=binascii.unhexlify(b'83fc9d26e90ed70f161cbd4b6af6c4cf5d27525dedd5477d054b9a4935cf01d9'),
                             prev_index=0,
                             )

        out1 = proto_types.TxOutputType(address='tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z',
                              amount=210000000 - 1940,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        with self.client:
            self.client.set_tx_api(TXAPIZcashTestnet())
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXMETA, details=proto_types.TxRequestDetailsType(tx_hash=binascii.unhexlify(b"83fc9d26e90ed70f161cbd4b6af6c4cf5d27525dedd5477d054b9a4935cf01d9"))),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=binascii.unhexlify(b"83fc9d26e90ed70f161cbd4b6af6c4cf5d27525dedd5477d054b9a4935cf01d9"))),
                proto.TxRequest(request_type=proto_types.TXEXTRADATA, details=proto_types.TxRequestDetailsType(tx_hash=binascii.unhexlify(b"83fc9d26e90ed70f161cbd4b6af6c4cf5d27525dedd5477d054b9a4935cf01d9"),extra_data_offset=0, extra_data_len=1024)),
                proto.TxRequest(request_type=proto_types.TXEXTRADATA, details=proto_types.TxRequestDetailsType(tx_hash=binascii.unhexlify(b"83fc9d26e90ed70f161cbd4b6af6c4cf5d27525dedd5477d054b9a4935cf01d9"),extra_data_offset=1024, extra_data_len=875)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])

            (signatures, serialized_tx) = self.client.sign_tx('Zcash Testnet', [inp1, ], [out1, ])

        self.assertEqual(len(signatures), 1)
        self.assertEqual(binascii.hexlify(signatures[0]), b'3045022100adb008fb056919eeeb61285689048333a0e782208a04d84d1b7bd5eb42f231d6022064a0c903723025d52ee664354b048127d076a68c77d459d1b822168b6db241e6')

        # Accepted by network: tx 1c2a9faa81403643b8d17de905db64bb9c6e50a49ac9cc5688588d676efd5687
        self.assertEqual(binascii.hexlify(serialized_tx), b'0100000001d901cf35499a4b057d47d5ed5d52275dcfc4f66a4bbd1c160fd70ee9269dfc83000000006b483045022100adb008fb056919eeeb61285689048333a0e782208a04d84d1b7bd5eb42f231d6022064a0c903723025d52ee664354b048127d076a68c77d459d1b822168b6db241e60121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff01ec50840c000000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac00000000')

if __name__ == '__main__':
    unittest.main()
