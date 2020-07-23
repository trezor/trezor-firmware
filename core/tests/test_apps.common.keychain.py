from common import *

from mock_storage import mock_storage

from storage import cache
import storage.device
from apps.common import HARDENED
from apps.common.paths import path_is_hardened
from apps.common.keychain import LRUCache, Keychain, with_slip44_keychain, get_keychain
from trezor import wire
from trezor.crypto import bip39


class TestKeychain(unittest.TestCase):
    @mock_storage
    def test_verify_path(self):
        n = [
            [44 | HARDENED, 134 | HARDENED],
            [44 | HARDENED, 11 | HARDENED],
        ]
        keychain = Keychain(b"", "secp256k1", n)

        correct = (
            [44 | HARDENED, 134 | HARDENED],
            [44 | HARDENED, 11 | HARDENED],
            [44 | HARDENED, 11 | HARDENED, 12],
        )
        for path in correct:
            keychain.verify_path(path)

        fails = (
            [44 | HARDENED, 134],  # path does not match
            [44, 134],  # path does not match (non-hardened items)
            [44 | HARDENED, 13 | HARDENED],  # invalid second item
        )
        for f in fails:
            with self.assertRaises(wire.DataError):
                keychain.verify_path(f)

        # turn off restrictions
        storage.device.set_unsafe_prompts_allowed(True)
        for path in correct + fails:
            keychain.verify_path(path)

    def test_verify_path_special_ed25519(self):
        n = [[44 | HARDENED, 134 | HARDENED]]
        k = Keychain(b"", "ed25519-keccak", n)

        # OK case
        k.verify_path([44 | HARDENED, 134 | HARDENED])

        # failing case: non-hardened component with ed25519-like derivation
        with self.assertRaises(wire.DataError):
            k.verify_path([44 | HARDENED, 134 | HARDENED, 1])

    def test_verify_path_empty_namespace(self):
        k = Keychain(b"", "secp256k1", [[]])
        correct = (
            [],
            [1, 2, 3, 4],
            [44 | HARDENED, 11 | HARDENED],
            [44 | HARDENED, 11 | HARDENED, 12],
        )
        for c in correct:
            k.verify_path(c)

    def test_get_keychain(self):
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.start_session()
        cache.set(cache.APP_COMMON_SEED, seed)

        namespaces = [[44 | HARDENED]]
        keychain = await_result(
            get_keychain(wire.DUMMY_CONTEXT, "secp256k1", namespaces)
        )

        # valid path:
        self.assertIsNotNone(keychain.derive([44 | HARDENED, 1 | HARDENED]))

        # invalid path:
        with self.assertRaises(wire.DataError):
            keychain.derive([44])

    def test_with_slip44(self):
        seed = bip39.seed(" ".join(["all"] * 12), "")
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
            self.assertEqual(keychain.curve, "ed25519")
            check_valid_paths(keychain, valid_path)
            check_invalid_paths(keychain, testnet_path, invalid_path)

        await_result(func_id_only(wire.DUMMY_CONTEXT, None))
        await_result(func_allow_testnet(wire.DUMMY_CONTEXT, None))
        await_result(func_with_curve(wire.DUMMY_CONTEXT, None))

    def test_lru_cache(self):
        class Deletable:
            def __init__(self):
                self.deleted = False

            def __del__(self):
                self.deleted = True

        cache = LRUCache(10)

        obj_a = Deletable()
        self.assertIsNone(cache.get("a"))
        cache.insert("a", obj_a)

        self.assertIs(cache.get("a"), obj_a)

        # test eviction
        objects = [(i, Deletable()) for i in range(10)]
        for key, obj in objects:
            cache.insert(key, obj)

        # object A should have been evicted
        self.assertIsNone(cache.get("a"))
        self.assertTrue(obj_a.deleted)

        cache.insert("a", obj_a)
        for key, obj in objects[:-1]:
            # objects should have been evicted in insertion order
            self.assertIsNone(cache.get(key))
            self.assertTrue(obj.deleted)
            cache.insert(key, obj)

        # use "a" object
        self.assertIs(cache.get("a"), obj_a)
        # insert last object
        key, obj = objects[-1]
        cache.insert(key, obj)

        # "a" is recently used so should not be evicted now
        self.assertIs(cache.get("a"), obj_a)


if __name__ == "__main__":
    unittest.main()
