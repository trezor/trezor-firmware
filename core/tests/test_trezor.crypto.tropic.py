from common import *  # isort:skip

from slip39_vectors import vectors
from trezor.crypto import tropic


class TestCryptoTropic(unittest.TestCase):
    def test_ping(self):
        self.assertEqual(tropic.ping("HeLlO!"), "HeLlO!")

    def test_get_certificate(self):
        self.assertEqual(len(tropic.get_certificate()), 512)

    def test_sign(self):
        try:
            tropic.sign(0, "ASD")
            assert False
        except ValueError as e:
            self.assertIn("invalid length", str(e).lower())

        tropic.key_generate(0)

        # signing should work now that we have a key
        self.assertEqual(len(tropic.sign(0, "a" * 32)), 64)

if __name__ == "__main__":
    unittest.main()
