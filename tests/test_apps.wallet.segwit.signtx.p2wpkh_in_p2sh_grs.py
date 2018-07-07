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

# https://groestlsight-test.groestlcoin.org/api/tx/4ce0220004bdfe14e3dd49fd8636bcb770a400c0c9e9bff670b6a13bb8f15c72
class TestSignSegwitTxP2WPKHInP2SH_GRS(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_p2wpkh_in_p2sh(self):

        coin = coins.by_name('Groestlcoin Testnet')

        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, coin.curve_name)

        inp1 = TxInputType(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('09a48bce2f9d5c6e4f0cb9ea1b32d0891855e8acfe5334f9ebd72b9ad2de60cf'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        out1 = TxOutputType(
            address='mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutputType(
            address='2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=123456789 - 11000 - 12300000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=None, lock_time=650756, inputs_count=1, outputs_count=2)

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

            signing.UiConfirmTotal(123445789, 11000, coin),
            True,

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized inp1
                serialized_tx=unhexlify('01000000000101cf60ded29a2bd7ebf93453feace8551889d0321beab90c4f6e5c9d2fce8ba4090000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5feffffff'),
            )),
            TxAck(tx=TransactionType(outputs=[out1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('02e0aebb00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac'),
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
                serialized_tx=unhexlify('02483045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7904ee0900'),
                signature_index=0,
                signature=unhexlify('3045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80'),
            )),
        ]

        signer = signing.sign_tx(tx, root)
        for request, response in chunks(messages, 2):
            self.assertEqualEx(signer.send(request), response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_p2wpkh_in_p2sh_change(self):

        coin = coins.by_name('Groestlcoin Testnet')

        seed = bip39.seed(' '.join(['all'] * 12), '')
        root = bip32.from_seed(seed, coin.curve_name)

        inp1 = TxInputType(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('09a48bce2f9d5c6e4f0cb9ea1b32d0891855e8acfe5334f9ebd72b9ad2de60cf'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        out1 = TxOutputType(
            address='mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y',
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
        tx = SignTx(coin_name='Groestlcoin Testnet', version=None, lock_time=650756, inputs_count=1, outputs_count=2)

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

            signing.UiConfirmTotal(12300000, 11000, coin),
            True,

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=None),
            TxAck(tx=TransactionType(inputs=[inp1])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized inp1
                          serialized_tx=unhexlify(
                              '01000000000101cf60ded29a2bd7ebf93453feace8551889d0321beab90c4f6e5c9d2fce8ba4090000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5feffffff'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAck(tx=TransactionType(outputs=[TxOutputType(**out1.__dict__)])),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out1
                          serialized_tx=unhexlify(
                              '02e0aebb00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac'),
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
                serialized_tx=unhexlify('02483045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7904ee0900'),
                signature_index=0,
                signature=unhexlify('3045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80'),
            )),
        ]

        signer = signing.sign_tx(tx, root)
        for request, response in chunks(messages, 2):
            self.assertEqualEx(signer.send(request), response)
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
