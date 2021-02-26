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

from trezorlib import solana, messages as proto
from trezorlib.tools import parse_path


@pytest.mark.altcoin
@pytest.mark.solana
class TestMsgSolanaSignTx:
    def test_solana_sign_tx_send(self, client):
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.SolanaSignedTx(
                        signature=bytes.fromhex(
                            "74887ea6108acfe1f0c9f76315107bd8d2480214db98dbb25056baba2d9d2d06151d9524291c2934aa254421cb68e69b9d48eb26990489242880793a31ac1507"
                        )
                    ),
                ]
            )

            solana.sign_tx(
                client,
                parse_path("m/44'/501'/0'"),
                bytes.fromhex("deadbeef"),
            )
