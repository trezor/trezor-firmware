import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
import trezor.utils

import trezor.crypto.hash
import trezor.crypto.hmac
import trezor.crypto.pbkdf2

class TestCryptoPbkdf2(unittest.TestCase):

    # vectors from https://stackoverflow.com/questions/5130513/pbkdf2-hmac-sha2-test-vectors
    def test_hmac_sha256(self):
        P = b'password'
        S = b'salt'
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 1, trezor.crypto.hash.sha256, trezor.crypto.hmac).read(32)
        self.assertEqual(k, trezor.utils.unhexlify('120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b'))
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 2, trezor.crypto.hash.sha256, trezor.crypto.hmac).read(32)
        self.assertEqual(k, trezor.utils.unhexlify('ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43'))
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 4096, trezor.crypto.hash.sha256, trezor.crypto.hmac).read(32)
        self.assertEqual(k, trezor.utils.unhexlify('c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a'))
        P = b'passwordPASSWORDpassword'
        S = b'saltSALTsaltSALTsaltSALTsaltSALTsalt'
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 4096, trezor.crypto.hash.sha256, trezor.crypto.hmac).read(40)
        self.assertEqual(k, trezor.utils.unhexlify('348c89dbcbd32b2f32d814b8116e84cf2b17347ebc1800181c4e2a1fb8dd53e1c635518c7dac47e9'))

    # vectors from https://stackoverflow.com/questions/15593184/pbkdf2-hmac-sha-512-test-vectors
    def test_hmac_sha512(self):
        P = b'password'
        S = b'salt'
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 1, trezor.crypto.hash.sha512, trezor.crypto.hmac).read(64)
        self.assertEqual(k, trezor.utils.unhexlify('867f70cf1ade02cff3752599a3a53dc4af34c7a669815ae5d513554e1c8cf252c02d470a285a0501bad999bfe943c08f050235d7d68b1da55e63f73b60a57fce'))
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 2, trezor.crypto.hash.sha512, trezor.crypto.hmac).read(64)
        self.assertEqual(k, trezor.utils.unhexlify('e1d9c16aa681708a45f5c7c4e215ceb66e011a2e9f0040713f18aefdb866d53cf76cab2868a39b9f7840edce4fef5a82be67335c77a6068e04112754f27ccf4e'))
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 4096, trezor.crypto.hash.sha512, trezor.crypto.hmac).read(64)
        self.assertEqual(k, trezor.utils.unhexlify('d197b1b33db0143e018b12f3d1d1479e6cdebdcc97c5c0f87f6902e072f457b5143f30602641b3d55cd335988cb36b84376060ecd532e039b742a239434af2d5'))
        P = b'passwordPASSWORDpassword'
        S = b'saltSALTsaltSALTsaltSALTsaltSALTsalt'
        k = trezor.crypto.pbkdf2.PBKDF2(P, S, 4096, trezor.crypto.hash.sha512, trezor.crypto.hmac).read(64)
        self.assertEqual(k, trezor.utils.unhexlify('8c0511f4c6e597c6ac6315d8f0362e225f3c501495ba23b868c005174dc4ee71115b59f9e60cd9532fa33e0f75aefe30225c583a186cd82bd4daea9724a3d3b8'))

if __name__ == '__main__':
    unittest.main()
