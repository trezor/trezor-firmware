from common import *
from storage import cache
from trezor import wire
from trezor.crypto import bip39
from apps.common.paths import HARDENED

from apps.bitcoin.keychain import get_keychain_for_coin


class TestBitcoinKeychain(unittest.TestCase):
    def setUp(self):
        cache.start_session()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.set(cache.APP_COMMON_SEED, seed)

    def test_bitcoin(self):
        keychain, coin = await_result(
            get_keychain_for_coin(wire.DUMMY_CONTEXT, "Bitcoin")
        )
        self.assertEqual(coin.coin_name, "Bitcoin")

        valid_addresses = (
            [44 | HARDENED, 0 | HARDENED],
            [45 | HARDENED, 123456],
            [48 | HARDENED, 0 | HARDENED],
            [49 | HARDENED, 0 | HARDENED],
            [84 | HARDENED, 0 | HARDENED],
        )
        invalid_addresses = (
            [43 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 1 | HARDENED],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)

    def test_testnet(self):
        keychain, coin = await_result(
            get_keychain_for_coin(wire.DUMMY_CONTEXT, "Testnet")
        )
        self.assertEqual(coin.coin_name, "Testnet")

        valid_addresses = (
            [44 | HARDENED, 1 | HARDENED],
            [45 | HARDENED, 123456],
            [48 | HARDENED, 1 | HARDENED],
            [49 | HARDENED, 1 | HARDENED],
            [84 | HARDENED, 1 | HARDENED],
        )
        invalid_addresses = (
            [43 | HARDENED, 1 | HARDENED],
            [44 | HARDENED, 0 | HARDENED],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)

    def test_unspecified(self):
        keychain, coin = await_result(get_keychain_for_coin(wire.DUMMY_CONTEXT, None))
        self.assertEqual(coin.coin_name, "Bitcoin")
        keychain.derive([44 | HARDENED, 0 | HARDENED])

    def test_unknown(self):
        with self.assertRaises(wire.DataError):
            await_result(get_keychain_for_coin(wire.DUMMY_CONTEXT, "MadeUpCoin2020"))


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestAltcoinKeychains(unittest.TestCase):
    def setUp(self):
        cache.start_session()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.set(cache.APP_COMMON_SEED, seed)

    def test_bcash(self):
        keychain, coin = await_result(
            get_keychain_for_coin(wire.DUMMY_CONTEXT, "Bcash")
        )
        self.assertEqual(coin.coin_name, "Bcash")

        self.assertFalse(coin.segwit)
        valid_addresses = (
            [44 | HARDENED, 145 | HARDENED],
            [44 | HARDENED, 0 | HARDENED],
            [45 | HARDENED, 123456],
            [48 | HARDENED, 145 | HARDENED],
            [48 | HARDENED, 0 | HARDENED],
        )
        invalid_addresses = (
            [43 | HARDENED, 145 | HARDENED],
            [43 | HARDENED, 0 | HARDENED],
            [49 | HARDENED, 145 | HARDENED],
            [49 | HARDENED, 0 | HARDENED],
            [84 | HARDENED, 145 | HARDENED],
            [84 | HARDENED, 0 | HARDENED],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)

    def test_litecoin(self):
        keychain, coin = await_result(
            get_keychain_for_coin(wire.DUMMY_CONTEXT, "Litecoin")
        )
        self.assertEqual(coin.coin_name, "Litecoin")

        self.assertTrue(coin.segwit)
        valid_addresses = (
            [44 | HARDENED, 2 | HARDENED],
            [45 | HARDENED, 123456],
            [48 | HARDENED, 2 | HARDENED],
            [49 | HARDENED, 2 | HARDENED],
            [84 | HARDENED, 2 | HARDENED],
        )
        invalid_addresses = (
            [43 | HARDENED, 2 | HARDENED],
            [44 | HARDENED, 0 | HARDENED],
            [48 | HARDENED, 0 | HARDENED],
            [49 | HARDENED, 0 | HARDENED],
            [84 | HARDENED, 0 | HARDENED],
        )

        for addr in valid_addresses:
            keychain.derive(addr)

        for addr in invalid_addresses:
            self.assertRaises(wire.DataError, keychain.derive, addr)


if __name__ == "__main__":
    unittest.main()
