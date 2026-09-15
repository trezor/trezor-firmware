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


class TestXpubPathWarning(unittest.TestCase):
    """Which xpub paths the account-naming table can name.

    The table decides only the account label; the warning is decided by
    validate_xpub_path_against_script_type(), see TestValidateXpubPath.
    Purpose 48 has entries; purpose 45 and the compatibility patterns do not.
    """

    def test_unnamed_multisig_sharing_points(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import address_n_to_name

        coin = _get_coin_by_name("Bitcoin")

        # Sharing points of recognized multisig patterns that the table still
        # cannot name, hence still labelled "Unknown path". The BIP-48 levels
        # used to be here too; they are now covered by
        # test_named_account_types.
        unnamed = (
            ([H_(45)], InputScriptType.SPENDADDRESS),
            ([H_(45)], InputScriptType.SPENDP2SHWITNESS),
            ([H_(45), 0, 0], InputScriptType.SPENDP2SHWITNESS),
            ([H_(45), H_(0), H_(0)], InputScriptType.SPENDADDRESS),
            ([H_(45), H_(0), H_(0)], InputScriptType.SPENDMULTISIG),
            ([H_(3), H_(100)], InputScriptType.SPENDADDRESS),
            ([49, 0, 0], InputScriptType.SPENDP2SHWITNESS),
        )

        for path, script_type in unnamed:
            self.assertIsNone(
                address_n_to_name(coin, path, script_type, account_level=True)
            )

    def test_named_account_types(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import address_n_to_name

        coin = _get_coin_by_name("Bitcoin")

        named = (
            ([H_(44), H_(0), H_(0)], InputScriptType.SPENDADDRESS, "Legacy"),
            ([H_(49), H_(0), H_(0)], InputScriptType.SPENDP2SHWITNESS, "L. SegWit"),
            ([H_(84), H_(0), H_(0)], InputScriptType.SPENDWITNESS, "SegWit"),
            ([H_(86), H_(0), H_(0)], InputScriptType.SPENDTAPROOT, "Taproot"),
            # BIP-48 multisig account nodes, one label per script-type level.
            # Before these entries existed the signing and xpub screens showed
            # "Unknown path" here.
            (
                [H_(48), H_(0), H_(0), H_(0)],
                InputScriptType.SPENDADDRESS,
                "Legacy MS",
            ),
            (
                [H_(48), H_(0), H_(0), H_(1)],
                InputScriptType.SPENDP2SHWITNESS,
                "L. SW MS",
            ),
            (
                [H_(48), H_(0), H_(0), H_(2)],
                InputScriptType.SPENDWITNESS,
                "SegWit MS",
            ),
        )

        for path, script_type, name in named:
            self.assertEqual(
                address_n_to_name(coin, path, script_type, account_level=True),
                name + " #1",
            )

        # The same names at leaf depth, which is what SignMessage passes.
        leaves = (
            (
                [H_(48), H_(0), H_(0), H_(0), 0, 0],
                InputScriptType.SPENDADDRESS,
                "Legacy MS",
            ),
            (
                [H_(48), H_(0), H_(0), H_(1), 0, 0],
                InputScriptType.SPENDP2SHWITNESS,
                "L. SW MS",
            ),
            (
                [H_(48), H_(0), H_(0), H_(2), 0, 0],
                InputScriptType.SPENDWITNESS,
                "SegWit MS",
            ),
        )

        for path, script_type, name in leaves:
            self.assertEqual(address_n_to_name(coin, path, script_type), name + " #1")

        # The "#N" suffix tracks the account index.
        self.assertEqual(
            address_n_to_name(
                coin,
                [H_(48), H_(0), H_(4), H_(2), 0, 0],
                InputScriptType.SPENDWITNESS,
            ),
            "SegWit MS #5",
        )

        # A mismatched script type must stay unnamed, so the levels cannot be
        # confused for one another.
        self.assertIsNone(
            address_n_to_name(
                coin,
                [H_(48), H_(0), H_(0), H_(2)],
                InputScriptType.SPENDADDRESS,
                account_level=True,
            )
        )

    def test_depth_1_is_unreachable(self):
        """No AccountType can match a depth-1 path, so m/45' cannot be named.

        get_name() discards BIP32_WALLET_DEPTH components and every address
        pattern has at least four, so the shallowest reachable depth is 2.
        """
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import address_n_to_name

        coin = _get_coin_by_name("Bitcoin")

        for purpose in (44, 45, 48, 49, 84, 86):
            for script_type in (
                InputScriptType.SPENDADDRESS,
                InputScriptType.SPENDMULTISIG,
                InputScriptType.SPENDP2SHWITNESS,
                InputScriptType.SPENDWITNESS,
                InputScriptType.SPENDTAPROOT,
            ):
                self.assertIsNone(
                    address_n_to_name(
                        coin, [H_(purpose)], script_type, account_level=True
                    )
                )


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
            ([H_(44), H_(0), H_(0), 0, 0], InputScriptType.SPENDMULTISIG),
            # Not even on BIP-48 0', where trezorctl used to guess it: the
            # client sends the single-key analogue now, so the device does not
            # reinterpret the script type on any path.
            ([H_(48), H_(0), H_(0), H_(0)], InputScriptType.SPENDMULTISIG),
            (
                [H_(48), H_(0), H_(0), H_(0), 0, 0],
                InputScriptType.SPENDMULTISIG,
            ),
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


class TestSignMessageKeyAccess(TestCaseWithContext):
    """The keys SignMessage may derive, and no others.

    On top of the per-coin schemas SignMessage unlocks the BIP-48 account
    nodes and nothing else, so a path outside the keychain is still refused
    outright under strict safety checks rather than merely warned about.
    See #7717.
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

    def _derive(self, msg):
        """Derive msg.address_n the way a handler decorated with
        with_keychain() does, i.e. through the schemas the wrapper picks."""
        from apps.bitcoin.keychain import with_keychain

        @with_keychain
        async def handler(msg, keychain, coin):
            keychain.derive(msg.address_n)
            return True

        return await_result(handler(msg))

    def _sign_message(self, address_n, script_type=None):
        from trezor.messages import SignMessage

        return SignMessage(
            address_n=address_n,
            message=b"hello",
            coin_name="Bitcoin",
            script_type=script_type,
        )

    def test_unrecognized_path_is_refused(self):
        """The grant is the account nodes, not every path.

        Keychain.verify_path() raises for a path in no schema, so an unknown
        derivation scheme cannot be signed with at all under strict safety
        checks -- it is not a warning the user can click through.
        """
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import validate_path_against_script_type

        coin = _get_coin_by_name("Bitcoin")
        # In no pattern table and in no schema.
        address_n = [H_(1234), H_(5), H_(6)]
        msg = self._sign_message(address_n, InputScriptType.SPENDADDRESS)

        self.assertRaises(wire.DataError, self._derive, msg)
        self.assertFalse(validate_path_against_script_type(coin, msg))

    def test_cross_namespace_paths_are_refused(self):
        """Another coin's namespace, and the master key itself.

        PATTERN_BIP44 substitutes Bitcoin's coin_type, so 44'/60' matches
        nothing, and PathSchema.match() rejects a path shorter than its schema,
        so the empty path matches nothing either. Neither is reachable, which
        is the point: a namespace is signable only once allowlisted.
        """
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import validate_path_against_script_type

        coin = _get_coin_by_name("Bitcoin")

        for address_n in (
            [H_(44), H_(60), H_(0), 0, 0],  # Ethereum's SLIP-44 coin type
            [],  # the BIP-32 master node
        ):
            msg = self._sign_message(address_n, InputScriptType.SPENDADDRESS)
            self.assertRaises(wire.DataError, self._derive, msg)
            # ... and unrecognized, so they would warn even if they were not.
            self.assertFalse(validate_path_against_script_type(coin, msg), address_n)

    def test_bip48_account_node_and_leaf(self):
        """The two paths #7717 asks for: signable, and without a warning."""
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import validate_path_against_script_type

        coin = _get_coin_by_name("Bitcoin")
        account = [H_(48), H_(0), H_(0), H_(2)]

        for address_n in (account, account + [0, 0]):
            msg = self._sign_message(address_n, InputScriptType.SPENDWITNESS)
            self.assertTrue(self._derive(msg), address_n)
            self.assertTrue(validate_path_against_script_type(coin, msg), address_n)

    def test_slip25_still_requires_unlock_path(self):
        """_get_unlock_schemas() offers SignMessage the external chain alone,
        and only after UnlockPath."""
        from trezor.enums import InputScriptType

        from apps.common.paths import SLIP25_PURPOSE

        msg = self._sign_message(
            [SLIP25_PURPOSE, H_(0), H_(0), H_(1), 0, 0],
            InputScriptType.SPENDTAPROOT,
        )
        self.assertRaises(wire.DataError, self._derive, msg)

    def test_account_node_is_not_shared_with_other_messages(self):
        """The BIP-48 account node is a SignMessage grant, nothing wider.

        GetAddress cannot derive it -- it is in no schema of its own, the
        six-component BIP-48 patterns being two levels deeper -- and the
        pattern union that recognizes it is not offered to a caller passing
        address_n/script_type directly, as GetAddress and SignTx do.
        """
        from trezor.enums import InputScriptType
        from trezor.messages import GetAddress

        from apps.bitcoin.keychain import validate_path_against_script_type

        coin = _get_coin_by_name("Bitcoin")
        account = [H_(48), H_(0), H_(0), H_(2)]

        msg = GetAddress(
            address_n=account,
            coin_name="Bitcoin",
            script_type=InputScriptType.SPENDWITNESS,
        )
        self.assertRaises(wire.DataError, self._derive, msg)

        for multisig in (False, True):
            self.assertFalse(
                validate_path_against_script_type(
                    coin,
                    address_n=account,
                    script_type=InputScriptType.SPENDWITNESS,
                    multisig=multisig,
                ),
                multisig,
            )

    def test_other_messages_keep_their_schemas(self):
        """Whatever SignMessage unlocks, GetAddress must not inherit."""
        from trezor.enums import InputScriptType
        from trezor.messages import GetAddress

        msg = GetAddress(
            address_n=[H_(1234), H_(5), H_(6)],
            coin_name="Bitcoin",
            script_type=InputScriptType.SPENDADDRESS,
        )
        self.assertRaises(wire.DataError, self._derive, msg)


class TestSignMessageAccountPatterns(unittest.TestCase):
    """Which BIP-48 account nodes are recognized, and therefore not warned
    about. A pure policy list: access no longer depends on it."""

    def test_spendmultisig_is_not_offered(self):
        """Message signing is single-key, so SPENDMULTISIG gets no account node.

        get_address() would raise "Multisig details required", so recognizing
        it would drop the warning from a path the operation cannot use.
        """
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import _get_sign_message_account_patterns

        coin = _get_coin_by_name("Bitcoin")

        self.assertEqual(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDMULTISIG),
            [],
        )

    def test_patterns_are_script_type_specific(self):
        from trezor.enums import InputScriptType

        from apps.bitcoin.keychain import (
            PATTERN_BIP48_P2SHSEGWIT_ACCOUNT,
            PATTERN_BIP48_SEGWIT_ACCOUNT,
            _get_sign_message_account_patterns,
        )

        coin = _get_coin_by_name("Bitcoin")

        # The 2' level answers for SPENDWITNESS alone; asking under another
        # script type leaves the node unrecognized, so it still warns.
        self.assertEqual(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDWITNESS),
            [PATTERN_BIP48_SEGWIT_ACCOUNT],
        )
        self.assertEqual(
            _get_sign_message_account_patterns(coin, InputScriptType.SPENDP2SHWITNESS),
            [PATTERN_BIP48_P2SHSEGWIT_ACCOUNT],
        )


if __name__ == "__main__":
    unittest.main()
