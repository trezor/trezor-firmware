from common import *

from trezor.utils import chunks
from trezor.crypto import bip32, bip39
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TxAck import TxAck
from trezor.messages.TransactionType import TransactionType
from trezor.messages.RequestType import TXINPUT, TXOUTPUT, TXFINISHED
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.messages import InputScriptType
from trezor.messages import OutputScriptType

from apps.common import coins
from apps.wallet.sign_tx import signing


class TestSignSegwitTxP2WPKHInP2SH(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_p2wpkh_in_p2sh(self):

        coin = coins.by_name('Testnet')

        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, 'secp256k1')

        inp1 = TxInputType(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        out1 = TxOutputType(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address='2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=123456789 - 11000 - 12300000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=None, lock_time=None, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None)),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
            TxAck(tx=TransactionType(outputs=[out1])),

            signing.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=None),
            TxAck(tx=TransactionType(outputs=[out2])),

            signing.UiConfirmOutput(out2, coin),
            True,

            signing.UiConfirmTotal(123445789 + 11000, 11000, coin),
            True,

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized inp1
                serialized_tx=unhexlify('0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff'),
            )),
            TxAck(tx=TransactionType(outputs=[out1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(outputs=[out2])),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out2
                serialized_tx=unhexlify('3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=None, serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000'),
                signature_index=0,
                signature=unhexlify('3045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b'),
            )),
        ]

        signer = signing.sign_tx(tx, root)
        for request, response in chunks(messages, 2):
            self.assertEqualEx(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_p2wpkh_in_p2sh_change(self):

        coin = coins.by_name('Testnet')

        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, 'secp256k1')

        inp1 = TxInputType(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        out1 = TxOutputType(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOP2SHWITNESS,
            amount=123456789 - 11000 - 12300000,
            address=None,
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=None, lock_time=None, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None)),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(outputs=[out1])),

            signing.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(outputs=[out2])),

            signing.UiConfirmTotal(12300000 + 11000, 11000, coin),
            True,

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized inp1
                          serialized_tx=unhexlify(
                              '0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out1.__dict__)])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out1
                          serialized_tx=unhexlify(
                              '02e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
                          signature_index=None,
                          signature=None,
            )),
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out2.__dict__)])),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out2
                          serialized_tx=unhexlify(
                              '3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                          signature_index=None,
                          signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=None, serialized=TxRequestSerializedType(
                serialized_tx=unhexlify(
                    '02483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000'),
                signature_index=0,
                signature=unhexlify('3045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b'),
            )),
        ]

        signer = signing.sign_tx(tx, root)
        for request, response in chunks(messages, 2):
            self.assertEqualEx(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    # see https://github.com/trezor/trezor-mcu/commit/6b615ce40567cc0da0b3b38ff668916aaae9dd4b#commitcomment-25505919
    # for the rational behind this attack
    def test_send_p2wpkh_in_p2sh_attack_amount(self):

        coin = coins.by_name('Testnet')

        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, 'secp256k1')

        inp1 = TxInputType(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=10,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        inpattack = TxInputType(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=9,  # modified!
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        out1 = TxOutputType(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
            amount=8,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOP2SHWITNESS,
            amount=1,
            address=None,
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=None, lock_time=None, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None)),
            TxAck(tx=TransactionType(inputs=[inpattack])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(outputs=[out1])),

            signing.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(outputs=[out2])),

            signing.UiConfirmTotal(8, 0, coin),
            True,

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized inpattack
                          serialized_tx=unhexlify(
                              '0100000000010137c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out1.__dict__)])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out1
                          serialized_tx=unhexlify(
                              '0208000000000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
                          signature_index=None,
                          signature=None,
            )),
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out2.__dict__)])),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out2
                          serialized_tx=unhexlify(
                              '010000000000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                          signature_index=None,
                          signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=None)
        ]

        signer = signing.sign_tx(tx, root)
        i = 0
        messages_count = int(len(messages) / 2)
        for request, response in chunks(messages, 2):
            if i == messages_count - 1:  # last message should throw SigningError
                self.assertRaises(signing.SigningError, signer.send, request)
            else:
                self.assertEqualEx(signer.send(request), response)
            i += 1
        with self.assertRaises(StopIteration):
            signer.send(None)

    def assertEqualEx(self, a, b):
        # hack to avoid adding __eq__ to signing.Ui* classes
        if ((isinstance(a, signing.UiConfirmOutput) and isinstance(b, signing.UiConfirmOutput)) or
                (isinstance(a, signing.UiConfirmTotal) and isinstance(b, signing.UiConfirmTotal))):
            return self.assertEqual(a.__dict__, b.__dict__)
        else:
            return self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
