# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import messages, ripple
from trezorlib.tools import CallException, parse_path

from .common import TrezorTest


@pytest.mark.ripple
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgRippleSignTx(TrezorTest):
    def test_ripple_sign_payment_tx(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Amount": 100000000,
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                },
                "Flags": 0x80000000,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "3045022100e243ef623675eeeb95965c35c3e06d63a9fc68bb37e17dc87af9c0af83ec057e02206ca8aa5eaab8396397aef6d38d25710441faf7c79d292ee1d627df15ad9346c0"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000022800000002400000019614000000005f5e1006840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100e243ef623675eeeb95965c35c3e06d63a9fc68bb37e17dc87af9c0af83ec057e02206ca8aa5eaab8396397aef6d38d25710441faf7c79d292ee1d627df15ad9346c081148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Amount": 1,
                    "Destination": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
                },
                "Fee": 10,
                "Sequence": 1,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3044022069900e6e578997fad5189981b74b16badc7ba8b9f1052694033fa2779113ddc002206c8006ada310edf099fb22c0c12073550c8fc73247b236a974c5f1144831dd5f"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000000161400000000000000168400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274463044022069900e6e578997fad5189981b74b16badc7ba8b9f1052694033fa2779113ddc002206c8006ada310edf099fb22c0c12073550c8fc73247b236a974c5f1144831dd5f8114bdf86f3ae715ba346b7772ea0e133f48828b766483148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Amount": 100000009,
                    "Destination": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
                    "DestinationTag": 123456,
                },
                "Flags": 0,
                "Fee": 100,
                "Sequence": 100,
                "LastLedgerSequence": 333111,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "30450221008770743a472bb2d1c746a53ef131cc17cc118d538ec910ca928d221db4494cf702201e4ef242d6c3bff110c3cc3897a471fed0f5ac10987ea57da63f98dfa01e94df"
        )
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000642e0001e240201b00051537614000000005f5e109684000000000000064732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed2744730450221008770743a472bb2d1c746a53ef131cc17cc118d538ec910ca928d221db4494cf702201e4ef242d6c3bff110c3cc3897a471fed0f5ac10987ea57da63f98dfa01e94df8114bdf86f3ae715ba346b7772ea0e133f48828b766483148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
                    "IssuedAmount": {
                        "value": "123.45",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Fee": "15",
                "Flags": 2147483648,
                "Sequence": 7,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100e15e1c0b2bff650bb686f883b0799fc9aed60aba1f9bb0331c0fa5488febe931022079d960609e45fa5ee9eba5f275dd13bf124957b4170458c0bc5bd8b0175bfc02"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000000761d50462c56df9a80000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d168400000000000000f732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100e15e1c0b2bff650bb686f883b0799fc9aed60aba1f9bb0331c0fa5488febe931022079d960609e45fa5ee9eba5f275dd13bf124957b4170458c0bc5bd8b0175bfc028114bdf86f3ae715ba346b7772ea0e133f48828b766483148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

    def test_ripple_sign_set_regular_key_tx(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "SetRegularKey",
                "Sequence": 18,
                "Fee": "18",
                "SetRegularKey": {"RegularKey": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H"},
                "Flags": 2147483648,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "3045022100b8bce12392637e500f4434f0a64244dd57bfbbfc4522d03385b51cc40db70add0220345e075e5036dee3671a8bc61e48061b034508c6b063cd7ee278c255fcab8419"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000522800000002400000012684000000000000012732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100b8bce12392637e500f4434f0a64244dd57bfbbfc4522d03385b51cc40db70add0220345e075e5036dee3671a8bc61e48061b034508c6b063cd7ee278c255fcab841981148fb40e1ffa5d557ce9851a535af94965e0dd098888148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

        # Remove
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "SetRegularKey",
                "Sequence": 18,
                "Fee": "18",
                "SetRegularKey": {},
                "Flags": 2147483648,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "30440220401c0af97bcb44a17600ed4ab5e18504a0220ded4369760e229480a04c5e17620220599188c155cc803a0e47701da57ea1c0f77772e84f85a88da32cc2f249e02f09"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000522800000002400000012684000000000000012732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe4744630440220401c0af97bcb44a17600ed4ab5e18504a0220ded4369760e229480a04c5e17620220599188c155cc803a0e47701da57ea1c0f77772e84f85a88da32cc2f249e02f0981148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

    def test_ripple_escrow(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "EscrowCreate",
                "EscrowCreate": {
                    "Destination": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
                    "DestinationTag": 1338,
                    "Amount": "10000",
                    "CancelAfter": 533257958,
                    "FinishAfter": 533171558,
                    "Condition": "A0258020E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855810100",
                },
                "AccountTxnID": "F02EB74CB4F5D2E6AC8BE70CEA41CCA872E680F9EFD2027605F0B42666037AA8",
                "Memos": [
                    {
                        "Memo": {
                            "MemoData": "446576656C6F70656420627920546F776F204C616273"
                        }
                    },
                    {
                        "Memo": {
                            "MemoType": "68747470733A2F2F7777772E787270746F6F6C6B69742E636F6D",
                            "MemoData": "546F776F204C616273203C332048617264776172652077616C6C6574",
                        }
                    },
                    {
                        "Memo": {
                            "MemoType": "68747470733A2F2F7777772E787270746F6F6C6B69742E636F6D",
                            "MemoFormat": "746578742F706C61696E",
                            "MemoData": "546F776F204C616273203C332054686520585250204C6564676572202620496E7465726C65646765722050726F746F636F6C",
                        }
                    },
                ],
                "SourceTag": 888,
                "Fee": "20",
                "Flags": 2147483648,
                "Sequence": 3,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100c18c97bb4bcb3b1146e028f082f09f834047d420736a2bba1038c3ab4e6e71c30220134d41a8a1ca846c24c3ea460ee1eca5eec36c43e96d3443b59c338bf91e8d0c"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200012280000000230000037824000000032e0000053a20241fc8dee620251fc78d6659f02eb74cb4f5d2e6ac8be70cea41cca872e680f9efd2027605f0b42666037aa8614000000000002710684000000000000014732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100c18c97bb4bcb3b1146e028f082f09f834047d420736a2bba1038c3ab4e6e71c30220134d41a8a1ca846c24c3ea460ee1eca5eec36c43e96d3443b59c338bf91e8d0c701127a0258020e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b8558101008114bdf86f3ae715ba346b7772ea0e133f48828b766483148fb40e1ffa5d557ce9851a535af94965e0dd0988f9ea7d16446576656c6f70656420627920546f776f204c616273e1ea7c1a68747470733a2f2f7777772e787270746f6f6c6b69742e636f6d7d1c546f776f204c616273203c332048617264776172652077616c6c6574e1ea7c1a68747470733a2f2f7777772e787270746f6f6c6b69742e636f6d7d32546f776f204c616273203c332054686520585250204c6564676572202620496e7465726c65646765722050726f746f636f6c7e0a746578742f706c61696ee1f1"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "EscrowFinish",
                "EscrowFinish": {
                    "Owner": "rLNTReLbEZXPXopKYcaXMwELo5TpRd8eK2",
                    "OfferSequence": 3,
                },
                "Fee": "20",
                "Flags": 2147483648,
                "Sequence": 3,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100f688a3f62419f3a020068bd383c936fd21512aae8d3af53757e33e4fef74505b02206ba097e5848e830724f67a89389bab10ba9b0be408ed8ad6a019afdae9ef4e82"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000222800000002400000003201900000003684000000000000014732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100f688a3f62419f3a020068bd383c936fd21512aae8d3af53757e33e4fef74505b02206ba097e5848e830724f67a89389bab10ba9b0be408ed8ad6a019afdae9ef4e828114bdf86f3ae715ba346b7772ea0e133f48828b76648214d2f5db14adeb2f4afd1730c5a75a4404a7a71214"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "EscrowCancel",
                "EscrowCancel": {
                    "Owner": "rLNTReLbEZXPXopKYcaXMwELo5TpRd8eK2",
                    "OfferSequence": 3,
                },
                "Fee": "20",
                "Flags": 2147483648,
                "Sequence": 3,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100cad3698a0259b117411b05726c7284420176582aa909103a68c2cd3dd5f778bc02203d156af2d0cbf50aa92f5baea2dd347245b5af412fd4c25a577e288ccb6872bb"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000422800000002400000003201900000003684000000000000014732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100cad3698a0259b117411b05726c7284420176582aa909103a68c2cd3dd5f778bc02203d156af2d0cbf50aa92f5baea2dd347245b5af412fd4c25a577e288ccb6872bb8114bdf86f3ae715ba346b7772ea0e133f48828b76648214d2f5db14adeb2f4afd1730c5a75a4404a7a71214"
        )

    def test_ripple_account_set(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "AccountSet",
                "AccountSet": {
                    "Domain": "6578616D706C652E636F6D",
                    "SetFlag": 5,
                    "EmailHash": "505350263FB896C545C901343E8EE2DA",
                    "MessageKey": "03AB40A0490F9B7ED8DF29D246BF2D6269820A0EE7742ACDD457BEA7C7D0931EDB",
                    "WalletLocator": "EA8FBF830B802CF8E0976DFD66BE512C892BDEA79BAECDB7669DB3AC7B6311E2",
                    "TransferRate": 1000000001,
                    "TickSize": 4,
                },
                "Fee": "10",
                "Sequence": 23,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "30450221009d782bba47100a2af2973c8605167421abd1a38f1c25e4f19560fa6a1051ffb602204c73c2b86ee528b0138df0e3ba787464907a709b1fefdc66eb28339372a41a50"
        )
        assert (
            resp.serialized_tx.hex()
            == "120003228000000024000000172b3b9aca0120210000000541505350263fb896c545c901343e8ee2da68400000000000000a722103ab40a0490f9b7ed8df29d246bf2d6269820a0ee7742acdd457bea7c7d0931edb732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed2744730450221009d782bba47100a2af2973c8605167421abd1a38f1c25e4f19560fa6a1051ffb602204c73c2b86ee528b0138df0e3ba787464907a709b1fefdc66eb28339372a41a50770b6578616d706c652e636f6d8114bdf86f3ae715ba346b7772ea0e133f48828b766400101004"
        )

        # Empty AccountSet
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "AccountSet",
                "AccountSet": {},
                "Fee": "10",
                "Sequence": 23,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "304402203c56ef44017241a4d72047bf96a16242b1c2fd1b298a6a452280dc3e35b3b91202203ef9cd7d1127ab13e2dec3eb17184150ede47977a7192d3924d1a6bbeef35511"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200032280000000240000001768400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed27446304402203c56ef44017241a4d72047bf96a16242b1c2fd1b298a6a452280dc3e35b3b91202203ef9cd7d1127ab13e2dec3eb17184150ede47977a7192d3924d1a6bbeef355118114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "AccountSet",
                "AccountSet": {"TransferRate": 0},
                "Fee": "10",
                "Sequence": 23,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100df3ffa49af6af3c12a72669a248d42e9d1eb285635f78abb762988e53787b1bc02206e83b2d46089fd8f80aaefe75c2863a6a45eb27993b2d4901b9570ca61c4f0d5"
        )
        assert (
            resp.serialized_tx.hex()
            == "120003228000000024000000172b0000000068400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100df3ffa49af6af3c12a72669a248d42e9d1eb285635f78abb762988e53787b1bc02206e83b2d46089fd8f80aaefe75c2863a6a45eb27993b2d4901b9570ca61c4f0d58114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "AccountSet",
                "AccountSet": {"TransferRate": 1},
                "Fee": "10",
                "Sequence": 23,
            }
        )
        with pytest.raises(CallException) as exc:
            ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert exc.value.args[0] == messages.FailureType.ProcessError
        assert exc.value.args[1].endswith("Invalid transfer rate")

    def test_ripple_check(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "CheckCreate",
                "CheckCreate": {
                    "InvoiceID": "6F1DFD1D0FE8A32E40E1F2C05CF1C15545BAB56B617F9C6C2D63A6B704BEF59B",
                    "DestinationTag": 1,
                    "IssuedSendMax": {
                        "value": "184467e44",
                        "currency": "USD",
                        "issuer": "r9cZA1mLK5R5Am25ArfXFmqgNwjZgnfk59",
                    },
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Expiration": 570113521,
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "304402204a192203eedd7074d3c88b5c6f2158d1f79fcd3d644a2ec3c888adb5fef59568022014eb1a233a129e4a421aff94a314654a480bdef7adc1063d3c3550e4da3b13ba"
        )
        assert (
            resp.serialized_tx.hex()
            == "120010228000000024000000192a21fb3df12e0000000150116f1dfd1d0fe8a32e40e1f2c05cf1c15545bab56b617f9c6c2d63a6b704bef59b68400000000000000a69e0c68db7b413ec0000000000000000000000000055534400000000005e7b112523f68d2f5e879db4eac51c6698a69304732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed27446304402204a192203eedd7074d3c88b5c6f2158d1f79fcd3d644a2ec3c888adb5fef59568022014eb1a233a129e4a421aff94a314654a480bdef7adc1063d3c3550e4da3b13ba8114bdf86f3ae715ba346b7772ea0e133f48828b766483147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "CheckCash",
                "CheckCash": {
                    "IssuedAmount": {
                        "value": "98218",
                        "currency": "USD",
                        "issuer": "r9cZA1mLK5R5Am25ArfXFmqgNwjZgnfk59",
                    },
                    "CheckID": "838766BA2B995C00744175F69A1B11E32C3DBC40E64801A4056FCBD657F57334",
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100bfd8f0730f31afebfa93e7455bf999730c8b1a486a717a90026b20e01688a12b02201ddc177fab2c27e39e18aa48a81cb6d6e88f58392d84beb011e5d0d30ab84e15"
        )
        assert (
            resp.serialized_tx.hex()
            == "120011228000000024000000195018838766ba2b995c00744175f69a1b11e32c3dbc40e64801a4056fcbd657f5733461d5a2e4e0040e100000000000000000000000000055534400000000005e7b112523f68d2f5e879db4eac51c6698a6930468400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100bfd8f0730f31afebfa93e7455bf999730c8b1a486a717a90026b20e01688a12b02201ddc177fab2c27e39e18aa48a81cb6d6e88f58392d84beb011e5d0d30ab84e158114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "CheckCancel",
                "CheckCancel": {
                    "CheckID": "49647F0D748DC3FE26BDACBC57F251AADEFFF391403EC9BF87C97F67E9977FB0"
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100afba1b7ce60063066afbd85d96c468df9a5fd150bc5ea5fd6505e8944f5109660220166ad698a2b0106d4fd48c2b526a1f31ee411cba907f2e42198324c9eddfbc02"
        )
        assert (
            resp.serialized_tx.hex()
            == "12001222800000002400000019501849647f0d748dc3fe26bdacbc57f251aadefff391403ec9bf87c97f67e9977fb068400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100afba1b7ce60063066afbd85d96c468df9a5fd150bc5ea5fd6505e8944f5109660220166ad698a2b0106d4fd48c2b526a1f31ee411cba907f2e42198324c9eddfbc028114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

    def test_ripple_deposit_preauth(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "DepositPreauth",
                "DepositPreauth": {"Authorize": "rEhxGqkqPPSxQ3P25J66ft5TwpzV14k2de"},
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "304402202146f1e130af252a32ec44a00c23fee795add233f14ac45bac1aa8b39a23b99202202b9f17756637a3f2dc7d2ec097cec1bb98710195cd4007b8f58786dbeaa74414"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200132280000000240000001968400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed27446304402202146f1e130af252a32ec44a00c23fee795add233f14ac45bac1aa8b39a23b99202202b9f17756637a3f2dc7d2ec097cec1bb98710195cd4007b8f58786dbeaa744148114bdf86f3ae715ba346b7772ea0e133f48828b766485149a51260615192af5a94692d5f02eab105d129f51"
        )

    def test_ripple_offer(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "OfferCreate",
                "OfferCreate": {
                    "LastLedgerSequence": 7108682,
                    "IssuedTakerPays": {
                        "currency": "GKO",
                        "issuer": "ruazs5h1qEsqpke88pcqnaseXdm6od2xc",
                        "value": "2",
                    },
                    "TakerGets": "6000000",
                    "Expiration": 534171558,
                    "OfferSequence": 4321,
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100a7fef0ba0988b066c809b7dc4335d3420d21fad89c952f6e6dd659e693076aa50220483143f922be3e5697a2107ae71059a2fd854295467c6f14dbf729522697d225"
        )
        assert (
            resp.serialized_tx.hex()
            == "120007228000000024000000192a1fd6cfa62019000010e164d4871afd498d0000000000000000000000000000474b4f000000000009da9ff58ab99d0c08537b272a796186e50f3dc16540000000005b8d8068400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100a7fef0ba0988b066c809b7dc4335d3420d21fad89c952f6e6dd659e693076aa50220483143f922be3e5697a2107ae71059a2fd854295467c6f14dbf729522697d2258114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "OfferCancel",
                "OfferCancel": {"OfferSequence": 89},
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "304402206443f97424569663b8b36efa31643f0a4d0dca43d6a9807e439e2836916c9e930220764fc004c57156cb6f4f4f604f83c6e11534c9bb48e46dcacef90619ca7a3af0"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200082280000000240000001920190000005968400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed27446304402206443f97424569663b8b36efa31643f0a4d0dca43d6a9807e439e2836916c9e930220764fc004c57156cb6f4f4f604f83c6e11534c9bb48e46dcacef90619ca7a3af08114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

    def test_ripple_payment_channel(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "PaymentChannelCreate",
                "PaymentChannelCreate": {
                    "Amount": "10000",
                    "Destination": "rsA2LpzuawewSBQXkiju3YQTMzW13pAAdW",
                    "SettleDelay": 86400,
                    "PublicKey": "03DBED1E77CB91A005E2EC71AFBCCCE5444C9BE58276665A3859040F692DE8FED2",
                    "CancelAfter": 533171558,
                    "DestinationTag": 23480,
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3044022034404133b0492aae24429751590f16562aeecf129d4e9349de4e74007441cae5022032093ecb0e5a0cc2e3232631427a5854a7688af9b17c681c892be2cd8cba92e5"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000d228000000024000000192e00005bb820241fc78d6620270001518061400000000000271068400000000000000a712103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed2732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274463044022034404133b0492aae24429751590f16562aeecf129d4e9349de4e74007441cae5022032093ecb0e5a0cc2e3232631427a5854a7688af9b17c681c892be2cd8cba92e58114bdf86f3ae715ba346b7772ea0e133f48828b76648314204288d2e47f8ef6c99bcc457966320d12409711"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "PaymentChannelClaim",
                "PaymentChannelClaim": {
                    "Amount": "1000000",
                    "Balance": "1000000",
                    "Channel": "C1AE6DDDEEC05CF2978C0BAD6FE302948E9533691DC749DCDD3B9E5992CA6198",
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        print(resp.serialized_tx.hex())

        assert (
            resp.signature.hex()
            == "304402206f2ddd751d6bfb7d8d901da510e9b34dd869e38f76a47029fef3c6f03d1669520220625049ce5e980817c5f6bb88f37bd33815cd9f150ab28a057c98a969b26c4e68"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000f228000000024000000195016c1ae6dddeec05cf2978c0bad6fe302948e9533691dc749dcdd3b9e5992ca61986140000000000f42406240000000000f424068400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed27446304402206f2ddd751d6bfb7d8d901da510e9b34dd869e38f76a47029fef3c6f03d1669520220625049ce5e980817c5f6bb88f37bd33815cd9f150ab28a057c98a969b26c4e688114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "PaymentChannelFund",
                "PaymentChannelFund": {
                    "Amount": "10000",
                    "Channel": "C1AE6DDDEEC05CF2978C0BAD6FE302948E9533691DC749DCDD3B9E5992CA6198",
                    "Expiration": 543171558,
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100b165043e9027f6a378953eddc188d56e3b71474e956ae6d38c43649cf05bd87a022056f98f409d9372832792e3311ec7c70dcfbb7adf8ae767ce4ba41c7ee9788711"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000e228000000024000000192a206023e65016c1ae6dddeec05cf2978c0bad6fe302948e9533691dc749dcdd3b9e5992ca619861400000000000271068400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100b165043e9027f6a378953eddc188d56e3b71474e956ae6d38c43649cf05bd87a022056f98f409d9372832792e3311ec7c70dcfbb7adf8ae767ce4ba41c7ee97887118114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

    def test_ripple_signer_list_set(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "SignerListSet",
                "SignerListSet": {
                    "SignerQuorum": 11,
                    "SignerEntries": [
                        {
                            "SignerEntry": {
                                "Account": "rMRFD5eRj78pDR2LT261iVKUPXGNHYC9zK",
                                "SignerWeight": 1,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "rgQxSyLzRwfktHpozmt4o3U3gcGDXPp13",
                                "SignerWeight": 3,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "rn2i8bgJ798Qp4Ynv6xhyu9K2cneVaRw8g",
                                "SignerWeight": 5,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "rn3s1S6Lz9tpEB7MAGqRKc2z7hYnHGY7SX",
                                "SignerWeight": 1,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "rwT6kYyAkuAn1YxEeDVCDxbh3bUi87AbpU",
                                "SignerWeight": 6,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "rJCQqXWAyfUMuCjXgZcuBGqCDkDhhQN4jV",
                                "SignerWeight": 2,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "ra9hSnoYV1ckycXZyrJo8BWdXvtaajqVbk",
                                "SignerWeight": 3,
                            }
                        },
                        {
                            "SignerEntry": {
                                "Account": "rhXNJ4hYYcN22A4tMvySDoPhHzVesYFzXx",
                                "SignerWeight": 4,
                            }
                        },
                    ],
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 98,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100cee75f65efdd3c407d1f2cb358fe13edbff3d256aa7719f6abb5a0f487ece3dc02207d343d96bf1981b344b5202a00f8eb5d5701f3f48e5cfc1c10cfb4c5b4d35775"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000c2280000000240000006220230000000b68400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100cee75f65efdd3c407d1f2cb358fe13edbff3d256aa7719f6abb5a0f487ece3dc02207d343d96bf1981b344b5202a00f8eb5d5701f3f48e5cfc1c10cfb4c5b4d357758114bdf86f3ae715ba346b7772ea0e133f48828b7664f4eb1300018114e013ea594fe17f533435c2f624dfee51a1fbba23e1eb13000381140774384fd96fb4761c5b065511c627eaab2a7ff7e1eb13000581143247ca0e0460b4cf82c09e20083996584e62b9bfe1eb13000181142d35cf74faafb54e5ba0f68030773bfc11d50151e1eb130006811467c5f6d4fbf9962b0c7e2c8ee76f31f7aa2b358ce1eb1300028114c1bdd7bbf8c3d7f99698ab9104938eb46872ac27e1eb1300038114385ed26744dc77ea4e1e1037dfd01c7f94e93033e1eb1300048114269ff53c8c704ff461fcb83a6fe64eaf11dab72ee1f1"
        )

    def test_ripple_trust_set(self):
        self.setup_mnemonic_allallall()

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "TrustSet",
                "TrustSet": {
                    "LimitAmount": {
                        "currency": "SEK",
                        "issuer": "rsP3mgGb2tcYUrxiLFiHJiQXhsziegtwBc",
                        "value": "18937964132",
                    }
                },
                "Fee": "10",
                "Flags": 2147483648,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3045022100ad56411bf9612b0a9a16e29a71f6b1847d7a1736306cbe153953664862c9434302200163ed3af716294296a10e6f929adb0cb6508a066f67a8a543f674839265abef"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200142280000000240000001963d706ba65d67c568000000000000000000000000053454b00000000001a1fe3983c300d142ec2cf154c8a6bbb275875d268400000000000000a732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274473045022100ad56411bf9612b0a9a16e29a71f6b1847d7a1736306cbe153953664862c9434302200163ed3af716294296a10e6f929adb0cb6508a066f67a8a543f674839265abef8114bdf86f3ae715ba346b7772ea0e133f48828b7664"
        )

    def test_ripple_multisign(self):
        self.setup_mnemonic_allallall()

        # No previous signers
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "AccountSet",
                "Fee": 50,
                "Flags": 2147483648,
                "Sequence": 42,
                "SigningPubKey": "",
                "Account": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                "AccountSet": {},
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "3044022055cbf5569d9b44b2eb0f51b2302692ef779739a377041da0ff222d270371026702204d41c7c4d1efcb173779de6ee4ebf6e2c297b1f3565b09828a66be838a7c8dc8"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200032280000000240000002a684000000000000032730081147148ebebf7304ccdf1676fefcf9734cf1e780826f3e010732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed274463044022055cbf5569d9b44b2eb0f51b2302692ef779739a377041da0ff222d270371026702204d41c7c4d1efcb173779de6ee4ebf6e2c297b1f3565b09828a66be838a7c8dc88114bdf86f3ae715ba346b7772ea0e133f48828b7664e1f1"
        )

        # With previous (unsorted) signers
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "AccountSet",
                "Fee": 50,
                "Flags": 2147483648,
                "Sequence": 42,
                "SigningPubKey": "",
                "Account": "rTooLkitCksh5mQa67eaa2JaWHDBnHkpy",
                "AccountSet": {},
                "Signers": [
                    {
                        "Signer": {
                            "Account": "rUpy3eEg8rqjqfUoLeBnZkscbKbFsKXC3v",
                            "SigningPubKey": "028FFB276505F9AC3F57E8D5242B386A597EF6C40A7999F37F1948636FD484E25B",
                            "TxnSignature": "30440220680BBD745004E9CFB6B13A137F505FB92298AD309071D16C7B982825188FD1AE022004200B1F7E4A6A84BB0E4FC09E1E3BA2B66EBD32F0E6D121A34BA3B04AD99BC1",
                        }
                    },
                    {
                        "Signer": {
                            "Account": "rsA2LpzuawewSBQXkiju3YQTMzW13pAAdW",
                            "SigningPubKey": "02B3EC4E5DD96029A647CFA20DA07FE1F85296505552CCAC114087E66B46BD77DF",
                            "TxnSignature": "3044022019F0AB62F908C1A84E97EEF70BD224AC660E5B6EBC98C756D74A3C24A93828E802206841F75CC86E26C70433AF4B81F5778A4B85673EB63FE47904BF3714720F05D1",
                        }
                    },
                ],
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert (
            resp.signature.hex()
            == "30440220219d4eebd15620ecee16315b061356f0b9a0a47185d0b643f10d34efc173b78d022017026e6b6792957159d698642c2a8d62fe356f401e15d979124214e6caa73948"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200032280000000240000002a684000000000000032730081140511e17db83bb6f113939d67bc8ea539edc926fcf3e010732102b3ec4e5dd96029a647cfa20da07fe1f85296505552ccac114087e66b46bd77df74463044022019f0ab62f908c1a84e97eef70bd224ac660e5b6ebc98c756d74a3c24a93828e802206841f75cc86e26c70433af4b81f5778a4b85673eb63fe47904bf3714720f05d18114204288d2e47f8ef6c99bcc457966320d12409711e1e0107321028ffb276505f9ac3f57e8d5242b386a597ef6c40a7999f37f1948636fd484e25b744630440220680bbd745004e9cfb6b13a137f505fb92298ad309071d16c7b982825188fd1ae022004200b1f7e4a6a84bb0e4fc09e1e3ba2b66ebd32f0e6d121a34ba3b04ad99bc181147908a7f0edd48ea896c3580a399f0ee78611c8e3e1e010732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed2744630440220219d4eebd15620ecee16315b061356f0b9a0a47185d0b643f10d34efc173b78d022017026e6b6792957159d698642c2a8d62fe356f401e15d979124214e6caa739488114bdf86f3ae715ba346b7772ea0e133f48828b7664e1f1"
        )

    def test_ripple_signing_pub_key(self):
        self.setup_mnemonic_allallall()

        public_key = ripple.get_public_key(self.client, parse_path("m/44'/144'/0'/0/0"))
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Amount": 100000000,
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                },
                "Flags": 0x80000000,
                "Fee": 100000,
                "Sequence": 25,
                "SigningPubKey": public_key,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "3045022100e243ef623675eeeb95965c35c3e06d63a9fc68bb37e17dc87af9c0af83ec057e02206ca8aa5eaab8396397aef6d38d25710441faf7c79d292ee1d627df15ad9346c0"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000022800000002400000019614000000005f5e1006840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100e243ef623675eeeb95965c35c3e06d63a9fc68bb37e17dc87af9c0af83ec057e02206ca8aa5eaab8396397aef6d38d25710441faf7c79d292ee1d627df15ad9346c081148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Signing on a different BIP path with the same public key should fail
        with pytest.raises(CallException) as exc:
            ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/1"), msg)
        assert exc.value.args[0] == messages.FailureType.ProcessError
        assert exc.value.args[1].endswith(
            "The supplied SigningPubKey does not match the device public key"
        )

    def test_ripple_amounts(self):
        self.setup_mnemonic_allallall()

        # Negative XRP amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Amount": -1000000,
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )

        with pytest.raises(Exception):
            ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)

        # Negative XRP amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Amount": -10000,
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )

        with pytest.raises(Exception):
            ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)

        # Zero XRP amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Amount": 0,
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000196140000000000000006840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100bd66e2bf3e3f05ad579fa9d3a07867a90b3966b3944ca941212ee3de7ba3366702203d6d5e6207d296fcd1ae75acdd72cc22d417b81a06c3dba4a489a0f80fc2c9b381148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Positive XRP amount, no decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Amount": 100000000,
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "12000022800000002400000019614000000005f5e1006840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100e243ef623675eeeb95965c35c3e06d63a9fc68bb37e17dc87af9c0af83ec057e02206ca8aa5eaab8396397aef6d38d25710441faf7c79d292ee1d627df15ad9346c081148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Positive XRP amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Amount": 10000,
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000196140000000000027106840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100bea7328a34bb78087eb50064533b68ff86ab710eda21ee4a569007f1c65bb29c02202fd720843d80b3bc3f880d8b963b788be870d19dd2ffe045e35514fdbca546b681148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Maximum possible XRP amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "Amount": 100000000000000000,
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961416345785d8a00006840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474463044022037f4796594e56efdb6f8db4c01ddfbbd68d76875a50d73cfd92653b91752c7a8022014108f5340b10590b48e08b1b9cee465c274793706a97aa6b3eda45444c0418e81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Negative issued USD amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "-10",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000196194c38d7ea4c6800000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402200b7ddee649d89cdc4b69ca31488e46d77cb7f2080ce7b7e9cfad879fb914331a0220133d5d090246eb895419464011ca756f86dd2470525cb4c9a7820831064d2cba81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Negative issued USD amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "-12.34",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000196194c4625103a7200000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402204d130392396eab5cb2039cbc47fd969afa95e44ded45fd44985e6068652e897d02201f2a73d0e5f7bd2c40042c9891022da770cf8e26b04b311ccde2a1679662784e81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Zero issued USD amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "0",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961800000000000000000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100e20a3af0b3704e6acc872a8e784fbf8684f0cee7774cfb15465500aa57b096410220238bede044faed891ca23480c73093b104ca85e06e10838fc932a12b06a83ac681148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Zero issued USD amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "0.0",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961800000000000000000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100e20a3af0b3704e6acc872a8e784fbf8684f0cee7774cfb15465500aa57b096410220238bede044faed891ca23480c73093b104ca85e06e10838fc932a12b06a83ac681148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Positive issued USD amount, no decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "1234",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961d544625103a7200000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474463044022067af9543e8f01351c0def580d3aa8979ae133c3df6d8a542d9a32bf30d9e23040220667649ddb8050d55907731441cb8413c8e1f9003c804ca424c93a829542cd1f581148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Positive issued USD amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "12.34",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961d4c4625103a7200000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402200e6b99e09b08ba8d5ef08165e4d94ba13877745e590470ad6c2c9276462bfa5e022070fc2af83ec77f204c38ba29fb84ce69dabca60e608db1465359c9ae4cd529aa81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Maximum possible issued USD amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "1000000000000000e80",
                        "currency": "USD",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961ec438d7ea4c6800000000000000000000000000055534400000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100ad009a131f1540c54254ef9a5f1ae8eb8eb68231507934c4642bdfc58ce16a4602204d6341896e5e62ddb9b6d0083d5925c92efcd6a4af5744fb862d20f3f983008b81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Negative issued 534F4C4F00000000000000000000000000000000 amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "-10",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000196194c38d7ea4c68000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402206fcc6a29916dbe2c5d87506ea7c319d7348df402fbbad21b56c69e9fef69be6802203b2d89748ec0878d3abf5365e8cb4e677ffb7a5fb953ff07afcd864e7c9bf6d581148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Negative issued 534F4C4F00000000000000000000000000000000 amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "-12.34",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000196194c4625103a72000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100c229b7945e7315d61d9a8fa63eb66e759a4f39f98c302a38b4e09d85a37663c7022060024187bd94808835aec1dabb931d9776ecd446aca27cb1f5f00726d1c1ab3b81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Zero issued 534F4C4F00000000000000000000000000000000 amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "0",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "12000022800000002400000019618000000000000000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402206a119f63055f10ffc9892f69de19e7243b90397f55aee07860dc944ba610665202203e6473b96bedbd494a50811a24d9947533e63e678b18fc6184f40306e5743a7a81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Zero issued 534F4C4F00000000000000000000000000000000 amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "0.0",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "12000022800000002400000019618000000000000000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402206a119f63055f10ffc9892f69de19e7243b90397f55aee07860dc944ba610665202203e6473b96bedbd494a50811a24d9947533e63e678b18fc6184f40306e5743a7a81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Positive issued 534F4C4F00000000000000000000000000000000 amount, no decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "1234",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961d544625103a72000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100ddd5774af21e3d610e59b9036355f3d7bd36718a9f97a53aad80cd71773212f602207ba8bd20552d44d9cc620fb8b1950858943ad300c9baebd840e63c68a3c079cc81148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Positive issued 534F4C4F00000000000000000000000000000000 amount, decimal
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "12.34",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961d4c4625103a72000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100dbdac00f0d0f66645220ffe1e80dc22a7bddf82cd1c6dcdc0abb7147510d53eb02201233b49f844b67e5d4b4ed121e4e89f6b295e2239478fde8b55e0d68cfd58c2181148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )

        # Maximum possible issued 534F4C4F00000000000000000000000000000000 amount
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Destination": "rBKz5MC2iXdoS3XgnNSYmF69K1Yo4NS3Ws",
                    "IssuedAmount": {
                        "value": "1000000000000000e80",
                        "currency": "534F4C4F00000000000000000000000000000000",
                        "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                    },
                },
                "Flags": 2147483648,
                "Fee": 100000,
                "Sequence": 25,
            }
        )
        resp = ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.serialized_tx.hex()
            == "1200002280000000240000001961ec438d7ea4c68000534f4c4f000000000000000000000000000000000a20b3c85f482532a9578dbb3950b85ca06594d16840000000000186a0732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe4744730450221008bb175c3db1f757268cdb59c53ab7ab73c2033673f90c0ed1b824beeeca7111c022050dc838282dfb143dc293f1b940a162279d5e1d9a0ff0ffac37919ec0190be0781148fb40e1ffa5d557ce9851a535af94965e0dd098883147148ebebf7304ccdf1676fefcf9734cf1e780826"
        )
