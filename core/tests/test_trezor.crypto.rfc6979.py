from common import unhexlify, unittest

from trezor.crypto import rfc6979
from trezor.crypto.hashlib import sha256


class TestCryptoRfc6979(unittest.TestCase):

    def test_vectors(self):

        vectors = [
            ("c9afa9d845ba75166b5c215767b1d6934e50c3db36e89b127b8a622b120f6721",
             "sample",
             "a6e3c57dd01abe90086538398355dd4c3b17aa873382b0f24d6129493d8aad60"),
            ("cca9fbcc1b41e5a95d369eaa6ddcff73b61a4efaa279cfc6567e8daa39cbaf50",
             "sample",
             "2df40ca70e639d89528a6b670d9d48d9165fdc0febc0974056bdce192b8e16a3"),
            ("0000000000000000000000000000000000000000000000000000000000000001",
             "Satoshi Nakamoto",
             "8f8a276c19f4149656b280621e358cce24f5f52542772691ee69063b74f15d15"),
            ("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364140",
             "Satoshi Nakamoto",
             "33a19b60e25fb6f4435af53a3d42d493644827367e6453928554f43e49aa6f90"),
            ("f8b8af8ce3c7cca5e300d33939540c10d45ce001b8f252bfbc57ba0342904181",
             "Alan Turing", "525a82b70e67874398067543fd84c83d30c175fdc45fdeee082fe13b1d7cfdf1"),
            ("0000000000000000000000000000000000000000000000000000000000000001",
             "All those moments will be lost in time, like tears in rain. Time to die...",
             "38aa22d72376b4dbc472e06c3ba403ee0a394da63fc58d88686c611aba98d6b3"),
            ("e91671c46231f833a6406ccbea0e3e392c76c167bac1cb013f6f1013980455c2",
             "There is a computer disease that anybody who works with computers knows about. It's a very serious disease and it interferes completely with the work. The trouble with computers is that you 'play' with them!",
             "1f4b84c23a86a221d233f2521be018d9318639d5b8bbd6374a8a59232d16ad3d"),
        ]

        for key, msg, k in vectors:
            rng = rfc6979(unhexlify(key), sha256(msg).digest())
            self.assertEqual(rng.next(), unhexlify(k))


if __name__ == '__main__':
    unittest.main()
