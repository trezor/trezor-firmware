from common import *  # isort:skip

from trezor.crypto import bip39
from trezor.enums import AmountUnit, OutputScriptType
from trezor.enums.RequestType import TXFINISHED, TXINPUT, TXMETA, TXOUTPUT
from trezor.messages import (
    PrevInput,
    PrevOutput,
    PrevTx,
    SignTx,
    TxAckInput,
    TxAckInputWrapper,
    TxAckOutput,
    TxAckOutputWrapper,
    TxAckPrevInput,
    TxAckPrevInputWrapper,
    TxAckPrevMeta,
    TxAckPrevOutput,
    TxAckPrevOutputWrapper,
    TxInput,
    TxOutput,
    TxRequest,
    TxRequestDetailsType,
    TxRequestSerializedType,
)
from trezor.utils import chunks

from apps.bitcoin.keychain import _get_schemas_for_coin
from apps.bitcoin.sign_tx import bitcoin, helpers
from apps.common import coins
from apps.common.keychain import Keychain

EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())


class TestSignTx(unittest.TestCase):
    # pylint: disable=C0301

    def test_one_one_fee(self):
        # input tx: 1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3
        # input 0: 0.03801747 BTC

        # output tx: https://btc1.trezor.io/tx/e590d5d76867e9f14466f715e26438845afff0ae082cda1f2f55aa8bf7f98140

        coin_bitcoin = coins.by_name("Bitcoin")

        ptx1 = PrevTx(
            version=1, lock_time=0, inputs_count=2, outputs_count=1, extra_data_len=0
        )
        pinp1 = PrevInput(
            script_sig=unhexlify(
                "47304402202df6c8885489be0fd52ed1f82c20b4c2c03e479369ea8439ed6233a3bb349ddd02207f749a00dd98d1aca699178d8fa954dc45b9faff33d3c9f03b81fa766061f2d70121038b60c00f69d78f2c5df84a24b30894c3700e4d6176a1f440461c8c69bf1f4262"
            ),
            prev_hash=unhexlify(
                "468c0de3bf9dfcc4915354904108611db9547a16ec38a24bf6b240ccc946e0d3"
            ),
            prev_index=0,
            sequence=0xFFFF_FFFF,
        )
        pinp2 = PrevInput(
            script_sig=unhexlify(
                "483045022100b11b3804e9b5fbbad70532e550192b3bbdd65b51f30572638a5559a86600856702204b3bd50a847ddf66426c0f413b9e1a98388b0d36479e66ef37b2d53d9ad13d47012103d443712f673afafafc006ccb6e19220de7ae0c07c9832666103974293d04a93c"
            ),
            prev_hash=unhexlify(
                "ebb32bba661e3dccb216acf593de26223f5f2c17f6a75634f2a0b581c4855fa0"
            ),
            prev_index=0,
            sequence=0xFFFF_FFFF,
        )
        pout1 = PrevOutput(
            script_pubkey=unhexlify(
                "76a914be145c9a7c131ad0c6c9b86f83748d660b42e2f488ac"
            ),
            amount=3_801_747,
        )

        inp1 = TxInput(
            address_n=[44 | 0x80000000, 0 | 0x80000000, 0 | 0x80000000, 0, 10],
            prev_hash=unhexlify(
                "1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3"
            ),
            prev_index=0,
            amount=3_801_747,
            multisig=None,
            sequence=0xFFFF_FFFF,
        )
        out1 = TxOutput(
            address="19WEjX2zgXdn6FCLmRAJ5Ty593GkJ77pNj",
            amount=3_801_747 - 50_000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        tx = SignTx(
            coin_name=None, version=1, lock_time=0, inputs_count=1, outputs_count=1
        )

        # precomputed tx weight is 768
        fee_rate = 50_000 / (768 / 4)

        messages = [
            None,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmOutput(out1, coin_bitcoin, AmountUnit.BITCOIN, 0, False),
            True,
            helpers.UiConfirmTotal(
                3_801_747,
                50_000,
                fee_rate,
                coin_bitcoin,
                AmountUnit.BITCOIN,
                inp1.address_n[:3],
            ),
            True,
            # ButtonRequest(code=ButtonRequest_ConfirmOutput),
            # ButtonRequest(code=ButtonRequest_SignTx),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXMETA,
                details=TxRequestDetailsType(
                    request_index=None,
                    tx_hash=unhexlify(
                        "1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3"
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
                        "1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3"
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
                        "1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3"
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
                        "1f326f65768d55ef146efbb345bd87abe84ac7185726d0457a026fc347a26ef3"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
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
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    signature_index=0,
                    signature=unhexlify(
                        "3045022100bebe58e7eac8170334f987d0f67032a2eddd0e2f378e002502ec88a69460ea460220040a8effc41167f5d5a5ffc77f37317d8125c7cd05f92d142e4d977f2f132c94"
                    ),
                    serialized_tx=unhexlify(
                        "f36ea247c36f027a45d0265718c74ae8ab87bd45b3fb6e14ef558d76656f321f000000006b483045022100bebe58e7eac8170334f987d0f67032a2eddd0e2f378e002502ec88a69460ea460220040a8effc41167f5d5a5ffc77f37317d8125c7cd05f92d142e4d977f2f132c940121038bac33bcdaeec5626e2f2c5680a9fdc5e551d4e1167f272825bea98e6158d4c8ffffffff01"
                    ),
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            TxRequest(
                request_type=TXFINISHED,
                details=TxRequestDetailsType(),
                serialized=TxRequestSerializedType(
                    signature_index=None,
                    signature=None,
                    serialized_tx=unhexlify(
                        "433f3900000000001976a9145d48886f4e2aad3164e55e23a7a41b921646a33488ac00000000"
                    ),
                ),
            ),
        ]

        seed = bip39.seed(
            " ".join(["all"] * 12),
            "",
        )
        ns = _get_schemas_for_coin(coin_bitcoin)
        keychain = Keychain(seed, coin_bitcoin.curve_name, ns)
        signer = bitcoin.Bitcoin(tx, keychain, coin_bitcoin, None).signer()

        for request, response in chunks(messages, 2):
            res = signer.send(request)
            if isinstance(res, tuple):
                _, res = res
            self.assertEqual(res, response)

        with self.assertRaises(StopIteration):
            signer.send(None)


if __name__ == "__main__":
    unittest.main()
