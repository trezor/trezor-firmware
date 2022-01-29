from common import *

from trezor.crypto import random
from trezor.crypto.curve import bip340


class TestCryptoBip340(unittest.TestCase):
    # Test vectors from https://github.com/bitcoin/bips/blob/master/bip-0340/test-vectors.csv
    vectors = [
        (
            "0000000000000000000000000000000000000000000000000000000000000003",
            "F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9",
        ),
        (
            "B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF",
            "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
        ),
        (
            "C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9",
            "DD308AFEC5777E13121FA72B9CC1B7CC0139715309B086C960E18FD969774EB8",
        ),
        (
            "0B432B2677937381AEF05BB02A66ECD012773062CF3FA2549E44F58ED2401710",
            "25D1DFF95105F5253C4022F628A996AD3A0D95FBF21D468A1B33F8C160D8F517",
        ),
    ]

    def test_generate_secret(self):
        for _ in range(100):
            sk = bip340.generate_secret()
            self.assertTrue(len(sk) == 32)
            self.assertTrue(sk != b"\x00" * 32)
            self.assertTrue(
                sk
                < b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE\xBA\xAE\xDC\xE6\xAF\x48\xA0\x3B\xBF\xD2\x5E\x8C\xD0\x36\x41\x41"
            )

    def test_publickey(self):
        for sk, pk in self.vectors:
            pk_computed = hexlify(bip340.publickey(unhexlify(sk))).decode()
            self.assertEqual(str(pk_computed).upper(), pk)

    def test_sign_verify_random(self):
        for _ in range(100):
            sk = bip340.generate_secret()
            pk = bip340.publickey(sk)
            dig = random.bytes(32)
            sig = bip340.sign(sk, dig)
            self.assertTrue(bip340.verify(pk, sig, dig))


if __name__ == "__main__":
    unittest.main()
