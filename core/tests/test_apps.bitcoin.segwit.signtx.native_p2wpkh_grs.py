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


# https://groestlsight-test.groestlcoin.org/api/tx/9b5c4859a8a31e69788cb4402812bb28f14ad71cbd8c60b09903478bc56f79a3
@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSignSegwitTxNativeP2WPKH_GRS(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_native_p2wpkh(self):

        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 84'/1'/0'/0/0" - tgrs1qkvwu9g3k2pdxewfqr7syz89r3gj557l3ued7ja
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=650645, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('483045022100d9615361c044e91f6dd7bb4455f3ad686cd5a663d7800bb74c448b2706500ccb022026bed24b81a501e8398411c5a9a793741d9bfe39617d51c363dde0a84f44f4f9012102659a6eefcc72d6f2eff92e57095388b17db0b06034946ecd44120e5e7a830ff4'),
                            prev_hash=unhexlify('1c92508b38239e5c10b23fb46dcf765ee2f3a95b835edbf0943ec21b21711160'),
                            prev_index=1,
                            sequence=4294967293)
        pout1 = PrevOutput(script_pubkey=unhexlify('0014b31dc2a236505a6cb9201fa0411ca38a254a7bf1'),
                                amount=12300000)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a91438cc090e4a4b2e458c33fe35af1c5c0094699ac288ac'),
                                amount=9887699777)

        out1 = TxOutput(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address='tgrs1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt9lkd57',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=12300000 - 11000 - 5000000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=1, lock_time=650713, inputs_count=1, outputs_count=2)

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

            helpers.UiConfirmTotal(12300000, 11000, coin, AmountUnit.BITCOIN),
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
                serialized_tx=unhexlify('d1613f483f2086d076c82fe34674385a86beb08f052d5405fe1aed397f852f4f0000000000feffffff02'),
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987'),
                signature_index=None,
                signature=None,
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out2
                serialized_tx=unhexlify('a8386f0000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b'),
                signature_index=None,
                signature=None,
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862d9ed0900'),
                signature_index=0,
                signature=unhexlify('3045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3'),
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

    def test_send_native_p2wpkh_change(self):

        coin = coins.by_name('Groestlcoin Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 84'/1'/0'/0/0" - tgrs1qkvwu9g3k2pdxewfqr7syz89r3gj557l3ued7ja
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=12300000,
            prev_hash=unhexlify('4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1'),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xfffffffe,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=650645, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('483045022100d9615361c044e91f6dd7bb4455f3ad686cd5a663d7800bb74c448b2706500ccb022026bed24b81a501e8398411c5a9a793741d9bfe39617d51c363dde0a84f44f4f9012102659a6eefcc72d6f2eff92e57095388b17db0b06034946ecd44120e5e7a830ff4'),
                            prev_hash=unhexlify('1c92508b38239e5c10b23fb46dcf765ee2f3a95b835edbf0943ec21b21711160'),
                            prev_index=1,
                            sequence=4294967293)
        pout1 = PrevOutput(script_pubkey=unhexlify('0014b31dc2a236505a6cb9201fa0411ca38a254a7bf1'),
                                amount=12300000)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a91438cc090e4a4b2e458c33fe35af1c5c0094699ac288ac'),
                                amount=9887699777)

        out1 = TxOutput(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address=None,
            address_n=[84 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOWITNESS,
            amount=12300000 - 11000 - 5000000,
            multisig=None,
        )
        tx = SignTx(coin_name='Groestlcoin Testnet', version=1, lock_time=650713, inputs_count=1, outputs_count=2)

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

            helpers.UiConfirmTotal(5000000 + 11000, 11000, coin, AmountUnit.BITCOIN),
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
                serialized_tx=unhexlify('d1613f483f2086d076c82fe34674385a86beb08f052d5405fe1aed397f852f4f0000000000feffffff02'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAckOutput(tx=TxAckOutputWrapper(output=TxOutput(**out1.__dict__))),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987'),
                signature_index=None,
                signature=None,
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=TxOutput(**out2.__dict__))),

            # segwit
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out2
                serialized_tx=unhexlify('a8386f0000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b'),
                signature_index=None,
                signature=None,
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862d9ed0900'),
                signature_index=0,
                signature=unhexlify('3045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3'),
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
