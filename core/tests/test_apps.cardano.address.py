from common import *
from trezor import wire
from trezor.crypto import cardano, slip39
from trezor.enums import CardanoAddressType
from trezor.messages import CardanoAddressParametersType
from trezor.messages import CardanoBlockchainPointerType

from apps.common import seed
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.cardano.address import derive_human_readable_address, validate_address_parameters
    from apps.cardano.byron_address import _address_hash
    from apps.cardano.helpers import network_ids, protocol_magics
    from apps.cardano.seed import Keychain


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoAddress(unittest.TestCase):
    def setUp(self):
        mnemonic = "all all all all all all all all all all all all"
        passphrase = ""
        secret = cardano.derive_icarus(mnemonic, passphrase, False)
        node = cardano.from_secret(secret)
        self.keychain = Keychain(node)

    def test_hardened_address_derivation_scheme(self):
        addresses = [
            "Ae2tdPwUPEZ98eHFwxSsPBDz73amioKpr58Vw85mP1tMkzq8siaftiejJ3j",
            "Ae2tdPwUPEZKA971NCHuHqaEnxZDFWPzH3fEsLpDnbEpG6UeMRHnRzCzEwK",
            "Ae2tdPwUPEZL9Ag1ouS4b1zjuPxKpvEUgjpVpG1KQFs5pNewQb65F1WXVQ2",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i'
            address_parameters = CardanoAddressParametersType(
                address_type=CardanoAddressType.BYRON,
                address_n=[0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000 + i],
            )
            address = derive_human_readable_address(self.keychain, address_parameters, protocol_magics.MAINNET, network_ids.MAINNET)
            self.assertEqual(expected, address)

        nodes = [
            (
                b"3881a8de77d069001010d7f7d5211552e7d539b0e253add710367f95e528ed51",
                b"9b77608b38e0a0c7861aa234557c81482f42aae2d17993a8ddaec1868fb04d60",
                b"a938c8554ae04616cfaae7cd0eb557475082c4e910242ce774967e0bd7492408",
                b"cbf6ab47c8eb1a0477fc40b25dbb6c4a99454edb97d6fe5acedd3e238ef46fe0"
            ),
            (
                b"3003aca659846540b9ed04f2b844f2d8ea964856ca38a7dffedef4f6e528ed51",
                b"8844ccc81d633e1c7126f30c2524c1652617cf58da755014070215bf5070ba38",
                b"be28c00ed6cb9b70310f78028f8e3a2db935baf482d84afa590b0b5b864571cc",
                b"584b4631d752023a249e980779517280e6c0b3ac7a7f27c6e9456bfd228ca60b"
            ),
            (
                b"68e4482add0a741e14c8f2306bf83206a623e3729dd24175915eedece428ed51",
                b"3165a80c5efe846224d46a0427cdb2be4f31ea3585c51f4131faefc4328ad95a",
                b"9a32499976ffb582daa9988dfc42a303de5ed00c320c929f496be3c6eb1cf405",
                b"da07ca30a3d1c5fe3c34ce5fa197722446a646624a10bdf8889a4b9c347b2ef2"
            ),
        ]

        for i, (priv, ext, pub, chain) in enumerate(nodes):
            n = self.keychain.derive([0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000 + i])
            self.assertEqual(hexlify(n.private_key()), priv)
            self.assertEqual(hexlify(n.private_key_ext()), ext)
            self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
            self.assertEqual(hexlify(n.chain_code()), chain)

    def test_non_hardened_address_derivation_scheme(self):
        addresses = [
            "Ae2tdPwUPEZ5YUb8sM3eS8JqKgrRLzhiu71crfuH2MFtqaYr5ACNRdsswsZ",
            "Ae2tdPwUPEZJb8r1VZxweSwHDTYtqeYqF39rZmVbrNK62JHd4Wd7Ytsc8eG",
            "Ae2tdPwUPEZFm6Y7aPZGKMyMAK16yA5pWWKU9g73ncUQNZsAjzjhszenCsq",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i
            address_parameters = CardanoAddressParametersType(
                address_type=CardanoAddressType.BYRON,
                address_n=[0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i],
            )
            address = derive_human_readable_address(self.keychain, address_parameters, protocol_magics.MAINNET, network_ids.MAINNET)
            self.assertEqual(address, expected)

        nodes = [
            (
                b"d03ba81163fd55af97bd132bf651a0da5b5e6201b15b1caca60b0be8e028ed51",
                b"493f44aa8d25fe0d3fe2935c76ea6b3e9e41c79e9dbcbe7131357c5aa1b6cac5",
                b"b90fb812a2268e9569ff1172e8daed1da3dc7e72c7bded7c5bcb7282039f90d5",
                b"fd8e71c1543de2cdc7f7623130c5f2cceb53549055fa1f5bc88199989e08cce7"
            ),
            (
                b"08b6438c8dd49d34b71c8e914d6ac3184e5ab3dcc8af023d08503a7edf28ed51",
                b"3fee605fdfaddc1ee2ea0b246b02c9abc54ad741054bc83943e8b21487b5a053",
                b"89053545a6c254b0d9b1464e48d2b5fcf91d4e25c128afb1fcfc61d0843338ea",
                b"26308151516f3b0e02bb1638142747863c520273ce9bd3e5cd91e1d46fe2a635"
            ),
            (
                b"088f0275bf4a1bd18f08d7ef06c6ddb6ce7e3dc415fb4e89fe21bf39e628ed51",
                b"4c44563c7df519ea9b4d1801c1ab98b449db28b87f1c3837759c20f68c4c1e65",
                b"52548cb98e6f46a592bdf7f3598a9abc0126c78dfa3f46d1894ee52a5213e833",
                b"91af0668ee449e613e61bbb2482e5ddee1d9b15785727ec3e362c36861bff923"
            ),
        ]

        for i, (priv, ext, pub, chain) in enumerate(nodes):
            n = self.keychain.derive([0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(hexlify(n.private_key()), priv)
            self.assertEqual(hexlify(n.private_key_ext()), ext)
            self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
            self.assertEqual(hexlify(n.chain_code()), chain)


    def test_root_address_derivation_scheme(self):
        # 44'/1815'
        address_parameters = CardanoAddressParametersType(
            address_type=CardanoAddressType.BYRON,
            address_n=[0x80000000 | 44, 0x80000000 | 1815],
        )
        address = derive_human_readable_address(self.keychain, address_parameters, protocol_magics.MAINNET, network_ids.MAINNET)
        self.assertEqual(address, "Ae2tdPwUPEZ2FGHX3yCKPSbSgyuuTYgMxNq652zKopxT4TuWvEd8Utd92w3")

        priv, ext, pub, chain = (
            b"204ec79cbb6502a141de60d274962010c7f1c94a2987b26506433184d228ed51",
            b"975cdd1c8610b44701567f05934c45c8716064263ccfe72ed2167ccb705c09b6",
            b"8c47ebce34234d04fd3dfbac33feaba6133e4e3d77c4b5ab18120ec6878ad4ce",
            b"02ac67c59a8b0264724a635774ca2c242afa10d7ab70e2bf0a8f7d4bb10f1f7a"
        )

        n = self.keychain.derive([0x80000000 | 44, 0x80000000 | 1815])
        self.assertEqual(hexlify(n.private_key()), priv)
        self.assertEqual(hexlify(n.private_key_ext()), ext)
        self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
        self.assertEqual(hexlify(n.chain_code()), chain)


    def test_address_hash(self):
        data = [0, [0, b"}\x1d\xe3\xf2/S\x90M\x00\x7f\xf83\xfa\xdd|\xd6H.\xa1\xe89\x18\xb9\x85\xb4\xea3\xe6<\x16\xd1\x83z\x04\xa6\xaa\xb0\xed\x12\xafV*&\xdbM\x104DT'M\x0b\xfan5\x81\xdf\x1d\xc0/\x13\xc5\xfb\xe5"], {}]
        result = _address_hash(data)

        self.assertEqual(result, b'\x1c\xca\xee\xc9\x80\xaf}\xb0\x9a\xa8\x96E\xd6\xa4\xd1\xb4\x13\x85\xb9\xc2q\x1d5/{\x12"\xca')


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

        node = cardano.from_seed_slip23(master_secret)

        # Check root node.
        root_priv = b"c0fe4a6973df4de06262693fc9186f71faf292960350882d49456bf108d13954"
        root_ext = b"4064253ffefc4127489bce1b825a47329010c5afb4d21154ef949ef786204405"
        root_pub = b"83e3ecaf57f90f022c45e10d1b8cb78499c30819515ad9a81ad82139fdb12a90"
        root_chain = b"22c12755afdd192742613b3062069390743ea232bc1b366c8f41e37292af9305"

        self.assertEqual(hexlify(node.private_key()), root_priv)
        self.assertEqual(hexlify(node.private_key_ext()), root_ext)
        self.assertEqual(hexlify(seed.remove_ed25519_prefix(node.public_key())), root_pub)
        self.assertEqual(hexlify(node.chain_code()), root_chain)

        # Check derived nodes and addresses.
        keychain = Keychain(node)

        nodes = [
            (
                "Ae2tdPwUPEYxF9NAMNdd3v2LZoMeWp7gCZiDb6bZzFQeeVASzoP7HC4V9s6",
                b"e0acfe234aa6e1219ce7d3d8d91853e0808bab92ecb8a0ff0f345ff31ad13954",
                b"ff89dc71365c4b67bb7bb75d566e65b8a95f16e4d70cce51c25937db15614530",
                b"bc043d84b8b891d49890edb6aced6f2d78395f255c5b6aea8878b913f83e8579",
                b"dc3f0d2b5cccb822335ef6213fd133f4ca934151ec44a6000aee43b8a101078c",
            ),
            (
                "Ae2tdPwUPEZ1TjYcvfkWAbiHtGVxv4byEHHZoSyQXjPJ362DifCe1ykgqgy",
                b"d0ce3e7a6445bc91801319b9bbaf47fdfca9364257295fb13bc5046a20d13954",
                b"c800359abdc875944754ae7368bab7ef75184d48816c368f5a28af4bcf1d1ee8",
                b"24c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c",
                b"6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b",
            ),
            (
                "Ae2tdPwUPEZGXmSbda1kBNfyhRQGRcQxJFdk7mhWZXAGnapyejv2b2U3aRb",
                b"e8320644cce22a6e9fc33865fc5a598b1cda061c47a548aead3af4ed1cd13954",
                b"9e2ece5d7fe8119cb76090009be926a84fc5d3b95855b5962ffe2f880836cf09",
                b"831a63d381a8dab1e6e1ee991a4300fc70687aae5f97f4fcf92ed1b6c2bd99de",
                b"672d6af4707aba201b7940231e83dd357f92f8851b3dfdc224ef311e1b64cdeb"
            )
        ]

        for i, (address, priv, ext, pub, chain) in enumerate(nodes):
            # 44'/1815'/0'/0/i
            address_parameters = CardanoAddressParametersType(
                address_type=CardanoAddressType.BYRON,
                address_n=[0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i],
            )
            a = derive_human_readable_address(keychain, address_parameters, protocol_magics.MAINNET, network_ids.MAINNET)
            n = keychain.derive([0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(a, address)
            self.assertEqual(hexlify(n.private_key()), priv)
            self.assertEqual(hexlify(n.private_key_ext()), ext)
            self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
            self.assertEqual(hexlify(n.chain_code()), chain)

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

        node = cardano.from_seed_slip23(master_secret)

        # Check root node.
        root_priv = b"90633724b5daf770a8b420b8658e7d8bc21e066b60ec8cd4d5730681cc294e4f"
        root_ext = b"f9d99bf3cd9c7e12663e8646afa40cb3aecf15d91f2abc15d21056c6bccb3414"
        root_pub = b"eea170f0ef97b59d22907cb429888029721ed67d3e7a1b56b81731086ab7db64"
        root_chain = b"04f1de750b62725fcc1ae1b93ca4063acb53c486b959cadaa100ebd7828e5460"

        self.assertEqual(hexlify(node.private_key()), root_priv)
        self.assertEqual(hexlify(node.private_key_ext()), root_ext)
        self.assertEqual(hexlify(seed.remove_ed25519_prefix(node.public_key())), root_pub)
        self.assertEqual(hexlify(node.chain_code()), root_chain)

        # Check derived nodes and addresses.
        keychain = Keychain(node)

        nodes = [
            (
                "Ae2tdPwUPEYyDD1C2FbVJFAE3FuAxLspfMYt29TJ1urnSKr57cVhEcioSCC",
                b"38e8a4b17ca07b6a309f1cee83f87593e34a1fc3a289785ea451ef65df294e4f",
                b"405d10ef71c2b0019250d11837de8db825d8556bf1e57f8866920af6d8c90002",
                b"967a9a041ad1379e31c2c7f2aa4bc2b3f7769341c0ea89ccfb12a904f2e10877",
                b"7b15d8d9006afe3cd7e04f375a1126a8c7c7c07c59a6f0c5b0310f4245f4edbb",
            ),
            (
                "Ae2tdPwUPEZHJGtyz47F6wD7qAegt1JNRJWuiE36QLvFzeqJPBZ2EBvhr8M",
                b"a09f90e3f76a7bdb7f8721cc0c142dbd6398fd704b83455e123fa886dc294e4f",
                b"917e4166bb404def9f12634e84ecbcb98afdea051ba7c38745e208178a9e9baf",
                b"6f3805bbc1b7a75afa95dffec331671f3c4662800615e80d2ec1202a9d874c86",
                b"44baf30fd549e6a1e05f99c2a2c8971aea8894ee8d9c5fc2c5ae6ee839a56b2d",
            ),
            (
                "Ae2tdPwUPEYxD9xNPBJTzYmtFVVWEPB6KW4TCDijQ4pDwU11wt5621PyCi4",
                b"78dd824aea33bed5c1502d1a17f11a4adbe923aac1cd1f7ae98c9506db294e4f",
                b"ddfe7f27e2894b983df773d8ac2a07973fc37ff36e93a2f2d71fb7327d4e18f4",
                b"7f145b50ef07fb9accc40ee07a01fe93ceb6fa07d5a9f20fc3c8a48246dd4d02",
                b"e67d2864614ada5eec8fb8ee1225a94a6fb0a1b3c347c854ec3037351c6a0fc7",
            )
        ]

        for i, (address, priv, ext, pub, chain) in enumerate(nodes):
            # 44'/1815'/0'/0/i
            address_parameters = CardanoAddressParametersType(
                address_type=CardanoAddressType.BYRON,
                address_n=[0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i],
            )
            a = derive_human_readable_address(keychain, address_parameters, protocol_magics.MAINNET, network_ids.MAINNET)
            n = keychain.derive([0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i])
            self.assertEqual(a, address)
            self.assertEqual(hexlify(n.private_key()), priv)
            self.assertEqual(hexlify(n.private_key_ext()), ext)
            self.assertEqual(hexlify(seed.remove_ed25519_prefix(n.public_key())), pub)
            self.assertEqual(hexlify(n.chain_code()), chain)

    def test_testnet_byron_address(self):
        addresses = [
            "2657WMsDfac5F3zbgs9BwNWx3dhGAJERkAL93gPa68NJ2i8mbCHm2pLUHWSj8Mfea",
            "2657WMsDfac6ezKWszxLFqJjSUgpg9NgxKc1koqi24sVpRaPhiwMaExk4useKn5HA",
            "2657WMsDfac7hr1ioJGr6g7r6JRx4r1My8Rj91tcPTeVjJDpfBYKURrPG2zVLx2Sq",
        ]

        for i, expected in enumerate(addresses):
            # 44'/1815'/0'/0/i'
            address_parameters = CardanoAddressParametersType(
                address_type=CardanoAddressType.BYRON,
                address_n=[0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, i],
            )
            address = derive_human_readable_address(self.keychain, address_parameters, protocol_magics.TESTNET, 0)
            self.assertEqual(expected, address)

    def test_derive_address(self):
        address_parameters = {
            "BASE": CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 4 | HARDENED, 0, 0],
                address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 4 | HARDENED, 2, 0]
            ),
            "BASE_OWN_STAKING_KEY_HASH": CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 4 | HARDENED, 0, 0],
                staking_key_hash=unhexlify("1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff")
            ),
            "BASE_OWN_STAKING_KEY_HASH": CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 4 | HARDENED, 0, 0],
                staking_key_hash=unhexlify("1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff")
            ),
            # staking key hash not owned - derived with "all all..." mnenomnic
            "BASE_FOREIGN_STAKING_KEY_HASH_ACCOUNT_4": CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 4 | HARDENED, 0, 0],
                staking_key_hash=unhexlify("122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277")
            ),
            # staking key hash not owned - derived with "all all..." mnenomnic
            "BASE_FOREIGN_STAKING_KEY_HASH_ACCOUNT_0": CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                staking_key_hash=unhexlify("122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277")
            ),
            "BASE_SCRIPT_KEY_SCRIPT_HASH":CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_SCRIPT_KEY,
                address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
            ),
            "BASE_KEY_SCRIPT_HASH":CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_KEY_SCRIPT,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                script_staking_hash=unhexlify("8d7bebc7a58f1c7b5fb7c9391071ecd3b51b032695522f8c555343a9"),
            ),
            "BASE_SCRIPT_SCRIPT_HASHES": CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_SCRIPT_SCRIPT,
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
                script_staking_hash=unhexlify("8d7bebc7a58f1c7b5fb7c9391071ecd3b51b032695522f8c555343a9"),
            ),
            "POINTER1": CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                certificate_pointer=CardanoBlockchainPointerType(block_index=1, tx_index=2, certificate_index=3),
            ),
            "POINTER2": CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                certificate_pointer=CardanoBlockchainPointerType(block_index=24157, tx_index=177, certificate_index=42),
            ),
            "POINTER_SCRIPT_HASH": CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER_SCRIPT,
                certificate_pointer=CardanoBlockchainPointerType(block_index=24157, tx_index=177, certificate_index=42),
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
            ),
            "ENTERPRISE": CardanoAddressParametersType(
                address_type=CardanoAddressType.ENTERPRISE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            ),
            "ENTERPRISE_SCRIPT_HASH": CardanoAddressParametersType(
                address_type=CardanoAddressType.ENTERPRISE_SCRIPT,
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
            ),
            "REWARD": CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD,
                address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
            ),
            "REWARD_SCRIPT_HASH": CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD_SCRIPT,
                script_staking_hash=unhexlify("8d7bebc7a58f1c7b5fb7c9391071ecd3b51b032695522f8c555343a9"),
            ),
        }
        test_vectors = [
            # base address
            (network_ids.MAINNET, CardanoAddressType.BASE, address_parameters["BASE"], "addr1q8v42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wnrqua2vw243tmjfjt0h5wsru6appuz8c0pfd75ur7myyeqsx9990"),
            (network_ids.TESTNET, CardanoAddressType.BASE, address_parameters["BASE"], "addr_test1qrv42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wnrqua2vw243tmjfjt0h5wsru6appuz8c0pfd75ur7myyeqnsc9fs"),
            # base address with staking key hash
            (network_ids.MAINNET, CardanoAddressType.BASE, address_parameters["BASE_OWN_STAKING_KEY_HASH"], "addr1q8v42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wsmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hlsydc62k"),
            (network_ids.TESTNET, CardanoAddressType.BASE, address_parameters["BASE_OWN_STAKING_KEY_HASH"], "addr_test1qrv42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wsmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hls8m96xf"),
            (network_ids.MAINNET, CardanoAddressType.BASE, address_parameters["BASE_FOREIGN_STAKING_KEY_HASH_ACCOUNT_4"], "addr1q8v42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wsj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfms06skxl"),
            (network_ids.MAINNET, CardanoAddressType.BASE, address_parameters["BASE_FOREIGN_STAKING_KEY_HASH_ACCOUNT_0"], "addr1qxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92sj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsl3s9zt"),
            (network_ids.TESTNET, CardanoAddressType.BASE, address_parameters["BASE_FOREIGN_STAKING_KEY_HASH_ACCOUNT_4"], "addr_test1qrv42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wsj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsvvdk2q"),
            # base_script_key address
            (network_ids.MAINNET, CardanoAddressType.BASE_SCRIPT_KEY, address_parameters["BASE_SCRIPT_KEY_SCRIPT_HASH"], "addr1zyx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3lsj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsf42dkl"),
            (network_ids.TESTNET, CardanoAddressType.BASE_SCRIPT_KEY, address_parameters["BASE_SCRIPT_KEY_SCRIPT_HASH"], "addr_test1zqx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3lsj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfms2rhd6q"),
            # base_key_script address
            (network_ids.MAINNET, CardanoAddressType.BASE_KEY_SCRIPT, address_parameters["BASE_KEY_SCRIPT_HASH"], "addr1yxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z925d004u0fv0r3a4ld7f8yg8rmxnk5dsxf542ghcc42ngw5s8vnrtt"),
            (network_ids.TESTNET, CardanoAddressType.BASE_KEY_SCRIPT, address_parameters["BASE_KEY_SCRIPT_HASH"], "addr_test1yzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z925d004u0fv0r3a4ld7f8yg8rmxnk5dsxf542ghcc42ngw5sy6wr85"),
            # base_script_script address
            (network_ids.MAINNET, CardanoAddressType.BASE_SCRIPT_SCRIPT, address_parameters["BASE_SCRIPT_SCRIPT_HASHES"], "addr1xyx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3l5d004u0fv0r3a4ld7f8yg8rmxnk5dsxf542ghcc42ngw5s3gftll"),
            (network_ids.TESTNET, CardanoAddressType.BASE_SCRIPT_SCRIPT, address_parameters["BASE_SCRIPT_SCRIPT_HASHES"], "addr_test1xqx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3l5d004u0fv0r3a4ld7f8yg8rmxnk5dsxf542ghcc42ngw5sj75tnq"),
            # pointer address
            (network_ids.MAINNET, CardanoAddressType.POINTER, address_parameters["POINTER1"], "addr1gxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92spqgpsl97q83"),
            (network_ids.TESTNET, CardanoAddressType.POINTER, address_parameters["POINTER2"], "addr_test1gzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z925ph3wczvf2ag2x9t"),
            # pointer_script address
            (network_ids.MAINNET, CardanoAddressType.POINTER_SCRIPT, address_parameters["POINTER_SCRIPT_HASH"], "addr12yx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3l5ph3wczvf2zmd4yp"),
            (network_ids.TESTNET, CardanoAddressType.POINTER_SCRIPT, address_parameters["POINTER_SCRIPT_HASH"], "addr_test12qx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3l5ph3wczvf2d4sugn"),
            # enterprise address
            (network_ids.MAINNET, CardanoAddressType.ENTERPRISE, address_parameters["ENTERPRISE"], "addr1vxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92su77c6m"),
            (network_ids.TESTNET, CardanoAddressType.ENTERPRISE, address_parameters["ENTERPRISE"], "addr_test1vzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92s8k2y47"),
            # enterprise_script address
            (network_ids.MAINNET, CardanoAddressType.ENTERPRISE_SCRIPT, address_parameters["ENTERPRISE_SCRIPT_HASH"], "addr1wyx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3lsqee7sp"),
            (network_ids.TESTNET, CardanoAddressType.ENTERPRISE_SCRIPT, address_parameters["ENTERPRISE_SCRIPT_HASH"], "addr_test1wqx44jlk580mpjrjfesd7v2fsuc4ejlh3wmvp7dk702k3lsm3dzly"),
            # reward address
            (network_ids.MAINNET, CardanoAddressType.REWARD, address_parameters["REWARD"], "stake1uyfz49rtntfa9h0s98f6s28sg69weemgjhc4e8hm66d5yacalmqha"),
            (network_ids.TESTNET, CardanoAddressType.REWARD, address_parameters["REWARD"], "stake_test1uqfz49rtntfa9h0s98f6s28sg69weemgjhc4e8hm66d5yac643znq"),
            # reward_script address
            (network_ids.MAINNET, CardanoAddressType.REWARD_SCRIPT, address_parameters["REWARD_SCRIPT_HASH"], "stake17xxhh6785k83c76lklynjyr3anfm2xcry624ytuv24f582gt5mad4"),
            (network_ids.TESTNET, CardanoAddressType.REWARD_SCRIPT, address_parameters["REWARD_SCRIPT_HASH"], "stake_test17zxhh6785k83c76lklynjyr3anfm2xcry624ytuv24f582gv73lfg"),
        ]


        for network_id, address_type, address_parameters, expected_address in test_vectors:
            validate_address_parameters(address_parameters)
            actual_address = derive_human_readable_address(self.keychain, address_parameters, protocol_magics.MAINNET, network_id)

            self.assertEqual(actual_address, expected_address)

    def test_validate_address_parameters(self):
        test_vectors = [
            # base address - both address_n_staking and staking_key_hash are None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                address_n_staking=None,
                staking_key_hash=None,
            ),
            # base address - both address_n_staking and staking_key_hash are set
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 2, 0],
                staking_key_hash=unhexlify("1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff"),
            ),
            # base address - staking_key_hash is too short
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                address_n_staking=None,
                staking_key_hash=unhexlify("1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8d"),
            ),
            # base address - address_n_staking is not a staking path
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                staking_key_hash=None,
            ),
            # base_script_key address - script_payment_hash is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_SCRIPT_KEY,
                script_payment_hash=None,
                staking_key_hash=unhexlify("1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8d"),
            ),
            # base_script_key address - address_n_staking is not a staking path
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_SCRIPT_KEY,
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
                address_n_staking=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            ),
            # base_key_script address - script_staking_hash is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_KEY_SCRIPT,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                script_staking_hash=None,
            ),
            # base_script_script address - script_payment_hash is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_SCRIPT_SCRIPT,
                script_payment_hash=None,
                script_staking_hash=unhexlify("8d7bebc7a58f1c7b5fb7c9391071ecd3b51b032695522f8c555343a9"),
            ),
            # base_script_script address - script_staking and script_staking_hash are None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_SCRIPT_SCRIPT,
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
                script_staking_hash=None,
            ),
            # pointer address - pointer is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                certificate_pointer=None,
            ),
            # pointer_script address - pointer is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER_SCRIPT,
                script_payment_hash=unhexlify("0d5acbf6a1dfb0c8724e60df314987315ccbf78bb6c0f9b6f3d568fe"),
                certificate_pointer=None,
            ),
            # pointer_script address - script_payment_script is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER_SCRIPT,
                script_payment_hash=None,
                certificate_pointer=CardanoBlockchainPointerType(block_index=24157, tx_index=177, certificate_index=42),
            ),
            # enterprise_script address - script_payment_hash is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.ENTERPRISE_SCRIPT,
                script_payment_hash=None,
            ),
            # reward address - non staking path
            CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0]
            ),
            # reward_script address - script_staking_hash is None
            CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD_SCRIPT,
                script_staking_hash=None,
            ),

            # Shelley addresses with Byron namespace
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE,
                address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                staking_key_hash=unhexlify("1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff"),
            ),
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BASE_KEY_SCRIPT,
                address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                script_staking_hash=unhexlify("8d7bebc7a58f1c7b5fb7c9391071ecd3b51b032695522f8c555343a9"),
            ),
            CardanoAddressParametersType(
                address_type=CardanoAddressType.POINTER,
                address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                certificate_pointer=CardanoBlockchainPointerType(block_index=0, tx_index=0, certificate_index=0)
            ),
            CardanoAddressParametersType(
                address_type=CardanoAddressType.ENTERPRISE,
                address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            ),
            CardanoAddressParametersType(
                address_type=CardanoAddressType.REWARD,
                address_n=[44 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            ),

            # Byron address with Shelley namespace
            CardanoAddressParametersType(
                address_type=CardanoAddressType.BYRON,
                address_n=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
            )
        ]

        for address_parameters in test_vectors:
            with self.assertRaises(wire.ProcessError):
                validate_address_parameters(address_parameters)


if __name__ == '__main__':
    unittest.main()
