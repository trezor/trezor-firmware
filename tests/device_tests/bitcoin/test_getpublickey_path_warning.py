# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

"""Warning-screen behaviour of GetPublicKey(show_display=True)."""

import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ...input_flows import InputFlowShowXpubQRCode

B = messages.ButtonRequestType
IST = messages.InputScriptType

WARN = True
SILENT = False

VECTORS = (  # path, script_type, warns
    # PATTERN_CASA is unhardened below m/45', so the purpose level is the
    # deepest hardened prefix and an export point of its own
    pytest.param("m/45h", IST.SPENDADDRESS, SILENT, id="casa_address"),
    pytest.param("m/45h", IST.SPENDP2SHWITNESS, SILENT, id="casa_p2sh"),
    # One level deeper is neither the deepest hardened prefix nor the account
    pytest.param("m/45h/0", IST.SPENDADDRESS, WARN, id="below_casa"),
    # The BIP-48 account node, where cosigners share the xpub
    pytest.param("m/48h/0h/0h/2h", IST.SPENDWITNESS, SILENT, id="bip48_account"),
    pytest.param("m/44h/0h/0h", IST.SPENDADDRESS, SILENT, id="bip44_account"),
    # A pattern with no hardened component has no export point
    pytest.param("m/1", IST.SPENDADDRESS, WARN, id="unhardened"),
)


@pytest.mark.models("core")
@pytest.mark.parametrize("path, script_type, warns", VECTORS)
def test_path_warning(
    session: Session,
    path: str,
    script_type: messages.InputScriptType,
    warns: bool,
):
    expected = []
    if warns:
        expected.append(messages.ButtonRequest(code=B.UnknownDerivationPath))
    expected += [
        messages.ButtonRequest(code=B.PublicKey),
        messages.PublicKey,
    ]

    with session.test_ctx as client:
        IF = InputFlowShowXpubQRCode(session)
        client.set_input_flow(IF.get())
        client.set_expected_responses(expected)
        btc.get_public_node(
            session,
            parse_path(path),
            coin_name="Bitcoin",
            script_type=script_type,
            show_display=True,
        )
