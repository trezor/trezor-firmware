# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto import base32


class TestCryptoBase32(unittest.TestCase):

    # test vectors from:
    # https://tools.ietf.org/html/rfc4648
    # https://github.com/emn178/hi-base32/blob/master/tests/test.js
    vectors = [
        (b"", ""),
        (b"f", "MY======"),
        (b"fo", "MZXQ===="),
        (b"foo", "MZXW6==="),
        (b"foob", "MZXW6YQ="),
        (b"fooba", "MZXW6YTB"),
        (b"foobar", "MZXW6YTBOI======"),
        (b"H", "JA======"),
        (b"He", "JBSQ===="),
        (b"Hel", "JBSWY==="),
        (b"Hell", "JBSWY3A="),
        (b"Hello", "JBSWY3DP"),
        (
            b"zlutoucky kun upel dabelske ody",
            "PJWHK5DPOVRWW6JANN2W4IDVOBSWYIDEMFRGK3DTNNSSA33EPE======",
        ),
        ("中文".encode(), "4S4K3ZUWQ4======"),
        ("中文1".encode(), "4S4K3ZUWQ4YQ===="),
        ("中文12".encode(), "4S4K3ZUWQ4YTE==="),
        ("aécio".encode(), "MHB2SY3JN4======"),
        ("𠜎".encode(), "6CQJZDQ="),
        (
            "Base64是一種基於64個可列印字元來表示二進制資料的表示方法".encode(),
            "IJQXGZJWGTTJRL7EXCAOPKFO4WP3VZUWXQ3DJZMARPSY7L7FRCL6LDNQ4WWZPZMFQPSL5BXIUGUOPJF24S5IZ2MAWLSYRNXIWOD6NFUZ46NIJ2FBVDT2JOXGS246NM4V",
        ),
    ]

    def test_encode(self):
        for a, b in self.vectors:
            self.assertEqual(base32.encode(a), b)

    def test_decode(self):
        for a, b in self.vectors:
            self.assertEqual(base32.decode(b), a)


if __name__ == "__main__":
    unittest.main()
