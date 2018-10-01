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

from .common import TrezorTest


@pytest.mark.xfail
@pytest.mark.ontology
@pytest.mark.skip_t1
class TestMsgOntologySignWithdraw(TrezorTest):
    def test_ontology_sign_withdraw_ong(self):
        self.setup_mnemonic_nopin_nopassphrase()

        transaction = messages.OntologyTransaction(
            version=0x00,
            nonce=0x7F7F1CEB,
            type=0xD1,
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

        signature = ontology.sign_withdrawal(
            self.client, parse_path("m/44'/1024'/0'/0/0"), transaction, withdraw_ong
        )
        assert (
            signature.payload.hex()
            == "9300c66b140b045b101bc9fabaf181e251a38e76b73962111b6a7cc81400000000000000000000000000000000000000016a7cc814e885e849e7f545ea84e8c555b86c70e4f751c4ec6a7cc808001bb700000000006a7cc86c0c7472616e7366657246726f6d1400000000000000000000000000000000000000020068164f6e746f6c6f67792e4e61746976652e496e766f6b65"
        )
        assert (
            signature.signature.hex()
            == "01a44355ac4549a021ecc571eb85ffb6ae4ff50cffc416ec55df40cad538fa55c64386167df2fb6b3fa9e698ebe265088839667b88da7e599ce7df679b0d5dfe60"
        )
