import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest
from ubinascii import unhexlify

from trezor.crypto import bip32

SECP256K1_NAME = 'secp256k1'


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
        s = unhexlify("000102030405060708090a0b0c0d0e0f")
        with self.assertRaises(ValueError):
            bip32.from_seed(s, '')
        with self.assertRaises(ValueError):
            bip32.from_seed(s, bytes())
        with self.assertRaises(ValueError):
            bip32.from_seed(s, bytearray())
        with self.assertRaises(ValueError):
            bip32.from_seed(s, 'foobar')

    def test_secp256k1_vector_1(self):
        # pylint: disable=C0301
        # test vector 1 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

        # init m
        n = bip32.from_seed(unhexlify("000102030405060708090a0b0c0d0e0f"), SECP256K1_NAME)

        # [Chain m]
        self.assertEqual(n.fingerprint(), 0x00000000)
        self.assertEqual(n.chain_code(), unhexlify("873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508"))
        self.assertEqual(n.private_key(), unhexlify("e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"))
        self.assertEqual(n.public_key(), unhexlify("0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2"))
        ns = n.serialize_private()
        self.assertEqual(ns, "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi")
        ns2 = bip32.deserialize(ns).serialize_private()
        self.assertEqual(ns2, ns)
        ns = n.serialize_public()
        self.assertEqual(ns, "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8")
        n2 = bip32.deserialize(ns)
        self.assertEqual(n2.private_key(), bytes(32))
        ns2 = n2.serialize_public()
        self.assertEqual(ns2, ns)

        # [Chain m/0']
        n.derive(0x80000000 | 0)
        self.assertEqual(n.fingerprint(), 0x3442193e)
        self.assertEqual(n.chain_code(), unhexlify("47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141"))
        self.assertEqual(n.private_key(), unhexlify("edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea"))
        self.assertEqual(n.public_key(), unhexlify("035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56"))
        ns = n.serialize_private()
        self.assertEqual(ns, "xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7")
        ns2 = bip32.deserialize(ns).serialize_private()
        self.assertEqual(ns2, ns)
        ns = n.serialize_public()
        self.assertEqual(ns, "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw")
        n2 = bip32.deserialize(ns)
        self.assertEqual(n2.private_key(), bytes(32))
        ns2 = n2.serialize_public()
        self.assertEqual(ns2, ns)

        # [Chain m/0'/1]
        n.derive(1)
        self.assertEqual(n.fingerprint(), 0x5c1bd648)
        self.assertEqual(n.chain_code(), unhexlify("2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19"))
        self.assertEqual(n.private_key(), unhexlify("3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368"))
        self.assertEqual(n.public_key(), unhexlify("03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c"))
        ns = n.serialize_private()
        self.assertEqual(ns, "xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs")
        ns2 = bip32.deserialize(ns).serialize_private()
        self.assertEqual(ns2, ns)
        ns = n.serialize_public()
        self.assertEqual(ns, "xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ")
        n2 = bip32.deserialize(ns)
        self.assertEqual(n2.private_key(), bytes(32))
        ns2 = n2.serialize_public()
        self.assertEqual(ns2, ns)

        # [Chain m/0'/1/2']
        n.derive(0x80000000 | 2)
        self.assertEqual(n.fingerprint(), 0xbef5a2f9)
        self.assertEqual(n.chain_code(), unhexlify("04466b9cc8e161e966409ca52986c584f07e9dc81f735db683c3ff6ec7b1503f"))
        self.assertEqual(n.private_key(), unhexlify("cbce0d719ecf7431d88e6a89fa1483e02e35092af60c042b1df2ff59fa424dca"))
        self.assertEqual(n.public_key(), unhexlify("0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2"))
        ns = n.serialize_private()
        self.assertEqual(ns, "xprv9z4pot5VBttmtdRTWfWQmoH1taj2axGVzFqSb8C9xaxKymcFzXBDptWmT7FwuEzG3ryjH4ktypQSAewRiNMjANTtpgP4mLTj34bhnZX7UiM")
        ns2 = bip32.deserialize(ns).serialize_private()
        self.assertEqual(ns2, ns)
        ns = n.serialize_public()
        self.assertEqual(ns, "xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5")
        n2 = bip32.deserialize(ns)
        self.assertEqual(n2.private_key(), bytes(32))
        ns2 = n2.serialize_public()
        self.assertEqual(ns2, ns)

        # [Chain m/0'/1/2'/2]
        n.derive(2)
        self.assertEqual(n.fingerprint(), 0xee7ab90c)
        self.assertEqual(n.chain_code(), unhexlify("cfb71883f01676f587d023cc53a35bc7f88f724b1f8c2892ac1275ac822a3edd"))
        self.assertEqual(n.private_key(), unhexlify("0f479245fb19a38a1954c5c7c0ebab2f9bdfd96a17563ef28a6a4b1a2a764ef4"))
        self.assertEqual(n.public_key(), unhexlify("02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29"))
        ns = n.serialize_private()
        self.assertEqual(ns, "xprvA2JDeKCSNNZky6uBCviVfJSKyQ1mDYahRjijr5idH2WwLsEd4Hsb2Tyh8RfQMuPh7f7RtyzTtdrbdqqsunu5Mm3wDvUAKRHSC34sJ7in334")
        ns2 = bip32.deserialize(ns).serialize_private()
        self.assertEqual(ns2, ns)
        ns = n.serialize_public()
        self.assertEqual(ns, "xpub6FHa3pjLCk84BayeJxFW2SP4XRrFd1JYnxeLeU8EqN3vDfZmbqBqaGJAyiLjTAwm6ZLRQUMv1ZACTj37sR62cfN7fe5JnJ7dh8zL4fiyLHV")
        n2 = bip32.deserialize(ns)
        self.assertEqual(n2.private_key(), bytes(32))
        ns2 = n2.serialize_public()
        self.assertEqual(ns2, ns)

        # [Chain m/0'/1/2'/2/1000000000]
        n.derive(1000000000)
        self.assertEqual(n.fingerprint(), 0xd880d7d8)
        self.assertEqual(n.chain_code(), unhexlify("c783e67b921d2beb8f6b389cc646d7263b4145701dadd2161548a8b078e65e9e"))
        self.assertEqual(n.private_key(), unhexlify("471b76e389e528d6de6d816857e012c5455051cad6660850e58372a6c3e6e7c8"))
        self.assertEqual(n.public_key(), unhexlify("022a471424da5e657499d1ff51cb43c47481a03b1e77f951fe64cec9f5a48f7011"))
        ns = n.serialize_private()
        self.assertEqual(ns, "xprvA41z7zogVVwxVSgdKUHDy1SKmdb533PjDz7J6N6mV6uS3ze1ai8FHa8kmHScGpWmj4WggLyQjgPie1rFSruoUihUZREPSL39UNdE3BBDu76")
        ns2 = bip32.deserialize(ns).serialize_private()
        self.assertEqual(ns2, ns)
        ns = n.serialize_public()
        self.assertEqual(ns, "xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy")
        n2 = bip32.deserialize(ns)
        self.assertEqual(n2.private_key(), bytes(32))
        ns2 = n2.serialize_public()
        self.assertEqual(ns2, ns)

if __name__ == '__main__':
    unittest.main()
