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
_PLAIN = "5ff36e3c32295047e9f6ccd13453f9aa03e5526286c62e9f2d6cfe57a85fd9a3"
_STRONG = {
    "T2T1": "5ff36e3c32295047e9f6ccd13453f9aa03e5526286c62e9f2d6cfe57a85fd9a3",
    "T2B1": "dc1c9346ad9293c4a46f345ce03d4cd611514ad676c42a69355e7fabda58dbbf",
    "T3B1": "dc1c9346ad9293c4a46f345ce03d4cd611514ad676c42a69355e7fabda58dbbf",
    "T3T1": "dc1c9346ad9293c4a46f345ce03d4cd611514ad676c42a69355e7fabda58dbbf",
    "T3W1": "67bff2eb8e3590101f015152cadab88b3f29c9fb7e112840262cdab4041e0858",
}


class TestCryptoRandomStrong(unittest.TestCase):
    def test_weak(self):
        random.reseed(0)
        self.assertEqual(hexlify(random.bytes(32)).decode(), _PLAIN)

    def test_strong(self):
        expected = _STRONG[utils.INTERNAL_MODEL]

        random.reseed(0)
        self.assertEqual(hexlify(random.bytes(32, True)).decode(), expected)

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
