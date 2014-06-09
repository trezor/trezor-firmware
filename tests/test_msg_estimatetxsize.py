import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException

class TestMsgEstimatetxsize(common.TrezorTest):
    def test_estimate_size(self):
        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             # amount=390000,
                             prev_hash=binascii.unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                             prev_index=0,
                             )

        out1 = proto_types.TxOutputType(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                              amount=390000 - 10000,
                              script_type=proto_types.PAYTOADDRESS,
                              )


        est_size = self.client.estimate_tx_size('Bitcoin', [inp1, ], [out1, ])
        self.assertEqual(est_size, 194)

        (_, tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])
        real_size = len(tx)

        self.assertGreaterEqual(est_size, real_size)

if __name__ == '__main__':
    unittest.main()
