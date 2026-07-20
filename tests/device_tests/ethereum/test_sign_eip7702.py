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

import pytest

from trezorlib import device, ethereum
from trezorlib.debuglink import DebugSession as Session
from trezorlib.messages import SafetyCheckLevel
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum, pytest.mark.experimental]

# Test vectors validated with Foundry
# cast wallet sign-auth $ADDRESS --mnemonic $MNEMONIC --mnemonic-derivation-path "m/44'/60'/0'/0/0" --nonce $NONCE --chain $CHAINID */


@pytest.mark.models("core", reason="T1 does not support EIP 7702")
@parametrize_using_common_fixtures("ethereum/sign_auth_eip7702.json")
def test_sign_eip7702(session: Session, parameters, result):
    delegate = parameters["delegate"]
    if delegate != "0x0000000000000000000000000000000000000000":
        device.apply_settings(
            session,
            safety_checks=SafetyCheckLevel.PromptTemporarily,
        )

    res = ethereum.sign_auth_eip7702(
        session,
        n=parse_path(parameters["path"]),
        chain_id=parameters["chain_id"],
        delegate=parameters["delegate"],
        nonce=parameters["nonce"],
    )
    assert res.signature_v == result["sig_v"]
    assert res.signature_r.hex() == result["sig_r"]
    assert res.signature_s.hex() == result["sig_s"]
