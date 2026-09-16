# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import cache_common
from trezor import wire
from trezor.crypto import bip39
from trezor.wire import context

from apps.bitcoin.keychain import (
    _get_coin_by_name,
    _get_keychain_for_coin,
    validate_path_against_script_type,
    validate_xpub_path_against_script_type,
    with_keychain,
)

if not utils.USE_THP:
    from storage import cache_codec


class TestBitcoinKeychain(TestCaseWithContext):
    if utils.USE_THP:

        def setUp(self):
            seed = bip39.seed(" ".join(["all"] * 12), "")
            context.cache_set(cache_common.APP_COMMON_SEED, seed)

    else:

        def setUp(self):
            cache_codec.start_session()
            seed = bip39.seed(" ".join(["all"] * 12), "")
            cache_codec.get_active_session().set(cache_common.APP_COMMON_SEED, seed)

    def test_bitcoin(self):
        coin = _get_coin_by_name("Bitcoin")
        keychain = await_result(_get_keychain_for_coin(coin))
        self.assertEqual(coin.coin_name, "Bitcoin")

        valid_addresses = (
            [H_(44), H_(0), H_(0), 0, 0],
            [H_(45), 99, 1, 1000],
            [H_(48), H_(0), H_(0), H_(2), 1, 1000],
            [H_(49), H_(0), H_(0), 0, 10],
            [H_(84), H_(0), H_(0), 0, 10],
            # Casa:
            [49, 0, 0, 0, 10],
            # Green:
            [1, 1000],
            [H_(3), H_(10), 4, 1000],
        )
        invalid_addresses = (
            [H_(43), H_(0), H_(0), 0, 0],
            [H_(44), H_(1), H_(0), 0, 0],
            [44, 0, 0, 0, 0],
            [H_(44), H_(0), H_(0)],
            [H_(44), H_(0), H_(0), 0, 0, 0],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)

    def test_testnet(self):
        coin = _get_coin_by_name("Testnet")
        keychain = await_result(_get_keychain_for_coin(coin))
        self.assertEqual(coin.coin_name, "Testnet")

        valid_addresses = (
            [H_(44), H_(1), H_(0), 0, 0],
            [H_(48), H_(1), H_(0), H_(2), 1, 1000],
            [H_(49), H_(1), H_(0), 0, 10],
            [H_(84), H_(1), H_(0), 0, 10],
            # Casa:
            [49, 1, 0, 0, 10],
        )
        invalid_addresses = (
            [H_(43), H_(1), H_(0), 0, 0],
            [H_(44), H_(0), H_(0), 0, 0],
            [44, 1, 0, 0, 0],
            [H_(44), H_(1), H_(0)],
            [H_(44), H_(1), H_(0), 0, 0, 0],
            [H_(45), 99, 1, 1000],
            # Green:
            [1, 1000],
            [H_(3), H_(10), 4, 1000],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)

    def test_unspecified(self):
        coin = _get_coin_by_name(None)
        keychain = await_result(_get_keychain_for_coin(coin))
        self.assertEqual(coin.coin_name, "Bitcoin")
        keychain.derive([H_(44), H_(0), H_(0), 0, 0])

    def test_unknown(self):
        with self.assertRaises(wire.DataError):
            _get_coin_by_name("MadeUpCoin2020")


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestAltcoinKeychains(TestCaseWithContext):
    if utils.USE_THP:

        def setUp(self):
            seed = bip39.seed(" ".join(["all"] * 12), "")
            context.cache_set(cache_common.APP_COMMON_SEED, seed)

    else:

        def setUp(self):
            cache_codec.start_session()
            seed = bip39.seed(" ".join(["all"] * 12), "")
            cache_codec.get_active_session().set(cache_common.APP_COMMON_SEED, seed)

    def test_bcash(self):
        coin = _get_coin_by_name("Bcash")
        keychain = await_result(_get_keychain_for_coin(coin))
        self.assertEqual(coin.coin_name, "Bcash")

        self.assertFalse(coin.segwit)
        self.assertIsNotNone(coin.fork_id)

        valid_addresses = (
            [H_(44), H_(145), H_(0), 0, 0],
            # Bitcoin paths should be allowed, as Bcash has strong replay protection
            [H_(44), H_(0), H_(0), 0, 0],
            [H_(45), 99, 1, 1000],
            [H_(48), H_(145), H_(0), H_(0), 1, 1000],
            [H_(48), H_(0), H_(0), H_(0), 1, 1000],
        )
        invalid_addresses = (
            [H_(43), H_(145), H_(0), 0, 0],
            [44, 145, 0, 0, 0],
            [H_(44), H_(145), H_(0)],
            [H_(44), H_(145), H_(0), 0, 0, 0],
            # segwit:
            [H_(49), H_(145), H_(0), 0, 10],
            [H_(84), H_(145), H_(0), 0, 10],
            # Casa:
            [49, 145, 0, 0, 10],
            # Green:
            [1, 1000],
            [H_(3), 10, 4, 1000],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)

    def test_litecoin(self):
        coin = _get_coin_by_name("Litecoin")
        keychain = await_result(_get_keychain_for_coin(coin))
        self.assertEqual(coin.coin_name, "Litecoin")

        self.assertTrue(coin.segwit)
        valid_addresses = (
            [H_(44), H_(2), H_(0), 0, 0],
            [H_(48), H_(2), H_(0), H_(2), 1, 1000],
            [H_(49), H_(2), H_(0), 0, 10],
            [H_(84), H_(2), H_(0), 0, 10],
        )
        invalid_addresses = (
            [H_(43), H_(2), H_(0), 0, 0],
            # Bitcoin paths:
            [H_(44), H_(0), H_(0), 0, 0],
            [H_(45), 99, 1, 1000],
            [H_(49), H_(0), H_(0), 0, 0],
            [H_(84), H_(0), H_(0), 0, 0],
            [44, 2, 0, 0, 0],
            [H_(44), H_(2), H_(0)],
            [H_(44), H_(2), H_(0), 0, 0, 0],
            # Casa:
            [49, 2, 0, 0, 10],
            # Green:
            [1, 1000],
            [H_(3), 10, 4, 1000],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)


