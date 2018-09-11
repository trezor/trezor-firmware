from common import *

from trezor.crypto import pbkdf2


class TestCryptoPbkdf2(unittest.TestCase):

    # vectors from https://stackoverflow.com/questions/5130513/pbkdf2-hmac-sha2-test-vectors

    def test_pbkdf2_hmac_sha256(self):
        P = b'password'
        S = b'salt'
        dk = pbkdf2(pbkdf2.HMAC_SHA256, P, S, 1).key()
        self.assertEqual(dk, unhexlify('120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b'))
        dk = pbkdf2(pbkdf2.HMAC_SHA256, P, S, 2).key()
        self.assertEqual(dk, unhexlify('ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43'))
        dk = pbkdf2(pbkdf2.HMAC_SHA256, P, S, 4096).key()
        self.assertEqual(dk, unhexlify('c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a'))
        P = b'passwordPASSWORDpassword'
        S = b'saltSALTsaltSALTsaltSALTsaltSALTsalt'
        dk = pbkdf2(pbkdf2.HMAC_SHA256, P, S, 4096).key()
        self.assertEqual(dk, unhexlify('348c89dbcbd32b2f32d814b8116e84cf2b17347ebc1800181c4e2a1fb8dd53e1'))

    def test_pbkdf2_hmac_sha256_update(self):
        P = b'password'
        S = b'salt'
        p = pbkdf2(pbkdf2.HMAC_SHA256, P, S)
        p.update(1)
        dk = p.key()
        self.assertEqual(dk, unhexlify('120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b'))
        p = pbkdf2(pbkdf2.HMAC_SHA256, P, S)
        p.update(1)
        p.update(1)
        dk = p.key()
        self.assertEqual(dk, unhexlify('ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43'))
        p = pbkdf2(pbkdf2.HMAC_SHA256, P, S)
        for i in range(32):
            p.update(128)
        dk = p.key()
        self.assertEqual(dk, unhexlify('c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a'))
        P = b'passwordPASSWORDpassword'
        S = b'saltSALTsaltSALTsaltSALTsaltSALTsalt'
        p = pbkdf2(pbkdf2.HMAC_SHA256, P, S)
        for i in range(64):
            p.update(64)
        dk = p.key()
        self.assertEqual(dk, unhexlify('348c89dbcbd32b2f32d814b8116e84cf2b17347ebc1800181c4e2a1fb8dd53e1'))

    # vectors from https://stackoverflow.com/questions/15593184/pbkdf2-hmac-sha-512-test-vectors

    def test_pbkdf2_hmac_sha512(self):
        P = b'password'
        S = b'salt'
        dk = pbkdf2(pbkdf2.HMAC_SHA512, P, S, 1).key()
        self.assertEqual(dk, unhexlify('867f70cf1ade02cff3752599a3a53dc4af34c7a669815ae5d513554e1c8cf252c02d470a285a0501bad999bfe943c08f050235d7d68b1da55e63f73b60a57fce'))
        dk = pbkdf2(pbkdf2.HMAC_SHA512, P, S, 2).key()
        self.assertEqual(dk, unhexlify('e1d9c16aa681708a45f5c7c4e215ceb66e011a2e9f0040713f18aefdb866d53cf76cab2868a39b9f7840edce4fef5a82be67335c77a6068e04112754f27ccf4e'))
        dk = pbkdf2(pbkdf2.HMAC_SHA512, P, S, 4096).key()
        self.assertEqual(dk, unhexlify('d197b1b33db0143e018b12f3d1d1479e6cdebdcc97c5c0f87f6902e072f457b5143f30602641b3d55cd335988cb36b84376060ecd532e039b742a239434af2d5'))
        P = b'passwordPASSWORDpassword'
        S = b'saltSALTsaltSALTsaltSALTsaltSALTsalt'
        dk = pbkdf2(pbkdf2.HMAC_SHA512, P, S, 4096).key()
        self.assertEqual(dk, unhexlify('8c0511f4c6e597c6ac6315d8f0362e225f3c501495ba23b868c005174dc4ee71115b59f9e60cd9532fa33e0f75aefe30225c583a186cd82bd4daea9724a3d3b8'))

    def test_pbkdf2_hmac_sha512_update(self):
        P = b'password'
        S = b'salt'
        p = pbkdf2(pbkdf2.HMAC_SHA512, P, S)
        p.update(1)
        dk = p.key()
        self.assertEqual(dk, unhexlify('867f70cf1ade02cff3752599a3a53dc4af34c7a669815ae5d513554e1c8cf252c02d470a285a0501bad999bfe943c08f050235d7d68b1da55e63f73b60a57fce'))
        p = pbkdf2(pbkdf2.HMAC_SHA512, P, S)
        p.update(1)
        p.update(1)
        dk = p.key()
        self.assertEqual(dk, unhexlify('e1d9c16aa681708a45f5c7c4e215ceb66e011a2e9f0040713f18aefdb866d53cf76cab2868a39b9f7840edce4fef5a82be67335c77a6068e04112754f27ccf4e'))
        p = pbkdf2(pbkdf2.HMAC_SHA512, P, S)
        for i in range(32):
            p.update(128)
        dk = p.key()
        self.assertEqual(dk, unhexlify('d197b1b33db0143e018b12f3d1d1479e6cdebdcc97c5c0f87f6902e072f457b5143f30602641b3d55cd335988cb36b84376060ecd532e039b742a239434af2d5'))
        P = b'passwordPASSWORDpassword'
        S = b'saltSALTsaltSALTsaltSALTsaltSALTsalt'
        p = pbkdf2(pbkdf2.HMAC_SHA512, P, S)
        for i in range(64):
            p.update(64)
        dk = p.key()
        self.assertEqual(dk, unhexlify('8c0511f4c6e597c6ac6315d8f0362e225f3c501495ba23b868c005174dc4ee71115b59f9e60cd9532fa33e0f75aefe30225c583a186cd82bd4daea9724a3d3b8'))

    def test_key_multi(self):
        P = b'password'
        S = b'salt'
        p = pbkdf2(pbkdf2.HMAC_SHA256, P, S, 16)
        k0 = p.key()
        k1 = p.key()
        k2 = p.key()
        self.assertEqual(k0, k1)
        self.assertEqual(k0, k2)
        p = pbkdf2(pbkdf2.HMAC_SHA512, P, S, 16)
        k0 = p.key()
        k1 = p.key()
        k2 = p.key()
        self.assertEqual(k0, k1)
        self.assertEqual(k0, k2)


if __name__ == '__main__':
    unittest.main()
