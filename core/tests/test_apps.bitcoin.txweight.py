from common import *

from trezor.messages import MultisigRedeemScriptType
from trezor.messages import TxInput
from trezor.messages import TxOutput
from trezor.messages import HDNodeType
from trezor.enums import OutputScriptType
from trezor.crypto import bip39

from apps.common import coins
from apps.common.keychain import Keychain
from apps.common.paths import AlwaysMatchingSchema
from apps.bitcoin.sign_tx.tx_weight import *
from apps.bitcoin.scripts import output_derive_script


class TestCalculateTxWeight(unittest.TestCase):
    # pylint: disable=C0301

    def test_p2pkh_txweight(self):

        coin = coins.by_name('Bitcoin')

        inp1 = TxInput(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                           # amount=390000,
                           prev_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                           prev_index=0,
                           amount=None,
                           script_type=InputScriptType.SPENDADDRESS,
                           sequence=0xffff_ffff,
                           multisig=None)
        out1 = TxOutput(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                            amount=390000 - 10000,
                            script_type=OutputScriptType.PAYTOADDRESS,
                            address_n=[],
                            multisig=None)

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))

        serialized_tx = '010000000182488650ef25a58fef6788bd71b8212038d7f2bbe4750bc7bcb44701e85ef6d5000000006b4830450221009a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b7077102202b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede7810121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0160cc0500000000001976a914de9b2a8da088824e8fe51debea566617d851537888ac00000000'
        tx_weight = len(serialized_tx) / 2 * 4  # non-segwit tx's weight is simple length*4

        self.assertEqual(calculator.get_total(), tx_weight)

    def test_p2wpkh_in_p2sh_txweight(self):

        coin = coins.by_name('Testnet')

        inp1 = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        out1 = TxOutput(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address='2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=123456789 - 11000 - 12300000,
            address_n=[],
            multisig=None,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))
        calculator.add_output(output_derive_script(out2.address, coin))

        self.assertEqual(calculator.get_total(), 670)
        # non-segwit: header, inputs, outputs, locktime 4*(4+65+67+4) = 560
        # segwit: segwit header, witness stack item count, witness 1*(2+1+107) = 110
        # total 670

    def test_native_p2wpkh_txweight(self):

        coin = coins.by_name('Testnet')

        inp1 = TxInput(
            # 49'/1'/0'/0/0" - tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        out1 = TxOutput(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address='tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=12300000 - 11000 - 5000000,
            address_n=[],
            multisig=None,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))
        calculator.add_output(output_derive_script(out2.address, coin))

        self.assertEqual(calculator.get_total(), 566)
        # non-segwit: header, inputs, outputs, locktime 4*(4+42+64+4) = 456
        # segwit: segwit header, witness stack item count, witness 1*(2+1+107) = 110
        # total 566

    def test_legacy_multisig_txweight(self):
        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema])

        nodes = []
        for index in range(1, 4):
            node = keychain.derive([48 | 0x80000000, 0 | 0x80000000, index | 0x80000000, 0 | 0x80000000])
            nodes.append(HDNodeType(
                depth=node.depth(),
                child_num=node.child_num(),
                fingerprint=node.fingerprint(),
                chain_code=node.chain_code(),
                public_key=node.public_key(),
            ))

        multisig = MultisigRedeemScriptType(
            nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
        )

        inp1 = TxInput(
            address_n=[48 | 0x80000000, 0 | 0x80000000, 1 | 0x80000000, 0, 0],
            amount=100000,
            prev_hash=unhexlify('c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52'),
            prev_index=1,
            script_type=InputScriptType.SPENDMULTISIG,
            multisig=multisig,
        )

        out1 = TxOutput(
            address="12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss",
            amount=100000,
            script_type=OutputScriptType.PAYTOADDRESS,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))

        # 010000000152ba4dfcde9c4bed88f55479cdea03e711ae586e9a89352a98230c4cdf1a09c601000000fdfe00004830450221009276eea820aa54a24bd9f1a056cb09a15f50c0816570a7c7878bd1c5ee7248540220677d200aec5e2f25bcf4000bdfab3faa9e1746d7f80c4ae4bfa1f5892eb5dcbf01483045022100c2a9fbfbff1be87036d8a6a22745512b158154f7f3d8f4cad4ba7ed130b37b83022058f5299b4c26222588dcc669399bd88b6f2bc6e04b48276373683853187a4fd6014c69522103dc0ff15b9c85c0d2c87099758bf47d36229c2514aeefcf8dea123f0f93c679762102bfe426e8671601ad46d54d09ee15aa035610d36d411961c87474908d403fbc122102a5d57129c6c96df663ad29492aa18605dad97231e043be8a92f9406073815c5d53aeffffffff01a0860100000000001976a91412e8391ad256dcdc023365978418d658dfecba1c88ac00000000
        self.assertEqual(calculator.get_total(), 4*341)

    def test_segwit_multisig_txweight(self):
        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')
        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema])

        nodes = []
        for index in range(1, 4):
            node = keychain.derive([49 | 0x80000000, 1 | 0x80000000, index | 0x80000000])
            nodes.append(HDNodeType(
                depth=node.depth(),
                child_num=node.child_num(),
                fingerprint=node.fingerprint(),
                chain_code=node.chain_code(),
                public_key=node.public_key(),
            ))

        multisig = MultisigRedeemScriptType(
            nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
        )

        inp1 = TxInput(
            address_n=[49 | 0x80000000, 1 | 0x80000000, 1 | 0x80000000, 0, 0],
            prev_hash=unhexlify('c9348040bbc2024e12dcb4a0b4806b0398646b91acf314da028c3f03dd0179fc'),
            prev_index=1,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            multisig=multisig,
            amount=1610436,
        )

        out1 = TxOutput(
            address="tb1qch62pf820spe9mlq49ns5uexfnl6jzcezp7d328fw58lj0rhlhasge9hzy",
            amount=1605000,
            script_type=OutputScriptType.PAYTOADDRESS,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))

        # 01000000000101be0210025c5be68a473f6a38bf53b53bc88d5c46567616026dc056e72b92319c01000000232200208d398cfb58a1d9cdb59ccbce81559c095e8c6f4a3e64966ca385078d9879f95effffffff01887d180000000000220020c5f4a0a4ea7c0392efe0a9670a73264cffa90b19107cd8a8e9750ff93c77fdfb0400483045022100dd6342c65197af27d7894d8b8b88b16b568ee3b5ebfdc55fdfb7caa9650e3b4c02200c7074a5bcb0068f63d9014c7cd2b0490aba75822d315d41aad444e9b86adf5201483045022100e7e6c2d21109512ba0609e93903e84bfb7731ac3962ee2c1cad54a7a30ff99a20220421497930226c39fc3834e8d6da3fc876516239518b0e82e2dc1e3c46271a17c01695221021630971f20fa349ba940a6ba3706884c41579cd760c89901374358db5dd545b92102f2ff4b353702d2bb03d4c494be19d77d0ab53d16161b53fbcaf1afeef4ad0cb52103e9b6b1c691a12ce448f1aedbbd588e064869c79fbd760eae3b8cd8a5f1a224db53ae00000000
        self.assertEqual(calculator.get_total(), 4*129 + 256)


if __name__ == '__main__':
    unittest.main()
