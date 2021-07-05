from common import *

from mock_storage import mock_storage

from storage import cache
from apps.common import safety_checks
from apps.common.paths import PATTERN_SEP5, PathSchema
from apps.common.keychain import LRUCache, Keychain, with_slip44_keychain, get_keychain
from trezor import wire
from trezor.crypto import bip39
from trezor.messages import SafetyCheckLevel


class TestKeychain(unittest.TestCase):
    def setUp(self):
        cache.start_session()

    def tearDown(self):
        cache.clear_all()

    @mock_storage
    def test_verify_path(self):
        schemas = (
            PathSchema.parse("m/44'/coin_type'", slip44_id=134),
            PathSchema.parse("m/44'/coin_type'", slip44_id=11),
        )
        keychain = Keychain(b"", "secp256k1", schemas)

        correct = (
            [H_(44), H_(134)],
            [H_(44), H_(11)],
        )
        for path in correct:
            keychain.verify_path(path)

        fails = (
            [H_(44), 134],  # path does not match
            [44, 134],  # path does not match (non-hardened items)
            [H_(44), H_(13)],  # invalid second item
        )
        for f in fails:
            with self.assertRaises(wire.DataError):
                keychain.verify_path(f)

        # turn off restrictions
        safety_checks.apply_setting(SafetyCheckLevel.PromptTemporarily)
        for path in correct + fails:
            keychain.verify_path(path)

    def test_verify_path_special_ed25519(self):
        schema = PathSchema.parse("m/44'/coin_type'/*", slip44_id=134)
        k = Keychain(b"", "ed25519-keccak", [schema])

        # OK case
        k.verify_path([H_(44), H_(134)])

        # failing case: non-hardened component with ed25519-like derivation
        with self.assertRaises(wire.DataError):
            k.verify_path([H_(44), H_(134), 1])

    def test_no_schemas(self):
        k = Keychain(b"", "secp256k1", [])
        paths = (
            [],
            [1, 2, 3, 4],
            [H_(44), H_(11)],
            [H_(44), H_(11), 12],
        )
        for path in paths:
            self.assertRaises(wire.DataError, k.verify_path, path)

    def test_get_keychain(self):
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.set(cache.APP_COMMON_SEED, seed)

        schema = PathSchema.parse("m/44'/1'", 0)
        keychain = await_result(
            get_keychain(wire.DUMMY_CONTEXT, "secp256k1", [schema])
        )

        # valid path:
        self.assertIsNotNone(keychain.derive([H_(44), H_(1)]))

        # invalid path:
        with self.assertRaises(wire.DataError):
            keychain.derive([44])

    def test_with_slip44(self):
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.set(cache.APP_COMMON_SEED, seed)

        slip44_id = 42
        valid_path = [H_(44), H_(slip44_id), H_(0)]
        invalid_path = [H_(44), H_(99), H_(0)]
        testnet_path = [H_(44), H_(1), H_(0)]

        def check_valid_paths(keychain, *paths):
            for path in paths:
                self.assertIsNotNone(keychain.derive(path))

        def check_invalid_paths(keychain, *paths):
            for path in paths:
                self.assertRaises(wire.DataError, keychain.derive, path)

        @with_slip44_keychain(PATTERN_SEP5, slip44_id=slip44_id)
        async def func_id_only(ctx, msg, keychain):
            check_valid_paths(keychain, valid_path, testnet_path)
            check_invalid_paths(keychain, invalid_path)

        @with_slip44_keychain(PATTERN_SEP5, slip44_id=slip44_id, allow_testnet=False)
        async def func_disallow_testnet(ctx, msg, keychain):
            check_valid_paths(keychain, valid_path)
            check_invalid_paths(keychain, testnet_path, invalid_path)

        @with_slip44_keychain(PATTERN_SEP5, slip44_id=slip44_id, curve="ed25519")
        async def func_with_curve(ctx, msg, keychain):
            self.assertEqual(keychain.curve, "ed25519")
            check_valid_paths(keychain, valid_path, testnet_path)
            check_invalid_paths(keychain, invalid_path)

        await_result(func_id_only(wire.DUMMY_CONTEXT, None))
        await_result(func_disallow_testnet(wire.DUMMY_CONTEXT, None))
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
