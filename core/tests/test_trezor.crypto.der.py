from common import *

from trezor.crypto import der


class TestCryptoDer(unittest.TestCase):

    vectors_seq = [
        (('9a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b70771',
          '2b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede781'),
         '30450221009a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b7077102202b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede781'),

        (('6666666666666666666666666666666666666666666666666666666666666666',
          '7777777777777777777777777777777777777777777777777777777777777777'),
         '30440220666666666666666666666666666666666666666666666666666666666666666602207777777777777777777777777777777777777777777777777777777777777777'),

        (('6666666666666666666666666666666666666666666666666666666666666666',
          'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'),
         '304502206666666666666666666666666666666666666666666666666666666666666666022100eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'),

        (('eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
          '7777777777777777777777777777777777777777777777777777777777777777'),
         '3045022100eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee02207777777777777777777777777777777777777777777777777777777777777777'),

        (('eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
          'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),
         '3046022100eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee022100ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),

        (('0000000000000000000000000000000000000000000000000000000000000066',
          '0000000000000000000000000000000000000000000000000000000000000077'),
         '3006020166020177'),

        (('0000000000000000000000000000000000000000000000000000000000000066',
          '00000000000000000000000000000000000000000000000000000000000000ee'),
         '3007020166020200ee'),

        (('00000000000000000000000000000000000000000000000000000000000000ee',
          '0000000000000000000000000000000000000000000000000000000000000077'),
         '3007020200ee020177'),

        (('00000000000000000000000000000000000000000000000000000000000000ee',
          '00000000000000000000000000000000000000000000000000000000000000ff'),
         '3008020200ee020200ff'),
    ]

    def test_der_encode_seq(self):

        for s, d in self.vectors_seq:
            s = tuple(unhexlify(i) for i in s)
            d = unhexlify(d)
            d2 = der.encode_seq(s)
            self.assertEqual(d2, d)
            s = [i.lstrip(b"\x00") for i in s]
            s2 = der.decode_seq(d)
            self.assertEqual(s2, s)

    def test_der_encode_decode_long_seq(self):
        for length in (1, 127, 128, 129, 255, 256, 257):
            raw_int = bytes((i & 0xfe) + 1 for i in range(length))
            for leading_zeros in range(3):
                encoded = der.encode_seq((b"\x00" * leading_zeros + raw_int,))
                decoded = der.decode_seq(encoded)
                self.assertEqual(decoded, [raw_int])

        for zeroes in range(3):
            encoded = der.encode_seq((b"\x00" * zeroes,))
            decoded = der.decode_seq(encoded)
            self.assertEqual(decoded, [b"\x00"])

if __name__ == '__main__':
    unittest.main()
