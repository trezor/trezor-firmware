# flake8: noqa: F403,F405
from common import *  # isort:skip

if utils.USE_TROPIC:
    from trezor.crypto import tropic


@unittest.skipUnless(utils.USE_TROPIC, "tropic")
class TestCryptoTropic(unittest.TestCase):
    def test_ping(self):
        self.assertEqual(tropic.ping(""), "")
        self.assertEqual(tropic.ping("HeLlO!"), "HeLlO!")

    def test_sign(self):
        key_index = 31
        try:
            tropic.sign(key_index, "ASD")
            assert False
        except tropic.TropicError as e:
            # key is not generated yet
            self.assertIn("lt_ecc_eddsa_sign failed", str(e).lower())

        tropic.key_generate(key_index)

        # signing should work now that we have a key
        self.assertEqual(len(tropic.sign(key_index, "a" * 32)), 64)


if __name__ == "__main__":
    unittest.main()
