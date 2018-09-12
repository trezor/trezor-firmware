# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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
    def test_ripple_sign_simple_tx(self):
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
            == "30440220025a9cc2809527799e6ea5eb029488dc46c6632a8ca1ed7d3ca2d9211e80403a02202cfe8604e6c6d1d3c64246626cc1a1a9bd8a2163b969e561c6adda5dca8fc2a5"
        )
        assert (
            resp.serialized_tx.hex()
            == "12000022800000002400000064201b00051537614000000005f5e109684000000000000064732103dbed1e77cb91a005e2ec71afbccce5444c9be58276665a3859040f692de8fed2744630440220025a9cc2809527799e6ea5eb029488dc46c6632a8ca1ed7d3ca2d9211e80403a02202cfe8604e6c6d1d3c64246626cc1a1a9bd8a2163b969e561c6adda5dca8fc2a58114bdf86f3ae715ba346b7772ea0e133f48828b766483148fb40e1ffa5d557ce9851a535af94965e0dd0988"
        )

    def test_ripple_sign_invalid_fee(self):
        self.setup_mnemonic_allallall()

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
            ripple.sign_tx(self.client, parse_path("m/44'/144'/0'/0/2"), msg)
        assert exc.value.args[0] == messages.FailureType.ProcessError
        assert exc.value.args[1].endswith(
            "Fee must be in the range of 10 to 10,000 drops"
        )
