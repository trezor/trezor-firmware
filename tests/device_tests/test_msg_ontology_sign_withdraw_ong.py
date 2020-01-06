# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from trezorlib import messages, ontology
from trezorlib.tools import parse_path

from ..common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.ontology
@pytest.mark.skip_t1
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_ontology_sign_withdraw_ong(client):
    transaction = messages.OntologyTransaction(
        version=0x00,
        nonce=0x7F7F1CEB,
        gas_price=500,
        gas_limit=30000,
        payer="AGn8JFPGM5S4jkWhTC89Xtz1Y76sPz29Rc",
        tx_attributes=[],
    )

    withdraw_ong = messages.OntologyWithdrawOng(
        amount=12000000,
        from_address="AGn8JFPGM5S4jkWhTC89Xtz1Y76sPz29Rc",
        to_address="AcyLq3tokVpkMBMLALVMWRdVJ83TTgBUwU",
    )

    signature = ontology.sign(
        client, parse_path("m/44'/1024'/0'/0/0"), transaction, withdraw_ong
    )
    assert (
        signature.hex()
        == "01a44355ac4549a021ecc571eb85ffb6ae4ff50cffc416ec55df40cad538fa55c64386167df2fb6b3fa9e698ebe265088839667b88da7e599ce7df679b0d5dfe60"
    )
