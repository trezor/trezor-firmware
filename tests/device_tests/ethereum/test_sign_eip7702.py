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
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import EthereumAuth7702Signature, SafetyCheckLevel
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from .test_signtx import make_defs

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ethereum,
    pytest.mark.experimental,
    pytest.mark.models("core", reason="T1 does not support EIP 7702"),
]

# Test vectors validated with Foundry
# cast wallet sign-auth $ADDRESS --mnemonic $MNEMONIC --mnemonic-derivation-path "m/44'/60'/0'/0/0" --nonce $NONCE --chain $CHAINID */


@parametrize_using_common_fixtures("ethereum/sign_auth_eip7702.json")
def test_sign_eip7702(session: Session, parameters, result):
    delegate = parameters["delegate"]
    defs = make_defs(parameters)

    def _sign() -> EthereumAuth7702Signature:
        return ethereum.sign_auth_eip7702(
            session,
            n=parse_path(parameters["path"]),
            chain_id=parameters["chain_id"],
            delegate=delegate,
            nonce=parameters["nonce"],
            encoded_network=defs.encoded_network,
        )

    if delegate != "0x0000000000000000000000000000000000000000":
        with pytest.raises(
            TrezorFailure,
            match="ProcessError: EIP-7702 authorisation not allowed with strict safety checks",
        ):
            _sign()

        device.apply_settings(
            session,
            safety_checks=SafetyCheckLevel.PromptTemporarily,
        )

    res = _sign()
    assert res.signature_v == result["sig_v"]
    assert res.signature_r.hex() == result["sig_r"]
    assert res.signature_s.hex() == result["sig_s"]


@parametrize_using_common_fixtures("ethereum/sign_auth_eip7702_errors.json")
def test_sign_eip7702_errors(session: Session, parameters, result):
    device.apply_settings(
        session,
        safety_checks=SafetyCheckLevel.PromptTemporarily,
    )

    with pytest.raises(TrezorFailure, match=result["error"]):
        ethereum.sign_auth_eip7702(
            session,
            n=parse_path(parameters["path"]),
            chain_id=parameters["chain_id"],
            delegate=parameters["delegate"],
            nonce=parameters["nonce"],
        )
