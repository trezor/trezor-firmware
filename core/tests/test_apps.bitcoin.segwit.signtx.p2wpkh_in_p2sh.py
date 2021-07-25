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
from apps.bitcoin.sign_tx import bitcoin, helpers


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


class TestSignSegwitTxP2WPKHInP2SH(unittest.TestCase):
    # pylint: disable=C0301

    def test_send_p2wpkh_in_p2sh(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('4730440220548e087d0426b20b8a571b03b9e05829f7558b80c53c12143e342f56ab29e51d02205b68cb7fb223981d4c999725ac1485a982c4259c4f50b8280f137878c232998a012102794a25b254a268e59a5869da57fbae2fadc6727cb3309321dab409b12b2fa17c'),
                            prev_hash=unhexlify('802cabf0843b945eabe136d7fc7c89f41021658abf56cba000acbce88c41143a'),
                            prev_index=0,
                            sequence=4294967295)
        pout1 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a914b84bacdcd8f4cc59274a5bfb73f804ca10f7fd1488ac'),
                                amount=865519308)

        out1 = TxOutput(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
            amount=12300000,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address='2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX',
            script_type=OutputScriptType.PAYTOADDRESS,
            amount=123456789 - 11000 - 12300000,
            address_n=[],
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=1, lock_time=0, inputs_count=1, outputs_count=2)

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
                serialized_tx=unhexlify('37c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02'),
            )),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=TxRequestSerializedType(
                # returned serialized out1
                serialized_tx=unhexlify('e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
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
                serialized_tx=unhexlify('02483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000'),
                signature_index=0,
                signature=unhexlify('3045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b'),
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

    def test_send_p2wpkh_in_p2sh_change(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=123456789,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('4730440220548e087d0426b20b8a571b03b9e05829f7558b80c53c12143e342f56ab29e51d02205b68cb7fb223981d4c999725ac1485a982c4259c4f50b8280f137878c232998a012102794a25b254a268e59a5869da57fbae2fadc6727cb3309321dab409b12b2fa17c'),
                            prev_hash=unhexlify('802cabf0843b945eabe136d7fc7c89f41021658abf56cba000acbce88c41143a'),
                            prev_index=0,
                            sequence=4294967295)
        pout1 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a914b84bacdcd8f4cc59274a5bfb73f804ca10f7fd1488ac'),
                                amount=865519308)

        out1 = TxOutput(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
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
        tx = SignTx(coin_name='Testnet', version=1, lock_time=0, inputs_count=1, outputs_count=2)

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
                              '37c361fb8f2d9056ba8c98c5611930fcb48cacfdd0fe2e0449d83eea982f91200000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5ffffffff02'),
            )),
            # the out has to be cloned not to send the same object which was modified
            TxAckOutput(tx=TxAckOutputWrapper(output=TxOutput(**out1.__dict__))),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None),
                      serialized=TxRequestSerializedType(
                          # returned serialized out1
                          serialized_tx=unhexlify(
                              'e0aebb00000000001976a91414fdede0ddc3be652a0ce1afbc1b509a55b6b94888ac'),
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
                serialized_tx=unhexlify(
                    '02483045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7900000000'),
                signature_index=0,
                signature=unhexlify('3045022100ccd253bfdf8a5593cd7b6701370c531199f0f05a418cd547dfc7da3f21515f0f02203fa08a0753688871c220648f9edadbdb98af42e5d8269364a326572cf703895b'),
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

    def test_send_p2wpkh_in_p2sh_attack_amount(self):

        coin = coins.by_name('Testnet')
        seed = bip39.seed(' '.join(['all'] * 12), '')

        inp1 = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=10,
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('4730440220548e087d0426b20b8a571b03b9e05829f7558b80c53c12143e342f56ab29e51d02205b68cb7fb223981d4c999725ac1485a982c4259c4f50b8280f137878c232998a012102794a25b254a268e59a5869da57fbae2fadc6727cb3309321dab409b12b2fa17c'),
                            prev_hash=unhexlify('802cabf0843b945eabe136d7fc7c89f41021658abf56cba000acbce88c41143a'),
                            prev_index=0,
                            sequence=4294967295)
        pout1 = PrevOutput(script_pubkey=unhexlify('a91458b53ea7f832e8f096e896b8713a8c6df0e892ca87'),
                                amount=123456789)
        pout2 = PrevOutput(script_pubkey=unhexlify('76a914b84bacdcd8f4cc59274a5bfb73f804ca10f7fd1488ac'),
                                amount=865519308)

        inpattack = TxInput(
            # 49'/1'/0'/1/0" - 2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            amount=9,  # modified!
            prev_hash=unhexlify('20912f98ea3ed849042efed0fdac8cb4fc301961c5988cba56902d8ffb61c337'),
            prev_index=0,
            script_type=InputScriptType.SPENDP2SHWITNESS,
            sequence=0xffffffff,
            multisig=None,
        )
        out1 = TxOutput(
            address='mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC',
            amount=8,
            script_type=OutputScriptType.PAYTOADDRESS,
            address_n=[],
            multisig=None,
        )
        out2 = TxOutput(
            address_n=[49 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 1, 0],
            script_type=OutputScriptType.PAYTOP2SHWITNESS,
            amount=1,
            address=None,
            multisig=None,
        )
        tx = SignTx(coin_name='Testnet', version=1, lock_time=0, inputs_count=1, outputs_count=2)

        messages = [
            None,

            # check fee
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inpattack)),

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),

            helpers.UiConfirmOutput(out1, coin, AmountUnit.BITCOIN),
            True,

            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=1, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),

            helpers.UiConfirmTotal(9 - 1, 9 - 8 - 1, coin, AmountUnit.BITCOIN),
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
        ]

        ns = get_schemas_for_coin(coin)
        keychain = Keychain(seed, coin.curve_name, ns)
        signer = bitcoin.Bitcoin(tx, keychain, coin, None).signer()
        i = 0
        messages_count = int(len(messages) / 2)
        for request, expected_response in chunks(messages, 2):
            if i == messages_count - 1:  # last message should throw wire.Error
                self.assertRaises(wire.DataError, signer.send, request)
            else:
                response = signer.send(request)
                if isinstance(response, tuple):
                    _, response = response
                self.assertEqual(response, expected_response)
            i += 1
        with self.assertRaises(StopIteration):
            signer.send(None)


if __name__ == '__main__':
    unittest.main()
