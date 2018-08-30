from common import *
from apps.common import HARDENED
from apps.common.paths import validate_path_for_get_public_key, is_hardened


class TestPaths(unittest.TestCase):

    def test_is_hardened(self):
        self.assertTrue(is_hardened(44 | HARDENED))
        self.assertTrue(is_hardened(0 | HARDENED))
        self.assertTrue(is_hardened(99999 | HARDENED))

        self.assertFalse(is_hardened(44))
        self.assertFalse(is_hardened(0))
        self.assertFalse(is_hardened(99999))

    def test_path_for_get_public_key(self):
        # 44'/41'/0'
        self.assertTrue(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED], 41))
        # 44'/111'/0'
        self.assertTrue(validate_path_for_get_public_key([44 | HARDENED, 111 | HARDENED, 0 | HARDENED], 111))
        # 44'/0'/0'/0
        self.assertTrue(validate_path_for_get_public_key([44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0], 0))
        # 44'/0'/0'/0/0
        self.assertTrue(validate_path_for_get_public_key([44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0, 0], 0))

        # 44'/41'
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED], 41))
        # 44'/41'/0
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0], 41))
        # 44'/41'/0' slip44 mismatch
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED], 99))
        # # 44'/41'/0'/0'
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED, 0 | HARDENED], 41))
        # # 44'/41'/0'/0'/0
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0], 41))
        # # 44'/41'/0'/0'/0'
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED], 41))
        # # 44'/41'/0'/0/0/0
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED, 0, 0, 0], 41))
        # # 44'/41'/0'/0/0'
        self.assertFalse(validate_path_for_get_public_key([44 | HARDENED, 41 | HARDENED, 0 | HARDENED, 0, 0 | HARDENED], 41))


if __name__ == '__main__':
    unittest.main()
