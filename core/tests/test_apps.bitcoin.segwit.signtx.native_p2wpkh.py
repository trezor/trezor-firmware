from common import *

from trezor.utils import chunks
from trezor.crypto import bip39
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxOutputType import TxOutputType
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
from apps.bitcoin.sign_tx import helpers, bitcoin
from apps.bitcoin.sign_tx.approvers import BasicApprover


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


class TestSignSegwitTxNativeP2WPKH(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_native_p2wpkh(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInputType(
            # 49'/1'/0'/0/0" - tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                            prev_index=0,
                            script_type=None,
                            sequence=4294967295)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('00140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c'),
                                amount=12300000)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=111145789)

        out1 = TxOutputType(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address='tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=12300000 - 11000 - 5000000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=None, lock_time=None, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out1])),

            helpers.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out2])),

            helpers.UiConfirmOutput(out2, coin),
            True,

            helpers.UiConfirmTotal(12300000, 11000, coin),
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
                serialized_tx=unhexlify('8a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02'),
            )),
            TxAck(tx=TransactionType(outputs=[out1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(outputs=[out2])),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out2
                serialized_tx=unhexlify('a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000'),
                signature_index=0,
                signature=unhexlify('3045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b95'),
            )),
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoin.Bitcoin(tx, keychain, coin, approver).signer()
        for request, response in chunks(messages, 2):
            res = signer.send(request)
            self.assertEqual(res, response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_native_p2wpkh_change(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInputType(
            # 49'/1'/0'/0/0" - tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                            prev_index=0,
                            script_type=None,
                            sequence=4294967295)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('00140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c'),
                                amount=12300000)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=111145789)

        out1 = TxOutputType(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address=None,
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOWITNESS,
            amount=12300000 - 11000 - 5000000,
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=None, lock_time=None, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out1])),

            helpers.UiConfirmOutput(out1, coin),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out2])),

            helpers.UiConfirmTotal(5000000 + 11000, 11000, coin),
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
                serialized_tx=unhexlify('8a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out1.__dict__)])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out2.__dict__)])),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out2
                serialized_tx=unhexlify('a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000'),
                signature_index=0,
                signature=unhexlify('3045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b95'),
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

    def test_send_native_invalid_address(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInputType(
            # 49'/1'/0'/0/0" - tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                            prev_index=0,
                            script_type=None,
                            sequence=4294967295)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('00140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c'),
                                amount=12300000)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=111145789)

        out1 = TxOutputType(
            address='TB1Q694CCP5QCC0UDMFWGP692U2S2HJPQ5H407URTU',  # Error: should be lower case
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=12300000 - 11000 - 5000000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=None, lock_time=None, inputs_count=1, outputs_count=1)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),

            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out1])),
            None
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoin.Bitcoin(tx, keychain, coin, approver).signer()
        for request, response in chunks(messages, 2):
            if response is None:
                with self.assertRaises(wire.DataError):
                    signer.send(request)
            else:
                self.assertEqual(signer.send(request), response)


if __name__ == '__main__':
    unittest.main()
