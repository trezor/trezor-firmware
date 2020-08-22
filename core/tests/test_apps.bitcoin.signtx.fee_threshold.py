from common import *

from trezor.utils import chunks
from trezor.crypto import bip32, bip39
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TxAck import TxAck
from trezor.messages.TransactionType import TransactionType
from trezor.messages.RequestType import TXINPUT, TXOUTPUT, TXMETA
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.messages import OutputScriptType

from apps.common import coins
from apps.common.keychain import Keychain
from apps.bitcoin.sign_tx import bitcoin, helpers
from apps.bitcoin.sign_tx.approvers import BasicApprover


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

        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=2, outputs_cnt=1, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('483045022072ba61305fe7cb542d142b8f3299a7b10f9ea61f6ffaab5dca8142601869d53c0221009a8027ed79eb3b9bc13577ac2853269323434558528c6b6a7e542be46e7e9a820141047a2d177c0f3626fc68c53610b0270fa6156181f46586c679ba6a88b34c6f4874686390b4d92e5769fbb89c8050b984f4ec0b257a0e5c4ff8bd3b035a51709503'),
                            prev_hash=unhexlify('c16a03f1cf8f99f6b5297ab614586cacec784c2d259af245909dedb0e39eddcf'),
                            prev_index=1,
                            multisig=None,
                            script_type=None,
                            sequence=None)
        pinp2 = TxInputType(script_sig=unhexlify('48304502200fd63adc8f6cb34359dc6cca9e5458d7ea50376cbd0a74514880735e6d1b8a4c0221008b6ead7fe5fbdab7319d6dfede3a0bc8e2a7c5b5a9301636d1de4aa31a3ee9b101410486ad608470d796236b003635718dfc07c0cac0cfc3bfc3079e4f491b0426f0676e6643a39198e8e7bdaffb94f4b49ea21baa107ec2e237368872836073668214'),
                            prev_hash=unhexlify('1ae39a2f8d59670c8fc61179148a8e61e039d0d9e8ab08610cb69b4a19453eaf'),
                            prev_index=1,
                            multisig=None,
                            script_type=None,
                            sequence=None)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac'),
                                amount=390000)

        inp1 = TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                           # amount=390000,
                           prev_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                           prev_index=0,
                           amount=None,
                           script_type=None,
                           multisig=None,
                           sequence=None)
        out1 = TxOutputType(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                            amount=390000 - 100000,  # fee increased to 100000 => too high
                            multisig=None,
                            script_type=OutputScriptType.PAYTOADDRESS,
                            address_n=[])
        tx = SignTx(coin_name=None, version=None, lock_time=None, inputs_count=1, outputs_count=1)

        messages = [
            None,

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None)),
            TxAck(tx=TransactionType(inputs=[inp1])),
            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,
            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAck(tx=ptx1),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAck(tx=TransactionType(inputs=[pinp1])),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=1, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAck(tx=TransactionType(inputs=[pinp2])),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=None),
            TxAck(tx=TransactionType(bin_outputs=[pout1])),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
            TxAck(tx=TransactionType(outputs=[out1])),
            helpers.UiConfirmOutput(out1, coin_bitcoin),
            True,
            helpers.UiConfirmFeeOverThreshold(100000, coin_bitcoin),
            True,
            helpers.UiConfirmTotal(290000 + 100000, 100000, coin_bitcoin),
            True,
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=None),
        ]

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        root = bip32.from_seed(seed, 'secp256k1')

        keychain = Keychain([[coin_bitcoin.curve_name]], [root])
        signer = signing.sign_tx(tx, keychain)
        for request, response in chunks(messages, 2):
            self.assertEqual(signer.send(request), response)
    """

    def test_under_threshold(self):
        coin_bitcoin = coins.by_name('Bitcoin')

        ptx1 = TransactionType(version=1, lock_time=0, inputs_cnt=2, outputs_cnt=1, extra_data_len=0)
        pinp1 = TxInputType(script_sig=unhexlify('483045022072ba61305fe7cb542d142b8f3299a7b10f9ea61f6ffaab5dca8142601869d53c0221009a8027ed79eb3b9bc13577ac2853269323434558528c6b6a7e542be46e7e9a820141047a2d177c0f3626fc68c53610b0270fa6156181f46586c679ba6a88b34c6f4874686390b4d92e5769fbb89c8050b984f4ec0b257a0e5c4ff8bd3b035a51709503'),
                            prev_hash=unhexlify('c16a03f1cf8f99f6b5297ab614586cacec784c2d259af245909dedb0e39eddcf'),
                            prev_index=1,
                            script_type=None,
                            multisig=None,
                            sequence=None)
        pinp2 = TxInputType(script_sig=unhexlify('48304502200fd63adc8f6cb34359dc6cca9e5458d7ea50376cbd0a74514880735e6d1b8a4c0221008b6ead7fe5fbdab7319d6dfede3a0bc8e2a7c5b5a9301636d1de4aa31a3ee9b101410486ad608470d796236b003635718dfc07c0cac0cfc3bfc3079e4f491b0426f0676e6643a39198e8e7bdaffb94f4b49ea21baa107ec2e237368872836073668214'),
                            prev_hash=unhexlify('1ae39a2f8d59670c8fc61179148a8e61e039d0d9e8ab08610cb69b4a19453eaf'),
                            prev_index=1,
                            multisig=None,
                            script_type=None,
                            sequence=None)
        pout1 = TxOutputBinType(script_pubkey=unhexlify('76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac'),
                                amount=390000)

        inp1 = TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                           amount=390000,
                           prev_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                           prev_index=0,
                           multisig=None,
                           script_type=None,
                           sequence=None)
        out1 = TxOutputType(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                            amount=390000 - 90000,  # fee increased to 90000, slightly less than the threshold
                            script_type=OutputScriptType.PAYTOADDRESS,
                            multisig=None,
                            address_n=[])
        tx = SignTx(coin_name=None, version=None, lock_time=None, inputs_count=1, outputs_count=1)

        messages = [
            None,

            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),
            helpers.UiConfirmForeignAddress(address_n=inp1.address_n),
            True,
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(outputs=[out1])),
            helpers.UiConfirmOutput(out1, coin_bitcoin),
            True,
            helpers.UiConfirmTotal(300000 + 90000, 90000, coin_bitcoin),
            True,
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[inp1])),
            TxRequest(request_type=TXMETA, details=TxRequestDetailsType(request_index=None, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAck(tx=ptx1),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[pinp1])),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=1, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(inputs=[pinp2])),
            TxRequest(request_type=TXOUTPUT, details=TxRequestDetailsType(request_index=0, tx_hash=unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')), serialized=EMPTY_SERIALIZED),
            TxAck(tx=TransactionType(bin_outputs=[pout1])),
            TxRequest(request_type=TXINPUT, details=TxRequestDetailsType(request_index=0, tx_hash=None), serialized=TxRequestSerializedType(serialized_tx=unhexlify('0100000001'))),
        ]

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')

        keychain = Keychain(seed, coin_bitcoin.curve_name, [[]])
        approver = BasicApprover(tx, coin_bitcoin)
        signer = bitcoin.Bitcoin(tx, keychain, coin_bitcoin, approver).signer()
        for request, response in chunks(messages, 2):
            res = signer.send(request)
            self.assertEqual(res, response)


if __name__ == '__main__':
    unittest.main()
