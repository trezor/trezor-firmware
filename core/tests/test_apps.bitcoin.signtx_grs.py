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
from trezor.enums.RequestType import TXINPUT, TXOUTPUT, TXMETA, TXFINISHED
from trezor.messages import TxRequestDetailsType
from trezor.messages import TxRequestSerializedType
from trezor.enums import AmountUnit
from trezor.enums import OutputScriptType

from apps.common import coins
from apps.common.keychain import Keychain
from apps.bitcoin.keychain import get_schemas_for_coin
from apps.bitcoin.sign_tx import bitcoinlike, helpers


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSignTx_GRS(unittest.TestCase):
    # pylint: disable=C0301

    def test_one_one_fee(self):
        # http://groestlsight.groestlcoin.org/tx/f56521b17b828897f72b30dd21b0192fd942342e89acbb06abf1d446282c30f5
        # ptx1: http://groestlsight.groestlcoin.org/api/tx/cb74c8478c5814742c87cffdb4a21231869888f8042fb07a90e015a9db1f9d4a

        coin = coins.by_name('Groestlcoin')

        ptx1 = PrevTx(version=1, lock_time=2160993, inputs_count=1, outputs_count=1, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('48304502210096a287593b1212a188e778596eb8ecd4cc169b93a4d115226460d8e3deae431c02206c78ec09b3df977f04a6df5eb53181165c4ea5a0b35f826551349130f879d6b8012102cf5126ff54e38a80a919579d7091cafe24840eab1d30fe2b4d59bdd9d267cad8'),
                            prev_hash=unhexlify('7dc74a738c50c2ae1228ce9890841e5355fd6d7f2c1367e0a74403ab60db3224'),
                            prev_index=0,
                            sequence=4294967294)
        pout1 = PrevOutput(script_pubkey=unhexlify('76a914172b4e06e9b7881a48d2ee8062b495d0b2517fe888ac'),
                                amount=210016)

        inp1 = TxInput(address_n=[44 | 0x80000000, 17 | 0x80000000, 0 | 0x80000000, 0, 2],  #  FXHDsC5ZqWQHkDmShzgRVZ1MatpWhwxTAA
                           prev_hash=unhexlify('cb74c8478c5814742c87cffdb4a21231869888f8042fb07a90e015a9db1f9d4a'),
                           prev_index=0,
                           amount=210016)
        out1 = TxOutput(address='FtM4zAn9aVYgHgxmamWBgWPyZsb6RhvkA9',
                            amount=210016 - 192,
                            script_type=OutputScriptType.PAYTOADDRESS,
                            address_n=[])
        tx = SignTx(coin_name='Groestlcoin', version=1, lock_time=0, inputs_count=1, outputs_count=1)

        messages = [
            None,
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmOutput(out1, coin, AmountUnit.BITCOIN),
            True,
            helpers.UiConfirmTotal(210016, 192, coin, AmountUnit.BITCOIN),
            True,
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=unhexlify('cb74c8478c5814742c87cffdb4a21231869888f8042fb07a90e015a9db1f9d4a')), serialized=EMPTY_SERIALIZED),
            TxAckPrevMeta(tx=ptx1),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('cb74c8478c5814742c87cffdb4a21231869888f8042fb07a90e015a9db1f9d4a')), serialized=EMPTY_SERIALIZED),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('cb74c8478c5814742c87cffdb4a21231869888f8042fb07a90e015a9db1f9d4a')), serialized=EMPTY_SERIALIZED),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            # ButtonRequest(code=ButtonRequest_ConfirmOutput),
            # ButtonRequest(code=ButtonRequest_SignTx),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                signature_index=None,
                signature=None,
                serialized_tx=unhexlify('0100000001'))),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(
                signature_index=0,
                signature=unhexlify('304402201fb96d20d0778f54520ab59afe70d5fb20e500ecc9f02281cf57934e8029e8e10220383d5a3e80f2e1eb92765b6da0f23d454aecbd8236f083d483e9a74302368761'),
                serialized_tx=unhexlify('4a9d1fdba915e0907ab02f04f88898863112a2b4fdcf872c7414588c47c874cb000000006a47304402201fb96d20d0778f54520ab59afe70d5fb20e500ecc9f02281cf57934e8029e8e10220383d5a3e80f2e1eb92765b6da0f23d454aecbd8236f083d483e9a7430236876101210331693756f749180aeed0a65a0fab0625a2250bd9abca502282a4cf0723152e67ffffffff01'))),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            TxRequest(request_type=TXFINISHED, details=TxRequestDetailsType(), serialized=TxRequestSerializedType(
                signature_index=None,
                signature=None,
                serialized_tx=unhexlify('a0330300000000001976a914fe40329c95c5598ac60752a5310b320cb52d18e688ac00000000'),
            )),
        ]

        seed = bip39.seed(' '.join(['all'] * 12), '')
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
