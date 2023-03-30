from common import *

from trezor.crypto import hashlib


class TestCryptoBlake2s(unittest.TestCase):

    # vectors from https://raw.githubusercontent.com/BLAKE2/BLAKE2/master/testvectors/blake2s-kat.txt

    vectors = [
        ('', '48a8997da407876b3d79c0d92325ad3b89cbb754d86ab71aee047ad345fd2c49'),
        ('00', '40d15fee7c328830166ac3f918650f807e7e01e177258cdc0a39b11f598066f1'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e', 'b6156f72d380ee9ea6acd190464f2307a5c179ef01fd71f99f2d0f7a57360aea'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20', '2c3e08176f760c6264c3a2cd66fec6c3d78de43fc192457b2a4a660a1e0eb22b'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f4041', '2ef73f3c26f12d93889f3c78b6a66c1d52b649dc9e856e2c172ea7c58ac2b5e3'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f60', '288c4ad9b9409762ea07c24a41f04f69a7d74bee2d95435374bde946d7241c7b'),
    ]

    def test_digest(self):
        key = unhexlify('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f')
        for d, h in self.vectors:
            self.assertEqual(hashlib.blake2s(unhexlify(d), key=key).digest(), unhexlify(h))

    def test_update(self):
        key = unhexlify('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f')
        x = hashlib.blake2s(b'', key=key)
        x.update(bytes(range(10)))
        self.assertEqual(x.digest(), unhexlify('f5c4b2ba1a00781b13aba0425242c69cb1552f3f71a9a3bb22b4a6b4277b46dd'))
        x.update(bytes(range(10, 30)))
        self.assertEqual(x.digest(), unhexlify('3ca989de10cfe609909472c8d35610805b2f977734cf652cc64b3bfc882d5d89'))
        x.update(bytes(range(30, 80)))
        self.assertEqual(x.digest(), unhexlify('30f3548370cfdceda5c37b569b6175e799eef1a62aaa943245ae7669c227a7b5'))
        x.update(bytes(range(80, 111)))
        self.assertEqual(x.digest(), unhexlify('9fe03bbe69ab1834f5219b0da88a08b30a66c5913f0151963c360560db0387b3'))
        x.update(bytes(range(111, 127)))
        self.assertEqual(x.digest(), unhexlify('ddbfea75cc467882eb3483ce5e2e756a4f4701b76b445519e89f22d60fa86e06'))
        x.update(bytes(range(127, 255)))
        self.assertEqual(x.digest(), unhexlify('3fb735061abc519dfe979e54c1ee5bfad0a9d858b3315bad34bde999efd724dd'))

    def test_digest_multi(self):
        x = hashlib.blake2s()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
