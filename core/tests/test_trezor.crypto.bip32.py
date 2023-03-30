from common import *

from trezor.crypto import bip32

SECP256K1_NAME = 'secp256k1'
HARDENED = 0x80000000
VERSION_PUBLIC = 0x0488b21e
VERSION_PRIVATE = 0x0488ade4


class TestCryptoBip32(unittest.TestCase):

    def test_from_seed_invalid(self):
        for c in [SECP256K1_NAME]:
            with self.assertRaises(ValueError):
                bip32.from_seed('', c)
            with self.assertRaises(ValueError):
                bip32.from_seed(bytes(), c)
            with self.assertRaises(ValueError):
                bip32.from_seed(bytearray(), c)
            with self.assertRaises(TypeError):
                bip32.from_seed(1, c)
        s = unhexlify('000102030405060708090a0b0c0d0e0f')
        with self.assertRaises(ValueError):
            bip32.from_seed(s, '')
        with self.assertRaises(ValueError):
            bip32.from_seed(s, bytes())
        with self.assertRaises(ValueError):
            bip32.from_seed(s, bytearray())
        with self.assertRaises(ValueError):
            bip32.from_seed(s, 'foobar')

    def test_secp256k1_vector_1_derive(self):
        # pylint: disable=C0301
        # test vector 1 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

        # init m
        n = bip32.from_seed(unhexlify('000102030405060708090a0b0c0d0e0f'), SECP256K1_NAME)

        # [Chain m]
        self.assertEqual(n.fingerprint(), 0x00000000)
        self.assertEqual(n.chain_code(), unhexlify('873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508'))
        self.assertEqual(n.private_key(), unhexlify('e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35'))
        self.assertEqual(n.public_key(), unhexlify('0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8')

        # [Chain m/0']
        n.derive(HARDENED | 0)
        self.assertEqual(n.fingerprint(), 0x3442193e)
        self.assertEqual(n.chain_code(), unhexlify('47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141'))
        self.assertEqual(n.private_key(), unhexlify('edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea'))
        self.assertEqual(n.public_key(), unhexlify('035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw')

        # [Chain m/0'/1]
        n.derive(1)
        self.assertEqual(n.fingerprint(), 0x5c1bd648)
        self.assertEqual(n.chain_code(), unhexlify('2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19'))
        self.assertEqual(n.private_key(), unhexlify('3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368'))
        self.assertEqual(n.public_key(), unhexlify('03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ')

        # [Chain m/0'/1/2']
        n.derive(HARDENED | 2)
        self.assertEqual(n.fingerprint(), 0xbef5a2f9)
        self.assertEqual(n.chain_code(), unhexlify('04466b9cc8e161e966409ca52986c584f07e9dc81f735db683c3ff6ec7b1503f'))
        self.assertEqual(n.private_key(), unhexlify('cbce0d719ecf7431d88e6a89fa1483e02e35092af60c042b1df2ff59fa424dca'))
        self.assertEqual(n.public_key(), unhexlify('0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5')

        # [Chain m/0'/1/2'/2]
        n.derive(2)
        self.assertEqual(n.fingerprint(), 0xee7ab90c)
        self.assertEqual(n.chain_code(), unhexlify('cfb71883f01676f587d023cc53a35bc7f88f724b1f8c2892ac1275ac822a3edd'))
        self.assertEqual(n.private_key(), unhexlify('0f479245fb19a38a1954c5c7c0ebab2f9bdfd96a17563ef28a6a4b1a2a764ef4'))
        self.assertEqual(n.public_key(), unhexlify('02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6FHa3pjLCk84BayeJxFW2SP4XRrFd1JYnxeLeU8EqN3vDfZmbqBqaGJAyiLjTAwm6ZLRQUMv1ZACTj37sR62cfN7fe5JnJ7dh8zL4fiyLHV')

        # [Chain m/0'/1/2'/2/1000000000]
        n.derive(1000000000)
        self.assertEqual(n.fingerprint(), 0xd880d7d8)
        self.assertEqual(n.chain_code(), unhexlify('c783e67b921d2beb8f6b389cc646d7263b4145701dadd2161548a8b078e65e9e'))
        self.assertEqual(n.private_key(), unhexlify('471b76e389e528d6de6d816857e012c5455051cad6660850e58372a6c3e6e7c8'))
        self.assertEqual(n.public_key(), unhexlify('022a471424da5e657499d1ff51cb43c47481a03b1e77f951fe64cec9f5a48f7011'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy')

    def test_secp256k1_vector_2_derive(self):
        # pylint: disable=C0301
        # test vector 2 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

        # init m
        n = bip32.from_seed(unhexlify('fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542'), SECP256K1_NAME)

        # [Chain m]
        self.assertEqual(n.fingerprint(), 0x00000000)
        self.assertEqual(n.chain_code(), unhexlify('60499f801b896d83179a4374aeb7822aaeaceaa0db1f85ee3e904c4defbd9689'))
        self.assertEqual(n.private_key(), unhexlify('4b03d6fc340455b363f51020ad3ecca4f0850280cf436c70c727923f6db46c3e'))
        self.assertEqual(n.public_key(), unhexlify('03cbcaa9c98c877a26977d00825c956a238e8dddfbd322cce4f74b0b5bd6ace4a7'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB')

        # [Chain m/0]
        n.derive(0)
        self.assertEqual(n.fingerprint(), 0xbd16bee5)
        self.assertEqual(n.chain_code(), unhexlify('f0909affaa7ee7abe5dd4e100598d4dc53cd709d5a5c2cac40e7412f232f7c9c'))
        self.assertEqual(n.private_key(), unhexlify('abe74a98f6c7eabee0428f53798f0ab8aa1bd37873999041703c742f15ac7e1e'))
        self.assertEqual(n.public_key(), unhexlify('02fc9e5af0ac8d9b3cecfe2a888e2117ba3d089d8585886c9c826b6b22a98d12ea'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub69H7F5d8KSRgmmdJg2KhpAK8SR3DjMwAdkxj3ZuxV27CprR9LgpeyGmXUbC6wb7ERfvrnKZjXoUmmDznezpbZb7ap6r1D3tgFxHmwMkQTPH')

        # [Chain m/0/2147483647']
        n.derive(HARDENED | 2147483647)
        self.assertEqual(n.fingerprint(), 0x5a61ff8e)
        self.assertEqual(n.chain_code(), unhexlify('be17a268474a6bb9c61e1d720cf6215e2a88c5406c4aee7b38547f585c9a37d9'))
        self.assertEqual(n.private_key(), unhexlify('877c779ad9687164e9c2f4f0f4ff0340814392330693ce95a58fe18fd52e6e93'))
        self.assertEqual(n.public_key(), unhexlify('03c01e7425647bdefa82b12d9bad5e3e6865bee0502694b94ca58b666abc0a5c3b'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6ASAVgeehLbnwdqV6UKMHVzgqAG8Gr6riv3Fxxpj8ksbH9ebxaEyBLZ85ySDhKiLDBrQSARLq1uNRts8RuJiHjaDMBU4Zn9h8LZNnBC5y4a')

        # [Chain m/0/2147483647'/1]
        n.derive(1)
        self.assertEqual(n.fingerprint(), 0xd8ab4937)
        self.assertEqual(n.chain_code(), unhexlify('f366f48f1ea9f2d1d3fe958c95ca84ea18e4c4ddb9366c336c927eb246fb38cb'))
        self.assertEqual(n.private_key(), unhexlify('704addf544a06e5ee4bea37098463c23613da32020d604506da8c0518e1da4b7'))
        self.assertEqual(n.public_key(), unhexlify('03a7d1d856deb74c508e05031f9895dab54626251b3806e16b4bd12e781a7df5b9'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6DF8uhdarytz3FWdA8TvFSvvAh8dP3283MY7p2V4SeE2wyWmG5mg5EwVvmdMVCQcoNJxGoWaU9DCWh89LojfZ537wTfunKau47EL2dhHKon')

        # [Chain m/0/2147483647'/1/2147483646']
        n.derive(HARDENED | 2147483646)
        self.assertEqual(n.fingerprint(), 0x78412e3a)
        self.assertEqual(n.chain_code(), unhexlify('637807030d55d01f9a0cb3a7839515d796bd07706386a6eddf06cc29a65a0e29'))
        self.assertEqual(n.private_key(), unhexlify('f1c7c871a54a804afe328b4c83a1c33b8e5ff48f5087273f04efa83b247d6a2d'))
        self.assertEqual(n.public_key(), unhexlify('02d2b36900396c9282fa14628566582f206a5dd0bcc8d5e892611806cafb0301f0'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6ERApfZwUNrhLCkDtcHTcxd75RbzS1ed54G1LkBUHQVHQKqhMkhgbmJbZRkrgZw4koxb5JaHWkY4ALHY2grBGRjaDMzQLcgJvLJuZZvRcEL')

        # [Chain m/0/2147483647'/1/2147483646'/2]
        n.derive(2)
        self.assertEqual(n.fingerprint(), 0x31a507b8)
        self.assertEqual(n.chain_code(), unhexlify('9452b549be8cea3ecb7a84bec10dcfd94afe4d129ebfd3b3cb58eedf394ed271'))
        self.assertEqual(n.private_key(), unhexlify('bb7d39bdb83ecf58f2fd82b6d918341cbef428661ef01ab97c28a4842125ac23'))
        self.assertEqual(n.public_key(), unhexlify('024d902e1a2fc7a8755ab5b694c575fce742c48d9ff192e63df5193e4c7afe1f9c'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6FnCn6nSzZAw5Tw7cgR9bi15UV96gLZhjDstkXXxvCLsUXBGXPdSnLFbdpq8p9HmGsApME5hQTZ3emM2rnY5agb9rXpVGyy3bdW6EEgAtqt')

    def test_secp256k1_vector_1_derive_path(self):
        # pylint: disable=C0301
        # test vector 1 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

        # init m
        m = bip32.from_seed(unhexlify('000102030405060708090a0b0c0d0e0f'), SECP256K1_NAME)

        # [Chain m]
        n = m.clone()
        self.assertEqual(n.fingerprint(), 0x00000000)
        self.assertEqual(n.chain_code(), unhexlify('873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508'))
        self.assertEqual(n.private_key(), unhexlify('e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35'))
        self.assertEqual(n.public_key(), unhexlify('0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8')

        # [Chain m/0']
        n = m.clone()
        n.derive_path([HARDENED | 0])
        self.assertEqual(n.fingerprint(), 0x3442193e)
        self.assertEqual(n.chain_code(), unhexlify('47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141'))
        self.assertEqual(n.private_key(), unhexlify('edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea'))
        self.assertEqual(n.public_key(), unhexlify('035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw')

        # [Chain m/0'/1]
        n = m.clone()
        n.derive_path([HARDENED | 0, 1])
        self.assertEqual(n.fingerprint(), 0x5c1bd648)
        self.assertEqual(n.chain_code(), unhexlify('2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19'))
        self.assertEqual(n.private_key(), unhexlify('3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368'))
        self.assertEqual(n.public_key(), unhexlify('03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ')

        # [Chain m/0'/1/2']
        n = m.clone()
        n.derive_path([HARDENED | 0, 1, HARDENED | 2])
        self.assertEqual(n.fingerprint(), 0xbef5a2f9)
        self.assertEqual(n.chain_code(), unhexlify('04466b9cc8e161e966409ca52986c584f07e9dc81f735db683c3ff6ec7b1503f'))
        self.assertEqual(n.private_key(), unhexlify('cbce0d719ecf7431d88e6a89fa1483e02e35092af60c042b1df2ff59fa424dca'))
        self.assertEqual(n.public_key(), unhexlify('0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5')

        # [Chain m/0'/1/2'/2]
        n = m.clone()
        n.derive_path([HARDENED | 0, 1, HARDENED | 2, 2])
        self.assertEqual(n.fingerprint(), 0xee7ab90c)
        self.assertEqual(n.chain_code(), unhexlify('cfb71883f01676f587d023cc53a35bc7f88f724b1f8c2892ac1275ac822a3edd'))
        self.assertEqual(n.private_key(), unhexlify('0f479245fb19a38a1954c5c7c0ebab2f9bdfd96a17563ef28a6a4b1a2a764ef4'))
        self.assertEqual(n.public_key(), unhexlify('02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6FHa3pjLCk84BayeJxFW2SP4XRrFd1JYnxeLeU8EqN3vDfZmbqBqaGJAyiLjTAwm6ZLRQUMv1ZACTj37sR62cfN7fe5JnJ7dh8zL4fiyLHV')

        # [Chain m/0'/1/2'/2/1000000000]
        n = m.clone()
        n.derive_path([HARDENED | 0, 1, HARDENED | 2, 2, 1000000000])
        self.assertEqual(n.fingerprint(), 0xd880d7d8)
        self.assertEqual(n.chain_code(), unhexlify('c783e67b921d2beb8f6b389cc646d7263b4145701dadd2161548a8b078e65e9e'))
        self.assertEqual(n.private_key(), unhexlify('471b76e389e528d6de6d816857e012c5455051cad6660850e58372a6c3e6e7c8'))
        self.assertEqual(n.public_key(), unhexlify('022a471424da5e657499d1ff51cb43c47481a03b1e77f951fe64cec9f5a48f7011'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy')

    def test_secp256k1_vector_2_derive_path(self):
        # pylint: disable=C0301
        # test vector 2 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

        # init m
        m = bip32.from_seed(unhexlify('fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542'), SECP256K1_NAME)

        # [Chain m]
        n = m.clone()
        self.assertEqual(n.fingerprint(), 0x00000000)
        self.assertEqual(n.chain_code(), unhexlify('60499f801b896d83179a4374aeb7822aaeaceaa0db1f85ee3e904c4defbd9689'))
        self.assertEqual(n.private_key(), unhexlify('4b03d6fc340455b363f51020ad3ecca4f0850280cf436c70c727923f6db46c3e'))
        self.assertEqual(n.public_key(), unhexlify('03cbcaa9c98c877a26977d00825c956a238e8dddfbd322cce4f74b0b5bd6ace4a7'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB')

        # [Chain m/0]
        n = m.clone()
        n.derive_path([0])
        self.assertEqual(n.fingerprint(), 0xbd16bee5)
        self.assertEqual(n.chain_code(), unhexlify('f0909affaa7ee7abe5dd4e100598d4dc53cd709d5a5c2cac40e7412f232f7c9c'))
        self.assertEqual(n.private_key(), unhexlify('abe74a98f6c7eabee0428f53798f0ab8aa1bd37873999041703c742f15ac7e1e'))
        self.assertEqual(n.public_key(), unhexlify('02fc9e5af0ac8d9b3cecfe2a888e2117ba3d089d8585886c9c826b6b22a98d12ea'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub69H7F5d8KSRgmmdJg2KhpAK8SR3DjMwAdkxj3ZuxV27CprR9LgpeyGmXUbC6wb7ERfvrnKZjXoUmmDznezpbZb7ap6r1D3tgFxHmwMkQTPH')

        # [Chain m/0/2147483647']
        n = m.clone()
        n.derive_path([0, HARDENED | 2147483647])
        self.assertEqual(n.fingerprint(), 0x5a61ff8e)
        self.assertEqual(n.chain_code(), unhexlify('be17a268474a6bb9c61e1d720cf6215e2a88c5406c4aee7b38547f585c9a37d9'))
        self.assertEqual(n.private_key(), unhexlify('877c779ad9687164e9c2f4f0f4ff0340814392330693ce95a58fe18fd52e6e93'))
        self.assertEqual(n.public_key(), unhexlify('03c01e7425647bdefa82b12d9bad5e3e6865bee0502694b94ca58b666abc0a5c3b'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6ASAVgeehLbnwdqV6UKMHVzgqAG8Gr6riv3Fxxpj8ksbH9ebxaEyBLZ85ySDhKiLDBrQSARLq1uNRts8RuJiHjaDMBU4Zn9h8LZNnBC5y4a')

        # [Chain m/0/2147483647'/1]
        n = m.clone()
        n.derive_path([0, HARDENED | 2147483647, 1])
        self.assertEqual(n.fingerprint(), 0xd8ab4937)
        self.assertEqual(n.chain_code(), unhexlify('f366f48f1ea9f2d1d3fe958c95ca84ea18e4c4ddb9366c336c927eb246fb38cb'))
        self.assertEqual(n.private_key(), unhexlify('704addf544a06e5ee4bea37098463c23613da32020d604506da8c0518e1da4b7'))
        self.assertEqual(n.public_key(), unhexlify('03a7d1d856deb74c508e05031f9895dab54626251b3806e16b4bd12e781a7df5b9'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6DF8uhdarytz3FWdA8TvFSvvAh8dP3283MY7p2V4SeE2wyWmG5mg5EwVvmdMVCQcoNJxGoWaU9DCWh89LojfZ537wTfunKau47EL2dhHKon')

        # [Chain m/0/2147483647'/1/2147483646']
        n = m.clone()
        n.derive_path([0, HARDENED | 2147483647, 1, HARDENED | 2147483646])
        self.assertEqual(n.fingerprint(), 0x78412e3a)
        self.assertEqual(n.chain_code(), unhexlify('637807030d55d01f9a0cb3a7839515d796bd07706386a6eddf06cc29a65a0e29'))
        self.assertEqual(n.private_key(), unhexlify('f1c7c871a54a804afe328b4c83a1c33b8e5ff48f5087273f04efa83b247d6a2d'))
        self.assertEqual(n.public_key(), unhexlify('02d2b36900396c9282fa14628566582f206a5dd0bcc8d5e892611806cafb0301f0'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6ERApfZwUNrhLCkDtcHTcxd75RbzS1ed54G1LkBUHQVHQKqhMkhgbmJbZRkrgZw4koxb5JaHWkY4ALHY2grBGRjaDMzQLcgJvLJuZZvRcEL')

        # [Chain m/0/2147483647'/1/2147483646'/2]
        n = m.clone()
        n.derive_path([0, HARDENED | 2147483647, 1, HARDENED | 2147483646, 2])
        self.assertEqual(n.fingerprint(), 0x31a507b8)
        self.assertEqual(n.chain_code(), unhexlify('9452b549be8cea3ecb7a84bec10dcfd94afe4d129ebfd3b3cb58eedf394ed271'))
        self.assertEqual(n.private_key(), unhexlify('bb7d39bdb83ecf58f2fd82b6d918341cbef428661ef01ab97c28a4842125ac23'))
        self.assertEqual(n.public_key(), unhexlify('024d902e1a2fc7a8755ab5b694c575fce742c48d9ff192e63df5193e4c7afe1f9c'))
        ns = n.serialize_public(VERSION_PUBLIC)
        self.assertEqual(ns, 'xpub6FnCn6nSzZAw5Tw7cgR9bi15UV96gLZhjDstkXXxvCLsUXBGXPdSnLFbdpq8p9HmGsApME5hQTZ3emM2rnY5agb9rXpVGyy3bdW6EEgAtqt')


if __name__ == '__main__':
    unittest.main()
