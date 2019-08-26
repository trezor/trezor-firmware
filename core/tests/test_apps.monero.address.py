from common import *
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.monero.misc import validate_full_path


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroGetAddress(unittest.TestCase):

    def test_paths(self):
        # 44'/128'/a' is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 128 | HARDENED],
            [44 | HARDENED, 128 | HARDENED, 0],
            [44 | HARDENED, 128 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 128 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 128 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 128 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 128 | HARDENED, 9999000 | HARDENED],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0],
            [1 | HARDENED, 1 | HARDENED, 1 | HARDENED],
        ]
        correct_paths = [
            [44 | HARDENED, 128 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 128 | HARDENED, 3 | HARDENED],
            [44 | HARDENED, 128 | HARDENED, 9 | HARDENED],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == '__main__':
    unittest.main()
