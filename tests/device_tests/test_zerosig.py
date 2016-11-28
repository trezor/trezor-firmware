from __future__ import print_function

import unittest
import common
import binascii
import sys

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types

if sys.version_info < (3,):
    def byteindex(data, index):
        return ord(data[index])
else:
    byteindex = lambda data, index: data[index]

# address_n = [177] < 68
# address_n = [16518] < 66
class TestZeroSig(common.TrezorTest):

    '''
    def test_mine_zero_signature(self):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             # amount=390000,
                             prev_hash=binascii.unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                             prev_index=0,
                             )

        msg = self.client._prepare_sign_tx('Bitcoin', [inp1, ], [])

        for n in range(3500, 200000):
            out1 = proto_types.TxOutputType(address_n=[n],
                                  amount=390000 - 10000,
                                  script_type=proto_types.PAYTOADDRESS,
                                  )
            msg.ClearField('outputs')
            msg.outputs.extend([out1, ])

            tx = self.client.call(msg)

            siglen = byteindex(tx.serialized_tx, 44)
            print(siglen)
            if siglen < 67:
                print("!!!!", n)
                print(binascii.hexlify(tx.serialized_tx))
                return
    '''

    def test_one_zero_signature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             # amount=390000,
                             prev_hash=binascii.unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                             prev_index=0,
                             )

        # Following address_n has been mined by 'test_mine_zero_signature'
        out1 = proto_types.TxOutputType(address_n=[177],
                              amount=390000 - 10000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])
        siglen = byteindex(serialized_tx, 44)

        # TREZOR must strip leading zero from signature
        self.assertEqual(siglen, 67)

    def test_two_zero_signature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             # amount=390000,
                             prev_hash=binascii.unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                             prev_index=0,
                             )

        # Following address_n has been mined by 'test_mine_zero_signature'
        out1 = proto_types.TxOutputType(address_n=[16518],
                              amount=390000 - 10000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])
        siglen = byteindex(serialized_tx, 44)

        # TREZOR must strip leading zero from signature
        self.assertEqual(siglen, 66)

if __name__ == '__main__':
    unittest.main()
