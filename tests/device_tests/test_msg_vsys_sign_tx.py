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
import axolotl_curve25519 as curve

from trezorlib import messages, vsys
from trezorlib.protobuf import dict_to_proto
from trezorlib.tools import parse_path, b58decode


VSYS_PATH = parse_path("m/44'/360'/0'")


@pytest.mark.altcoin
@pytest.mark.vsys
@pytest.mark.skip_t1
class TestMsgVsysSignTx:
    def input_flow(self, debug, num_pages):
        yield
        for _ in range(num_pages - 1):
            debug.swipe_up()
        debug.press_yes()

    def test_vsys_sign_tx_proposal(self, client):
        with client:
            client.set_input_flow(self.input_flow(client.debug, num_pages=1))
            public_key = vsys.get_public_key(client, VSYS_PATH)
            resp = vsys.sign_tx(
                client,
                VSYS_PATH,
                dict_to_proto(
                    messages.VsysSignTx,
                    {
                        "protocol": "v.systems",
                        "api": 1,
                        "opc": "transaction",
                        "transactionType": 2,
                        "senderPublicKey": public_key,
                        "amount": 1000000000,
                        "fee": 10000000,
                        "feeScale": 100,
                        "recipient": "AU6GsBinGPqW8zUuvmjgwpBNLfyyTU3p83Q",
                        "timestamp": 1547722056762119200,
                        "attachment": "HXRC"
                    },
                ),
            )

        context_bytes = [0x02, 0x15, 0x7a, 0x9d, 0x02, 0xac, 0x57, 0xd4, 0x20, 0x00, 0x00, 0x00, 0x00, 0x3b, 0x9a,
                         0xca, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x98, 0x96, 0x80, 0x00, 0x64, 0x05, 0x54, 0x9c,
                         0x6d, 0xf7, 0xb3, 0x76, 0x77, 0x1b, 0x19, 0xff, 0x3b, 0xdb, 0x58, 0xd0, 0x4b, 0x49, 0x99,
                         0x91, 0x66, 0x3c, 0x47, 0x44, 0x4e, 0x42, 0x5f, 0x00, 0x03, 0x31, 0x32, 0x33]

        assert (
            curve.verifySignature(b58decode(public_key), bytes(context_bytes), b58decode(resp.signature)) == 0
        )
