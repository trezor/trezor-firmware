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
from trezor import wire

from apps.common import coins
from apps.common.keychain import Keychain
from apps.bitcoin.keychain import get_schemas_for_coin
from apps.bitcoin.sign_tx import helpers, bitcoin


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


class TestSignSegwitTxNativeP2WPKH(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_native_p2wpkh(self):

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
        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                            prev_index=0,
                            sequence=4294967295)
        pout1 = PrevOutput(script_pubkey=unhexlify('00140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c'),
                                amount=12300000)
        pout2 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=111145789)

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
        tx = SignTx(coin_name='Testnet', version=1, lock_time=0, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            helpers.UiConfirmOutput(out1, coin, AmountUnit.BITCOIN),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

            helpers.UiConfirmOutput(out2, coin, AmountUnit.BITCOIN),
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
                serialized_tx=unhexlify('8a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02'),
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
                serialized_tx=unhexlify('a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                signature_index=None,
                signature=None,
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000'),
                signature_index=0,
                signature=unhexlify('3045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b95'),
            )),
        ]

        ns = get_schemas_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        signer = bitcoin.Bitcoin(tx, keychain, coin, None).signer()
        for request, response in chunks(messages, 2):
            res = signer.send(request)
            if isinstance(res, tuple):
                _, res = res
            self.assertEqual(res, response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_native_p2wpkh_change(self):

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
        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                            prev_index=0,
                            sequence=4294967295)
        pout1 = PrevOutput(script_pubkey=unhexlify('00140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c'),
                                amount=12300000)
        pout2 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=111145789)

        out1 = TxOutput(
            address='2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp',
            amount=5000000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address=None,
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOWITNESS,
            amount=12300000 - 11000 - 5000000,
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=1, lock_time=0, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            helpers.UiConfirmOutput(out1, coin, AmountUnit.BITCOIN),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

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
                serialized_tx=unhexlify('8a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02'),
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
                serialized_tx=unhexlify('a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                signature_index=None,
                signature=None,
            )),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                serialized_tx=unhexlify('02483045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b950121033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf00000000'),
                signature_index=0,
                signature=unhexlify('3045022100a7ca8f097525f9044e64376dc0a0f5d4aeb8d15d66808ba97979a0475b06b66502200597c8ebcef63e047f9aeef1a8001d3560470cf896c12f6990eec4faec599b95'),
            )),
        ]

        ns = get_schemas_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        signer = bitcoin.Bitcoin(tx, keychain, coin, None).signer()
        for request, expected_response in chunks(messages, 2):
            response = signer.send(request)
            if isinstance(response, tuple):
                _, response = response
            self.assertEqual(response, expected_response)
        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_send_native_invalid_address(self):

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
        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('160014d16b8c0680c61fc6ed2e407455715055e41052f5'),
                            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
                            prev_index=0,
                            sequence=4294967295)
        pout1 = PrevOutput(script_pubkey=unhexlify('00140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c'),
                                amount=12300000)
        pout2 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=111145789)

        out1 = TxOutput(
            address='TB1Q694CCP5QCC0UDMFWGP692U2S2HJPQ5H407URTU',  # Error: should be lower case
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=12300000 - 11000 - 5000000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=1, lock_time=0, inputs_count=1, outputs_count=1)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),

            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            None
        ]

        ns = get_schemas_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        signer = bitcoin.Bitcoin(tx, keychain, coin, None).signer()
        for request, expected_response in chunks(messages, 2):
            if expected_response is None:
                with self.assertRaises(wire.DataError):
                    signer.send(request)
            else:
                response = signer.send(request)
                if isinstance(response, tuple):
                    _, response = response
                self.assertEqual(response, expected_response)


if __name__ == '__main__':
    unittest.main()
