from common import *
from apps.common.paths import HARDENED
from apps.ripple.helpers import address_from_public_key, validate_full_path


class TestRippleAddress(unittest.TestCase):

    def test_pubkey_to_address(self):
        addr = address_from_public_key(unhexlify('ed9434799226374926eda3b54b1b461b4abf7237962eae18528fea67595397fa32'))
        self.assertEqual(addr, 'rDTXLQ7ZKZVKz33zJbHjgVShjsBnqMBhmN')

        addr = address_from_public_key(unhexlify('03e2b079e9b09ae8916da8f5ee40cbda9578dbe7c820553fe4d5f872eec7b1fdd4'))
        self.assertEqual(addr, 'rhq549rEtUrJowuxQC2WsHNGLjAjBQdAe8')

        addr = address_from_public_key(unhexlify('0282ee731039929e97db6aec242002e9aa62cd62b989136df231f4bb9b8b7c7eb2'))
        self.assertEqual(addr, 'rKzE5DTyF9G6z7k7j27T2xEas2eMo85kmw')

    def test_paths(self):
        # 44'/144'/a'/0/0 is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 144 | HARDENED],
            [44 | HARDENED, 144 | HARDENED, 0],
            [44 | HARDENED, 144 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 144 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 144 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 144 | HARDENED, 0 | HARDENED, 0, 5],
            [44 | HARDENED, 144 | HARDENED, 9999 | HARDENED],
            [44 | HARDENED, 144 | HARDENED, 9999000 | HARDENED, 0, 0],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0],
            [1 | HARDENED, 1 | HARDENED, 1 | HARDENED],
        ]
        correct_paths = [
            [44 | HARDENED, 144 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 144 | HARDENED, 3 | HARDENED, 0, 0],
            [44 | HARDENED, 144 | HARDENED, 9 | HARDENED, 0, 0],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == '__main__':
    unittest.main()
