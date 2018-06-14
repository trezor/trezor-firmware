from common import *

from apps.cardano.cbor import (
    Tagged,
    IndefiniteLengthArray,
    encode
)
from ubinascii import unhexlify

class TestCardanoCbor(unittest.TestCase):
    def test_cbor_encoding(self):
        test_vectors = [
            # integers
            (0, '00'),
            (1, '01'),
            (10, '0a'),
            (23, '17'),
            (24, '1818'),
            (25, '1819'),
            (100, '1864'),
            (1000, '1903e8'),
            (1000000, '1a000f4240'),
            (1000000000000, '1b000000e8d4a51000'),

            # binary strings
            (b'', '40'),
            (unhexlify('01020304'), '4401020304'),

            # tags
            (Tagged(1, 1363896240), 'c11a514b67b0'),
            (Tagged(23, unhexlify('01020304')), 'd74401020304'),

            # arrays
            ([], '80'),
            ([1, 2, 3], '83010203'),
            ([1, [2, 3], [4, 5]], '8301820203820405'),
            (list(range(1, 26)), '98190102030405060708090a0b0c0d0e0f101112131415161718181819'),

            # maps
            ({}, 'a0'),

            # Note: normal python dict doesn't have a fixed item ordering
            ({1: 2, 3: 4}, 'a203040102'),

            # indefinite
            (IndefiniteLengthArray([]), '9fff'),
            (IndefiniteLengthArray([1, [2, 3], [4, 5]]), '9f01820203820405ff'),
            (IndefiniteLengthArray([1, [2, 3], IndefiniteLengthArray([4, 5])]),
             '9f018202039f0405ffff'),
        ]
        for val, expected in test_vectors:
            encoded = encode(val)
            self.assertEqual(unhexlify(expected), encoded)

if __name__ == '__main__':
    unittest.main()
