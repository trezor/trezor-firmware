from common import *

from apps.common.cbor import (
    Tagged,
    IndefiniteLengthArray,
    decode,
    encode,
)

class TestCardanoCbor(unittest.TestCase):
    def test_cbor_encoding(self):
        test_vectors = [
            # unsigned integers
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

            # negative integers
            (-1, '20'),
            (-10, '29'),
            (-24, '37'),
            (-25, '3818'),
            (-26, '3819'),
            (-100, '3863'),
            (-1000, '3903E7'),
            (-1000000, '3A000F423F'),
            (-1000000000000, '3B000000E8D4A50FFF'),

            # binary strings
            (b'', '40'),
            (unhexlify('01020304'), '4401020304'),

            # text strings
            ('', '60'),
            ('Fun', '6346756e'),
            (u'P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f', '786550c599c3adc5a165726ec49b20c5be6c75c5a56f75c48d6bc3bd206bc5afc58820c3ba70c49b6c20c48fc3a162656c736bc3a920c3b36479207ac3a16b65c5996ec3bd2075c48d65c5882062c49bc5bec3ad20706f64c3a96c207ac3b36e7920c3ba6cc5af'),

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
            ({1: 2, 3: 4}, 'a201020304'),

            # indefinite
            (IndefiniteLengthArray([]), '9fff'),
            (IndefiniteLengthArray([1, [2, 3], [4, 5]]), '9f01820203820405ff'),
            (IndefiniteLengthArray([1, [2, 3], IndefiniteLengthArray([4, 5])]),
             '9f018202039f0405ffff'),

            # boolean
            (True, 'f5'),
            (False, 'f4'),

            # null
            (None, 'f6'),
        ]
        for val, encoded in test_vectors:
            self.assertEqual(unhexlify(encoded), encode(val))
            self.assertEqual(val, decode(unhexlify(encoded)))

    def test_cbor_tuples(self):
        """
        Tuples should be encoded as arrays and decoded back as lists.
        """
        test_vectors = [
            ([], '80'),
            ([1, 2, 3], '83010203'),
            ([1, [2, 3], [4, 5]], '8301820203820405'),
            (list(range(1, 26)), '98190102030405060708090a0b0c0d0e0f101112131415161718181819'),
        ]
        for val, encoded in test_vectors:
            value_tuple = tuple(val)
            self.assertEqual(unhexlify(encoded), encode(value_tuple))
            self.assertEqual(val, decode(unhexlify(encoded)))

if __name__ == '__main__':
    unittest.main()