class TestValidateXpubPath(unittest.TestCase):
    def test_export_points(self):
        from trezor.enums import InputScriptType

        coin = _get_coin_by_name("Bitcoin")

        def is_export_point(address_n, script_type):
            return validate_xpub_path_against_script_type(coin, address_n, script_type)

        # Casa: PATTERN_CASA is unhardened below m/45', so the purpose level
        # is the deepest hardened prefix and an export point of its own.
        self.assertTrue(is_export_point([H_(45)], InputScriptType.SPENDP2SHWITNESS))
        # BIP-48: the account node, where cosigners share the xpub.
        self.assertTrue(
            is_export_point([H_(48), H_(0), H_(0), H_(2)], InputScriptType.SPENDWITNESS)
        )
        self.assertTrue(
            is_export_point([H_(84), H_(0), H_(0)], InputScriptType.SPENDWITNESS)
        )
        self.assertFalse(
            is_export_point([H_(84), H_(0), H_(0), 0], InputScriptType.SPENDWITNESS)
        )
        # A pattern with no hardened component has no export point, so the
        # root xpub is never exportable this way.
        self.assertFalse(is_export_point([], InputScriptType.SPENDADDRESS))


class TestSignMessageBip48(TestCaseWithContext):
    """BIP-48 message signing: the account node and the leaf."""

    if utils.USE_THP:

        def setUp(self):
            seed = bip39.seed(" ".join(["all"] * 12), "")
            context.cache_set(cache_common.APP_COMMON_SEED, seed)

    else:

        def setUp(self):
            cache_codec.start_session()
            seed = bip39.seed(" ".join(["all"] * 12), "")
            cache_codec.get_active_session().set(cache_common.APP_COMMON_SEED, seed)

    def _sign_message(self, address_n, script_type, coin_name="Bitcoin"):
        from trezor.messages import SignMessage

        return SignMessage(
            address_n=address_n,
            message=b"hello",
            coin_name=coin_name,
            script_type=script_type,
        )

    def _derive(self, msg):
        """Derive msg.address_n through the schemas with_keychain() picks."""

        @with_keychain
        async def handler(msg, keychain, coin):
            keychain.derive(msg.address_n)
            return True

        return await_result(handler(msg))

    def test_account_node_and_leaf(self):
        from trezor.enums import InputScriptType

        coin = _get_coin_by_name("Bitcoin")
        account = [H_(48), H_(0), H_(0), H_(2)]
        leaf = account + [0, 0]

        for address_n in (account, leaf):
            msg = self._sign_message(address_n, InputScriptType.SPENDWITNESS)
            self.assertTrue(validate_path_against_script_type(coin, msg))
            self.assertTrue(self._derive(msg))

    def test_export_point_ignores_the_script_type(self):
        from trezor.enums import InputScriptType

        coin = _get_coin_by_name("Bitcoin")
        for script_type in (
            InputScriptType.SPENDADDRESS,
            InputScriptType.SPENDP2SHWITNESS,
            InputScriptType.SPENDWITNESS,
        ):
            msg = self._sign_message([H_(48), H_(0), H_(0), H_(2)], script_type)
            self.assertTrue(validate_path_against_script_type(coin, msg))
            self.assertTrue(self._derive(msg))

    def test_leaf_script_type_must_match_the_level(self):
        """Below an export point the encoding must match, but only warns."""
        from trezor.enums import InputScriptType

        coin = _get_coin_by_name("Bitcoin")
        msg = self._sign_message(
            [H_(48), H_(0), H_(0), H_(2), 0, 0], InputScriptType.SPENDADDRESS
        )

        self.assertFalse(validate_path_against_script_type(coin, msg))
        self.assertTrue(self._derive(msg))

    def test_fork_coins_get_no_bitcoin_path_alias(self):
        """The Bitcoin-namespace alias of a fork must not carry the grant.

        Bcash is not a segwit coin, so SPENDADDRESS is the only script type
        under which it has a BIP-48 pattern at all.
        """
        from trezor.enums import InputScriptType

        # Bcash's own coin type is granted...
        msg = self._sign_message(
            [H_(48), H_(145), H_(0), H_(0)],
            InputScriptType.SPENDADDRESS,
            coin_name="Bcash",
        )
        self.assertTrue(self._derive(msg))

        # ...the Bitcoin-namespace alias of it is not.
        msg = self._sign_message(
            [H_(48), H_(0), H_(0), H_(0)],
            InputScriptType.SPENDADDRESS,
            coin_name="Bcash",
        )
        self.assertRaises(wire.DataError, self._derive, msg)

    def test_grant_is_sign_message_only(self):
        """GetAddress gets no account node; it is not a spendable path."""
        from trezor.enums import InputScriptType
        from trezor.messages import GetAddress

        msg = GetAddress(
            address_n=[H_(48), H_(0), H_(0), H_(2)],
            coin_name="Bitcoin",
            script_type=InputScriptType.SPENDWITNESS,
        )
        self.assertRaises(wire.DataError, self._derive, msg)


if __name__ == "__main__":
    unittest.main()
