from common import *
from apps.common import HARDENED, coins
from apps.common.seed import Keychain, Slip21Node, _path_hardened
from apps.wallet.sign_tx import scripts, addresses
from trezor import wire
from trezor.crypto import bip39
from trezor.crypto.curve import secp256k1

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
            with self.assertRaises(wire.DataError):
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
            with self.assertRaises(wire.DataError):
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

        with self.assertRaises(wire.DataError):
            k.validate_path([1, 2, 3, 4], "ed25519")
            k.validate_path([], "ed25519")

    def test_path_hardened(self):
        self.assertTrue(_path_hardened([44 | HARDENED, 1 | HARDENED, 0 | HARDENED]))
        self.assertTrue(_path_hardened([0 | HARDENED, ]))

        self.assertFalse(_path_hardened([44, 44 | HARDENED, 0 | HARDENED]))
        self.assertFalse(_path_hardened([0, ]))
        self.assertFalse(_path_hardened([44 | HARDENED, 1 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0]))

    def test_slip21(self):
        seed = bip39.seed(' '.join(['all'] * 12), '')
        node1 = Slip21Node(seed)
        node2 = node1.clone()
        keychain = Keychain(seed, [["slip21", b"SLIP-0021"]])

        # Key(m)
        KEY_M = unhexlify(b"dbf12b44133eaab506a740f6565cc117228cbf1dd70635cfa8ddfdc9af734756")
        self.assertEqual(node1.key(), KEY_M)

        # Key(m/"SLIP-0021")
        KEY_M_SLIP0021 = unhexlify(b"1d065e3ac1bbe5c7fad32cf2305f7d709dc070d672044a19e610c77cdf33de0d")
        node1.derive_path([b"SLIP-0021"])
        self.assertEqual(node1.key(), KEY_M_SLIP0021)
        self.assertIsNone(keychain.validate_path([b"SLIP-0021"], "slip21"))
        self.assertEqual(keychain.derive([b"SLIP-0021"], "slip21").key(), KEY_M_SLIP0021)

        # Key(m/"SLIP-0021"/"Master encryption key")
        KEY_M_SLIP0021_MEK = unhexlify(b"ea163130e35bbafdf5ddee97a17b39cef2be4b4f390180d65b54cf05c6a82fde")
        node1.derive_path([b"Master encryption key"])
        self.assertEqual(node1.key(), KEY_M_SLIP0021_MEK)
        self.assertIsNone(keychain.validate_path([b"SLIP-0021", b"Master encryption key"], "slip21"))
        self.assertEqual(keychain.derive([b"SLIP-0021", b"Master encryption key"], "slip21").key(), KEY_M_SLIP0021_MEK)

        # Key(m/"SLIP-0021"/"Authentication key")
        KEY_M_SLIP0021_AK = unhexlify(b"47194e938ab24cc82bfa25f6486ed54bebe79c40ae2a5a32ea6db294d81861a6")
        node2.derive_path([b"SLIP-0021", b"Authentication key"])
        self.assertEqual(node2.key(), KEY_M_SLIP0021_AK)
        self.assertIsNone(keychain.validate_path([b"SLIP-0021", b"Authentication key"], "slip21"))
        self.assertEqual(keychain.derive([b"SLIP-0021", b"Authentication key"], "slip21").key(), KEY_M_SLIP0021_AK)

        # Forbidden paths.
        with self.assertRaises(wire.DataError):
            self.assertFalse(keychain.validate_path([], "slip21"))
        with self.assertRaises(wire.DataError):
            self.assertFalse(keychain.validate_path([b"SLIP-9999", b"Authentication key"], "slip21"))
        with self.assertRaises(wire.DataError):
            keychain.derive([b"SLIP-9999", b"Authentication key"], "slip21").key()

    def test_slip77(self):
        seed = bip39.seed("alcohol woman abuse must during monitor noble actual mixed trade anger aisle", "")
        keychain = Keychain(seed, [["slip21", b"SLIP-0077"], ["secp256k1"]])

        node = keychain.derive([44 | HARDENED, 1 | HARDENED, 0 | HARDENED, 0, 0])
        coin = coins.by_name('Elements')
        pubkey_hash = addresses.ecdsa_hash_pubkey(node.public_key(), coin)
        script = scripts.output_script_p2pkh(pubkey_hash)

        private_key = keychain.derive_slip77_blinding_private_key(script)
        self.assertEqual(private_key, unhexlify(b"26f1dc2c52222394236d76e0809516255cfcca94069fd5187c0f090d18f42ad6"))
        public_key = keychain.derive_slip77_blinding_public_key(script)
        self.assertEqual(public_key, unhexlify(b"03e84cd853fea825bd94f5d2d46580ae0d059c734707fa7a08f5e2f612a51c1acb"))
        self.assertEqual(secp256k1.publickey(private_key), public_key)


if __name__ == '__main__':
    unittest.main()
