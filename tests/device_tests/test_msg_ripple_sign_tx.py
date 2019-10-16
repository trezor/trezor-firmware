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


@pytest.mark.altcoin
@pytest.mark.ripple
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgRippleSignTx:
    def test_ripple_sign_simple_tx(self, client):
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
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/0"), msg)
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
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/2"), msg)
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
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/2"), msg)
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
                "Flags": 2147483648,
                "TransactionType": "AccountSet",
                "Sequence": 6,
                "Fee": "12",
                "AccountSet": {"SetFlag": 4},  # disableMaster flag
            }
        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "304402202db55c45d927ac54fae89a142316a9b522393f0bcf0305279378c0761a308f68022047519a4eb53d517b93a0db4a2833abe26714e1ed13c8ae5b93dcd5ca5fcd9771"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200032280000000240000000620210000000468400000000000000c732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402202db55c45d927ac54fae89a142316a9b522393f0bcf0305279378c0761a308f68022047519a4eb53d517b93a0db4a2833abe26714e1ed13c8ae5b93dcd5ca5fcd977181148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "Flags": 2147483648,
                "TransactionType": "Payment",
                "Sequence": 1,
                "Fee": 20,
                "Payment": {
                    "Amount": 22000000,
                    "Destination": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
                    "DestinationTag": 128,
                },
                "Multisig": True,
                "Account": "rEpwmtmvx8gkMhX5NLdU3vutQt7dor4MZm",
            }
        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "304402200f72837d8d8f22b288aec1a9e2a1bbf6b331fc5370ec6f173831b84c431e62d8022032ca726678e64b62e1e5bbc1d7691a8f8c6f9bd2834dd0e58d2c2cf054a4c9fe"
        )
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000012e000000806140000000014fb1806840000000000000147300811499ca55fb7bddcc34f596ddc881c005ca1afae23d8314b5f762798a53d543a014caf8b297cff8f2f937e8f3e010732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402200f72837d8d8f22b288aec1a9e2a1bbf6b331fc5370ec6f173831b84c431e62d8022032ca726678e64b62e1e5bbc1d7691a8f8c6f9bd2834dd0e58d2c2cf054a4c9fe81148fb40e1ffa5d557ce9851a535af94965e0dd0988e1f1"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Flags": 2147483648,
                "Sequence": 2,
                "Fee": "12",
                "Payment": {
                    "Amount": "3000000",
                    "Destination": "rJX2KwzaLJDyFhhtXKi3htaLfaUH2tptEX",
                    "DestinationTag": 128
                }
            }
        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "3045022100c7bdb7dfcd049c6a60cddbb3c31ed0bc966ef7f5c4586732362ccd55080235da02202942dad1c39bf8d88ec7ec43f93628fbe67754e13527e11fe4761a0a745132f7"
        )
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000022e000000806140000000002dc6c068400000000000000c732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe474473045022100c7bdb7dfcd049c6a60cddbb3c31ed0bc966ef7f5c4586732362ccd55080235da02202942dad1c39bf8d88ec7ec43f93628fbe67754e13527e11fe4761a0a745132f781148fb40e1ffa5d557ce9851a535af94965e0dd09888314c0426cfcb532e7523bd87b14e12c24c85121aaaa"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Flags": 0,
                "Sequence": 1,
                "LastLedgerSequence": 760000,
                "Fee": 12,
                "Account": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
                "Payment": {
                    "Amount": 22000000,
                    "Destination": "rJX2KwzaLJDyFhhtXKi3htaLfaUH2tptEX",
                    "DestinationTag": 810,
                },
            }
        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "30450221008f6710f8c312cbb2c0dca6f11316aa44e588f47c6c5583253fd263e621f2699f022021d6ee388f37802c8507d751b5f5654ee74faf0ec8a546eb225147625e0c9105"
        )
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000012e0000032a201b000b98c06140000000014fb18068400000000000000c732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe4744730450221008f6710f8c312cbb2c0dca6f11316aa44e588f47c6c5583253fd263e621f2699f022021d6ee388f37802c8507d751b5f5654ee74faf0ec8a546eb225147625e0c910581148fb40e1ffa5d557ce9851a535af94965e0dd09888314c0426cfcb532e7523bd87b14e12c24c85121aaaa"
        )

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Flags": 2147483648,
                "Sequence": 2,
                "Fee": "12",
                "Payment": {
                    "Amount": "22000000",
                    "Destination": "rN1CuZjtCe337zrNYqYNYkCZzwPa59YF1w",
                    "DestinationTag": 128
                }
            }

        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "304402207b861830121fb725d639af304f5dd28e1b098968a8ac3c7adfbd4abc3f12867d02206ac7543164f97a139e62337a3c897e5103585cd7478be1ad56e5cfbaf767652b"
        )
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000022e000000806140000000014fb18068400000000000000c732102131facd1eab748d6cddc492f54b04e8c35658894f4add2232ebc5afe7521dbe47446304402207b861830121fb725d639af304f5dd28e1b098968a8ac3c7adfbd4abc3f12867d02206ac7543164f97a139e62337a3c897e5103585cd7478be1ad56e5cfbaf767652b81148fb40e1ffa5d557ce9851a535af94965e0dd09888314982ee91daadb496f1020c9ea8b1695371e50cfcc"

        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "SignerListSet",
                "Sequence": 1,
                "Fee": "32",
                "multisig": False,
                "SignerListSet": {
                    "SignerQuorum": 3,
                    "SignerEntries": [
                        {
                            "Account": "rJX2KwzaLJDyFhhtXKi3htaLfaUH2tptEX",
                            "SignerWeight": 1
                        },
                        {
                            "Account": "r9skfe7kZkvqss7oMB3tuj4a59PXD5wRa2",
                            "SignerWeight": 3
                        },
                        {
                            "Account": "rNb97BY81ZpzvxHRJytSSrqbx2PJTS2pEd",
                            "SignerWeight": 2
                        }
                    ]
                }
            }
        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/4'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "3044022003770053e8b39fdc43a043724d2aa07e1b59f8359cd96abbb661e9f43f6b982002202adbb43966e5a50f4f123cef700d8c44e9f9ce41871ca5b025bc617998f928f0"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000c228000000024000000012023000000036840000000000000207321039827db639207dc51057f5ffd4060a367526ab67447ef45b9286d8d9383a1b6c374463044022003770053e8b39fdc43a043724d2aa07e1b59f8359cd96abbb661e9f43f6b982002202adbb43966e5a50f4f123cef700d8c44e9f9ce41871ca5b025bc617998f928f08114982ee91daadb496f1020c9ea8b1695371e50cfccf4eb1300018114c0426cfcb532e7523bd87b14e12c24c85121aaaae1eb13000381145845d414ad520dd3700167c2749d4150385fd713e1eb1300028114950ed8dfd390534a1871873975ece0dfa8dde703e1f1"
        )

         msg = ripple.create_sign_tx_msg(
             {
                 "Flags": 2147483648,
                 "TransactionType": "AccountSet",
                 "Sequence": 2,
                 "Fee": "12",
                 "AccountSet": {
                     "SetFlag": 4
                 }
             }
        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/4'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "30440220280c0340c905eadd64997ca41a42c1968e86e6015bc36ff397ab89b8b3ee04e002203461928cccb2796df596aacf468239a13de6398d4b7bad894adf860bb827ca44"
        )
        assert (
            resp.serialized_tx.hex()
            == "1200032280000000240000000220210000000468400000000000000c7321039827db639207dc51057f5ffd4060a367526ab67447ef45b9286d8d9383a1b6c3744630440220280c0340c905eadd64997ca41a42c1968e86e6015bc36ff397ab89b8b3ee04e002203461928cccb2796df596aacf468239a13de6398d4b7bad894adf860bb827ca448114982ee91daadb496f1020c9ea8b1695371e50cfcc"
        )

         msg = ripple.create_sign_tx_msg(
             {
                 "Flags": 2147483648,
                 "TransactionType": "Payment",
                 "Sequence": 4,
                 "Fee": "20",
                 "Payment": {
                     "Amount": "22000000",
                     "Destination": "r9skfe7kZkvqss7oMB3tuj4a59PXD5wRa2",
                     "DestinationTag": 128
                 },
                 "Multisig": True,
                 "Account": "rN1CuZjtCe337zrNYqYNYkCZzwPa59YF1w"
             }

        )
        resp = ripple.sign_tx(client, parse_path("m/44'/144'/3'/0/0"), msg)
        assert (
            resp.signature.hex()
            == "304402202bc7665be30624688b675ea540c0d771a8067c80881d9ede644d1e488cc54076022078f21618113b3fdad05ee21b5772ac3885fa05343d3e203bc9650d03beed0f8e"
        )
        assert (
            resp.serialized_tx.hex()
            == "120000228000000024000000042e000000806140000000014fb18068400000000000001473008114982ee91daadb496f1020c9ea8b1695371e50cfcc83145845d414ad520dd3700167c2749d4150385fd713f3e010732102e8a48a36f7053431f1a16221c639ab675b0a2a6ce6de0ead5866aa3c495450597446304402202bc7665be30624688b675ea540c0d771a8067c80881d9ede644d1e488cc54076022078f21618113b3fdad05ee21b5772ac3885fa05343d3e203bc9650d03beed0f8e81145845d414ad520dd3700167c2749d4150385fd713e1f1"
        )

    def test_ripple_sign_invalid_fee(self, client):
        msg = ripple.create_sign_tx_msg(
            {
                "TransactionType": "Payment",
                "Payment": {
                    "Amount": 1,
                    "Destination": "rNaqKtKrMSwpwZSzRckPf7S96DkimjkF4H",
                },
                "Flags": 1,
                "Fee": 1,
                "Sequence": 1,
            }
        )
        with pytest.raises(CallException) as exc:
            ripple.sign_tx(client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert exc.value.args[0] == messages.FailureType.ProcessError
        assert exc.value.args[1].endswith(
            "Fee must be in the range of 10 to 10,000 drops"
        )
