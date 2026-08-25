# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.enums import InputScriptType

from apps.bitcoin.keychain import _get_coin_by_name, address_n_to_name


class TestAccountNaming(unittest.TestCase):
    def setUp(self):
        self.coin = _get_coin_by_name("Bitcoin")

    def test_bip45_purpose_xpub_named(self):
        # m/45' export (BIP-45 purpose-level xpub) is named at account level
        name = address_n_to_name(
            self.coin,
            [H_(45)],
            InputScriptType.SPENDADDRESS,
            account_level=True,
        )
        self.assertEqual(name, "Multisig")

    def test_bip45_purpose_xpub_non_default_script_type(self):
        name = address_n_to_name(
            self.coin,
            [H_(45)],
            InputScriptType.SPENDP2SHWITNESS,
            account_level=True,
        )
        self.assertIsNone(name)


if __name__ == "__main__":
    unittest.main()
