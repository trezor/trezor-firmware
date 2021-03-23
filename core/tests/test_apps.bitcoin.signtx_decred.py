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
from apps.bitcoin.sign_tx import decred, helpers


EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())

coin_decred = coins.by_name("Decred")

ptx1 = PrevTx(version=1, lock_time=0, inputs_count=2, outputs_count=1, extra_data_len=0)
pinp1 = PrevInput(
    script_sig=unhexlify(
        "483045022072ba61305fe7cb542d142b8f3299a7b10f9ea61f6ffaab5dca8142601869d53c0221009a8027ed79eb3b9bc13577ac2853269323434558528c6b6a7e542be46e7e9a820141047a2d177c0f3626fc68c53610b0270fa6156181f46586c679ba6a88b34c6f4874686390b4d92e5769fbb89c8050b984f4ec0b257a0e5c4ff8bd3b035a51709503"
    ),
    prev_hash=unhexlify(
        "c16a03f1cf8f99f6b5297ab614586cacec784c2d259af245909dedb0e39eddcf"
    ),
    prev_index=1,
    sequence=0xFFFF_FFFF,
)
pinp2 = PrevInput(
    script_sig=unhexlify(
        "48304502200fd63adc8f6cb34359dc6cca9e5458d7ea50376cbd0a74514880735e6d1b8a4c0221008b6ead7fe5fbdab7319d6dfede3a0bc8e2a7c5b5a9301636d1de4aa31a3ee9b101410486ad608470d796236b003635718dfc07c0cac0cfc3bfc3079e4f491b0426f0676e6643a39198e8e7bdaffb94f4b49ea21baa107ec2e237368872836073668214"
    ),
    prev_hash=unhexlify(
        "1ae39a2f8d59670c8fc61179148a8e61e039d0d9e8ab08610cb69b4a19453eaf"
    ),
    prev_index=1,
    sequence=0xFFFF_FFFF,
)
pout1 = PrevOutput(
    script_pubkey=unhexlify("76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac"),
    amount=200000 + 200000 - 10000,
    decred_script_version=0,
)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSignTxDecred(unittest.TestCase):
    # pylint: disable=C0301

    def test_one_one_fee(self):

        inp1 = TxInput(
            address_n=[44 | 0x80000000, 42 | 0x80000000, 0 | 0x80000000, 0, 0],
            prev_hash=unhexlify(
                "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
            ),
            prev_index=0,
            amount=390000,
            multisig=None,
            sequence=0xFFFF_FFFF,
        )
        out1 = TxOutput(
            address="DsaHnKa418BeeQmyhpQEGG4cxGAPrneydfv",
            amount=390000 - 10000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        tx = SignTx(
            coin_name="Decred", version=1, lock_time=0, inputs_count=1, outputs_count=1
        )

        messages = [
            None,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("0100000001")
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("4ac247307a054c37525169a78d690a7a7f87d709bef7d722aae85584f59c8fdf0000000000ffffffff01")
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmOutput(out1, coin_decred, AmountUnit.BITCOIN),
            True,
            helpers.UiConfirmTotal(380000 + 10000, 10000, coin_decred, AmountUnit.BITCOIN),
            True,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("60cc05000000000000001976a914664b0cd46741a695a38f8ed37db2a20327471beb88ac0000000000000000")
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXMETA,
                details=TxRequestDetailsType(
                    request_index=None,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevMeta(tx=ptx1),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(
                    request_index=0,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(
                    request_index=1,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp2)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(
                    request_index=0,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("01")
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXFINISHED,
                details=TxRequestDetailsType(request_index=None, tx_hash=None),
                serialized=TxRequestSerializedType(
                    signature_index=0,
                    signature=unhexlify(
                        "3044022078a5c388838796562eb9dad176b00e6d9425bc360083f633a14948685ca8a5ce02202a1b49cd44104a9d40aee8f988281a8aac94a497b5bc7337c77cc7ddbab16f23"
                    ),
                    serialized_tx=unhexlify("70f305000000000000000000ffffffff6a473044022078a5c388838796562eb9dad176b00e6d9425bc360083f633a14948685ca8a5ce02202a1b49cd44104a9d40aee8f988281a8aac94a497b5bc7337c77cc7ddbab16f23012103fc15aa2f684457332c0ef1fe44d908ab97208102a1792caa13bcc5e886c4b321"),
                ),
            ),
        ]

        seed = bip39.seed(
            "alcohol woman abuse must during monitor noble actual mixed trade anger aisle",
            "",
        )
        ns = get_schemas_for_coin(coin_decred)
        keychain = Keychain(seed, coin_decred.curve_name, ns)
        signer = decred.Decred(tx, keychain, coin_decred, None).signer()

        for request, response in chunks(messages, 2):
            res = signer.send(request)
            if isinstance(res, tuple):
                _, res = res

            self.assertEqual(res, response)

        with self.assertRaises(StopIteration):
            signer.send(None)

    def test_purchase_ticket(self):
        inp1 = TxInput(
            address_n=[44 | 0x80000000, 42 | 0x80000000, 0 | 0x80000000, 0, 0],
            prev_hash=unhexlify(
                "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
            ),
            prev_index=0,
            amount=390000,
            multisig=None,
            sequence=0xFFFF_FFFF,
        )
        out1 = TxOutput(
            address="DsaHnKa418BeeQmyhpQEGG4cxGAPrneydfv",
            amount=390000 - 10000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        out2 = TxOutput(
            address_n=[44 | 0x80000000, 42 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=390000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        out3 = TxOutput(
            address="DsQxuVRvS4eaJ42dhQEsCXauMWjvopWgrVg",
            amount=0,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        tx = SignTx(
            coin_name="Decred", version=1, lock_time=0, inputs_count=1, outputs_count=3, decred_staking_ticket=True
        )

        messages = [
            None,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("0100000001")
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("4ac247307a054c37525169a78d690a7a7f87d709bef7d722aae85584f59c8fdf0000000000ffffffff03")
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmDecredSSTXSubmission(out1, coin_decred, AmountUnit.BITCOIN),
            True,
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=1, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("60cc05000000000000001aba76a914664b0cd46741a695a38f8ed37db2a20327471beb88ac")
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=2, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("00000000000000000000206a1e762e46655536d93ad13f88a49bde9a2df45fe62e70f30500000000000058")
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out3)),
            helpers.UiConfirmTotal(380000 + 10000, 10000, coin_decred, AmountUnit.BITCOIN),
            True,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("000000000000000000001abd76a914000000000000000000000000000000000000000088ac0000000000000000")
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXMETA,
                details=TxRequestDetailsType(
                    request_index=None,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevMeta(tx=ptx1),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(
                    request_index=0,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(
                    request_index=1,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp2)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(
                    request_index=0,
                    tx_hash=unhexlify(
                        "df8f9cf58455e8aa22d7f7be09d7877f7a0a698da7695152374c057a3047c24a"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify("01")
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXFINISHED,
                details=TxRequestDetailsType(),
                serialized=TxRequestSerializedType(
                    signature_index=0,
                    signature=unhexlify(
                        "3045022100d2a6baadc88ea67ec94a1f6dca70882e647e9af68d24e1bc72f9c27359e5e6ff02207b8a939e7cf82e79e2947e8fe59a14c11ee0b3a9cd1ff084d9bd54e23291b6be"
                    ),
                    serialized_tx=unhexlify("70f305000000000000000000ffffffff6b483045022100d2a6baadc88ea67ec94a1f6dca70882e647e9af68d24e1bc72f9c27359e5e6ff02207b8a939e7cf82e79e2947e8fe59a14c11ee0b3a9cd1ff084d9bd54e23291b6be012103fc15aa2f684457332c0ef1fe44d908ab97208102a1792caa13bcc5e886c4b321")
                ),
            ),
        ]

        seed = bip39.seed(
            "alcohol woman abuse must during monitor noble actual mixed trade anger aisle",
            "",
        )
        ns = get_schemas_for_coin(coin_decred)
        keychain = Keychain(seed, coin_decred.curve_name, ns)
        signer = decred.Decred(tx, keychain, coin_decred, None).signer()

        for request, response in chunks(messages, 2):
            res = signer.send(request)
            if isinstance(res, tuple):
                _, res = res

            self.assertEqual(res, response)

        with self.assertRaises(StopIteration):
            signer.send(None)


if __name__ == "__main__":
    unittest.main()
