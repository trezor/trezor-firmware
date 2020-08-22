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

from apps.common import coins
from apps.common.keychain import Keychain
from apps.bitcoin.keychain import get_namespaces_for_coin
from apps.bitcoin.sign_tx import bitcoinlike, helpers
from apps.bitcoin.sign_tx.approvers import BasicApprover


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


# https://groestlsight-test.groestlcoin.org/api/tx/9b5c4859a8a31e69788cb4402812bb28f14ad71cbd8c60b09903478bc56f79a3
@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSignSegwitTxNativeP2WPKH_GRS(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_native_p2wpkh(self):

        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInputType(
            # 84'/1'/0'/0/0" - tgrs1qkvwu9g3k2pdxewfqr7syz89r3gj557l3ued7ja
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        ptx1 = TransactionType(version=1, lock_time=650645, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('483045022100d9615361c044e91f6dd7bb4455f3ad686cd5a663d7800bb74c448b2706500ccb022026bed24b81a501e8398411c5a9a793741d9bfe39617d51c363dde0a84f44f4f9012102659a6eefcc72d6f2eff92e57095388b17db0b06034946ecd44120e5e7a830ff4'),
                            prev_hash=unhexlify('1c92508b38239e5c10b23fb46dcf765ee2f3a95b835edbf0943ec21b21711160'),
                            prev_index=1,
                            script_type=None,
                            sequence=4294967293)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('0014b31dc2a236505a6cb9201fa0411ca38a254a7bf1'),
                                amount=12300000)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('76a91438cc090e4a4b2e458c33fe35af1c5c0094699ac288ac'),
                                amount=9887699777)

        out1 = TxOutputType(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address='tgrs1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt9lkd57',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=12300000 - 11000 - 5000000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=None, lock_time=650713, inputs_count=1, outputs_count=2)

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

            helpers.UiConfirmNonDefaultLocktime(tx.lock_time, lock_time_disabled=False),
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
                serialized_tx=unhexlify('d1613f483f2086d076c82fe34674385a86beb08f052d5405fe1aed397f852f4f0000000000feffffff02'),
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
                serialized_tx=unhexlify('a8386f0000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862d9ed0900'),
                signature_index=0,
                signature=unhexlify('3045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3'),
            )),
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoinlike.Bitcoinlike(tx, keychain, coin, approver).signer()
        for request, response in chunks(messages, 2):
            self.assertEqual(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_native_p2wpkh_change(self):

        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInputType(
            # 84'/1'/0'/0/0" - tgrs1qkvwu9g3k2pdxewfqr7syz89r3gj557l3ued7ja
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        ptx1 = TransactionType(version=1, lock_time=650645, inputs_cnt=1, outputs_cnt=2, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('483045022100d9615361c044e91f6dd7bb4455f3ad686cd5a663d7800bb74c448b2706500ccb022026bed24b81a501e8398411c5a9a793741d9bfe39617d51c363dde0a84f44f4f9012102659a6eefcc72d6f2eff92e57095388b17db0b06034946ecd44120e5e7a830ff4'),
                            prev_hash=unhexlify('1c92508b38239e5c10b23fb46dcf765ee2f3a95b835edbf0943ec21b21711160'),
                            prev_index=1,
                            script_type=None,
                            sequence=4294967293)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('0014b31dc2a236505a6cb9201fa0411ca38a254a7bf1'),
                                amount=12300000)
        pout2 = TxOutputBinType(script_pubkey=unhexlify('76a91438cc090e4a4b2e458c33fe35af1c5c0094699ac288ac'),
                                amount=9887699777)

        out1 = TxOutputType(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address=None,
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOWITNESS,
            amount=12300000 - 11000 - 5000000,
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=None, lock_time=650713, inputs_count=1, outputs_count=2)

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

            helpers.UiConfirmNonDefaultLocktime(tx.lock_time, lock_time_disabled=False),
            True,

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
                serialized_tx=unhexlify('d1613f483f2086d076c82fe34674385a86beb08f052d5405fe1aed397f852f4f0000000000feffffff02'),
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
                serialized_tx=unhexlify('a8386f0000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b'),
                signature_index=None,
                signature=None,
            )),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862d9ed0900'),
                signature_index=0,
                signature=unhexlify('3045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3'),
            )),
        ]

        ns = get_namespaces_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        approver = BasicApprover(tx, coin)
        signer = bitcoinlike.Bitcoinlike(tx, keychain, coin, approver).signer()
        for request, response in chunks(messages, 2):
            self.assertEqual(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)


if __name__ == '__main__':
    unittest.main()
