from common import *

from trezor.crypto import crc


class TestCryptoCrc(unittest.TestCase):

    vectors_crc32 = [
        ('123456789', 0xCBF43926),
        (unhexlify('0000000000000000000000000000000000000000000000000000000000000000'), 0x190A55AD),
        (unhexlify('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'), 0xFF6CAB0B),
        (unhexlify('000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F'), 0x91267E8A),
        ('The quick brown fox jumps over the lazy dog', 0x414FA339),
    ]

    def test_crc32(self):
        for i, o in self.vectors_crc32:
            self.assertEqual(crc.crc32(i), o)


if __name__ == '__main__':
    unittest.main()
