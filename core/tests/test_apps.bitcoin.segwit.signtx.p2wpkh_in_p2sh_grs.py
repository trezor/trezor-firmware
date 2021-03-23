from common import *

from trezor.utils import chunks
from trezor.crypto import bip39
from trezor.messages import SignTx
from trezor.messages import TxAckInput
from trezor.messages import TxAckInputWrapper
from trezor.messages import TxInput
from trezor.messages import TxAckOutput
from trezor.messages import TxAckOutputWrapper
from trezor.messages import TxOutput
from trezor.messages import TxAckPrevMeta
from trezor.messages import PrevTx
from trezor.messages import TxAckPrevInput
from trezor.messages import TxAckPrevInputWrapper
from trezor.messages import PrevInput
from trezor.messages import TxAckPrevOutput
from trezor.messages import TxAckPrevOutputWrapper
from trezor.messages import PrevOutput
from trezor.messages import TxRequest
from trezor.enums.RequestType import TXINPUT, TXMETA, TXOUTPUT, TXFINISHED
from trezor.messages import TxRequestDetailsType
from trezor.messages import TxRequestSerializedType
from trezor.enums import AmountUnit
from trezor.enums import InputScriptType
from trezor.enums import OutputScriptType

from apps.common import coins
from apps.common.keychain import Keychain
from apps.bitcoin.keychain import get_schemas_for_coin
from apps.bitcoin.sign_tx import bitcoinlike, helpers


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


# https://groestlsight-test.groestlcoin.org/api/tx/4ce0220004bdfe14e3dd49fd8636bcb770a400c0c9e9bff670b6a13bb8f15c72
@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSignSegwitTxP2WPKHInP2SH_GRS(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_p2wpkh_in_p2sh(self):

        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('09a48bce2f9d5c6e4f0cb9ea1b32d0891855e8acfe5334f9ebd72b9ad2de60cf'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=650749, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('47304402201f8f57f708144c3a11da322546cb37bd385aa825d940c37e8016f0efd6ec3e9402202a41bc02c29e4f3f13efd4bededbcd4308a6393279111d614ee1f7635cf3e65701210371546a36bdf6bc82087301b3f6e759736dc8790150673d2e7e2715d2ad72f3a4'),
                            prev_hash=unhexlify('4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1'),
                            prev_index=1,
                            sequence=4294967294)
        pout1 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a91435528b20e9a793cf2c3a1cf9cff1f2127ad377da88ac'),
                                amount=9764242764)

        out1 = TxOutput(
            address='mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address='2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=123456789 - 11000 - 12300000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=1, lock_time=650756, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            helpers.UiConfirmOutput(out1, coin, AmountUnit.BITCOIN),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

            helpers.UiConfirmOutput(out2, coin, AmountUnit.BITCOIN),
            True,

            helpers.UiConfirmNonDefaultLocktime(tx.lock_time, lock_time_disabled=False),
            True,

            helpers.UiConfirmTotal(123445789 + 11000, 11000, coin, AmountUnit.BITCOIN),
            True,

            # check prev tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevMeta(tx=ptx1),

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout2)),

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized header
                serialized_tx=unhexlify('01000000000101'),
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized inp1
                serialized_tx=unhexlify('cf60ded29a2bd7ebf93453feace8551889d0321beab90c4f6e5c9d2fce8ba4090000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5feffffff02'),
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('e0aebb00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac'),
                signature_index=None,
                signature=None,
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out2
                serialized_tx=unhexlify('3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                signature_index=None,
                signature=None,
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7904ee0900'),
                signature_index=0,
                signature=unhexlify('3045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80'),
            )),
        ]

        ns = get_schemas_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        signer = bitcoinlike.Bitcoinlike(tx, keychain, coin, None).signer()
        for request, expected_response in chunks(messages, 2):
            response = signer.send(request)
            if isinstance(response, tuple):
                _, response = response
            self.assertEqual(response, expected_response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_p2wpkh_in_p2sh_change(self):

        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('09a48bce2f9d5c6e4f0cb9ea1b32d0891855e8acfe5334f9ebd72b9ad2de60cf'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=650749, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('47304402201f8f57f708144c3a11da322546cb37bd385aa825d940c37e8016f0efd6ec3e9402202a41bc02c29e4f3f13efd4bededbcd4308a6393279111d614ee1f7635cf3e65701210371546a36bdf6bc82087301b3f6e759736dc8790150673d2e7e2715d2ad72f3a4'),
                            prev_hash=unhexlify('4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1'),
                            prev_index=1,
                            sequence=4294967294)
        pout1 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a91435528b20e9a793cf2c3a1cf9cff1f2127ad377da88ac'),
                                amount=9764242764)

        out1 = TxOutput(
            address='mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOP2SHWITNESS,
            amount=123456789 - 11000 - 12300000,
            address=None,
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=1, lock_time=650756, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            helpers.UiConfirmOutput(out1, coin, AmountUnit.BITCOIN),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

            helpers.UiConfirmNonDefaultLocktime(tx.lock_time, lock_time_disabled=False),
            True,

            helpers.UiConfirmTotal(12300000 + 11000, 11000, coin, AmountUnit.BITCOIN),
            True,

            # check prev tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevMeta(tx=ptx1),

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=inp1.prev_hash), serialized=EMPTY_SERIALIZED),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout2)),

            # sign tx
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized header
                          serialized_tx=unhexlify(
                              '01000000000101'),
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized inp1
                          serialized_tx=unhexlify(
                              'cf60ded29a2bd7ebf93453feace8551889d0321beab90c4f6e5c9d2fce8ba4090000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5feffffff02'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAckOutput(tx=TxAckOutputWrapper(output=TxOutput(**out1.__dict__))),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out1
                          serialized_tx=unhexlify(
                              'e0aebb00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac'),
                          signature_index=None,
                          signature=None,
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=TxOutput(**out2.__dict__))),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out2
                          serialized_tx=unhexlify(
                              '3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                          signature_index=None,
                          signature=None,
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7904ee0900'),
                signature_index=0,
                signature=unhexlify('3045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80'),
            )),
        ]

        ns = get_schemas_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        signer = bitcoinlike.Bitcoinlike(tx, keychain, coin, None).signer()
        for request, expected_response in chunks(messages, 2):
            response = signer.send(request)
            if isinstance(response, tuple):
                _, response = response
            self.assertEqual(response, expected_response)
        with self.assertRaises(StopIteration):
            signer.send(None)


if __name__ == '__main__':
    unittest.main()
