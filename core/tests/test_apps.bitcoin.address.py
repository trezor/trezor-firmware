from common import *
from trezor.crypto import bip32, bip39
from trezor.messages import GetAddress
from trezor.utils import HashWriter

from apps.common import coins
from apps.bitcoin import scripts
from apps.bitcoin.addresses import *
from apps.bitcoin.keychain import validate_path_against_script_type
from apps.bitcoin.writers import *


def node_derive(root, path):
    node = root.clone()
    node.derive_path(path)
    return node


class TestAddress(unittest.TestCase):
    # pylint: disable=C0301

    def test_p2wpkh_in_p2sh_address(self):
        coin = coins.by_name('Testnet')
        address = address_p2wpkh_in_p2sh(
            unhexlify('03a1af804ac108a8a51782198c2d034b28bf90c8803f5a53f76276fa69a4eae77f'),
            coin
        )
        self.assertEqual(address, '2Mww8dCYPUpKHofjgcXcBCEGmniw9CoaiD2')

    def test_p2wpkh_in_p2sh_node_derive_address(self):
        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, 'secp256k1')

        node = node_derive(root, [H_(49), H_(1), H_(0), 1, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)

        self.assertEqual(address, '2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX')

        node = node_derive(root, [H_(49), H_(1), H_(0), 1, 1])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)

        self.assertEqual(address, '2NFWLCJQBSpz1oUJwwLpX8ECifFWGznBVqs')

        node = node_derive(root, [H_(49), H_(1), H_(0), 0, 0])
        address = address_p2wpkh_in_p2sh(node.public_key(), coin)

        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp')

    def test_p2wpkh_address(self):
        # test data from https://bc-2.jp/tools/bech32demo/index.html
        coin = coins.by_name('Testnet')
        address = address_p2wpkh(
            unhexlify('0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'),
            coin
        )
        self.assertEqual(address, 'tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx')

    def test_p2sh_address(self):
        coin = coins.by_name('Testnet')

        address = address_p2sh(
            unhexlify('7a55d61848e77ca266e79a39bfc85c580a6426c9'),
            coin
        )
        self.assertEqual(address, '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp')

    def test_p2wsh_address(self):
        coin = coins.by_name('Testnet')

        # pubkey OP_CHECKSIG
        script = unhexlify('210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac')
        h = HashWriter(sha256())
        write_bytes_unchecked(h, script)

        address = address_p2wsh(
            h.get_digest(),
            coin.bech32_prefix
        )
        self.assertEqual(address, 'tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7')

    def test_p2wsh_in_p2sh_address(self):
        coin = coins.by_name('Bitcoin')

        # test data from Mastering Bitcoin
        address = address_p2wsh_in_p2sh(
            unhexlify('9592d601848d04b172905e0ddb0adde59f1590f1e553ffc81ddc4b0ed927dd73'),
            coin
        )
        self.assertEqual(address, '3Dwz1MXhM6EfFoJChHCxh1jWHb8GQqRenG')

    def test_multisig_address_p2sh(self):
        # # test data from
        # # https://www.soroushjp.com/2014/12/20/bitcoin-multisig-the-hard-way-understanding-raw-multisignature-bitcoin-transactions/
        # # commented out because uncompressed public keys are not supported
        # coin = coins.by_name('Bitcoin')
        # pubkeys = [
        #     unhexlify('04a882d414e478039cd5b52a92ffb13dd5e6bd4515497439dffd691a0f12af9575fa349b5694ed3155b136f09e63975a1700c9f4d4df849323dac06cf3bd6458cd'),
        #     unhexlify('046ce31db9bdd543e72fe3039a1f1c047dab87037c36a669ff90e28da1848f640de68c2fe913d363a51154a0c62d7adea1b822d05035077418267b1a1379790187'),
        #     unhexlify('0411ffd36c70776538d079fbae117dc38effafb33304af83ce4894589747aee1ef992f63280567f52f5ba870678b4ab4ff6c8ea600bd217870a8b4f1f09f3a8e83'),
        # ]
        # address = address_multisig_p2sh(pubkeys, 2, coin.address_type_p2sh)
        # self.assertEqual(address, '347N1Thc213QqfYCz3PZkjoJpNv5b14kBd')

        coin = coins.by_name('Bitcoin')
        pubkeys = [
            unhexlify('02fe6f0a5a297eb38c391581c4413e084773ea23954d93f7753db7dc0adc188b2f'),
            unhexlify('02ff12471208c14bd580709cb2358d98975247d8765f92bc25eab3b2763ed605f8'),
        ]
        address = address_multisig_p2sh(pubkeys, 2, coin)
        self.assertEqual(address, '39bgKC7RFbpoCRbtD5KEdkYKtNyhpsNa3Z')

        for invalid_m in (-1, 0, len(pubkeys) + 1, 16):
            with self.assertRaises(wire.DataError):
                address_multisig_p2sh(pubkeys, invalid_m, coin)

    def test_multisig_address_p2wsh_in_p2sh(self):
        # test data from
        # https://bitcoin.stackexchange.com/questions/62656/generate-a-p2sh-p2wsh-address-and-spend-output-sent-to-it
        coin = coins.by_name('Testnet')
        pubkeys = [
            unhexlify('020b020e27e49f049eac10010506499a84e1d59a500cd3680e9ded580df9a107b0'),
            unhexlify('0320ce424c6d61f352ccfea60d209651672cfb03b2dc77d1d64d3ba519aec756ae'),
        ]

        address = address_multisig_p2wsh_in_p2sh(pubkeys, 2, coin)
        self.assertEqual(address, '2MsZ2fpGKUydzY62v6trPHR8eCx5JTy1Dpa')

    # def test_multisig_address_p2wsh(self):
    # todo couldn't find test data

    def validate(self, address_n, coin, script_type):
        msg = GetAddress(address_n=address_n, script_type=script_type)
        if script_type == InputScriptType.SPENDMULTISIG:
            msg.multisig = True
        return validate_path_against_script_type(coin, msg)

    def test_paths_btc(self):
        incorrect_derivation_paths = [
            ([H_(49)], InputScriptType.SPENDP2SHWITNESS),  # invalid length
            ([H_(49), H_(0), H_(0), H_(0), H_(0)], InputScriptType.SPENDP2SHWITNESS),  # too many HARDENED
            ([H_(49), H_(0)], InputScriptType.SPENDP2SHWITNESS),  # invalid length
            ([H_(49), H_(0), H_(0), 0, 0, 0, 0], InputScriptType.SPENDP2SHWITNESS),  # invalid length
            ([H_(49), H_(123), H_(0), 0, 0, 0], InputScriptType.SPENDP2SHWITNESS),  # invalid slip44
            ([H_(49), H_(0), H_(1000), 0, 0], InputScriptType.SPENDP2SHWITNESS),  # account too high
            ([H_(49), H_(0), H_(1), 2, 0], InputScriptType.SPENDP2SHWITNESS),  # invalid y
            ([H_(49), H_(0), H_(1), 0, 10000000], InputScriptType.SPENDP2SHWITNESS),  # address index too high
            ([H_(84), H_(0), H_(1), 0, 10000000], InputScriptType.SPENDWITNESS),  # address index too high
            ([H_(49), H_(0), H_(1), 0, 0], InputScriptType.SPENDWITNESS),  # invalid input type
            ([H_(84), H_(0), H_(1), 0, 0], InputScriptType.SPENDP2SHWITNESS),  # invalid input type
            ([H_(49), H_(0), H_(5), 0, 10], InputScriptType.SPENDMULTISIG),  # invalid input type
        ]
        correct_derivation_paths = [
            ([H_(44), H_(0), H_(0), 0, 0], InputScriptType.SPENDADDRESS),  # btc is segwit coin, but non-segwit paths are allowed as well
            ([H_(44), H_(0), H_(0), 0, 1], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(0), H_(0), 1, 0], InputScriptType.SPENDADDRESS),
            ([H_(49), H_(0), H_(0), 0, 0], InputScriptType.SPENDP2SHWITNESS),
            ([H_(49), H_(0), H_(0), 1, 0], InputScriptType.SPENDP2SHWITNESS),
            ([H_(49), H_(0), H_(0), 0, 1123], InputScriptType.SPENDP2SHWITNESS),
            ([H_(49), H_(0), H_(0), 1, 44444], InputScriptType.SPENDP2SHWITNESS),
            ([H_(49), H_(0), H_(5), 0, 0], InputScriptType.SPENDP2SHWITNESS),
            ([H_(84), H_(0), H_(0), 0, 0], InputScriptType.SPENDWITNESS),
            ([H_(84), H_(0), H_(5), 0, 0], InputScriptType.SPENDWITNESS),
            ([H_(84), H_(0), H_(5), 0, 10], InputScriptType.SPENDWITNESS),
            ([H_(48), H_(0), H_(5), H_(0), 0, 10], InputScriptType.SPENDMULTISIG),
        ]
        coin = coins.by_name('Bitcoin')

        for path, input_type in incorrect_derivation_paths:
            self.assertFalse(self.validate(path, coin, input_type))

        for path, input_type in correct_derivation_paths:
            self.assertTrue(self.validate(path, coin, input_type))

        self.assertTrue(self.validate([H_(44), H_(0), H_(0), 0, 0], coin, InputScriptType.SPENDADDRESS))
        self.assertFalse(self.validate([H_(44), H_(0), H_(0), 0, 0], coin, InputScriptType.SPENDWITNESS))

    @unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
    def test_paths_bch(self):
        incorrect_derivation_paths = [
            ([H_(44)], InputScriptType.SPENDADDRESS),  # invalid length
            ([H_(44), H_(145), H_(0), H_(0), H_(0)], InputScriptType.SPENDADDRESS),  # too many HARDENED
            ([H_(49), H_(145), H_(0), 0, 0], InputScriptType.SPENDP2SHWITNESS),  # bch is not segwit coin so 49' is not allowed
            ([H_(84), H_(145), H_(1), 0, 1], InputScriptType.SPENDWITNESS),  # and neither is 84'
            ([H_(44), H_(145)], InputScriptType.SPENDADDRESS),  # invalid length
            ([H_(44), H_(145), H_(0), 0, 0, 0, 0], InputScriptType.SPENDADDRESS),  # invalid length
            ([H_(44), H_(123), H_(0), 0, 0, 0], InputScriptType.SPENDADDRESS),  # invalid slip44
            ([H_(44), H_(145), H_(1000), 0, 0], InputScriptType.SPENDADDRESS),  # account too high
            ([H_(44), H_(145), H_(1), 2, 0], InputScriptType.SPENDADDRESS),  # invalid y
            ([H_(44), H_(145), H_(1), 0, 10000000], InputScriptType.SPENDADDRESS),  # address index too high
            ([H_(84), H_(145), H_(1), 0, 10000000], InputScriptType.SPENDWITNESS),  # address index too high
            ([H_(44), H_(145), H_(0), 0, 0], InputScriptType.SPENDWITNESS),  # input type mismatch
        ]
        correct_derivation_paths = [
            ([H_(44), H_(145), H_(0), 0, 0], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(145), H_(0), 1, 0], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(145), H_(0), 0, 1123], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(145), H_(0), 1, 44444], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(145), H_(5), 0, 0], InputScriptType.SPENDADDRESS),
            ([H_(48), H_(145), H_(0), H_(0), 0, 0], InputScriptType.SPENDMULTISIG),
            ([H_(48), H_(145), H_(5), H_(0), 0, 0], InputScriptType.SPENDMULTISIG),
            ([H_(48), H_(145), H_(5), H_(0), 0, 10], InputScriptType.SPENDMULTISIG),
        ]
        coin = coins.by_name('Bcash')  # segwit is disabled
        for path, input_type in incorrect_derivation_paths:
            self.assertFalse(self.validate(path, coin, input_type))

        for path, input_type in correct_derivation_paths:
            self.assertTrue(self.validate(path, coin, input_type))

    @unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
    def test_paths_other(self):
        incorrect_derivation_paths = [
            ([H_(44), H_(3), H_(0), 0, 0], InputScriptType.SPENDMULTISIG),  # input type mismatch
        ]
        correct_derivation_paths = [
            ([H_(44), H_(3), H_(0), 0, 0], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(3), H_(0), 1, 0], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(3), H_(0), 0, 1123], InputScriptType.SPENDADDRESS),
            ([H_(44), H_(3), H_(0), 1, 44444], InputScriptType.SPENDADDRESS),
        ]
        coin = coins.by_name('Dogecoin')  # segwit is disabled
        for path, input_type in correct_derivation_paths:
            self.assertTrue(self.validate(path, coin, input_type))

        for path, input_type in incorrect_derivation_paths:
            self.assertFalse(self.validate(path, coin, input_type))


if __name__ == '__main__':
    unittest.main()
