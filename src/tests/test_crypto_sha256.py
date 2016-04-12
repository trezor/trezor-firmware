import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
import trezor.utils

import trezor.crypto.sha256

class TestCryptoSha256(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html
    def test_hash(self):
        self.assertEqual(trezor.crypto.sha256.hash(b''), trezor.utils.unhexlify('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))
        self.assertEqual(trezor.crypto.sha256.hash(b'abc'), trezor.utils.unhexlify('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'))
        self.assertEqual(trezor.crypto.sha256.hash(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'), trezor.utils.unhexlify('248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'))
        self.assertEqual(trezor.crypto.sha256.hash(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu'), trezor.utils.unhexlify('cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1'))

if __name__ == '__main__':
    unittest.main()
