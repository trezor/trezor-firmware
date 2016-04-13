import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
import trezor.utils

import trezor.crypto.hash

class TestCryptoSha256(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html

    def test_digest(self):
        self.assertEqual(trezor.crypto.hash.sha256(b'').digest(), trezor.utils.unhexlify('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))
        self.assertEqual(trezor.crypto.hash.sha256(b'abc').digest(), trezor.utils.unhexlify('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'))
        self.assertEqual(trezor.crypto.hash.sha256(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq').digest(), trezor.utils.unhexlify('248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'))
        self.assertEqual(trezor.crypto.hash.sha256(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu').digest(), trezor.utils.unhexlify('cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1'))

    def test_update(self):
        x = trezor.crypto.hash.sha256()
        self.assertEqual(x.digest(), trezor.utils.unhexlify('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))

        x = trezor.crypto.hash.sha256()
        x.update(b'abc')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'))

        x = trezor.crypto.hash.sha256()
        x.update(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'))

        x = trezor.crypto.hash.sha256()
        x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1'))

        x = trezor.crypto.hash.sha256()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0'))

        '''
        x = trezor.crypto.hash.sha256()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), trezor.utils.unhexlify('50e72a0e26442fe2552dc3938ac58658228c0cbfb1d2ca872ae435266fcd055e'))
        '''

if __name__ == '__main__':
    unittest.main()
