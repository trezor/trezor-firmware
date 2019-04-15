from common import *

from trezor.crypto import random

from trezor.crypto.curve import ed25519


class TestCryptoEd25519(unittest.TestCase):

    # vectors from https://github.com/torproject/tor/blob/master/src/test/ed25519_vectors.inc
    vectors = [
        ('26c76712d89d906e6672dafa614c42e5cb1caac8c6568e4d2493087db51f0d36', 'c2247870536a192d142d056abefca68d6193158e7c1a59c1654c954eccaff894', 'd23188eac3773a316d46006fa59c095060be8b1a23582a0dd99002a82a0662bd246d8449e172e04c5f46ac0d1404cebe4aabd8a75a1457aa06cae41f3334f104'),
        ('fba7a5366b5cb98c2667a18783f5cf8f4f8d1a2ce939ad22a6e685edde85128d', '1519a3b15816a1aafab0b213892026ebf5c0dc232c58b21088d88cb90e9b940d', '3a785ac1201c97ee5f6f0d99323960d5f264c7825e61aa7cc81262f15bef75eb4fa5723add9b9d45b12311b6d403eb3ac79ff8e4e631fc3cd51e4ad2185b200b'),
        ('67e3aa7a14fac8445d15e45e38a523481a69ae35513c9e4143eb1c2196729a0e', '081faa81992e360ea22c06af1aba096e7a73f1c665bc8b3e4e531c46455fd1dd', 'cf431fd0416bfbd20c9d95ef9b723e2acddffb33900edc72195dea95965d52d888d30b7b8a677c0bd8ae1417b1e1a0ec6700deadd5d8b54b6689275e04a04509'),
        ('d51385942033a76dc17f089a59e6a5a7fe80d9c526ae8ddd8c3a506b99d3d0a6', '73cfa1189a723aad7966137cbffa35140bb40d7e16eae4c40b79b5f0360dd65a', '2375380cd72d1a6c642aeddff862be8a5804b916acb72c02d9ed052c1561881aa658a5af856fcd6d43113e42f698cd6687c99efeef7f2ce045824440d26c5d00'),
        ('5c8eac469bb3f1b85bc7cd893f52dc42a9ab66f1b02b5ce6a68e9b175d3bb433', '66c1a77104d86461b6f98f73acf3cd229c80624495d2d74d6fda1e940080a96b', '2385a472f599ca965bbe4d610e391cdeabeba9c336694b0d6249e551458280be122c2441dd9746a81bbfb9cd619364bab0df37ff4ceb7aefd24469c39d3bc508'),
        ('eda433d483059b6d1ff8b7cfbd0fe406bfb23722c8f3c8252629284573b61b86', 'd21c294db0e64cb2d8976625786ede1d9754186ae8197a64d72f68c792eecc19', 'e500cd0b8cfff35442f88008d894f3a2fa26ef7d3a0ca5714ae0d3e2d40caae58ba7cdf69dd126994dad6be536fcda846d89dd8138d1683cc144c8853dce7607'),
        ('4377c40431c30883c5fbd9bc92ae48d1ed8a47b81d13806beac5351739b5533d', 'c4d58b4cf85a348ff3d410dd936fa460c4f18da962c01b1963792b9dcc8a6ea6', 'd187b9e334b0050154de10bf69b3e4208a584e1a65015ec28b14bcc252cf84b8baa9c94867daa60f2a82d09ba9652d41e8dde292b624afc8d2c26441b95e3c0e'),
        ('c6bbcce615839756aed2cc78b1de13884dd3618f48367a17597a16c1cd7a290b', '95126f14d86494020665face03f2d42ee2b312a85bc729903eb17522954a1c4a', '815213640a643d198bd056e02bba74e1c8d2d931643e84497adf3347eb485079c9afe0afce9284cdc084946b561abbb214f1304ca11228ff82702185cf28f60d'),
    ]

    def test_publickey(self):
        for sk, pk, _ in self.vectors:
            pk2 = ed25519.publickey(unhexlify(sk))
            self.assertEqual(pk2, unhexlify(pk))

    def test_sign(self):
        for sk, pk, sig in self.vectors:
            # msg = pk
            sig2 = ed25519.sign(unhexlify(sk), unhexlify(pk))
            self.assertEqual(sig2, unhexlify(sig))

    def test_verify(self):
        for sk, pk, sig in self.vectors:
            # msg = pk
            self.assertTrue(ed25519.verify(unhexlify(pk), unhexlify(sig), unhexlify(pk)))
            pass

    def test_generate_secret(self):
        for _ in range(100):
            sk = ed25519.generate_secret()
            self.assertTrue(len(sk) == 32)
            self.assertTrue(sk[0] & 7 == 0 and sk[31] & 128 == 0 and sk[31] & 64 == 64)

    def test_sign_verify_random(self):
        for l in range(1, 300):
            sk = ed25519.generate_secret()
            pk = ed25519.publickey(sk)
            msg = random.bytes(l)
            sig = ed25519.sign(sk, msg)
            self.assertTrue(ed25519.verify(pk, sig, msg))


if __name__ == '__main__':
    unittest.main()
