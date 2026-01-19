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
    """
    Can be tested on https://adys.dev/miniscript, with the following policy:
    or_d(
        pk(tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg/<0;1>/*),
        and_v(
            v:pkh(tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb/<0;1>/*),
            older(1)
        )
    )
    `index=1` external address will be `tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza`
    """
    policy_name = "Basic inheritance policy"
    policy_template = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"
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

    assert address == "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"

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


@pytest.mark.xfail(reason="missing FW support for complex policies", raises=TrezorFailure)
def test_getpolicyaddress_complex(session: Session):
    """
    Can be tested on https://adys.dev/miniscript, with the following policy:

    or_i(
        and_v(
            v:thresh(
            2,
            pkh([00000000/84'/0'/0']xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/<2;3>/*),
            a:pkh([00000001/84'/0'/1']xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH/<2;3>/*),
            a:pkh([00000002/84'/0'/2']xpub6DDUPHpUo4pd5Z4Dmuk7igUc5DcYBoJXcVA1NJbKaRX1M2WKsTqHF5igMbwLpA23iHBwPXY11cidR2kiJVsQWfuJgaQJuxFrjm7iEhsMm4y/<0;1>/*)
            ),
            older(52596)
        ),
        and_v(
            v:pk([00000000/84'/0'/0']xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/<0;1>/*),
            pk([00000001/84'/0'/1']xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH/<0;1>/*)
        )
    )

    `index=1` external address will be `bc1qkye36enq7qzxadptuhh4v9t09zhelpw3cz9n0knvg2ayhdns5c7sc6vyde`
    """
    policy_name = "2-of-2 => 2-of-3 after 1y"
    policy_template = "or_i(and_v(v:thresh(2,pkh(@0/<2;3>/*),a:pkh(@1<2;3>/*),a:pkh([00000002/84'/0'/2']@2/<0;1>/*)),older(52596)),and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*)))"
    policy_xpubs = [
        "xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF",
        "xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH",
        "xpub6DDUPHpUo4pd5Z4Dmuk7igUc5DcYBoJXcVA1NJbKaRX1M2WKsTqHF5igMbwLpA23iHBwPXY11cidR2kiJVsQWfuJgaQJuxFrjm7iEhsMm4y",
    ]
    policy_blocks = 52596
    policy_registration = btc.register_policy(
        session, "Bitcoin", policy_name, policy_template, policy_xpubs, policy_blocks
    )

    mac = policy_registration.mac

    address = btc.get_policy_address(
        session,
        "Bitcoin",
        policy_name,
        policy_template,
        policy_xpubs,
        policy_blocks,
        mac,
        0,
        False,
        show_display=True,
    ).address

    assert address == "bc1qkye36enq7qzxadptuhh4v9t09zhelpw3cz9n0knvg2ayhdns5c7sc6vyde"
