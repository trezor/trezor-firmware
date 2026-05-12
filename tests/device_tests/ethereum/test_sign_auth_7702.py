# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from trezorlib import device, ethereum, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]

_ZERO_DELEGATE = "0x0000000000000000000000000000000000000000"


# Test vectors validated with Foundry
# cast wallet sign-auth $ADDRESS --mnemonic $MNEMONIC --mnemonic-derivation-path "m/44'/60'/0'/0/0" --nonce $NONCE --chain $CHAINID */
@pytest.mark.models("core")
@parametrize_using_common_fixtures("ethereum/sign_tx_auth7702.json")
def test_signAuth7702(session: Session, parameters, result):
    is_revocation = parameters["delegate"].lower() == _ZERO_DELEGATE
    if not is_revocation:
        device.apply_settings(
            session, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
        )

    input_flow = (
        InputFlowConfirmAllWarnings(session).get()
        if not session.debug.legacy_debug
        else None
    )

    with session.test_ctx as client:
        if input_flow:
            client.watch_layout()
            client.set_input_flow(input_flow)
        res = ethereum.sign_auth_7702(
            session,
            parse_path(parameters["path"]),
            parameters["nonce"],
            parameters["chain_id"],
            parameters["delegate"],
        )

    assert res.signature_v == result["sig_v"]
    assert res.signature_r.hex() == result["sig_r"]
    assert res.signature_s.hex() == result["sig_s"]
