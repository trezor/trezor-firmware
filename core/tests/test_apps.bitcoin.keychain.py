# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import cache_codec, cache_common
from trezor import wire
from trezor.crypto import bip39
from trezor.wire import context
from trezor.wire.codec.codec_context import CodecContext

from apps.bitcoin.keychain import _get_coin_by_name, _get_keychain_for_coin


class TestBitcoinKeychain(unittest.TestCase):

    def setUpClass(self):
        context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

    def tearDownClass(self):
        context.CURRENT_CONTEXT = None

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
class TestAltcoinKeychains(unittest.TestCase):

    def setUpClass(self):
        context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

    def tearDownClass(self):
        context.CURRENT_CONTEXT = None

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


if __name__ == "__main__":
    unittest.main()
