# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import MockAsync, patch
from storage import cache, cache_common
from trezor import config, wire
from trezor.crypto import bip39
from trezor.wire import context

from apps.common.keychain import with_slip44_keychain
from apps.common.paths import PATTERN_SEP5

if utils.USE_WARD:
    import trezorward

    from apps.ward import WardApp, WardField, WardSchema, layout, open_ward, with_ward
    from apps.ward.keys import derive_wallet_id
    from apps.ward.store import WardError, WardStore

    class Text(WardField):
        def __init__(self, text):
            self.text = text

        @classmethod
        def from_bytes(cls, data):
            return cls(data.decode())

        def to_bytes(self):
            return self.text.encode()

        def format(self):
            return self.text

        def __eq__(self, other):
            return isinstance(other, Text) and other.text == self.text

    class Number(WardField):
        def __init__(self, number):
            self.number = number

        @classmethod
        def from_bytes(cls, data):
            if len(data) != 4:
                raise ValueError
            return cls(int.from_bytes(data, "big"))

        def to_bytes(self):
            return self.number.to_bytes(4, "big")

        def format(self):
            return str(self.number)

        def __eq__(self, other):
            return isinstance(other, Number) and other.number == self.number

    APP = WardApp.BITCOIN
    OTHER_APP = 2
    SCHEMA = WardSchema(APP, {1: Text, 2: Number})
    OTHER_SCHEMA = WardSchema(OTHER_APP, {1: Text, 2: Number})

if not utils.USE_THP:
    from storage import cache_codec

MNEMONIC = " ".join(["all"] * 12)
SEED = bip39.seed(MNEMONIC, "")
SEED_PASSPHRASE = bip39.seed(MNEMONIC, "TREZOR")


