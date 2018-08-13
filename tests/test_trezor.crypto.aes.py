from common import *

from trezor.crypto import aes


class TestCryptoAes(unittest.TestCase):

    # test vectors from NIST Special Publication 800-38A (Appendix F)
    # https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-38a.pdf

    iv = unhexlify("000102030405060708090a0b0c0d0e0f")
    ctr = unhexlify("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
    key128 = unhexlify("2b7e151628aed2a6abf7158809cf4f3c")
    key192 = unhexlify("8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b")
    key256 = unhexlify(
        "603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4"
    )

    def test_ecb(self):
        vectors128 = [
            ("6bc1bee22e409f96e93d7e117393172a", "3ad77bb40d7a3660a89ecaf32466ef97"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "f5d3d58503b9699de785895a96fdbaaf"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "43b1cd7f598ece23881b00e3ed030688"),
            ("f69f2445df4f9b17ad2b417be66c3710", "7b0c785e27e8ad3f8223207104725dd4"),
        ]
        vectors192 = [
            ("6bc1bee22e409f96e93d7e117393172a", "bd334f1d6e45f25ff712a214571fa5cc"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "974104846d0ad3ad7734ecb3ecee4eef"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "ef7afd2270e2e60adce0ba2face6444e"),
            ("f69f2445df4f9b17ad2b417be66c3710", "9a4b41ba738d6c72fb16691603c18e0e"),
        ]
        vectors256 = [
            ("6bc1bee22e409f96e93d7e117393172a", "f3eed1bdb5d2a03c064b5a7e3db181f8"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "591ccb10d410ed26dc5ba74a31362870"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "b6ed21b99ca6f4f9f153e7b1beafed1d"),
            ("f69f2445df4f9b17ad2b417be66c3710", "23304b7a39f9f3ff067d8d8f9e24ecc7"),
        ]
        for key, vec in [
            (self.key128, vectors128),
            (self.key192, vectors192),
            (self.key256, vectors256),
        ]:
            ctx1 = aes(aes.ECB, key)
            ctx2 = aes(aes.ECB, key)
            for plain, cipher in vec:
                plain, cipher = unhexlify(plain), unhexlify(cipher)
                e = ctx1.encrypt(plain)
                self.assertEqual(e, cipher)
                d = ctx2.decrypt(cipher)
                self.assertEqual(d, plain)

    def test_cbc(self):
        vectors128 = [
            ("6bc1bee22e409f96e93d7e117393172a", "7649abac8119b246cee98e9b12e9197d"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "5086cb9b507219ee95db113a917678b2"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "73bed6b8e3c1743b7116e69e22229516"),
            ("f69f2445df4f9b17ad2b417be66c3710", "3ff1caa1681fac09120eca307586e1a7"),
        ]
        vectors192 = [
            ("6bc1bee22e409f96e93d7e117393172a", "4f021db243bc633d7178183a9fa071e8"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "b4d9ada9ad7dedf4e5e738763f69145a"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "571b242012fb7ae07fa9baac3df102e0"),
            ("f69f2445df4f9b17ad2b417be66c3710", "08b0e27988598881d920a9e64f5615cd"),
        ]
        vectors256 = [
            ("6bc1bee22e409f96e93d7e117393172a", "f58c4c04d6e5f1ba779eabfb5f7bfbd6"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "9cfc4e967edb808d679f777bc6702c7d"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "39f23369a9d9bacfa530e26304231461"),
            ("f69f2445df4f9b17ad2b417be66c3710", "b2eb05e2c39be9fcda6c19078c6a9d1b"),
        ]
        for key, vec in [
            (self.key128, vectors128),
            (self.key192, vectors192),
            (self.key256, vectors256),
        ]:
            ctx1 = aes(aes.CBC, key, self.iv)
            ctx2 = aes(aes.CBC, key, self.iv)
            for plain, cipher in vec:
                plain, cipher = unhexlify(plain), unhexlify(cipher)
                e = ctx1.encrypt(plain)
                self.assertEqual(e, cipher)
                d = ctx2.decrypt(cipher)
                self.assertEqual(d, plain)

    def test_cfb(self):
        vectors128 = [
            ("6bc1bee22e409f96e93d7e117393172a", "3b3fd92eb72dad20333449f8e83cfb4a"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "c8a64537a0b3a93fcde3cdad9f1ce58b"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "26751f67a3cbb140b1808cf187a4f4df"),
            ("f69f2445df4f9b17ad2b417be66c3710", "c04b05357c5d1c0eeac4c66f9ff7f2e6"),
        ]
        vectors192 = [
            ("6bc1bee22e409f96e93d7e117393172a", "cdc80d6fddf18cab34c25909c99a4174"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "67ce7f7f81173621961a2b70171d3d7a"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "2e1e8a1dd59b88b1c8e60fed1efac4c9"),
            ("f69f2445df4f9b17ad2b417be66c3710", "c05f9f9ca9834fa042ae8fba584b09ff"),
        ]
        vectors256 = [
            ("6bc1bee22e409f96e93d7e117393172a", "dc7e84bfda79164b7ecd8486985d3860"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "39ffed143b28b1c832113c6331e5407b"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "df10132415e54b92a13ed0a8267ae2f9"),
            ("f69f2445df4f9b17ad2b417be66c3710", "75a385741ab9cef82031623d55b1e471"),
        ]
        for key, vec in [
            (self.key128, vectors128),
            (self.key192, vectors192),
            (self.key256, vectors256),
        ]:
            ctx1 = aes(aes.CFB, key, self.iv)
            ctx2 = aes(aes.CFB, key, self.iv)
            for plain, cipher in vec:
                plain, cipher = unhexlify(plain), unhexlify(cipher)
                e = ctx1.encrypt(plain)
                self.assertEqual(e, cipher)
                d = ctx2.decrypt(cipher)
                self.assertEqual(d, plain)

    def test_ofb(self):
        vectors128 = [
            ("6bc1bee22e409f96e93d7e117393172a", "3b3fd92eb72dad20333449f8e83cfb4a"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "7789508d16918f03f53c52dac54ed825"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "9740051e9c5fecf64344f7a82260edcc"),
            ("f69f2445df4f9b17ad2b417be66c3710", "304c6528f659c77866a510d9c1d6ae5e"),
        ]
        vectors192 = [
            ("6bc1bee22e409f96e93d7e117393172a", "cdc80d6fddf18cab34c25909c99a4174"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "fcc28b8d4c63837c09e81700c1100401"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "8d9a9aeac0f6596f559c6d4daf59a5f2"),
            ("f69f2445df4f9b17ad2b417be66c3710", "6d9f200857ca6c3e9cac524bd9acc92a"),
        ]
        vectors256 = [
            ("6bc1bee22e409f96e93d7e117393172a", "dc7e84bfda79164b7ecd8486985d3860"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "4febdc6740d20b3ac88f6ad82a4fb08d"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "71ab47a086e86eedf39d1c5bba97c408"),
            ("f69f2445df4f9b17ad2b417be66c3710", "0126141d67f37be8538f5a8be740e484"),
        ]
        for key, vec in [
            (self.key128, vectors128),
            (self.key192, vectors192),
            (self.key256, vectors256),
        ]:
            ctx1 = aes(aes.OFB, key, self.iv)
            ctx2 = aes(aes.OFB, key, self.iv)
            for plain, cipher in vec:
                plain, cipher = unhexlify(plain), unhexlify(cipher)
                e = ctx1.encrypt(plain)
                self.assertEqual(e, cipher)
                d = ctx2.decrypt(cipher)
                self.assertEqual(d, plain)

    def test_ctr(self):
        vectors128 = [
            ("6bc1bee22e409f96e93d7e117393172a", "874d6191b620e3261bef6864990db6ce"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "9806f66b7970fdff8617187bb9fffdff"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "5ae4df3edbd5d35e5b4f09020db03eab"),
            ("f69f2445df4f9b17ad2b417be66c3710", "1e031dda2fbe03d1792170a0f3009cee"),
        ]
        vectors192 = [
            ("6bc1bee22e409f96e93d7e117393172a", "1abc932417521ca24f2b0459fe7e6e0b"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "090339ec0aa6faefd5ccc2c6f4ce8e94"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "1e36b26bd1ebc670d1bd1d665620abf7"),
            ("f69f2445df4f9b17ad2b417be66c3710", "4f78a7f6d29809585a97daec58c6b050"),
        ]
        vectors256 = [
            ("6bc1bee22e409f96e93d7e117393172a", "601ec313775789a5b7a7f504bbf3d228"),
            ("ae2d8a571e03ac9c9eb76fac45af8e51", "f443e3ca4d62b59aca84e990cacaf5c5"),
            ("30c81c46a35ce411e5fbc1191a0a52ef", "2b0930daa23de94ce87017ba2d84988d"),
            ("f69f2445df4f9b17ad2b417be66c3710", "dfc9c58db67aada613c2dd08457941a6"),
        ]
        for key, vec in [
            (self.key128, vectors128),
            (self.key192, vectors192),
            (self.key256, vectors256),
        ]:
            ctx1 = aes(aes.CTR, key, self.ctr)
            ctx2 = aes(aes.CTR, key, self.ctr)
            for plain, cipher in vec:
                plain, cipher = unhexlify(plain), unhexlify(cipher)
                e = ctx1.encrypt(plain)
                self.assertEqual(e, cipher)
                d = ctx2.decrypt(cipher)
                self.assertEqual(d, plain)


if __name__ == "__main__":
    unittest.main()
