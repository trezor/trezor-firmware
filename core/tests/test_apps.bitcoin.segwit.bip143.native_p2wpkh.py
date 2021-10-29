from common import *

from apps.bitcoin.common import SIGHASH_ALL
from apps.bitcoin.scripts import output_derive_script
from apps.bitcoin.sign_tx.bitcoin import Bip143Hash
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


class TestSegwitBip143NativeP2WPKH(unittest.TestCase):
    # pylint: disable=C0301

    tx = SignTx(coin_name='Bitcoin', version=1, lock_time=0x00000011, inputs_count=2, outputs_count=2)
    inp1 = TxInput(address_n=[0],
                       # Trezor expects hash in reversed format
                       prev_hash=unhexlify('9f96ade4b41d5433f4eda31e1738ec2b36f6e7d1420d94a6af99801a88f7f7ff'),
                       prev_index=0,
                       amount=625000000,  # 6.25 btc
                       script_type=InputScriptType.SPENDWITNESS,
                       multisig=None,
                       sequence=0xffffffee)
    inp2 = TxInput(address_n=[1],
                       # Trezor expects hash in reversed format
                       prev_hash=unhexlify('8ac60eb9575db5b2d987e29f301b5b819ea83a5c6579d282d189cc04b8e151ef'),
                       prev_index=1,
                       multisig=None,
                       amount=600000000,  # 6 btc
                       script_type=InputScriptType.SPENDWITNESS,
                       sequence=0xffffffff)
    out1 = TxOutput(address='1Cu32FVupVCgHkMMRJdYJugxwo2Aprgk7H',  # derived
                        amount=0x0000000006b22c20,
                        script_type=OutputScriptType.PAYTOADDRESS,
                        multisig=None,
                        address_n=[])
    out2 = TxOutput(address='16TZ8J6Q5iZKBWizWzFAYnrsaox5Z5aBRV',  # derived
                        amount=0x000000000d519390,
                        script_type=OutputScriptType.PAYTOADDRESS,
                        multisig=None,
                        address_n=[])

    def test_prevouts(self):
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bip143Hash()
        bip143.add_input(self.inp1, b"")
        bip143.add_input(self.inp2, b"")
        prevouts_hash = get_tx_hash(bip143.h_prevouts, double=coin.sign_hash_double)
        self.assertEqual(hexlify(prevouts_hash), b'96b827c8483d4e9b96712b6713a7b68d6e8003a781feba36c31143470b4efd37')

    def test_sequence(self):
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bip143Hash()
        bip143.add_input(self.inp1, b"")
        bip143.add_input(self.inp2, b"")
        sequence_hash = get_tx_hash(bip143.h_sequence, double=coin.sign_hash_double)
        self.assertEqual(hexlify(sequence_hash), b'52b0a642eea2fb7ae638c36f6252b6750293dbe574a806984b8e4d8548339a3b')

    def test_outputs(self):

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bip143Hash()

        for txo in [self.out1, self.out2]:
            script_pubkey = output_derive_script(txo.address, coin)
            txo_bin = PrevOutput(amount=txo.amount, script_pubkey=script_pubkey)
            bip143.add_output(txo_bin, script_pubkey)

        outputs_hash = get_tx_hash(bip143.h_outputs, double=coin.sign_hash_double)
        self.assertEqual(hexlify(outputs_hash), b'863ef3e1a92afbfdb97f31ad0fc7683ee943e9abcf2501590ff8f6551f47e5e5')

    def test_preimage_testdata(self):

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bip143Hash()
        bip143.add_input(self.inp1, b"")
        bip143.add_input(self.inp2, b"")

        for txo in [self.out1, self.out2]:
            script_pubkey = output_derive_script(txo.address, coin)
            txo_bin = PrevOutput(amount=txo.amount, script_pubkey=script_pubkey)
            bip143.add_output(txo_bin, script_pubkey)

        keychain = Keychain(seed, coin.curve_name, [AlwaysMatchingSchema])
        node = keychain.derive(self.inp2.address_n)

        # test data public key hash
        # only for input 2 - input 1 is not segwit
        result = bip143.preimage_hash(self.inp2, [node.public_key()], 1, self.tx, coin, SIGHASH_ALL)
        self.assertEqual(hexlify(result), b'2fa3f1351618b2532228d7182d3221d95c21fd3d496e7e22e9ded873cf022a8b')


if __name__ == '__main__':
    unittest.main()
