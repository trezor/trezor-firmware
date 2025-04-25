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

from trezorlib import ethereum
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


# Test vectors validated with Foundry
# cast wallet sign-auth $ADDRESS --mnemonic $MNEMONIC --mnemonic-derivation-path "m/44'/60'/0'/0/0" --nonce $NONCE --chain $CHAINID */
@pytest.mark.models("core", reason="T1 does not support EIP 7702 yet")
@parametrize_using_common_fixtures("ethereum/signAuth7702.json")
def test_signAuth7702(client: Client, parameters, result):
    res = ethereum.sign_auth_7702(
        client,
        parse_path(parameters["path"]),
        parameters["nonce"],
        parameters["chain_id"],
        parameters["delegate"],
    )
    assert res.signature_v == result["sig_v"]
    assert res.signature_r.hex() == result["sig_r"]
    assert res.signature_s.hex() == result["sig_s"]
