from common import *  # isort:skip

if utils.INTERNAL_MODEL in ("T2T1", ):
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
    from apps.bitcoin.sign_tx import decred, helpers
    from apps.common import coins
    from apps.common.keychain import Keychain

    EMPTY_SERIALIZED = TxRequestSerializedType(serialized_tx=bytearray())

    coin_decred = coins.by_name("Decred Testnet")

    ptx1 = PrevTx(
        version=1, lock_time=0, inputs_count=1, outputs_count=2, extra_data_len=0
    )
    pinp1 = PrevInput(
        script_sig=unhexlify(
            "47304402207d127d59a44187952d9d0de94ad34a19dd9a84beb124fd8a3fb439c862544d3202206618f321385c30bda96fb01ce03f70a269d78a301c0b0c2e3e3689dfae3f4733012102ae1f6b51086bd753f072f94eb8ffe6806d3570c088a3ede46c678b6ea47d1675"
        ),
        prev_hash=unhexlify(
            "21012b08c5077036460e8f75bbc57beb11d7bc30e7ad224ad5e67d15bd086500"
        ),
        prev_index=2,
        sequence=0xFFFF_FFFF,
    )
    pout1 = PrevOutput(
        script_pubkey=unhexlify("76a914e4111051ae0349ab5589cf2b7e125c6da694a1a188ac"),
        amount=153_185_001,
        decred_script_version=0,
    )
    pout2 = PrevOutput(
        script_pubkey=unhexlify("76a914dc1a98d791735eb9a8715a2a219c23680edcedad88ac"),
        amount=200_000_000,
        decred_script_version=0,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestSignTxDecred(unittest.TestCase):
    # pylint: disable=C0301

    def test_one_one_fee(self):
        inp1 = TxInput(
            address_n=[44 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            prev_hash=unhexlify(
                "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
            ),
            prev_index=1,
            amount=200_000_000,
            multisig=None,
            sequence=0xFFFF_FFFF,
        )
        out1 = TxOutput(
            address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
            amount=200_000_000 - 100_000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        tx = SignTx(
            coin_name="Decred Testnet",
            version=1,
            lock_time=0,
            inputs_count=1,
            outputs_count=1,
        )

        # precomputed tx weight is 864
        fee_rate = 100_000 / (864 / 4)

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
                    serialized_tx=unhexlify(
                        "1064cbf0f0889b919ce083c82065612710b1a6adcdb3f15d7ffc5e6de2cd8a4d0100000000ffffffff01"
                    )
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmOutput(out1, coin_decred, AmountUnit.BITCOIN, 0, False, [H_(44), H_(1), H_(0)]),
            True,
            helpers.UiConfirmTotal(
                200_000_000,
                100_000,
                fee_rate,
                coin_decred,
                AmountUnit.BITCOIN,
                inp1.address_n[:3],
            ),
            True,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify(
                        "603bea0b0000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac0000000000000000"
                    )
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXMETA,
                details=TxRequestDetailsType(
                    request_index=None,
                    tx_hash=unhexlify(
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
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
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(
                    request_index=0,
                    tx_hash=unhexlify(
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(
                    request_index=1,
                    tx_hash=unhexlify(
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout2)),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(serialized_tx=unhexlify("01")),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXFINISHED,
                details=TxRequestDetailsType(request_index=None, tx_hash=None),
                serialized=TxRequestSerializedType(
                    signature_index=0,
                    signature=unhexlify(
                        "304402205ea5a0aec7e405eb3c792165f103f61f8ef862e76a2b0146bec1082b243cfbff022061e307113d389b969313bbee2c9a149fad4afdf715e8bd78df579438ef692814"
                    ),
                    serialized_tx=unhexlify(
                        "00c2eb0b0000000000000000ffffffff6a47304402205ea5a0aec7e405eb3c792165f103f61f8ef862e76a2b0146bec1082b243cfbff022061e307113d389b969313bbee2c9a149fad4afdf715e8bd78df579438ef6928140121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
                    ),
                ),
            ),
        ]

        seed = bip39.seed(
            " ".join(["all"] * 12),
            "",
        )
        ns = _get_schemas_for_coin(coin_decred)
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
            address_n=[44 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            prev_hash=unhexlify(
                "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
            ),
            prev_index=1,
            amount=200_000_000,
            multisig=None,
            sequence=0xFFFF_FFFF,
        )
        out1 = TxOutput(
            address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
            amount=200_000_000 - 100_000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        out2 = TxOutput(
            address_n=[44 | 0x80000000, 1 | 0x80000000, 0 | 0x80000000, 0, 0],
            amount=200_000_000,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        out3 = TxOutput(
            address="TsR28UZRprhgQQhzWns2M6cAwchrNVvbYq2",
            amount=0,
            script_type=OutputScriptType.PAYTOADDRESS,
            multisig=None,
        )
        tx = SignTx(
            coin_name="Decred Testnet",
            version=1,
            lock_time=0,
            inputs_count=1,
            outputs_count=3,
            decred_staking_ticket=True,
        )

        # precomputed tx weight is 1188
        fee_rate = 100_000 / (1188 / 4)

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
                    serialized_tx=unhexlify(
                        "1064cbf0f0889b919ce083c82065612710b1a6adcdb3f15d7ffc5e6de2cd8a4d0100000000ffffffff03"
                    )
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out1)),
            helpers.UiConfirmDecredSSTXSubmission(
                out1, coin_decred, AmountUnit.BITCOIN
            ),
            True,
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=1, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify(
                        "603bea0b0000000000001aba76a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac"
                    )
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out2)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(request_index=2, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify(
                        "00000000000000000000206a1edc1a98d791735eb9a8715a2a219c23680edcedad00c2eb0b000000000058"
                    )
                ),
            ),
            TxAckOutput(tx=TxAckOutputWrapper(output=out3)),
            helpers.UiConfirmTotal(
                200_000_000,
                100_000,
                fee_rate,
                coin_decred,
                AmountUnit.BITCOIN,
                inp1.address_n[:3],
            ),
            True,
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(
                    serialized_tx=unhexlify(
                        "000000000000000000001abd76a914000000000000000000000000000000000000000088ac0000000000000000"
                    )
                ),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXMETA,
                details=TxRequestDetailsType(
                    request_index=None,
                    tx_hash=unhexlify(
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
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
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevInput(tx=TxAckPrevInputWrapper(input=pinp1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(
                    request_index=0,
                    tx_hash=unhexlify(
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout1)),
            TxRequest(
                request_type=TXOUTPUT,
                details=TxRequestDetailsType(
                    request_index=1,
                    tx_hash=unhexlify(
                        "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
                    ),
                ),
                serialized=EMPTY_SERIALIZED,
            ),
            TxAckPrevOutput(tx=TxAckPrevOutputWrapper(output=pout2)),
            TxRequest(
                request_type=TXINPUT,
                details=TxRequestDetailsType(request_index=0, tx_hash=None),
                serialized=TxRequestSerializedType(serialized_tx=unhexlify("01")),
            ),
            TxAckInput(tx=TxAckInputWrapper(input=inp1)),
            TxRequest(
                request_type=TXFINISHED,
                details=TxRequestDetailsType(),
                serialized=TxRequestSerializedType(
                    signature_index=0,
                    signature=unhexlify(
                        "3045022100b3a11ff4befcc035623de7665aaa76dacc9252e53aabf2a5d61238151e696532022004cbcc537c1d539e04c823140bac4524bdba09f528f5c4b76f3f1022b7dc0ad4"
                    ),
                    serialized_tx=unhexlify(
                        "00c2eb0b0000000000000000ffffffff6b483045022100b3a11ff4befcc035623de7665aaa76dacc9252e53aabf2a5d61238151e696532022004cbcc537c1d539e04c823140bac4524bdba09f528f5c4b76f3f1022b7dc0ad40121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
                    ),
                ),
            ),
        ]

        seed = bip39.seed(
            " ".join(["all"] * 12),
            "",
        )
        ns = _get_schemas_for_coin(coin_decred)
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
    if utils.INTERNAL_MODEL in ("T2T1",):
        unittest.main()
