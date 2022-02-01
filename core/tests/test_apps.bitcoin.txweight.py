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
from apps.bitcoin.scripts import output_derive_script, output_script_paytoopreturn


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

    def test_taproot_txweight(self):
        coin = coins.by_name('Testnet')

        inp1 = TxInput(
            address_n=[86 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=4600,
            prev_hash=unhexlify('7956f1de3e7362b04115b64a31f0b6822c50dd6c08d78398f392a0ac3f0e357b'),
            prev_index=1,
            script_type=InputScriptType.SPENDTAPROOT,
        )

        out1 = TxOutput(
            address="tb1paxhjl357yzctuf3fe58fcdx6nul026hhh6kyldpfsf3tckj9a3wslqd7zd",
            amount=4450,
            script_type=OutputScriptType.PAYTOADDRESS,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))

        # 010000000001017b350e3faca092f39883d7086cdd502c82b6f0314ab61541b062733edef156790100000000ffffffff016211000000000000225120e9af2fc69e20b0be2629cd0e9c34da9f3ef56af7beac4fb4298262bc5a45ec5d0140493145b992dacbd7ea579a415efc2cba20c3bf0f7827d1bcf999109c0d11783fe96f91ddb04a889faa17ad21ecc5c81a578009744e95c7e721aff2a5c442916600000000
        self.assertEqual(calculator.get_total(), 4*94 + 68)

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

    def test_mixed_txweight(self):
        coin = coins.by_name('Testnet')

        inp1 = TxInput(
            address_n=[49 | 0x80000000, 1 | 0x80000000, 1 | 0x80000000, 0, 0],
            amount=20000,
            prev_hash=unhexlify('8c3ea7a10ab6d289119b722ec8c27b70c17c722334ced31a0370d782e4b6775d'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
        )
        inp2 = TxInput(
            address_n=[84 | 0x80000000, 1 | 0x80000000, 1 | 0x80000000, 0, 0],
            amount=15000,
            prev_hash=unhexlify('7956f1de3e7362b04115b64a31f0b6822c50dd6c08d78398f392a0ac3f0e357b'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
        )
        inp3 = TxInput(
            address_n=[86 | 0x80000000, 1 | 0x80000000, 1 | 0x80000000, 0, 0],
            amount=4450,
            prev_hash=unhexlify('7956f1de3e7362b04115b64a31f0b6822c50dd6c08d78398f392a0ac3f0e357b'),
            prev_index=0,
            script_type=InputScriptType.SPENDTAPROOT,
        )
        inp4 = TxInput(
            address_n=[44 | 0x80000000, 1 | 0x80000000, 1 | 0x80000000, 0, 0],
            amount=10000,
            prev_hash=unhexlify('3ac32e90831d79385eee49d6030a2123cd9d009fe8ffc3d470af9a6a777a119b'),
            prev_index=2,
            script_type=InputScriptType.SPENDADDRESS,
        )

        out1 = TxOutput(
            address="tb1q6xnnna3g7lk22h5tn8nlx2ezmndlvuk556w4w3",
            amount=25000,
            script_type=OutputScriptType.PAYTOWITNESS,
        )
        out2 = TxOutput(
            address="mfnMbVFC1rH4p9GNbjkMfrAjyKRLycFAzA",
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=7000,
        )
        out3 = TxOutput(
            address="2MvAG8m2xSf83FgeR4ZpUtaubpLNjAMMoka",
            amount=6900,
            script_type=OutputScriptType.PAYTOP2SHWITNESS,
        )
        out4 = TxOutput(
            op_return_data=b"test of op_return data",
            amount=0,
            script_type=OutputScriptType.PAYTOOPRETURN,
        )
        out5 = TxOutput(
            address="tb1ptgp9w0mm89ms43flw0gkrhyx75gyc6qjhtpf0jmt5sv0dufpnsrsyv9nsz",
            amount=10000,
            script_type=OutputScriptType.PAYTOTAPROOT,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_input(inp2)
        calculator.add_input(inp3)
        calculator.add_input(inp4)
        calculator.add_output(output_derive_script(out1.address, coin))
        calculator.add_output(output_derive_script(out2.address, coin))
        calculator.add_output(output_derive_script(out3.address, coin))
        calculator.add_output(output_script_paytoopreturn(out4.op_return_data))
        calculator.add_output(output_derive_script(out5.address, coin))

        # 010000000001045d77b6e482d770031ad3ce3423727cc1707bc2c82e729b1189d2b60aa1a73e8c0000000017160014a33c6e24c99e108b97bc411e7e9ef31e9d5d6164ffffffff7b350e3faca092f39883d7086cdd502c82b6f0314ab61541b062733edef156790000000000ffffffff852e125137abca2dd7a42837dccfc34edc358c72eefd62978d6747d3be9315900000000000ffffffff9b117a776a9aaf70d4c3ffe89f009dcd23210a03d649ee5e38791d83902ec33a020000006b483045022100f6bd64136839b49822cf7e2050bc5c91346fc18b5cf97a945d4fd6c502f712d002207d1859e66d218f705b704f3cfca0c75410349bb1f50623f4fc2d09d5d8df0a3f012103bae960983f83e28fcb8f0e5f3dc1f1297b9f9636612fd0835b768e1b7275fb9dffffffff05a861000000000000160014d1a739f628f7eca55e8b99e7f32b22dcdbf672d4581b0000000000001976a91402e9b094fd98e2a26e805894eb78f7ff3fef199b88acf41a00000000000017a9141ff816cbeb74817050de585ceb2c772ebf71147a870000000000000000186a1674657374206f66206f705f72657475726e206461746110270000000000002251205a02573f7b39770ac53f73d161dc86f5104c6812bac297cb6ba418f6f1219c070247304402205fae7fa2b5141548593d5623ce5bd82ee18dfc751c243526039c91848efd603702200febfbe3467a68c599245ff89055514f26e146c79b58d932ced2325e6dad1b1a0121021630971f20fa349ba940a6ba3706884c41579cd760c89901374358db5dd545b90247304402201b21212100c84207697cebb852374669c382ed97cbd08afbbdfe1b302802161602206b32b2140d094cf5b7e758135961c95478c8e82fea0df30f56ccee284b79eaea012103f6b2377d52960a6094ec158cf19dcf9e33b3da4798c2302aa5806483ed4187ae01404a81e4b7f55d6d4a26923c5e2daf3cc86ed6030f83ea6e7bb16d7b81b988b34585be21a64ab45ddcc2fb9f17be2dfeff6b22cf943bc3fc8f125a7f463af428ed0000000000
        # The witness data is 283 bytes, but two of the DER signatures are one byte below the
        # average length, so the caculator should estimate 285 bytes of witness data.
        self.assertEqual(calculator.get_total(), 4*477 + 285)

    def test_external_txweight(self):
        coin = coins.by_name('Testnet')

        inp1 = TxInput(
            amount=100000,
            prev_hash=unhexlify('e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a'),
            prev_index=0,
            script_type=InputScriptType.EXTERNAL,
            script_pubkey=unhexlify('00149c02608d469160a92f40fdf8c6ccced029493088'),
            ownership_proof=unhexlify(
                '534c001900016b2055d8190244b2ed2d46513c40658a574d3bc2deb6969c0535bb818b44d2c40002483045022100d4ad0374c922848c71d913fba59c81b9075e0d33e884d953f0c4b4806b8ffd0c022024740e6717a2b6a5aa03148c3a28b02c713b4e30fc8aeae67fa69eb20e8ddcd9012103505f0d82bbdd251511591b34f36ad5eea37d3220c2b81a1189084431ddb3aa3d'
            ),
        )

        inp2 = TxInput(
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            prev_hash=unhexlify('70f9871eb03a38405cfd7a01e0e1448678132d815e2c9f552ad83ae23969509e'),
            prev_index=0,
            amount=100000,
            script_type=InputScriptType.SPENDWITNESS,
        )

        inp3 = TxInput(
            # tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd
            # address_n=parse_path("m/84h/1h/0h/0/1"),
            prev_hash=unhexlify('65b768dacccfb209eebd95a1fb80a04f1dd6a3abc6d7b41d5e9d9f91605b37d9'),
            prev_index=0,
            amount=10000,
            script_type=InputScriptType.EXTERNAL,
            script_pubkey=unhexlify('0014fb7e49f4017dc951615dea221b66626189aa43b9'),
            script_sig=bytes(0),
            witness=unhexlify(
                '024730440220432ac60461de52713ad543cbb1484f7eca1a72c615d539b3f42f5668da4501d2022063786a6d6940a5c1ed9c2d2fd02cef90b6c01ddd84829c946561e15be6c0aae1012103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d03'
            ),
        )

        out1 = TxOutput(
            address="tb1qnspxpr2xj9s2jt6qlhuvdnxw6q55jvygcf89r2",
            amount=100000 + 100000 + 10000,
            script_type=OutputScriptType.PAYTOWITNESS,
        )

        calculator = TxWeightCalculator()
        calculator.add_input(inp1)
        calculator.add_input(inp2)
        calculator.add_input(inp3)
        calculator.add_output(output_derive_script(out1.address, coin))

        self.assertEqual(calculator.get_total(), 4*164 + 325)
        # non-segwit: header, inputs, outputs, locktime 4*(4+1+3*41+1+31+4) = 4*164
        # segwit: segwit header, 2x estimated witness (including stack item count)
        # and 1x exact witness (including stack item count) 1*(2+108+108+107) = 325


if __name__ == '__main__':
    unittest.main()
