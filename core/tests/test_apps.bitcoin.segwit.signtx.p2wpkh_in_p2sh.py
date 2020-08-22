from common import *

from trezor.utils import chunks
from trezor.crypto import bip39
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TxAck import TxAck
from trezor.messages.TransactionType import TransactionType
from trezor.messages.RequestType import TXINPUT, TXMETA, TXOUTPUT, TXFINISHED
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.messages import InputScriptType
from trezor.messages import OutputScriptType
from trezor import wire

from apps.common import coins
from apps.common.keychain import Keychain
from apps.bitcoin.keychain import get_namespaces_for_coin
from apps.bitcoin.sign_tx import bitcoin, helpers
from apps.bitcoin.sign_tx.approvers import BasicApprover


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


class TestSignSegwitTxP2WPKHInP2SH(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_p2wpkh_in_p2sh(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

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
        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('4730440220548e087d0426b20b8a571b03b9e05829f7558b80c53c12143e342f56ab29e51d02205b68cb7fb223981d4c999725ac1485a982c4259c4f50b8280f137878c232998a012102794a25b254a268e59a5869da57fbae2fadc6727cb3309321dab409b12b2fa17c'),
                            prev_hash=unhexlify('802cabf0843b945eabe136d7fc7c89f41021658abf56cba000acbce88c41143a'),
                            prev_index=0,
                            script_type=None,
                            sequence=4294967295)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('76a914b84bacdcd8f4cc59274a5bfb73f804ca10f7fd1488ac'),
                                amount=865519308)

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
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out1])),

            helpers.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out2])),

            helpers.UiConfirmOutput(out2, coin),
            True,

            helpers.UiConfirmTotal(123445789 + 11000, 11000, coin),
            True,

            # check prev tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=ptx1),

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[pinp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout2])),

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized header
                serialized_tx=unhexlify('01000000000101'),
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized inp1
                serialized_tx=unhexlify('37c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02'),
            )),
            TxAck(tx=TransactionType(outputs=[out1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
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

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000'),
                signature_index=0,
                signature=unhexlify('3045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b'),
            )),
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoin.Bitcoin(tx, keychain, coin, approver).signer()
        for request, response in chunks(messages, 2):
            self.assertEqual(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_p2wpkh_in_p2sh_change(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

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
        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('4730440220548e087d0426b20b8a571b03b9e05829f7558b80c53c12143e342f56ab29e51d02205b68cb7fb223981d4c999725ac1485a982c4259c4f50b8280f137878c232998a012102794a25b254a268e59a5869da57fbae2fadc6727cb3309321dab409b12b2fa17c'),
                            prev_hash=unhexlify('802cabf0843b945eabe136d7fc7c89f41021658abf56cba000acbce88c41143a'),
                            prev_index=0,
                            script_type=None,
                            sequence=4294967295)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('76a914b84bacdcd8f4cc59274a5bfb73f804ca10f7fd1488ac'),
                                amount=865519308)

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
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),

            TxAck(tx=TransactionType(outputs=[out1])),

            helpers.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out2])),

            helpers.UiConfirmTotal(12300000 + 11000, 11000, coin),
            True,

            # check prev tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=ptx1),

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[pinp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout2])),

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized header
                          serialized_tx=unhexlify(
                              '01000000000101'),
            )),

            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized inp1
                          serialized_tx=unhexlify(
                              '37c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out1.__dict__)])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out1
                          serialized_tx=unhexlify(
                              'e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
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

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify(
                    '02483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000'),
                signature_index=0,
                signature=unhexlify('3045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b'),
            )),
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoin.Bitcoin(tx, keychain, coin, approver).signer()
        for request, response in chunks(messages, 2):
            self.assertEqual(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_p2wpkh_in_p2sh_attack_amount(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

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
        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('4730440220548e087d0426b20b8a571b03b9e05829f7558b80c53c12143e342f56ab29e51d02205b68cb7fb223981d4c999725ac1485a982c4259c4f50b8280f137878c232998a012102794a25b254a268e59a5869da57fbae2fadc6727cb3309321dab409b12b2fa17c'),
                            prev_hash=unhexlify('802cabf0843b945eabe136d7fc7c89f41021658abf56cba000acbce88c41143a'),
                            prev_index=0,
                            script_type=None,
                            sequence=4294967295)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('76a914b84bacdcd8f4cc59274a5bfb73f804ca10f7fd1488ac'),
                                amount=865519308)

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
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inpattack])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out1])),

            helpers.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out2])),

            helpers.UiConfirmTotal(9 - 1, 9 - 8 - 1, coin),
            True,

            # check prev tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=ptx1),

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[pinp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout2])),

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized header
                          serialized_tx=unhexlify(
                              '01000000000101'),
            )),
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoin.Bitcoin(tx, keychain, coin, approver).signer()
        i = 0
        messages_count = int(len(messages) / 2)
        for request, response in chunks(messages, 2):
            if i == messages_count - 1:  # last message should throw wire.Error
                self.assertRaises(wire.DataError, signer.send, request)
            else:
                self.assertEqual(signer.send(request), response)
            i += 1
        with self.assertRaises(StopIteration):
            signer.send(None)


if __name__ == '__main__':
    unittest.main()
