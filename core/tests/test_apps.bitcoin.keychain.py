# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import cache_common
from trezor import wire
from trezor.crypto import bip39
from trezor.wire import context

from apps.bitcoin.keychain import _get_coin_by_name, _get_keychain_for_coin

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
    def test_bitcoin(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import validate_xpub_path_against_script_type

        coin = _get_coin_by_name("Bitcoin")

        valid_paths = (
            # BIP-44 account
            ([H_(44), H_(0), H_(0)], InputScriptType.SPENDADDRESS),
            # BIP-45 and Casa purpose-level sharing root
            ([H_(45)], InputScriptType.SPENDADDRESS),
            ([H_(45)], InputScriptType.SPENDP2SHWITNESS),
            # Casa account
            ([H_(45), 0, 0], InputScriptType.SPENDP2SHWITNESS),
            # Unchained account
            ([H_(45), H_(0), H_(0)], InputScriptType.SPENDADDRESS),
            ([H_(45), H_(0), H_(0)], InputScriptType.SPENDMULTISIG),
            # BIP-48 script-type level
            ([H_(48), H_(0), H_(0), H_(0)], InputScriptType.SPENDADDRESS),
            ([H_(48), H_(0), H_(0), H_(1)], InputScriptType.SPENDP2SHWITNESS),
            ([H_(48), H_(0), H_(0), H_(2)], InputScriptType.SPENDWITNESS),
            # BIP-49, BIP-84, BIP-86 accounts
            ([H_(49), H_(0), H_(0)], InputScriptType.SPENDP2SHWITNESS),
            ([H_(84), H_(0), H_(0)], InputScriptType.SPENDWITNESS),
            ([H_(86), H_(0), H_(0)], InputScriptType.SPENDTAPROOT),
            # SLIP-25 coinjoin account
            ([H_(10025), H_(0), H_(0), H_(1)], InputScriptType.SPENDTAPROOT),
            # GreenAddress B subaccount: the host asked the device for
            # m/3'/subaccount' and derived /[1,4]/address_index itself, so this
            # is the requested export point.
            ([H_(3), H_(100)], InputScriptType.SPENDADDRESS),
        )
        invalid_paths = (
            # depths between or beyond the export points
            ([H_(44), H_(0)], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(0), H_(0), 0], InputScriptType.SPENDADDRESS),
            ([H_(45), 0], InputScriptType.SPENDP2SHWITNESS),
            ([H_(48), H_(0), H_(0)], InputScriptType.SPENDWITNESS),
            # script type mismatch
            ([H_(44), H_(0), H_(0)], InputScriptType.SPENDP2SHWITNESS),
            ([H_(49), H_(0), H_(0)], InputScriptType.SPENDADDRESS),
            ([H_(48), H_(0), H_(0), H_(2)], InputScriptType.SPENDP2SHWITNESS),
            # coin type mismatch
            ([H_(44), H_(1), H_(0)], InputScriptType.SPENDADDRESS),
            # m was GreenAddress A's real export point -- it asked for the root
            # and derived /[1,4]/address_index host-side -- but it is withheld:
            # the warning cannot be scoped to one requester, and the root xpub
            # also yields every PATTERN_CASA_UNHARDENED address. Withheld under
            # every script type that offers the pattern, and on every coin,
            # since the pattern is Bitcoin-only.
            ([], InputScriptType.SPENDADDRESS),
            ([], InputScriptType.SPENDWITNESS),
            # no GreenAddress pattern under taproot, so m is unreachable there
            # for a second, independent reason
            ([], InputScriptType.SPENDTAPROOT),
            # /1 and /4 are the branches the host derived itself; neither was
            # ever an export point
            ([1], InputScriptType.SPENDADDRESS),
            ([4], InputScriptType.SPENDADDRESS),
            # PATTERN_CASA_UNHARDENED has no hardened component either, so the
            # whole pattern is skipped and its account node is not an export point.
            ([49, 0, 0], InputScriptType.SPENDP2SHWITNESS),
        )

        for path, script_type in valid_paths:
            self.assertTrue(
                validate_xpub_path_against_script_type(coin, path, script_type)
            )

        for path, script_type in invalid_paths:
            self.assertFalse(
                validate_xpub_path_against_script_type(coin, path, script_type)
            )

    def test_litecoin(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import validate_xpub_path_against_script_type

        coin = _get_coin_by_name("Litecoin")

        self.assertTrue(
            validate_xpub_path_against_script_type(
                coin, [H_(49), H_(2), H_(0)], InputScriptType.SPENDP2SHWITNESS
            )
        )
        # BIP-45 is Bitcoin-only
        self.assertFalse(
            validate_xpub_path_against_script_type(
                coin, [H_(45)], InputScriptType.SPENDADDRESS
            )
        )
        # Casa applies to all segwit coins, like in address validation
        self.assertTrue(
            validate_xpub_path_against_script_type(
                coin, [H_(45)], InputScriptType.SPENDP2SHWITNESS
            )
        )
        # The GreenAddress patterns are Bitcoin-only, so m is not even a
        # candidate export point here
        self.assertFalse(
            validate_xpub_path_against_script_type(
                coin, [], InputScriptType.SPENDADDRESS
            )
        )


class TestSignMessagePathValidation(unittest.TestCase):
    """SignMessage has no multisig field, so it matches the union of both
    pattern sets. See #7717."""

    def _validate(self, coin, address_n, script_type):
        from trezor.messages import SignMessage

        from apps.bitcoin.keychain import validate_path_against_script_type

        msg = SignMessage(
            address_n=address_n, script_type=script_type, message=b"hello"
        )
        return validate_path_against_script_type(coin, msg)

    def test_bitcoin(self):
        from trezor.enums import InputScriptType

        coin = _get_coin_by_name("Bitcoin")

        valid_paths = (
            # BIP-44 leaf, accepted before this rule as well
            ([H_(44), H_(0), H_(0), 0, 0], InputScriptType.SPENDADDRESS),
            # BIP-48 leaves, one per script-type level. These are what #7717
            # asks for; without the union the BIP-48 patterns are unreachable
            # from message signing.
            ([H_(48), H_(0), H_(0), H_(0), 0, 0], InputScriptType.SPENDADDRESS),
            ([H_(48), H_(0), H_(0), H_(1), 0, 0], InputScriptType.SPENDP2SHWITNESS),
            ([H_(48), H_(0), H_(0), H_(2), 0, 0], InputScriptType.SPENDWITNESS),
            # BIP-48 account nodes, one per script-type level. The cosigner
            # xpub is shared here, so hosts sign with these keys to prove
            # account ownership; see #7717.
            ([H_(48), H_(0), H_(0), H_(0)], InputScriptType.SPENDADDRESS),
            ([H_(48), H_(0), H_(0), H_(1)], InputScriptType.SPENDP2SHWITNESS),
            ([H_(48), H_(0), H_(0), H_(2)], InputScriptType.SPENDWITNESS),
            # Unchained leaves, hardened and unhardened
            ([H_(45), H_(0), H_(63), 1000000, 0, 255], InputScriptType.SPENDADDRESS),
            ([H_(45), 0, 63, 1000000, 0, 255], InputScriptType.SPENDADDRESS),
            # BIP-45 leaf
            ([H_(45), 0, 0, 0], InputScriptType.SPENDADDRESS),
            # Model 1 firmware signing, offered for SignMessage only
            ([H_(10026), H_(826421588), H_(2), H_(0)], InputScriptType.SPENDADDRESS),
        )
        invalid_paths = (
            # Casa's leaf. Only PATTERN_CASA has five components and it is
            # offered under SPENDP2SHWITNESS alone, so the union does not
            # reach it. Purpose 45 is ambiguous, so no host can guess this.
            ([H_(45), 0, 0, 0, 0], InputScriptType.SPENDADDRESS),
            # ECDSA with a taproot account key must keep warning; see the note
            # in sign_tx/approvers.py about reusing a key across signature
            # schemes.
            ([H_(86), H_(0), H_(0), 0, 0], InputScriptType.SPENDWITNESS),
            # GreenAddress login challenge: in the keychain, but in no
            # script-type branch, so it always warns.
            ([1195487518], InputScriptType.SPENDADDRESS),
            # The BIP-48 account node under the wrong script-type level: only
            # the node matching script_type is offered, so 2' does not answer
            # for SPENDP2SHWITNESS.
            ([H_(48), H_(0), H_(0), H_(2)], InputScriptType.SPENDP2SHWITNESS),
            # Sharing points that are not BIP-48 account nodes stay unsignable.
            ([H_(45)], InputScriptType.SPENDADDRESS),
            ([H_(84), H_(0), H_(0)], InputScriptType.SPENDWITNESS),
            # sign_message() has no recovery byte for SPENDMULTISIG or
            # SPENDTAPROOT, so however standard these paths are to spend from,
            # accepting them here would promise a signature that cannot be
            # produced.
            ([H_(45), 0, 0, 0], InputScriptType.SPENDMULTISIG),
            (
                [H_(45), H_(0), H_(63), 1000000, 0, 255],
                InputScriptType.SPENDMULTISIG,
            ),
            ([H_(86), H_(0), H_(0), 0, 0], InputScriptType.SPENDTAPROOT),
        )

        for address_n, script_type in valid_paths:
            self.assertTrue(self._validate(coin, address_n, script_type))

        for address_n, script_type in invalid_paths:
            self.assertFalse(self._validate(coin, address_n, script_type))

    def test_union_is_sign_message_only(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import validate_path_against_script_type

        coin = _get_coin_by_name("Bitcoin")
        address_n = [H_(48), H_(0), H_(0), H_(2), 0, 0]

        # Must stay unmatched when the caller passes address_n/script_type
        # directly, as GetAddress and SignTx do: there multisig is load-bearing.
        self.assertFalse(
            validate_path_against_script_type(
                coin,
                address_n=address_n,
                script_type=InputScriptType.SPENDWITNESS,
                multisig=False,
            )
        )
        self.assertTrue(
            validate_path_against_script_type(
                coin,
                address_n=address_n,
                script_type=InputScriptType.SPENDWITNESS,
                multisig=True,
            )
        )


class TestSignMessageAccountAccess(TestCaseWithContext):
    """The keychain schemas that let SignMessage derive a BIP-48 account key.

    Validating the path is not enough: the six-component BIP-48 patterns do
    not cover the four-component node. See #7717.
    """

    if utils.USE_THP:

        def setUp(self):
            seed = bip39.seed(" ".join(["all"] * 12), "")
            context.cache_set(cache_common.APP_COMMON_SEED, seed)

    else:

        def setUp(self):
            cache_codec.start_session()
            seed = bip39.seed(" ".join(["all"] * 12), "")
            cache_codec.get_active_session().set(cache_common.APP_COMMON_SEED, seed)

    def test_account_node_needs_the_extra_schemas(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import (
            _get_sign_message_account_patterns,
            get_schemas_from_patterns,
        )

        coin = _get_coin_by_name("Bitcoin")
        account = [H_(48), H_(0), H_(0), H_(2)]

        # Without them the account node is out of reach, which is what #7717
        # reports as "Forbidden key path".
        keychain = await_result(_get_keychain_for_coin(coin))
        self.assertRaises(wire.DataError, keychain.derive, account)

        schemas = get_schemas_from_patterns(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDWITNESS),
            coin,
        )
        keychain = await_result(_get_keychain_for_coin(coin, schemas))
        keychain.derive(account)

        # The node only, never its subtree: the schema carries no wildcard, so
        # anything below is still reached through the ordinary BIP-48 pattern.
        self.assertRaises(wire.DataError, keychain.derive, account + [0])
        keychain.derive(account + [0, 0])

    def test_spendmultisig_is_not_offered(self):
        """Message signing is single-key, so SPENDMULTISIG gets no account node.

        get_address() would raise "Multisig details required", so offering it
        would let validation agree on a path the operation cannot use.
        """
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import (
            _get_sign_message_account_patterns,
            get_schemas_from_patterns,
        )

        coin = _get_coin_by_name("Bitcoin")

        self.assertEqual(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDMULTISIG),
            [],
        )

        schemas = get_schemas_from_patterns(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDMULTISIG),
            coin,
        )
        keychain = await_result(_get_keychain_for_coin(coin, schemas))
        self.assertRaises(
            wire.DataError, keychain.derive, [H_(48), H_(0), H_(0), H_(0)]
        )

    def test_schemas_are_script_type_specific(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import (
            _get_sign_message_account_patterns,
            get_schemas_from_patterns,
        )

        coin = _get_coin_by_name("Bitcoin")

        # The 2' level is unlocked for SPENDWITNESS only; asking under another
        # script type must not reach it.
        schemas = get_schemas_from_patterns(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDP2SHWITNESS),
            coin,
        )
        keychain = await_result(_get_keychain_for_coin(coin, schemas))
        keychain.derive([H_(48), H_(0), H_(0), H_(1)])
        self.assertRaises(
            wire.DataError, keychain.derive, [H_(48), H_(0), H_(0), H_(2)]
        )


if __name__ == "__main__":
    unittest.main()
