from common import *

from trezor.crypto import hashlib


class TestCryptoSha3_512(unittest.TestCase):

    # vectors from http://www.di-mgt.com.au/sha_testvectors.html
    vectors = [
        (b'', 'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26'),
        (b'abc', 'b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0'),
        (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', '04a371e84ecfb5b8b77cb48610fca8182dd457ce6f326a0fd3d7ec2f1e91636dee691fbe0c985302ba1b0d8dc78c086346b533b49c030d99a27daf1139d6e75e'),
        (b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu', 'afebb2ef542e6579c50cad06d2e578f9f8dd6881d7dc824d26360feebf18a4fa73e3261122948efcfd492e74e82e2189ed0fb440d187f382270cb455f21dd185'),
    ]

    vectors_keccak = [
        (b'', '0eab42de4c3ceb9235fc91acffe746b29c29a8c366b7c60e4e67c466f36a4304c00fa9caf9d87976ba469bcbe06713b435f091ef2769fb160cdab33d3670680e'),
        (b'abc', '18587dc2ea106b9a1563e32b3312421ca164c7f1f07bc922a9c83d77cea3a1e5d0c69910739025372dc14ac9642629379540c17e2a65b19d77aa511a9d00bb96'),
        (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', '6aa6d3669597df6d5a007b00d09c20795b5c4218234e1698a944757a488ecdc09965435d97ca32c3cfed7201ff30e070cd947f1fc12b9d9214c467d342bcba5d'),
        (b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu', 'ac2fb35251825d3aa48468a9948c0a91b8256f6d97d8fa4160faff2dd9dfcc24f3f1db7a983dad13d53439ccac0b37e24037e7b95f80f59f37a2f683c4ba4682'),
    ]

    def test_digest(self):
        for b, d in self.vectors:
            self.assertEqual(hashlib.sha3_512(b).digest(), unhexlify(d))

    def test_digest_keccak(self):
        for b, d in self.vectors_keccak:
            self.assertEqual(hashlib.sha3_512(b, keccak=True).digest(), unhexlify(d))

    def test_update(self):
        for b, d in self.vectors:
            x = hashlib.sha3_512()
            x.update(b)
            self.assertEqual(x.digest(), unhexlify(d))

        x = hashlib.sha3_512()
        for i in range(1000000):
            x.update(b'a')
        self.assertEqual(x.digest(), unhexlify('3c3a876da14034ab60627c077bb98f7e120a2a5370212dffb3385a18d4f38859ed311d0a9d5141ce9cc5c66ee689b266a8aa18ace8282a0e0db596c90b0a7b87'))

        '''
        x = hashlib.sha3_512()
        for i in range(16777216):
            x.update(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno')
        self.assertEqual(x.digest(), unhexlify('235ffd53504ef836a1342b488f483b396eabbfe642cf78ee0d31feec788b23d0d18d5c339550dd5958a500d4b95363da1b5fa18affc1bab2292dc63b7d85097c'))
        '''

    def test_update_keccak(self):
        for b, d in self.vectors_keccak:
            x = hashlib.sha3_512(keccak=True)
            x.update(b)
            self.assertEqual(x.digest(), unhexlify(d))

    def test_digest_multi(self):
        x = hashlib.sha3_512()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)

    def test_digest_multi_keccak(self):
        x = hashlib.sha3_512(keccak=True)
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
