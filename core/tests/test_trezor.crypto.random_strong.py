# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto import random

# On the emulator every entropy source is deterministic and unique.
#
# Asserting exact strong-RNG output verifies, end to end through the
# upymod binding and rng_fill_buffer_strong(), that every entropy source of
# the model contributed at every byte position. A dropped source, a lost
# strong=True, a truncated buffer each produce a different, wrong answer.

# generated with tools/gen_rng_mock_vectors.py --plain / --model MODEL
_PLAIN = "ccc07780286893c51eef095d7b83e887171d1fafdd2b26477d1db3306a583c73"
_STRONG = {
    "T2T1": "ccc07780286893c51eef095d7b83e887171d1fafdd2b26477d1db3306a583c73",
    "T2B1": "3bb68a45c8e628aaf3d1c251f406513c5ca95c6c61a73ac8454167d9a0c37bf3",
    "T3B1": "3bb68a45c8e628aaf3d1c251f406513c5ca95c6c61a73ac8454167d9a0c37bf3",
    "T3T1": "3bb68a45c8e628aaf3d1c251f406513c5ca95c6c61a73ac8454167d9a0c37bf3",
    "T3W1": "af5f5d845074ad2c85a11a28aef337677d022951da5856e7231ab050d420db18",
}


class TestCryptoRandomStrong(unittest.TestCase):
    def test_weak(self):
        random.reseed(0)
        self.assertEqual(random.bytes(32).hex(), _PLAIN)

    def test_strong(self):
        expected = _STRONG[utils.INTERNAL_MODEL]

        random.reseed(0)
        self.assertEqual(random.bytes(32, True).hex(), expected)

    def test_reseed_isolation(self):
        random.reseed(0)
        a = random.bytes(32, True)
        random.reseed(1)
        b = random.bytes(32, True)
        random.reseed(0)
        c = random.bytes(32, True)
        self.assertNotEqual(a, b)
        self.assertEqual(a, c)


if __name__ == "__main__":
    unittest.main()
