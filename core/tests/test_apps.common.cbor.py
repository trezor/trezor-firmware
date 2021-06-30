import math

from common import *

from apps.common.cbor import (
    IndefiniteLengthArray,
    OrderedMap,
    Tagged,
    create_array_header,
    create_map_header,
    decode,
    encode,
    encode_chunked,
    encode_streamed,
)


class TestCardanoCbor(unittest.TestCase):
    def test_create_array_header(self):
        test_vectors = [
            (0, '80'),
            (23, '97'),
            ((2 ** 8) - 1, '98ff'),
            ((2 ** 16) - 1, '99ffff'),
            ((2 ** 32) - 1, '9affffffff'),
            ((2 ** 64) - 1, '9bffffffffffffffff'),
        ]
        for val, header_hex in test_vectors:
            header = unhexlify(header_hex)
            self.assertEqual(create_array_header(val), header)

        with self.assertRaises(NotImplementedError):
            create_array_header(2 ** 64)

    def test_create_map_header(self):
        test_vectors = [
            (0, 'a0'),
            (23, 'b7'),
            ((2 ** 8) - 1, 'b8ff'),
            ((2 ** 16) - 1, 'b9ffff'),
            ((2 ** 32) - 1, 'baffffffff'),
            ((2 ** 64) - 1, 'bbffffffffffffffff'),
        ]
        for val, header_hex in test_vectors:
            header = unhexlify(header_hex)
            self.assertEqual(create_map_header(val), header)

        with self.assertRaises(NotImplementedError):
            create_map_header(2 ** 64)

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
            ({3: 4, 1: 2}, 'a201020304'),

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
        for val, encoded_hex in test_vectors:
            encoded = unhexlify(encoded_hex)
            self.assertEqual(encode(val), encoded)
            self.assertEqual(decode(encoded), val)

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
        for val, encoded_hex in test_vectors:
            value_tuple = tuple(val)
            encoded = unhexlify(encoded_hex)
            self.assertEqual(encode(value_tuple), encoded)
            self.assertEqual(decode(encoded), val)

    def test_cbor_ordered_map(self):
        """
        OrderedMaps should be encoded as maps without any ordering and decoded back as dicts.
        """
        test_vectors = [
            ({}, 'a0'),
            ([[1, 2], [3, 4]], 'a201020304'),
            ([[3, 4], [1, 2]], 'a203040102'),
        ]

        for val, encoded_hex in test_vectors:
            ordered_map = OrderedMap()
            for key, value in val:
                ordered_map[key] = value

            encoded = unhexlify(encoded_hex)
            self.assertEqual(encode(ordered_map), encoded)
            self.assertEqual(decode(encoded), {k: v for k, v in val})

    def test_encode_streamed(self):
        large_dict = {i: i for i in range(100)}
        encoded = encode(large_dict)

        encoded_streamed = [
            bytes(item) for item in encode_streamed(large_dict)
        ]

        self.assertEqual(b''.join(encoded_streamed), encoded)

    def test_encode_chunked(self):
        large_dict = {i: i for i in range(100)}
        encoded = encode(large_dict)

        encoded_len = len(encoded)
        assert encoded_len == 354

        arbitrary_encoded_len_factor = 59
        arbitrary_power_of_two = 64
        larger_than_encoded_len = encoded_len + 1

        for max_chunk_size in [
            1,
            10,
            arbitrary_encoded_len_factor,
            arbitrary_power_of_two,
            encoded_len,
            larger_than_encoded_len
        ]:
            encoded_chunks = [
                bytes(chunk) for chunk in encode_chunked(large_dict, max_chunk_size)
            ]

            expected_number_of_chunks = math.ceil(len(encoded) / max_chunk_size)
            self.assertEqual(len(encoded_chunks), expected_number_of_chunks)

            # all chunks except the last should be of chunk_size
            for i in range(len(encoded_chunks) - 1):
                self.assertEqual(len(encoded_chunks[i]), max_chunk_size)

            # last chunk should contain the remaining bytes or the whole chunk
            remaining_bytes = len(encoded) % max_chunk_size
            expected_last_chunk_size = remaining_bytes if remaining_bytes > 0 else max_chunk_size
            self.assertEqual(len(encoded_chunks[-1]), expected_last_chunk_size)

            self.assertEqual(b''.join(encoded_chunks), encoded)


if __name__ == '__main__':
    unittest.main()
