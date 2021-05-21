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

from trezorlib import btc, device, messages as proto
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..tx_cache import TxCache

TX_CACHE_MAINNET = TxCache("Bitcoin")
TX_CACHE_BCASH = TxCache("Bcash")

TXHASH_8cc1f4 = bytes.fromhex(
    "8cc1f4adf7224ce855cf535a5104594a0004cb3b640d6714fdb00b9128832dd5"
)
TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)


class TestMsgSigntxInvalidPath:

    # Adapted from TestMsgSigntx.test_one_one_fee,
    # only changed the coin from Bitcoin to Litecoin.
    # Litecoin does not have strong replay protection using SIGHASH_FORKID,
    # spending from Bitcoin path should fail.
    @pytest.mark.altcoin
    def test_invalid_path_fail(self, client):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 by changing the version
        out1 = proto.TxOutputType(
            address="LfWz9wLHmqU9HoDkMg9NqbRosrHvEixeVZ",
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with pytest.raises(TrezorFailure) as exc:
            btc.sign_tx(client, "Litecoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)

        if client.features.model == "1":
            assert exc.value.code == proto.FailureType.ProcessError
            assert exc.value.message.endswith("Failed to compile input")
        else:
            assert exc.value.code == proto.FailureType.DataError
            assert exc.value.message.endswith("Forbidden key path")

    # Adapted from TestMsgSigntx.test_one_one_fee,
    # only changed the coin from Bitcoin to Litecoin and set safety checks to prompt.
    # Litecoin does not have strong replay protection using SIGHASH_FORKID, but
    # spending from Bitcoin path should pass with safety checks set to prompt.
    @pytest.mark.altcoin
    def test_invalid_path_prompt(self, client):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 by changing the version
        out1 = proto.TxOutputType(
            address="LfWz9wLHmqU9HoDkMg9NqbRosrHvEixeVZ",
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        device.apply_settings(
            client, safety_checks=proto.SafetyCheckLevel.PromptTemporarily
        )

        btc.sign_tx(client, "Litecoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)

    # Adapted from TestMsgSigntx.test_one_one_fee,
    # only changed the coin from Bitcoin to Bcash.
    # Bcash does have strong replay protection using SIGHASH_FORKID,
    # spending from Bitcoin path should work.
    @pytest.mark.altcoin
    def test_invalid_path_pass_forkid(self, client):
        # tx: 8cc1f4adf7224ce855cf535a5104594a0004cb3b640d6714fdb00b9128832dd5
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(
            address_n=parse_path("44h/0h/0h/0/0"),
            amount=390000,
            prev_hash=TXHASH_8cc1f4,
            prev_index=0,
        )

        # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 to cashaddr format
        out1 = proto.TxOutputType(
            address="bitcoincash:qr0fk25d5zygyn50u5w7h6jkvctas52n0qxff9ja6r",
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        btc.sign_tx(client, "Bcash", [inp1], [out1], prev_txes=TX_CACHE_BCASH)
