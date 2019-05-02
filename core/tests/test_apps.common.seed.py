from common import unittest
from apps.common import HARDENED
from apps.common.seed import Keychain, _path_hardened
from trezor.wire.errors import DataError


class TestKeychain(unittest.TestCase):

    def test_validate_path(self):
        n = [
            ["ed25519", 44 | HARDENED, 134 | HARDENED],
            ["secp256k1", 44 | HARDENED, 11 | HARDENED],
        ]
        k = Keychain(b"", n)

        correct = (
            ([44 | HARDENED, 134 | HARDENED], "ed25519"),
            ([44 | HARDENED, 11 | HARDENED], "secp256k1"),
            ([44 | HARDENED, 11 | HARDENED, 12], "secp256k1"),
        )
        for c in correct:
            self.assertEqual(None, k.validate_path(*c))

        fails = [
            ([44 | HARDENED, 134], "ed25519"),  # path does not match
            ([44 | HARDENED, 134], "secp256k1"),  # curve and path does not match
            ([44 | HARDENED, 134 | HARDENED], "nist256p"),  # curve not included
            ([44, 134], "ed25519"),  # path does not match (non-hardened items)
            ([44 | HARDENED, 134 | HARDENED, 123], "ed25519"),  # non-hardened item in ed25519
            ([44 | HARDENED, 13 | HARDENED], "secp256k1"),  # invalid second item
        ]
        for f in fails:
            with self.assertRaises(DataError):
                k.validate_path(*f)

    def test_validate_path_special_ed25519(self):
        n = [
            ["ed25519-keccak", 44 | HARDENED, 134 | HARDENED],
        ]
        k = Keychain(b"", n)

        correct = (
            ([44 | HARDENED, 134 | HARDENED], "ed25519-keccak"),
        )
        for c in correct:
            self.assertEqual(None, k.validate_path(*c))

        fails = [
            ([44 | HARDENED, 134 | HARDENED, 1], "ed25519-keccak"),
        ]
        for f in fails:
            with self.assertRaises(DataError):
                k.validate_path(*f)

    def test_validate_path_empty_namespace(self):
        k = Keychain(b"", [["secp256k1"]])
        correct = (
            ([], "secp256k1"),
            ([1, 2, 3, 4], "secp256k1"),
            ([44 | HARDENED, 11 | HARDENED], "secp256k1"),
            ([44 | HARDENED, 11 | HARDENED, 12], "secp256k1"),
        )
        for c in correct:
            self.assertEqual(None, k.validate_path(*c))

        with self.assertRaises(DataError):
            k.validate_path([1, 2, 3, 4], "ed25519")
            k.validate_path([], "ed25519")

    def test_path_hardened(self):
        self.assertTrue(_path_hardened([44 | HARDENED, 1 | HARDENED, 0 | HARDENED]))
        self.assertTrue(_path_hardened([0 | HARDENED, ]))

        self.assertFalse(_path_hardened([44, 44 | HARDENED, 0 | HARDENED]))
        self.assertFalse(_path_hardened([0, ]))
        self.assertFalse(_path_hardened([44 | HARDENED, 1 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0]))


if __name__ == '__main__':
    unittest.main()
