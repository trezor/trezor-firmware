from common import *

from storage import cache
from apps.common import HARDENED, coins
from apps.common.seed import Keychain, Slip21Node, _path_hardened, get_keychain, with_slip44_keychain
from apps.wallet.sign_tx import scripts, addresses
from trezor import wire
from trezor.crypto import bip39
from trezor.crypto.curve import secp256k1

class TestKeychain(unittest.TestCase):

    def test_match_path(self):
        n = [
            ("ed25519", [44 | HARDENED, 134 | HARDENED]),
            ("secp256k1", [44 | HARDENED, 11 | HARDENED]),
        ]
        k = Keychain(b"", n)

        correct = (
            ([44 | HARDENED, 134 | HARDENED], "ed25519"),
            ([44 | HARDENED, 11 | HARDENED], "secp256k1"),
            ([44 | HARDENED, 11 | HARDENED, 12], "secp256k1"),
        )
        for path, curve in correct:
            i, suffix = k.match_path(path)
            ns_curve, ns = k.namespaces[i]
            self.assertEqual(curve, ns_curve)

        fails = [
            [44 | HARDENED, 134],  # path does not match
            [44, 134],  # path does not match (non-hardened items)
            [44 | HARDENED, 134 | HARDENED, 123],  # non-hardened item in ed25519 ns
            [44 | HARDENED, 13 | HARDENED],  # invalid second item
        ]
        for f in fails:
            with self.assertRaises(wire.DataError):
                k.match_path(f)

    def test_match_path_special_ed25519(self):
        n = [
            ("ed25519-keccak", [44 | HARDENED, 134 | HARDENED]),
        ]
        k = Keychain(b"", n)

        correct = (
            [44 | HARDENED, 134 | HARDENED],
        )
        for c in correct:
            k.match_path(c)

        fails = [
            [44 | HARDENED, 134 | HARDENED, 1], 
        ]
        for f in fails:
            with self.assertRaises(wire.DataError):
                k.match_path(f)

    def test_match_path_empty_namespace(self):
        k = Keychain(b"", [("secp256k1", [])])
        correct = (
            [],
            [1, 2, 3, 4],
            [44 | HARDENED, 11 | HARDENED],
            [44 | HARDENED, 11 | HARDENED, 12],
        )
        for c in correct:
            k.match_path(c)

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
        keychain = Keychain(seed, [("slip21", [b"SLIP-0021"])])

        # Key(m)
        KEY_M = unhexlify(b"dbf12b44133eaab506a740f6565cc117228cbf1dd70635cfa8ddfdc9af734756")
        self.assertEqual(node1.key(), KEY_M)

        # Key(m/"SLIP-0021")
        KEY_M_SLIP0021 = unhexlify(b"1d065e3ac1bbe5c7fad32cf2305f7d709dc070d672044a19e610c77cdf33de0d")
        node1.derive_path([b"SLIP-0021"])
        self.assertEqual(node1.key(), KEY_M_SLIP0021)
        keychain.match_path([b"SLIP-0021"])
        self.assertEqual(keychain.derive([b"SLIP-0021"]).key(), KEY_M_SLIP0021)

        # Key(m/"SLIP-0021"/"Master encryption key")
        KEY_M_SLIP0021_MEK = unhexlify(b"ea163130e35bbafdf5ddee97a17b39cef2be4b4f390180d65b54cf05c6a82fde")
        node1.derive_path([b"Master encryption key"])
        self.assertEqual(node1.key(), KEY_M_SLIP0021_MEK)
        keychain.match_path([b"SLIP-0021", b"Master encryption key"])
        self.assertEqual(keychain.derive([b"SLIP-0021", b"Master encryption key"]).key(), KEY_M_SLIP0021_MEK)

        # Key(m/"SLIP-0021"/"Authentication key")
        KEY_M_SLIP0021_AK = unhexlify(b"47194e938ab24cc82bfa25f6486ed54bebe79c40ae2a5a32ea6db294d81861a6")
        node2.derive_path([b"SLIP-0021", b"Authentication key"])
        self.assertEqual(node2.key(), KEY_M_SLIP0021_AK)
        keychain.match_path([b"SLIP-0021", b"Authentication key"])
        self.assertEqual(keychain.derive([b"SLIP-0021", b"Authentication key"]).key(), KEY_M_SLIP0021_AK)

        # Forbidden paths.
        with self.assertRaises(wire.DataError):
            self.assertFalse(keychain.match_path([]))
        with self.assertRaises(wire.DataError):
            self.assertFalse(keychain.match_path([b"SLIP-9999", b"Authentication key"]))
        with self.assertRaises(wire.DataError):
            keychain.derive([b"SLIP-9999", b"Authentication key"]).key()

    def test_get_keychain(self):
        seed = bip39.seed(' '.join(['all'] * 12), '')
        cache.start_session()
        cache.set(cache.APP_COMMON_SEED, seed)

        namespaces = [("secp256k1", [44 | HARDENED])]
        keychain = await_result(get_keychain(wire.DUMMY_CONTEXT, namespaces))

        # valid path:
        self.assertIsNotNone(keychain.derive([44 | HARDENED, 1 | HARDENED]))

        # invalid path:
        with self.assertRaises(wire.DataError):
            keychain.derive([44])

    def test_with_slip44(self):
        seed = bip39.seed(' '.join(['all'] * 12), '')
        cache.start_session()
        cache.set(cache.APP_COMMON_SEED, seed)

        slip44_id = 42
        valid_path = [44 | HARDENED, slip44_id | HARDENED]
        invalid_path = [44 | HARDENED, 99 | HARDENED]
        testnet_path = [44 | HARDENED, 1 | HARDENED]

        def check_valid_paths(keychain, *paths):
            for path in paths:
                self.assertIsNotNone(keychain.derive(path))

        def check_invalid_paths(keychain, *paths):
            for path in paths:
                self.assertRaises(wire.DataError, keychain.derive, path)

        @with_slip44_keychain(slip44_id)
        async def func_id_only(ctx, msg, keychain):
            check_valid_paths(keychain, valid_path)
            check_invalid_paths(keychain, testnet_path, invalid_path)

        @with_slip44_keychain(slip44_id, allow_testnet=True)
        async def func_allow_testnet(ctx, msg, keychain):
            check_valid_paths(keychain, valid_path, testnet_path)
            check_invalid_paths(keychain, invalid_path)

        @with_slip44_keychain(slip44_id, curve="ed25519")
        async def func_with_curve(ctx, msg, keychain):
            check_valid_paths(keychain, valid_path)
            check_invalid_paths(keychain, testnet_path, invalid_path)

            i, _ = keychain.match_path(valid_path)
            ns_curve, ns = keychain.namespaces[i]
            self.assertEqual(ns_curve, "ed25519")

        await_result(func_id_only(wire.DUMMY_CONTEXT, None))
        await_result(func_allow_testnet(wire.DUMMY_CONTEXT, None))
        await_result(func_with_curve(wire.DUMMY_CONTEXT, None))



if __name__ == '__main__':
    unittest.main()
