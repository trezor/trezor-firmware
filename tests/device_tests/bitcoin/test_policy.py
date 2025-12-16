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

from trezorlib import btc, device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ... import bip32
from ...common import is_core
from ...input_flows import InputFlowConfirmAllWarnings


def test_registerpolicy(session: Session):
    assert (
        btc.register_policy(
            session,
            "Bitcoin",
            "Basic inheritance",
            "wsh(or_d(pk(@0)...))",
            ["XPUB1", "XPUB2"],
            20,
        ).mac
        == b"<{\x93\xc8\t\n\xda\xd4F\x98#\xd0\x99\xe8jI\x07Naa\x87e\xa2!\xf6}p\xeb\xcd\xa5O\x00"
    )


def test_getpolicyaddress(session: Session):
    policy_name = "Basic inheritance policy"
    policy_template = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@0/<2;3>/*),older(1))))"
    policy_xpubs = [
        "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
        "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
    ]
    policy_blocks = 1
    policy_registration = btc.register_policy(
        session, "Testnet", policy_name, policy_template, policy_xpubs, policy_blocks
    )

    mac = policy_registration.mac

    address = btc.get_policy_address(
        session,
        "Testnet",
        policy_name,
        policy_template,
        policy_xpubs,
        policy_blocks,
        mac,
        0,
        False,
        show_display=True,
    ).address

    print(address)

    # altered_mac = bytes([mac[0] ^ 1]) + mac[1:]
    # with pytest.raises(TrezorFailure, match="Invalid MAC"):
    #     btc.get_policy_address(
    #         session,
    #         "Bitcoin",
    #         policy_name,
    #         policy_template,
    #         policy_xpubs,
    #         policy_blocks,
    #         altered_mac,
    #         0,
    #         False,
    #     )
    #
    # with pytest.raises(TrezorFailure, match="Invalid MAC"):
    #     btc.get_policy_address(
    #         session,
    #         "Bitcoin",
    #         policy_name + " 2",
    #         policy_template,
    #         policy_xpubs,
    #         policy_blocks,
    #         mac,
    #         0,
    #         False,
    #     )
