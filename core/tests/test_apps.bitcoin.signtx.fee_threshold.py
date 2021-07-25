from common import *

from trezor.utils import chunks
from trezor.crypto import bip32, bip39
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
from trezor.enums.RequestType import TXINPUT, TXOUTPUT, TXMETA
from trezor.messages import TxRequestDetailsType
from trezor.messages import TxRequestSerializedType
from trezor.enums import AmountUnit
from trezor.enums import OutputScriptType

from apps.common import coins
from apps.common.keychain import Keychain
from apps.common.paths import AlwaysMatchingSchema
from apps.bitcoin.sign_tx import bitcoin, helpers


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


class TestSignTxFeeThreshold(unittest.TestCase):
    # pylint: disable=C0301

    # the following test is disabled, because there are not enough
    # inputs to trigger the excessive threshold warning
    #
    # this is being tested in the device test:
    # test_msg_signtx.test_testnet_fee_too_high

    """
    def test_over_fee_threshold(self):
        coin_bitcoin = coins.by_name('Bitcoin')

        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=2, outputs_count=1, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('483045022072ba61305fe7cb542d142b8f3299a7b10f9ea61f6ffaab5dca8142601869d53c0221009a8027ed79eb3b9bc13577ac2853269323434558528c6b6a7e542be46e7e9a820141047a2d177c0f3626fc68c53610b0270fa6156181f46586c679ba6a88b34c6f4874686390b4d92e5769fbb89c8050b984f4ec0b257a0e5c4ff8bd3b035a51709503'),
                            prev_hash=unhexlify('c16a03f1cf8f99f6b5297ab614586cacec784c2d259af245909dedb0e39eddcf'),
                            prev_index=1)
        pinp2 = PrevInput(script_sig=unhexlify('48304502200fd63adc8f6cb34359dc6cca9e5458d7ea50376cbd0a74514880735e6d1b8a4c0221008b6ead7fe5fbdab7319d6dfede3a0bc8e2a7c5b5a9301636d1de4aa31a3ee9b101410486ad608470d796236b003635718dfc07c0cac0cfc3bfc3079e4f491b0426f0676e6643a39198e8e7bdaffb94f4b49ea21baa107ec2e237368872836073668214'),
                            prev_hash=unhexlify('1ae39a2f8d59670c8fc61179148a8e61e039d0d9e8ab08610cb69b4a19453eaf'),
                            prev_index=1)
        pout1 = PrevOutput(script_pubkey=unhexlify('76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac'),
                                amount=390000)

        inp1 = TxInput(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                           # amount=390000,
                           prev_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                           prev_index=0,
                           amount=None)
        out1 = TxOutput(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                            amount=390000 - 100000,  # fee increased to 100000 => too high
                            multisig=None,
                            script_type=OutputScriptType.PAYTOADDRESS,
                            address_n=[])
        tx = SignTx(coin_name=None, version=1, lock_time=0, inputs_count=1, outputs_count=1)

        messages = [
            None,

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None)),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,
            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAckPrevMeta(tx=ptx1),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=1, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp2)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmOutput(out1, coin_bitcoin, AmountUnit.BITCOIN),
            True,
            helpers.UiConfirmFeeOverThreshold(100000, coin_bitcoin),
            True,
            helpers.UiConfirmTotal(290000 + 100000, 100000, coin_bitcoin, AmountUnit.BITCOIN),
            True,
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
        ]

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        root = bip32.from_seed(seed, 'secp256k1')

        keychain = Keychain([[coin_bitcoin.curve_name]], [root])
        signer = signing.sign_tx(tx, keychain)
        for request, expected_response in chunks(messages, 2):
            response = signer.send(request)
            if isinstance(response, tuple):
                _, response = response
            self.assertEqual(response, expected_response)
    """

    def test_under_threshold(self):
        coin_bitcoin = coins.by_name('Bitcoin')

        ptx1 = PrevTx(version=1, lock_time=0, inputs_count=2, outputs_count=1, extra_data_len=0)
        pinp1 = PrevInput(script_sig=unhexlify('483045022072ba61305fe7cb542d142b8f3299a7b10f9ea61f6ffaab5dca8142601869d53c0221009a8027ed79eb3b9bc13577ac2853269323434558528c6b6a7e542be46e7e9a820141047a2d177c0f3626fc68c53610b0270fa6156181f46586c679ba6a88b34c6f4874686390b4d92e5769fbb89c8050b984f4ec0b257a0e5c4ff8bd3b035a51709503'),
                            prev_hash=unhexlify('c16a03f1cf8f99f6b5297ab614586cacec784c2d259af245909dedb0e39eddcf'),
                            prev_index=1,
                            sequence=0xffff_ffff)
        pinp2 = PrevInput(script_sig=unhexlify('48304502200fd63adc8f6cb34359dc6cca9e5458d7ea50376cbd0a74514880735e6d1b8a4c0221008b6ead7fe5fbdab7319d6dfede3a0bc8e2a7c5b5a9301636d1de4aa31a3ee9b101410486ad608470d796236b003635718dfc07c0cac0cfc3bfc3079e4f491b0426f0676e6643a39198e8e7bdaffb94f4b49ea21baa107ec2e237368872836073668214'),
                            prev_hash=unhexlify('1ae39a2f8d59670c8fc61179148a8e61e039d0d9e8ab08610cb69b4a19453eaf'),
                            prev_index=1,
                            sequence=0xffff_ffff)
        pout1 = PrevOutput(script_pubkey=unhexlify('76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac'),
                                amount=390000)

        inp1 = TxInput(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                           amount=390000,
                           prev_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                           prev_index=0,
                           multisig=None,
                           sequence=0xffff_ffff)
        out1 = TxOutput(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                            amount=390000 - 90000,  # fee increased to 90000, slightly less than the threshold
                            script_type=OutputScriptType.PAYTOADDRESS,
                            multisig=None,
                            address_n=[])
        tx = SignTx(coin_name=None, version=1, lock_time=0, inputs_count=1, outputs_count=1)

        messages = [
            None,

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmOutput(out1, coin_bitcoin, AmountUnit.BITCOIN),
            True,
            helpers.UiConfirmTotal(300000 + 90000, 90000, coin_bitcoin, AmountUnit.BITCOIN),
            True,
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAckPrevMeta(tx=ptx1),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=1, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp2)),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(serialized_tx=unhexlify('0100000001'))),
        ]

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')

        keychain = Keychain(seed, coin_bitcoin.curve_name, [AlwaysMatchingSchema])
        signer = bitcoin.Bitcoin(tx, keychain, coin_bitcoin, None).signer()
        for request, response in chunks(messages, 2):
            res = signer.send(request)
            if isinstance(res, tuple):
                _, res = res
            self.assertEqual(res, response)


if __name__ == '__main__':
    unittest.main()
