from common import *

from trezor.crypto import hashlib

from trezor.crypto import hmac


class TestCryptoHmac(unittest.TestCase):

    # vectors from https://tools.ietf.org/html/rfc4231

    def test_digest(self):

        # case 1
        key = b'\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
        msg = b'Hi There'
        self.assertEqual(hmac.new(key, msg, hashlib.sha256).digest(), unhexlify('b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7'))
        self.assertEqual(hmac.new(key, msg, hashlib.sha512).digest(), unhexlify('87aa7cdea5ef619d4ff0b4241a1d6cb02379f4e2ce4ec2787ad0b30545e17cdedaa833b7d6b8a702038b274eaea3f4e4be9d914eeb61f1702e696c203a126854'))

        # case 2
        key = b'Jefe'
        msg = b'what do ya want for nothing?'
        self.assertEqual(hmac.new(key, msg, hashlib.sha256).digest(), unhexlify('5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'))
        self.assertEqual(hmac.new(key, msg, hashlib.sha512).digest(), unhexlify('164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea2505549758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737'))

        # case 3
        key = b'\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa'
        msg = b'\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd'
        self.assertEqual(hmac.new(key, msg, hashlib.sha256).digest(), unhexlify('773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe'))
        self.assertEqual(hmac.new(key, msg, hashlib.sha512).digest(), unhexlify('fa73b0089d56a284efb0f0756c890be9b1b5dbdd8ee81a3655f83e33b2279d39bf3e848279a722c806b485a47e67c807b946a337bee8942674278859e13292fb'))

        # case 4
        key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19'
        msg = b'\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd\xcd'
        self.assertEqual(hmac.new(key, msg, hashlib.sha256).digest(), unhexlify('82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b'))
        self.assertEqual(hmac.new(key, msg, hashlib.sha512).digest(), unhexlify('b0ba465637458c6990e5a8c5f61d4af7e576d97ff94b872de76f8050361ee3dba91ca5c11aa25eb4d679275cc5788063a5f19741120c4f2de2adebeb10a298dd'))

        # case 6
        key = bytes([0xAA] * 131)
        msg = b'Test Using Larger Than Block-Size Key - Hash Key First'
        self.assertEqual(hmac.new(key, msg, hashlib.sha256).digest(), unhexlify('60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54'))
        self.assertEqual(hmac.new(key, msg, hashlib.sha512).digest(), unhexlify('80b24263c7c1a3ebb71493c1dd7be8b49b46d1f41b4aeec1121b013783f8f3526b56d037e05f2598bd0fd2215d6a1e5295e64f73f63f0aec8b915a985d786598'))

        # case 7
        key = bytes([0xAA] * 131)
        msg = b'This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm.'
        self.assertEqual(hmac.new(key, msg, hashlib.sha256).digest(), unhexlify('9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2'))
        self.assertEqual(hmac.new(key, msg, hashlib.sha512).digest(), unhexlify('e37b6a775dc87dbaa4dfa9f96e5e3ffddebd71f8867289865df5a32d20cdc944b6022cac3c4982b10d5eeb55c3e4de15134676fb6de0446065c97440fa8c6a58'))

    def test_update(self):

        # case 3
        key = b'\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa'
        x = hmac.new(key, b'', hashlib.sha256)
        for i in range(50):
            x.update(b'\xdd')
        self.assertEqual(x.digest(), unhexlify('773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe'))
        x = hmac.new(key, b'', hashlib.sha512)
        for i in range(50):
            x.update(b'\xdd')
        self.assertEqual(x.digest(), unhexlify('fa73b0089d56a284efb0f0756c890be9b1b5dbdd8ee81a3655f83e33b2279d39bf3e848279a722c806b485a47e67c807b946a337bee8942674278859e13292fb'))

        # case 4
        key = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19'
        x = hmac.new(key, b'', hashlib.sha256)
        for i in range(50):
            x.update(b'\xcd')
        self.assertEqual(x.digest(), unhexlify('82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b'))
        x = hmac.new(key, b'', hashlib.sha512)
        for i in range(50):
            x.update(b'\xcd')
        self.assertEqual(x.digest(), unhexlify('b0ba465637458c6990e5a8c5f61d4af7e576d97ff94b872de76f8050361ee3dba91ca5c11aa25eb4d679275cc5788063a5f19741120c4f2de2adebeb10a298dd'))

    def test_digest_multi(self):
        x = hmac.new(b'', b'', hashlib.sha256)
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
