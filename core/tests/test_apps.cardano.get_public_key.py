from common import *

from apps.cardano.seed import Keychain
from apps.cardano.get_public_key import _get_public_key
from trezor.crypto import bip32, slip39


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoGetPublicKey(unittest.TestCase):
    def test_get_public_key_scheme(self):
        mnemonic = "all all all all all all all all all all all all"
        passphrase = ""
        node = bip32.from_mnemonic_cardano(mnemonic, passphrase)
        node.derive_cardano(0x80000000 | 44)
        node.derive_cardano(0x80000000 | 1815)
        keychain = Keychain(node)

        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000],
            [0x80000000 | 44, 0x80000000 | 1815],
            [0x80000000 | 44, 0x80000000 | 1815, 0, 0, 0],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0],
        ]

        public_keys = [
            b'a938c8554ae04616cfaae7cd0eb557475082c4e910242ce774967e0bd7492408',
            b'8c47ebce34234d04fd3dfbac33feaba6133e4e3d77c4b5ab18120ec6878ad4ce',
            b'17cc0bf978756d0d5c76f931629036a810c61801b78beecb44555773d13e3791',
            b'b90fb812a2268e9569ff1172e8daed1da3dc7e72c7bded7c5bcb7282039f90d5',
        ]

        chain_codes = [
            b'cbf6ab47c8eb1a0477fc40b25dbb6c4a99454edb97d6fe5acedd3e238ef46fe0',
            b'02ac67c59a8b0264724a635774ca2c242afa10d7ab70e2bf0a8f7d4bb10f1f7a',
            b'646ac4a6295326bae6831be05921edfbcb362de48dfd37b12e74c227dfad768d',
            b'fd8e71c1543de2cdc7f7623130c5f2cceb53549055fa1f5bc88199989e08cce7',
        ]

        xpub_keys = [
            'a938c8554ae04616cfaae7cd0eb557475082c4e910242ce774967e0bd7492408cbf6ab47c8eb1a0477fc40b25dbb6c4a99454edb97d6fe5acedd3e238ef46fe0',
            '8c47ebce34234d04fd3dfbac33feaba6133e4e3d77c4b5ab18120ec6878ad4ce02ac67c59a8b0264724a635774ca2c242afa10d7ab70e2bf0a8f7d4bb10f1f7a',
            '17cc0bf978756d0d5c76f931629036a810c61801b78beecb44555773d13e3791646ac4a6295326bae6831be05921edfbcb362de48dfd37b12e74c227dfad768d',
            'b90fb812a2268e9569ff1172e8daed1da3dc7e72c7bded7c5bcb7282039f90d5fd8e71c1543de2cdc7f7623130c5f2cceb53549055fa1f5bc88199989e08cce7',
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(keychain, derivation_path)

            self.assertEqual(hexlify(key.node.public_key), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])

    def test_slip39_128(self):
        mnemonics = [
            "extra extend academic bishop cricket bundle tofu goat apart victim "
                "enlarge program behavior permit course armed jerky faint language modern",
            "extra extend academic acne away best indicate impact square oasis "
                "prospect painting voting guest either argue username racism enemy eclipse",
            "extra extend academic arcade born dive legal hush gross briefing "
                "talent drug much home firefly toxic analysis idea umbrella slice"
        ]
        passphrase = b"TREZOR"
        identifier, exponent, ems = slip39.recover_ems(mnemonics)
        master_secret = slip39.decrypt(ems, passphrase, exponent, identifier)

        node = bip32.from_seed(master_secret, "ed25519 cardano seed")

        node.derive_cardano(0x80000000 | 44)
        node.derive_cardano(0x80000000 | 1815)
        keychain = Keychain(node)

        # 44'/1815'/0'/0/i
        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 1],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 2]
        ]

        public_keys = [
            b'bc043d84b8b891d49890edb6aced6f2d78395f255c5b6aea8878b913f83e8579',
            b'24c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c',
            b'831a63d381a8dab1e6e1ee991a4300fc70687aae5f97f4fcf92ed1b6c2bd99de'
        ]

        chain_codes = [
            b"dc3f0d2b5cccb822335ef6213fd133f4ca934151ec44a6000aee43b8a101078c",
            b"6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b",
            b"672d6af4707aba201b7940231e83dd357f92f8851b3dfdc224ef311e1b64cdeb"
        ]

        xpub_keys = [
            "bc043d84b8b891d49890edb6aced6f2d78395f255c5b6aea8878b913f83e8579dc3f0d2b5cccb822335ef6213fd133f4ca934151ec44a6000aee43b8a101078c",
            "24c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b",
            "831a63d381a8dab1e6e1ee991a4300fc70687aae5f97f4fcf92ed1b6c2bd99de672d6af4707aba201b7940231e83dd357f92f8851b3dfdc224ef311e1b64cdeb"
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(keychain, derivation_path)

            self.assertEqual(hexlify(key.node.public_key), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])

    def test_slip39_256(self):
        mnemonics = [
            "hobo romp academic axis august founder knife legal recover alien expect "
                "emphasis loan kitchen involve teacher capture rebuild trial numb spider forward "
                "ladle lying voter typical security quantity hawk legs idle leaves gasoline",
            "hobo romp academic agency ancestor industry argue sister scene midst graduate "
                "profile numb paid headset airport daisy flame express scene usual welcome "
                "quick silent downtown oral critical step remove says rhythm venture aunt"
        ]
        passphrase = b"TREZOR"
        identifier, exponent, ems = slip39.recover_ems(mnemonics)
        master_secret = slip39.decrypt(ems, passphrase, exponent, identifier)

        node = bip32.from_seed(master_secret, "ed25519 cardano seed")

        node.derive_cardano(0x80000000 | 44)
        node.derive_cardano(0x80000000 | 1815)
        keychain = Keychain(node)

        # 44'/1815'/0'/0/i
        derivation_paths = [
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 1],
            [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 2]
        ]

        public_keys = [
            b"967a9a041ad1379e31c2c7f2aa4bc2b3f7769341c0ea89ccfb12a904f2e10877",
            b"6f3805bbc1b7a75afa95dffec331671f3c4662800615e80d2ec1202a9d874c86",
            b"7f145b50ef07fb9accc40ee07a01fe93ceb6fa07d5a9f20fc3c8a48246dd4d02",
        ]

        chain_codes = [
            b"7b15d8d9006afe3cd7e04f375a1126a8c7c7c07c59a6f0c5b0310f4245f4edbb",
            b"44baf30fd549e6a1e05f99c2a2c8971aea8894ee8d9c5fc2c5ae6ee839a56b2d",
            b"e67d2864614ada5eec8fb8ee1225a94a6fb0a1b3c347c854ec3037351c6a0fc7",
        ]

        xpub_keys = [
            "967a9a041ad1379e31c2c7f2aa4bc2b3f7769341c0ea89ccfb12a904f2e108777b15d8d9006afe3cd7e04f375a1126a8c7c7c07c59a6f0c5b0310f4245f4edbb",
            "6f3805bbc1b7a75afa95dffec331671f3c4662800615e80d2ec1202a9d874c8644baf30fd549e6a1e05f99c2a2c8971aea8894ee8d9c5fc2c5ae6ee839a56b2d",
            "7f145b50ef07fb9accc40ee07a01fe93ceb6fa07d5a9f20fc3c8a48246dd4d02e67d2864614ada5eec8fb8ee1225a94a6fb0a1b3c347c854ec3037351c6a0fc7",
        ]

        for index, derivation_path in enumerate(derivation_paths):
            key = _get_public_key(keychain, derivation_path)

            self.assertEqual(hexlify(key.node.public_key), public_keys[index])
            self.assertEqual(hexlify(key.node.chain_code), chain_codes[index])
            self.assertEqual(key.xpub, xpub_keys[index])

if __name__ == '__main__':
    unittest.main()
