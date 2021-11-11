from common import *

from apps.bitcoin.common import SigHashType
from apps.bitcoin.scripts import output_derive_script
from apps.bitcoin.sign_tx.bitcoin import BitcoinSigHasher
from apps.bitcoin.writers import get_tx_hash
from trezor.messages import SignTx
from trezor.messages import TxInput
from trezor.messages import TxOutput
from trezor.messages import PrevOutput
from trezor.enums import InputScriptType
from trezor.enums import OutputScriptType


VECTORS = [
    {  # https://github.com/bitcoin/bips/pull/1225/commits/f7af1f73b287c14cf2f63afcb8d199feaf6ab5e1
        "sign_tx": SignTx(coin_name='Bitcoin', version=2, lock_time=0x1dcd6500, inputs_count=9, outputs_count=2),
        "inputs": [
            TxInput(
                amount=420000000,
                prev_hash=unhexlify('9c4e333b5f116359b5f5578fe4a74c6f58b3bab9d28149a583da86f6bf0ce27d'),
                prev_index=1,
                script_pubkey=unhexlify('512053a1f6e454df1aa2776a2814a721372d6258050de330b3c6d10ee8f4e0dda343'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0x00000000,
            ),
            TxInput(
                amount=462000000,
                prev_hash=unhexlify('99ddaf6d9b75447d5127e17312f6def68acba2d4f464d0e2ac93137bb5cab7d7'),
                prev_index=0,
                script_pubkey=unhexlify('5120147c9c57132f6e7ecddba9800bb0c4449251c92a1e60371ee77557b6620f3ea3'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0xffffffff,
            ),
            TxInput(
                amount=294000000,
                prev_hash=unhexlify('4218a419542757d960174457dc82e06b3613ac8ed2c528926833433883f5e1f8'),
                prev_index=0,
                script_pubkey=unhexlify('76a914751e76e8199196d454941c45d1b3a323f1433bd688ac'),
                script_type=InputScriptType.SPENDADDRESS,
                sequence=0xffffffff,
            ),
            TxInput(
                amount=504000000,
                prev_hash=unhexlify('3b8504d63a84a0fd1043e7ec832adaeeb7382a6d3ca762b10cb363aa809168f0'),
                prev_index=1,
                script_pubkey=unhexlify('5120e4d810fd50586274face62b8a807eb9719cef49c04177cc6b76a9a4251d5450e'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0xfffffffe,
            ),
            TxInput(
                amount=630000000,
                prev_hash=unhexlify('7a488f58881cecb2523690afcf22eb8892372bae018a125e1f006283a38c630c'),
                prev_index=0,
                script_pubkey=unhexlify('512091b64d5324723a985170e4dc5a0f84c041804f2cd12660fa5dec09fc21783605'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0xfffffffe,
            ),
            TxInput(
                amount=378000000,
                prev_hash=unhexlify('50d0ac326d44a3a29358214139fecb8a7129aa2f2dbeb28e96aa6fc6bd496195'),
                prev_index=0,
                script_pubkey=unhexlify('00147dd65592d0ab2fe0d0257d571abf032cd9db93dc'),
                script_type=InputScriptType.SPENDWITNESS,
                sequence=0x00000000,
            ),
            TxInput(
                amount=672000000,
                prev_hash=unhexlify('3a013eb5a6a664585ddbc210e02147847cde7317c0ce4e056ee4f0f167a2ef81'),
                prev_index=1,
                script_pubkey=unhexlify('512075169f4001aa68f15bbed28b218df1d0a62cbbcf1188c6665110c293c907b831'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0x00000000,
            ),
            TxInput(
                amount=546000000,
                prev_hash=unhexlify('eebd075c693d6823dd39fe11e3a6d1993fdec6109860937d50624a3c9c6690a6'),
                prev_index=0,
                script_pubkey=unhexlify('51200f63ca2c7639b9bb4be0465cc0aa3ee78a0761ba5f5f7d6ff8eab340f09da561'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0xffffffff,
            ),
            TxInput(
                amount=588000000,
                prev_hash=unhexlify('9e667967d1eb839b9b0a1fd17b2f29e838ff0240a83c61f896844377f8b57a72'),
                prev_index=1,
                script_pubkey=unhexlify('5120053690babeabbb7850c32eead0acf8df990ced79f7a31e358fabf2658b4bc587'),
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0xffffffff,
            ),
        ],
        "outputs": [
            PrevOutput(
                amount=1000000000,
                script_pubkey=unhexlify('76a91406afd46bcdfd22ef94ac122aa11f241244a37ecc88ac'), # 1cMh228HTCiwS8ZsaakH8A8wze1JR5ZsP
            ),
            PrevOutput(
                amount=3410000000,
                script_pubkey=unhexlify('ac9a87f5594be208f8532db38cff670c450ed2fea8fcdefcc9a663f78bab962b'),
            )
        ],
        "sha_amounts": unhexlify('58a6964a4f5f8f0b642ded0a8a553be7622a719da71d1f5befcefcdee8e0fde6'),
        "sha_outputs": unhexlify('a2e6dab7c1f0dcd297c8d61647fd17d821541ea69c3cc37dcbad7f90d4eb4bc5'),
        "sha_prevouts": unhexlify('2bd4d5a417902673919b2c209d14f8efaa285ede022a88d6a45edf4bdd43db11'),
        "sha_scriptpubkeys": unhexlify('26003c31f2f1786d22fcb3e1f690ddcdff53627a59f9219d5a2c77985a8930c0'),
        "sha_sequences": unhexlify('18959c7221ab5ce9e26c3cd67b22c24f8baa54bac281d8e6b05e400e6c3a957e'),
        "signature_hashes":
        [
            {
                "index": 3,
                "hash_type": SigHashType.SIGHASH_ALL,
                "result": unhexlify('6ffd256e108685b41831385f57eebf2fca041bc6b5e607ea11b3e03d4cf9d9ba'),
            },
            {
                "index": 4,
                "hash_type": SigHashType.SIGHASH_ALL_TAPROOT,
                "result": unhexlify('9f90136737540ccc18707e1fd398ad222a1a7e4dd65cbfd22dbe4660191efa58'),
            },
        ]
    },
    {  # https://github.com/bitcoin/bips/pull/1191/commits/fa40b5ae3544c1ed1615ead93a688d72be963e08
        "sign_tx": SignTx(coin_name='Bitcoin', version=2, lock_time=0x00000000, inputs_count=2, outputs_count=1),
        "inputs": [
            TxInput(
                prev_hash=unhexlify('8dcb562f365cfeb249be74e7865135cf035add604234fc0d8330b49bec92605f'),
                prev_index=0,
                amount=500000000,  # 5 btc
                script_type=InputScriptType.SPENDWITNESS,
                multisig=None,
                sequence=0,
                script_pubkey=unhexlify("0014196a5bea745288a7f947993c28e3a0f2108d2e0a"),
            ),
            TxInput(
                prev_hash=unhexlify('e1323b577ed0d216f4e52bf2b4c490710dfa0088dae3d15e8ba26ad792184361'),
                prev_index=1,
                multisig=None,
                amount=600000000,  # 6 btc
                script_type=InputScriptType.SPENDTAPROOT,
                sequence=0,
                script_pubkey=unhexlify("512029d942d0408906b359397b6f87c5145814a9aefc8c396dd05efa8b5b73576bf2"),
            ),
        ],
        "outputs": [
            PrevOutput(
                amount=1000000000,
                script_pubkey=unhexlify('76a914682dfdbc97ab5c31300f36d3c12c6fd854b1b35a88ac'), # 1AVrNUPAytZZbisNduCacWcEVJS6eGRvaa
            ),
        ],
        "sha_amounts": unhexlify('5733468db74734c00efa0b466bca091d8f1aab074af2538f36bd0a734a5940c5'),
        "sha_outputs": unhexlify('8cdee56004a241f9c79cc55b7d79eaed04909d84660502a2d4e9c357c2047cf5'),
        "sha_prevouts": unhexlify('32553b113292dfa8216546e721388a6c19c76626ca65dc187e0348d6ed445f81'),
        "sha_scriptpubkeys": unhexlify('423cd73484fc5e3e0a623442846c279c2216f25a2f32d161fea6c5821a1adde7'),
        "sha_sequences": unhexlify('af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc'),
        "signature_hashes":
        [
            {
                "index": 1,
                "hash_type": SigHashType.SIGHASH_ALL_TAPROOT,
                "result": unhexlify('07333acfe6dce8196f1ad62b2e039a3d9f0b6627bf955be767c519c0f8789ff4'),
            },
        ]
    }
]


class TestSegwitBip341P2TR(unittest.TestCase):
    # pylint: disable=C0301

    def test_bip341(self):
        for i, tx in enumerate(VECTORS):
            hasher = BitcoinSigHasher()

            for txi in tx["inputs"]:
                hasher.add_input(txi, txi.script_pubkey)

            self.assertEqual(get_tx_hash(hasher.h_amounts), tx["sha_amounts"], f"sha_amounts tx {i}")
            self.assertEqual(get_tx_hash(hasher.h_prevouts), tx["sha_prevouts"], f"sha_prevouts tx {i}")
            self.assertEqual(get_tx_hash(hasher.h_scriptpubkeys), tx["sha_scriptpubkeys"], f"sha_scriptpubkeys tx {i}")
            self.assertEqual(get_tx_hash(hasher.h_sequences), tx["sha_sequences"], f"sha_sequences tx {i}")

            for txo in tx["outputs"]:
                hasher.add_output(txo, txo.script_pubkey)

            self.assertEqual(get_tx_hash(hasher.h_outputs), tx["sha_outputs"], f"sha_outputs tx {i}")

            for sh in tx["signature_hashes"]:
                txi = tx["inputs"][sh["index"]]
                result = hasher.hash341(sh["index"], tx["sign_tx"], sh["hash_type"])
                self.assertEqual(result, sh["result"], f"signature_hash tx {i} input {sh['index']}")


if __name__ == '__main__':
    unittest.main()
