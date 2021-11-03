from common import *

from apps.bitcoin.common import SIGHASH_ALL
from apps.bitcoin.scripts import output_derive_script
from apps.bitcoin.sign_tx.bitcoin import BitcoinSigHasher
from apps.bitcoin.writers import get_tx_hash
from apps.common import coins
from apps.common.keychain import Keychain
from apps.common.paths import AlwaysMatchingSchema
from trezor.messages import SignTx
from trezor.messages import TxInput
from trezor.messages import TxOutput
from trezor.messages import PrevOutput
from trezor.enums import InputScriptType
from trezor.enums import OutputScriptType
from trezor.crypto import bip39


class TestSegwitBip143(unittest.TestCase):
    # pylint: disable=C0301

    tx = SignTx(coin_name='Bitcoin', version=1, lock_time=0x00000492, inputs_count=1, outputs_count=2)
    inp1 = TxInput(address_n=[0],
                       # Trezor expects hash in reversed format
                       prev_hash=unhexlify('77541aeb3c4dac9260b68f74f44c973081a9d4cb2ebe8038b2d70faa201b6bdb'),
                       prev_index=1,
                       multisig=None,
                       amount=1000000000,  # 10 btc
                       script_type=InputScriptType.SPENDP2SHWITNESS,  # TODO: is this correct?
                       sequence=0xfffffffe)
    out1 = TxOutput(address='1Fyxts6r24DpEieygQiNnWxUdb18ANa5p7',
                        amount=0x000000000bebb4b8,
                        script_type=OutputScriptType.PAYTOADDRESS,
                        multisig=None,
                        address_n=[])
    out2 = TxOutput(address='1Q5YjKVj5yQWHBBsyEBamkfph3cA6G9KK8',
                        amount=0x000000002faf0800,
                        script_type=OutputScriptType.PAYTOADDRESS,
                        multisig=None,
                        address_n=[])

    def test_bip143_prevouts(self):
        coin = coins.by_name(self.tx.coin_name)
        sig_hasher = BitcoinSigHasher()
        sig_hasher.add_input(self.inp1, b"")
        prevouts_hash = get_tx_hash(sig_hasher.h_prevouts, double=coin.sign_hash_double)
        self.assertEqual(hexlify(prevouts_hash), b'b0287b4a252ac05af83d2dcef00ba313af78a3e9c329afa216eb3aa2a7b4613a')

    def test_bip143_sequence(self):
        coin = coins.by_name(self.tx.coin_name)
        sig_hasher = BitcoinSigHasher()
        sig_hasher.add_input(self.inp1, b"")
        sequence_hash = get_tx_hash(sig_hasher.h_sequences, double=coin.sign_hash_double)
        self.assertEqual(hexlify(sequence_hash), b'18606b350cd8bf565266bc352f0caddcf01e8fa789dd8a15386327cf8cabe198')

    def test_bip143_outputs(self):
        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        coin = coins.by_name(self.tx.coin_name)
        sig_hasher = BitcoinSigHasher()

        for txo in [self.out1, self.out2]:
            script_pubkey = output_derive_script(txo.address, coin)
            txo_bin = PrevOutput(amount=txo.amount, script_pubkey=script_pubkey)
            sig_hasher.add_output(txo_bin, script_pubkey)

        outputs_hash = get_tx_hash(sig_hasher.h_outputs, double=coin.sign_hash_double)
        self.assertEqual(hexlify(outputs_hash), b'de984f44532e2173ca0d64314fcefe6d30da6f8cf27bafa706da61df8a226c83')

    def test_bip143_preimage_testdata(self):
        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        coin = coins.by_name(self.tx.coin_name)
        sig_hasher = BitcoinSigHasher()
        sig_hasher.add_input(self.inp1, b"")
        for txo in [self.out1, self.out2]:
            script_pubkey = output_derive_script(txo.address, coin)
            txo_bin = PrevOutput(amount=txo.amount, script_pubkey=script_pubkey)
            sig_hasher.add_output(txo_bin, script_pubkey)

        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema])
        node = keychain.derive(self.inp1.address_n)

        # test data public key hash
        result = sig_hasher.hash143(self.inp1, [node.public_key()], 1, self.tx, coin, SIGHASH_ALL)
        self.assertEqual(hexlify(result), b'6e28aca7041720995d4acf59bbda64eef5d6f23723d23f2e994757546674bbd9')


if __name__ == '__main__':
    unittest.main()
