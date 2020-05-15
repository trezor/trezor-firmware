from common import *

from apps.bitcoin.sign_tx.omni import is_valid, parse

class TestSignTxOmni(unittest.TestCase):

    def test_is_valid(self):
        VECTORS = {
             "6f6d6e69": False,
             "6f6d6e69000000": False,
             "6f6d6e6900000000": True,
             "6f6d6e69000000000000001f0000000020c85580": True,
             "0f6d6e69000000000000001f0000000020c85580": False,
             "6f6d6e69000000000000001f0000000020c8558000": True,
             "6f6d6e69000000000000001f0000000020c855": True,
        }
        for k, v in VECTORS.items():
            k = unhexlify(k)
            self.assertEqual(is_valid(k), v)

    def test_parse(self):
        VECTORS = {
             "6f6d6e69000000000000001f000000002b752ee0": "Simple send of 7.291 USDT",
             "6f6d6e69000000000000001f0000000020c85580": "Simple send of 5.5 USDT",
             "6f6d6e690000000000000003000000002b752ee0": "Simple send of 729100000 MAID",
             "6f6d6e690000000000000000000000002b752ee0": "Simple send of 729100000 UNKN",
             "6f6d6e6901000000": "Unknown transaction",
        }
        for k, v in VECTORS.items():
            k = unhexlify(k)
            self.assertEqual(parse(k), v)

if __name__ == '__main__':
    unittest.main()
