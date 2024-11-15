# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto import bip32, bip39
from trezor.crypto.curve import secp256k1

if not utils.BITCOIN_ONLY:
    from apps.eos.helpers import public_key_to_wif


# NOTE: copy-pasted from apps.eos.get_public_key
def _get_public_key(node: bip32.HDNode) -> tuple[str, bytes]:
    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, True)
    wif = public_key_to_wif(public_key)
    return wif, public_key


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEosGetPublicKey(unittest.TestCase):
    def test_get_public_key_scheme(self):
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        seed = bip39.seed(mnemonic, "")

        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 194, 0x80000000, 0, 0],
            [0x80000000 | 44, 0x80000000 | 194, 0x80000000, 0, 1],
            [0x80000000 | 44, 0x80000000 | 194],
            [0x80000000 | 44, 0x80000000 | 194, 0x80000000, 0, 0x80000000],
        ]

        public_keys = [
            b"0315c358024ce46767102578947584c4342a6982b922d454f63588effa34597197",
            b"029622eff7248c4d298fe28f2df19ee0d5f7674f678844e05c31d1a5632412869e",
            b"02625f33c10399703e95e41bd5054beef3ab893dcc7df2bb9bdcee48359b29069d",
            b"037c9b7d24d42589941cca3f4debc75b37c0e7b881e6eb00d2e674958debe3bbc3",
        ]

        wif_keys = [
            "EOS6zpSNY1YoLxNt2VsvJjoDfBueU6xC1M1ERJw1UoekL1NHn8KNA",
            "EOS62cPUiWnLqbUjiBMxbEU4pm4Hp5X3RGk4KMTadvZNygjX72yHW",
            "EOS5dp8aCFoFwrKo6KuUfos1hwMfZGkiZUbaF2CyuD4chyBEN2wQK",
            "EOS7n7TXwR4Y3DtPt2ji6akhQi5uw4SruuPArvoNJso84vhwPQt1G",
        ]

        for index, path in enumerate(derivation_paths):
            node = bip32.from_seed(seed, "secp256k1")
            node.derive_path(path)
            wif, public_key = _get_public_key(node)

            self.assertEqual(hexlify(public_key), public_keys[index])
            self.assertEqual(wif, wif_keys[index])
            self.assertEqual(public_key_to_wif(public_key), wif_keys[index])


if __name__ == "__main__":
    unittest.main()