@unittest.skipUnless(utils.USE_WARD, "WARD is not enabled")
class TestWard(TestCaseWithContext):
    def setUp(self):
        config.init()
        config.wipe()
        if not utils.USE_THP:
            cache_codec.start_session()
        self.set_seed(SEED)
        self.confirm_store = MockAsync()
        self.confirm_delete = MockAsync()
        self.patches = (
            patch(layout, "confirm_store", self.confirm_store),
            patch(layout, "confirm_delete", self.confirm_delete),
        )
        for p in self.patches:
            p.__enter__()

    def tearDown(self):
        for p in self.patches:
            p.__exit__(None, None, None)
        cache.clear_all()

    def set_seed(self, seed):
        """Switch the current passphrase wallet."""
        context.cache_set(cache_common.APP_COMMON_SEED, seed)

    def open(self, schema=None):
        return await_result(open_ward(SCHEMA if schema is None else schema))

    def set_raw(self, key, value):
        """Store a raw record of `APP` in the current passphrase wallet."""
        trezorward.set(await_result(derive_wallet_id()), APP, key, value)

    def test_derive_wallet_id(self):
        # SLIP21(seed, [b"ward", b"wallet_id"]).key()
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "9cb4e6cc69b9ca91dcebde45f8f9c3351894bd0d7ca15c6c53253f9bf50f9137"
            ),
        )
        self.set_seed(SEED_PASSPHRASE)
        self.assertEqual(
            await_result(derive_wallet_id()),
            bytes.fromhex(
                "60b5a691c719704bb187536840246db5697c0d0e6bb2d4d8841a0c0810a49e39"
            ),
        )

    def test_schema(self):
        with self.assertRaises(ValueError):
            WardSchema(APP, {1: Text, 2: Text})
        with self.assertRaises(ValueError):
            WardSchema(APP, {256: Text})

        class Unknown(Text):
            pass

        ward = self.open()
        with self.assertRaises(ValueError):
            await_result(ward.set(Unknown("k"), Text("v")))
        with self.assertRaises(ValueError):
            await_result(ward.get(Text("k"), Unknown))

    def test_set(self):
        ward = self.open()
        await_result(ward.set(Text("k"), Text("v")))
        self.assertEqual(self.confirm_store.calls, [((APP, "k", "v", None), {})])
        self.assertEqual(await_result(ward.get(Text("k"), Text)), Text("v"))

    def test_set_replace(self):
        ward = self.open()
        await_result(ward.set(Text("k"), Number(1)))
        self.confirm_store.calls.clear()

        # an equal value is neither confirmed nor written again
        await_result(ward.set(Text("k"), Number(1)))
        self.assertEqual(self.confirm_store.calls, [])

        await_result(ward.set(Text("k"), Number(2)))
        # the replaced value is shown according to its own type
        await_result(ward.set(Text("k"), Text("v")))
        self.assertEqual(
            self.confirm_store.calls,
            [((APP, "k", "2", "1"), {}), ((APP, "k", "v", "2"), {})],
        )
        self.assertEqual(await_result(ward.get(Text("k"), Text)), Text("v"))

    def test_set_cancelled(self):
        ward = self.open()
        cancelled = MockAsync(raises=wire.ActionCancelled())
        with patch(layout, "confirm_store", cancelled):
            with self.assertRaises(wire.ActionCancelled):
                await_result(ward.set(Text("k"), Text("v")))
        self.assertIsNone(await_result(ward.get(Text("k"), Text)))

        await_result(ward.set(Text("k"), Text("v")))
        with patch(layout, "confirm_store", cancelled):
            with self.assertRaises(wire.ActionCancelled):
                await_result(ward.set(Text("k"), Text("w")))
        self.assertEqual(await_result(ward.get(Text("k"), Text)), Text("v"))

    def test_get(self):
        ward = self.open()
        self.assertIsNone(await_result(ward.get(Text("k"), Number)))
        await_result(ward.set(Text("k"), Number(1)))
        self.assertEqual(await_result(ward.get(Text("k"), Number)), Number(1))
        with self.assertRaises(WardError):
            await_result(ward.get(Text("k"), Text))

        self.set_raw(b"\x01m", b"\x02\x00")
        with self.assertRaises(WardError):
            await_result(ward.get(Text("m"), Number))

    def test_key_types(self):
        ward = self.open()
        await_result(ward.set(Text("abcd"), Text("text")))
        await_result(ward.set(Number(int.from_bytes(b"abcd", "big")), Text("number")))
        self.assertEqual(await_result(ward.get(Text("abcd"), Text)), Text("text"))
        self.assertEqual(
            await_result(ward.get(Number(int.from_bytes(b"abcd", "big")), Text)),
            Text("number"),
        )

    def test_delete(self):
        ward = self.open()
        self.assertFalse(await_result(ward.delete(Text("k"))))
        self.assertEqual(self.confirm_delete.calls, [])

        await_result(ward.set(Text("k"), Number(1)))
        self.assertTrue(await_result(ward.delete(Text("k"))))
        self.assertEqual(self.confirm_delete.calls, [((APP, "k", "1"), {})])
        self.assertIsNone(await_result(ward.get(Text("k"), Number)))

    def test_delete_cancelled(self):
        ward = self.open()
        await_result(ward.set(Text("k"), Text("v")))
        with patch(layout, "confirm_delete", MockAsync(raises=wire.ActionCancelled())):
            with self.assertRaises(wire.ActionCancelled):
                await_result(ward.delete(Text("k")))
        self.assertEqual(await_result(ward.get(Text("k"), Text)), Text("v"))

    def test_entries(self):
        ward = self.open()
        other = self.open(OTHER_SCHEMA)
        self.assertEqual(list(ward.entries()), [])

        await_result(ward.set(Text("a"), Number(1)))
        await_result(other.set(Text("x"), Text("")))
        await_result(ward.set(Number(2), Text("b")))
        self.assertEqual(
            list(ward.entries()), [(Text("a"), Number(1)), (Number(2), Text("b"))]
        )
        self.assertEqual(list(other.entries()), [(Text("x"), Text(""))])

    def test_undecodable(self):
        ward = self.open()
        self.set_raw(b"\x09k", b"\x01v")  # unknown key type
        self.set_raw(b"\x01u", b"\x09v")  # unknown value type
        self.set_raw(b"\x01m", b"\x02\x00")  # malformed value
        await_result(ward.set(Text("a"), Text("b")))
        self.assertEqual(list(ward.entries()), [(Text("a"), Text("b"))])

        # an undecodable value is shown as hex
        self.confirm_store.calls.clear()
        await_result(ward.set(Text("u"), Text("w")))
        self.assertEqual(self.confirm_store.calls, [((APP, "u", "w", "0976"), {})])
        self.assertTrue(await_result(ward.delete(Text("m"))))
        self.assertEqual(self.confirm_delete.calls, [((APP, "m", "0200"), {})])

    def test_isolation(self):
        wards = [self.open(), self.open(OTHER_SCHEMA)]
        self.set_seed(SEED_PASSPHRASE)
        wards.append(self.open())
        for i, ward in enumerate(wards):
            await_result(ward.set(Text("k"), Number(i)))
        for i, ward in enumerate(wards):
            self.assertEqual(await_result(ward.get(Text("k"), Number)), Number(i))
            self.assertEqual(list(ward.entries()), [(Text("k"), Number(i))])

    def test_errors(self):
        ward = self.open()
        with self.assertRaises(WardError):
            await_result(ward.set(Text("k"), Text("x" * 3000)))

        await_result(ward.set(Text("k"), Text("v")))
        config.lock()
        with self.assertRaises(WardError):
            await_result(ward.get(Text("k"), Text))

    def test_with_ward(self):
        @with_slip44_keychain(PATTERN_SEP5, slip44_id=42)
        @with_ward(SCHEMA)
        async def handler(msg, keychain, *, ward):
            return msg, ward

        msg, ward = await_result(handler("msg"))
        self.assertEqual(msg, "msg")
        self.assertTrue(isinstance(ward, WardStore))
        await_result(ward.set(Text("k"), Text("v")))
        self.assertEqual(await_result(self.open().get(Text("k"), Text)), Text("v"))

    def test_with_ward_error(self):
        @with_ward(SCHEMA)
        async def handler(msg, *, ward):
            await ward.set(Text("k"), Text("x" * 3000))

        with self.assertRaises(wire.ProcessError):
            await_result(handler("msg"))


if __name__ == "__main__":
    unittest.main()
