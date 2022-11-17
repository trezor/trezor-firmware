"""
source: https://github.com/zcash-hackworks/zcash-test-vectors/blob/master/zcash_test_vectors/ff1.py
"""

from common import *

if not utils.BITCOIN_ONLY:
    from apps.zcash.orchard.crypto.ff1 import ff1_aes256_encrypt, aes_cbcmac

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashFF1(unittest.TestCase):
    def test_ff1_aes(self):
        KEY        = unhexlify("0000000000000000000000000000000000000000000000000000000000000000")
        PLAINTEXT  = unhexlify("80000000000000000000000000000000")
        CIPHERTEXT = unhexlify("ddc6bf790c15760d8d9aeb6f9a75fd4e")
        self.assertEqual(aes_cbcmac(KEY, PLAINTEXT), CIPHERTEXT)

        key = unhexlify("f9e8389f5b80712e3886cc1fa2d28a3b8c9cd88a2d4a54c6aa86ce0fef944be0")
        acc = unhexlify("b379777f9050e2a818f2940cbbd9aba4")
        ct  = unhexlify("6893ebaf0a1fccc704326529fdfb60db")
        for i in range(1000):
            acc = aes_cbcmac(key, acc)
        self.assertEqual(acc, ct)

    def test_ff1_aes256_encrypt(self):
        key = unhexlify("2B7E151628AED2A6ABF7158809CF4F3CEF4359D8D580AA4F7F036D6F04FC6A94")

        test_vectors = [
            {
                "tweak": b'',
                "pt": [0]*88,
                "ct": list(map(int, "0000100100110101011101111111110011000001101100111110011101110101011010100100010011001111")),
            },
            {
                "tweak": b'',
                "pt": list(map(int, "0000100100110101011101111111110011000001101100111110011101110101011010100100010011001111")),
                "ct": list(map(int, "1101101011010001100011110000010011001111110110011101010110100001111001000101011111011000")),
            },
            {
                "tweak": b'',
                "pt": [0, 1]*44,
                "ct": list(map(int, "0000111101000001111011010111011111110001100101000000001101101110100010010111001100100110")),
            },
            {
                "tweak": bytes(range(255)),
                "pt": [0, 1]*44,
                "ct": list(map(int, "0111110110001000000111010110000100010101101000000011100111100100100010101101111010100011")),
            },
        ]

        for tv in test_vectors:
            ct = ff1_aes256_encrypt(key, tv["tweak"], iter(tv["pt"]))
            self.assertEqual(list(ct), tv["ct"])

if __name__ == "__main__":
    unittest.main()
