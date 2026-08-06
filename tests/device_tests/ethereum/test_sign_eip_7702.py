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

import typing as t

import pytest

from trezorlib import device, ethereum
from trezorlib._rlp import encode
from trezorlib.debuglink import DebugSession as Session
from trezorlib.messages import EthereumAuth7702, SafetyCheckLevel
from trezorlib.tools import parse_path

TEST_MNEMONIC = (
    "sudden conduct build spoil sight stairs corn congress enjoy plastic online leader"
)

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ethereum,
    pytest.mark.models("core", reason="T1 does not support EIP 7702"),
    pytest.mark.setup_client(mnemonic=TEST_MNEMONIC),
]

# txid=0x876aaa1c0ebd442b54e3d5aa1b789fae6257d6b425e0bccba3d8de7aa0027bd7 (authorize metamask)
tx_bytes_876aaa = bytes.fromhex(
    "04f8c80180830186a08407ea816383010fc59414495e5ef84823170b62176913d798b26a1a1a698080c0f85cf85a019463c0c19a282a1b52b07dd5a65b58948a07dae32b0101a0d426d296c73c62e5d5528e1cea701dd55060cc34264f33412ef2ea7c5007d380a07f83c40c1080483ecb8ba26a91f1408a2d3186f2577c4f563c2b95b467f78ed780a00ebf86aed4ee9b2a9fc8c1e39d91ebcb19a8cf54449a5f823d63c3cfc428ffada028c2eb4d75d2d78844a8521bbbffc26fdcab7e670ad768b28031532b9e488022"
)

# txid=0x592a79f5a8404da6dea891f11f42d884585ad5180ca8647c2c076090b97084d5 (revocation)
tx_bytes_592a79 = bytes.fromhex(
    "04f8c80102830186a08407bd666d830110179414495e5ef84823170b62176913d798b26a1a1a698080c0f85cf85a019400000000000000000000000000000000000000000301a03a4f2e8e70d2174356396d914ead9c0efa97fdbfee50baa3f6776d7e27b334c3a0663d78fbc752214d6f6c58d1d6ea837de7edbca815060170aff07d4f8f3c647180a0b99bf4d14da2a4be21296f7a630247e2df1cfe92e2378d7953d6b6891e9d0d69a04092b5ef8655d6f92df283195c9e5195dff96b48bea65f98e6a4d0ae6253593b"
)

_TX_TYPE = bytes([4])


def serialize_tx(*items) -> bytes:
    """Serialize EIP-7702 transaction."""
    return _TX_TYPE + encode(items)


def test_sign_eip7702_auth(session: Session):
    # Authorization requires disabling strict safety checks.
    device.apply_settings(
        session,
        safety_checks=SafetyCheckLevel.PromptTemporarily,
        experimental_features=True,
    )

    metamask = "63c0c19a282a1b52b07dd5a65b58948a07dae32b"
    kwargs: dict[str, t.Any] = dict(
        chain_id=1,
        nonce=0,
        to="14495E5EF84823170B62176913d798B26a1a1A69",
        value=0,
        data=b"",
        max_priority_fee=100000,
        max_gas_fee=132809059,
        gas_limit=69573,
        access_list=[],
        auth7702=EthereumAuth7702(delegate=metamask),
    )
    res = ethereum.sign_tx_eip1559(session, n=parse_path("m/44'/60'/0'/0/0"), **kwargs)
    expected_tuple = (
        kwargs["chain_id"],
        bytes.fromhex(metamask),
        kwargs["nonce"] + 1,  # tuple nonce
        # signature (y_parity, r, s)
        0x1,
        0xD426D296C73C62E5D5528E1CEA701DD55060CC34264F33412EF2EA7C5007D380,
        0x7F83C40C1080483ECB8BA26A91F1408A2D3186F2577C4F563C2B95B467F78ED7,
    )
    assert encode(res.auth7702_list) == encode([expected_tuple])
    assert tx_bytes_876aaa == serialize_tx(
        kwargs["chain_id"],
        kwargs["nonce"],
        kwargs["max_priority_fee"],
        kwargs["max_gas_fee"],
        kwargs["gas_limit"],
        bytes.fromhex(kwargs["to"]),
        kwargs["value"],
        kwargs["data"],
        kwargs["access_list"],
        res.auth7702_list,
        *res.signature_tuple(),
    )


def test_sign_eip7702_revoke(session: Session):
    # Authorization requires disabling strict safety checks.
    device.apply_settings(
        session,
        safety_checks=SafetyCheckLevel.PromptTemporarily,
        experimental_features=True,
    )

    revoke = bytes(20).hex()  # all zeroes
    kwargs: dict[str, t.Any] = dict(
        chain_id=1,
        nonce=2,
        to="14495E5EF84823170B62176913d798B26a1a1A69",
        value=0,
        data=b"",
        max_priority_fee=100000,
        max_gas_fee=129853037,
        gas_limit=69655,
        access_list=[],
        auth7702=EthereumAuth7702(delegate=revoke),
    )
    res = ethereum.sign_tx_eip1559(session, n=parse_path("m/44'/60'/0'/0/0"), **kwargs)
    expected_tuple = (
        kwargs["chain_id"],
        bytes.fromhex(revoke),
        kwargs["nonce"] + 1,  # tuple nonce
        # signature (y_parity, r, s)
        0x1,
        0x3A4F2E8E70D2174356396D914EAD9C0EFA97FDBFEE50BAA3F6776D7E27B334C3,
        0x663D78FBC752214D6F6C58D1D6EA837DE7EDBCA815060170AFF07D4F8F3C6471,
    )
    assert encode(res.auth7702_list) == encode([expected_tuple])
    assert tx_bytes_592a79 == serialize_tx(
        kwargs["chain_id"],
        kwargs["nonce"],
        kwargs["max_priority_fee"],
        kwargs["max_gas_fee"],
        kwargs["gas_limit"],
        bytes.fromhex(kwargs["to"]),
        kwargs["value"],
        kwargs["data"],
        kwargs["access_list"],
        res.auth7702_list,
        *res.signature_tuple(),
    )
