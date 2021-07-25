from common import *

from trezor.messages import TxInput
from trezor.messages import TxOutput
from trezor.enums import OutputScriptType
from trezor.crypto import bip32, bip39

from apps.common import coins
from apps.bitcoin.sign_tx.tx_weight import *
from apps.bitcoin.scripts import output_derive_script


class TestCalculateTxWeight(unittest.TestCase):
    # pylint: disable=C0301

    def test_p2pkh_txweight(self):

        coin = coins.by_name('Bitcoin')
        seed = bip39.seed(' '.join(['all'] * 12), '')

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

        calculator = TxWeightCalculator(1, 1)
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))

        serialized_tx = '010000000182488650ef25a58fef6788bd71b8212038d7f2bbe4750bc7bcb44701e85ef6d5000000006b4830450221009a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b7077102202b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede7810121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0160cc0500000000001976a914de9b2a8da088824e8fe51debea566617d851537888ac00000000'
        tx_weight = len(serialized_tx) / 2 * 4  # non-segwit tx's weight is simple length*4

        self.assertEqual(calculator.get_total(), tx_weight)

    def test_p2wpkh_in_p2sh_txweight(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

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

        calculator = TxWeightCalculator(1, 2)
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))
        calculator.add_output(output_derive_script(out2.address, coin))

        self.assertEqual(calculator.get_total(), 670)
        # non-segwit: header, inputs, outputs, locktime 4*(4+65+67+4) = 560
        # segwit: segwit header, witness count, 2x witness 1*(2+1+107) = 110
        # total 670

    def test_native_p2wpkh_txweight(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

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

        calculator = TxWeightCalculator(1, 2)
        calculator.add_input(inp1)
        calculator.add_output(output_derive_script(out1.address, coin))
        calculator.add_output(output_derive_script(out2.address, coin))

        self.assertEqual(calculator.get_total(), 566)
        # non-segwit: header, inputs, outputs, locktime 4*(4+42+64+4) = 456
        # segwit: segwit header, witness count, 2x witness 1*(2+1+107) = 110
        # total 566


if __name__ == '__main__':
    unittest.main()
