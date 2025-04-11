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

from trezorlib import binance
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...input_flows import InputFlowShowXpubQRCode

BINANCE_PATH = parse_path("m/44h/714h/0h/0/0")


@pytest.mark.altcoin
@pytest.mark.binance
@pytest.mark.models("core")
@pytest.mark.setup_client(
    mnemonic="offer caution gift cross surge pretty orange during eye soldier popular holiday mention east eight office fashion ill parrot vault rent devote earth cousin"
)
def test_binance_get_public_key(client: Client):
    with client:
        IF = InputFlowShowXpubQRCode(client)
        client.set_input_flow(IF.get())
        sig = binance.get_public_key(client, BINANCE_PATH, show_display=True)
        assert (
            sig.hex()
            == "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        )
