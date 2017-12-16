from common import *

from trezor.crypto.aes import *


class TestCryptoAes(unittest.TestCase):

    # vectors from https://github.com/ricmoo/pyaes
    key = b'This_key_for_demo_purposes_only!'
    iv = b'InitializationVe'

    def test_ecb(self):
        a = AES_ECB_Encrypt(key=self.key)
        plain = b'TextMustBe16Byte'
        e = a.update(plain)
        self.assertEqual(e, b'L6\x95\x85\xe4\xd9\xf1\x8a\xfb\xe5\x94X\x80|\x19\xc3')
        a = AES_ECB_Decrypt(key=self.key)
        d = a.update(e)
        self.assertEqual(d, plain)

    def test_cbc(self):
        a = AES_CBC_Encrypt(key=self.key, iv=self.iv)
        plain = b'TextMustBe16Byte'
        e = a.update(plain)
        self.assertEqual(e, b'\xd6:\x18\xe6\xb1\xb3\xc3\xdc\x87\xdf\xa7|\x08{k\xb6')
        a = AES_CBC_Decrypt(key=self.key, iv=self.iv)
        d = a.update(e)
        self.assertEqual(d, plain)

    def test_cfb(self):
        a = AES_CFB_Encrypt(key=self.key, iv=self.iv)
        plain = b'TextMustBeAMultipleOfSegmentSize'
        e = a.update(plain)
        self.assertEqual(e, b'v\xa9\xc1w"\x8aL\x93oU:\x9a\xa5\xa0\x90k\x1a/\xb4\\U\xc3>\xffh\x08\xe5\xac\'\xc4\xcfv')
        a = AES_CFB_Decrypt(key=self.key, iv=self.iv)
        d = a.update(e)
        self.assertEqual(d, plain)

    def test_ofb(self):
        a = AES_OFB_Encrypt(key=self.key, iv=self.iv)
        plain = b'Text may be any length you wish, no padding is required'
        e = a.update(plain)
        self.assertEqual(e, b'v\xa9\xc1wO\x92^\x9e\rR\x1e\xf7\xb1\xa2\x9d"l1\xc7\xe7\x9d\x87(\xc26s\xdd8\xc8@\xb6\xd9!\xf5\x0cM\xaa\x9b\xc4\xedLD\xe4\xb9\xd8\xdf\x9e\xac\xa1\xb8\xea\x0f\x8ev\xb5')
        a = AES_OFB_Decrypt(key=self.key, iv=self.iv)
        d = a.update(e)
        self.assertEqual(d, plain)

    def test_ctr(self):
        a = AES_CTR_Encrypt(key=self.key)
        plain = b'Text may be any length you wish, no padding is required'
        e = a.update(plain)
        self.assertEqual(e, b'1\xac\xd9d\xbaM\x8b\xf3I\xac\xce]\x8e\xac\xd8B\x8e\x99\x06.\xf0\x93\xc9\xd1\xc6\x0b*\xb1\x15\xf2*\x1dO\xe8\xef\xeeR63D\xb9~\x8a\x18\xe3\xdf\xd5\x08\\\xfa\x97"\x9dl\xb8')
        a = AES_CTR_Decrypt(key=self.key)
        d = a.update(e)
        self.assertEqual(d, plain)


if __name__ == '__main__':
    unittest.main()
