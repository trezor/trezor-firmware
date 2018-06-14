from common import *

from trezor.crypto import hashlib


class TestCryptoBlake2b(unittest.TestCase):

    # vectors from https://raw.githubusercontent.com/BLAKE2/BLAKE2/master/testvectors/blake2b-kat.txt
    vectors = [
        ('', '10ebb67700b1868efb4417987acf4690ae9d972fb7a590c2f02871799aaa4786b5e996e8f0f4eb981fc214b005f42d2ff4233499391653df7aefcbc13fc51568'),
        ('00', '961f6dd1e4dd30f63901690c512e78e4b45e4742ed197c3c5e45c549fd25f2e4187b0bc9fe30492b16b0d0bc4ef9b0f34c7003fac09a5ef1532e69430234cebd'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e', 'eba51acffb4cea31db4b8d87e9bf7dd48fe97b0253ae67aa580f9ac4a9d941f2bea518ee286818cc9f633f2a3b9fb68e594b48cdd6d515bf1d52ba6c85a203a7'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20', '5595e05c13a7ec4dc8f41fb70cb50a71bce17c024ff6de7af618d0cc4e9c32d9570d6d3ea45b86525491030c0d8f2b1836d5778c1ce735c17707df364d054347'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f4041', 'c516541701863f91005f314108ceece3c643e04fc8c42fd2ff556220e616aaa6a48aeb97a84bad74782e8dff96a1a2fa949339d722edcaa32b57067041df88cc'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f60', '31fc79738b8772b3f55cd8178813b3b52d0db5a419d30ba9495c4b9da0219fac6df8e7c23a811551a62b827f256ecdb8124ac8a6792ccfecc3b3012722e94463'),
    ]

    def test_digest(self):
        key = unhexlify('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f')
        for d, h in self.vectors:
            self.assertEqual(hashlib.blake2b(data=unhexlify(d), key=key).digest(), unhexlify(h))

    def test_update(self):
        key = unhexlify('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f')
        x = hashlib.blake2b(key=key)
        x.update(bytes(range(10)))
        self.assertEqual(x.digest(), unhexlify('4fe181f54ad63a2983feaaf77d1e7235c2beb17fa328b6d9505bda327df19fc37f02c4b6f0368ce23147313a8e5738b5fa2a95b29de1c7f8264eb77b69f585cd'))
        x.update(bytes(range(10, 30)))
        self.assertEqual(x.digest(), unhexlify('c6dbc61dec6eaeac81e3d5f755203c8e220551534a0b2fd105a91889945a638550204f44093dd998c076205dffad703a0e5cd3c7f438a7e634cd59fededb539e'))
        x.update(bytes(range(30, 80)))
        self.assertEqual(x.digest(), unhexlify('fa1549c9796cd4d303dcf452c1fbd5744fd9b9b47003d920b92de34839d07ef2a29ded68f6fc9e6c45e071a2e48bd50c5084e96b657dd0404045a1ddefe282ed'))
        x.update(bytes(range(80, 111)))
        self.assertEqual(x.digest(), unhexlify('2620f687e8625f6a412460b42e2cef67634208ce10a0cbd4dff7044a41b7880077e9f8dc3b8d1216d3376a21e015b58fb279b521d83f9388c7382c8505590b9b'))
        x.update(bytes(range(111, 127)))
        self.assertEqual(x.digest(), unhexlify('76d2d819c92bce55fa8e092ab1bf9b9eab237a25267986cacf2b8ee14d214d730dc9a5aa2d7b596e86a1fd8fa0804c77402d2fcd45083688b218b1cdfa0dcbcb'))
        x.update(bytes(range(127, 255)))
        self.assertEqual(x.digest(), unhexlify('142709d62e28fcccd0af97fad0f8465b971e82201dc51070faa0372aa43e92484be1c1e73ba10906d5d1853db6a4106e0a7bf9800d373d6dee2d46d62ef2a461'))

    def test_digest_multi(self):
        x = hashlib.blake2b()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
