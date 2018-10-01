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
class TestMsgOntologySigntx(TrezorTest):
    def test_ontology_sign_transfer_ont(self):
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

        transfer = messages.OntologyTransfer(
            asset=1,
            amount=100,
            from_address="AGn8JFPGM5S4jkWhTC89Xtz1Y76sPz29Rc",
            to_address="AcyLq3tokVpkMBMLALVMWRdVJ83TTgBUwU",
        )

        signature = ontology.sign_transfer(
            self.client, parse_path("m/44'/1024'/0'/0/0"), transaction, transfer
        )
        assert (
            signature.payload.hex()
            == "7900c66b140b045b101bc9fabaf181e251a38e76b73962111b6a7cc814e885e849e7f545ea84e8c555b86c70e4f751c4ec6a7cc80864000000000000006a7cc86c51c1087472616e736665721400000000000000000000000000000000000000010068164f6e746f6c6f67792e4e61746976652e496e766f6b65"
        )
        assert (
            signature.signature.hex()
            == "0102f9b0c43b2ed35aa89b0927a60e692cb8a74280c2da819a909150c8b3fd2b0b401806c97797fcc4b93d34f210ad01740cfd13b720a389a80f384c1f94fb749e"
        )

    def test_ontology_sign_transfer_ong(self):
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

        transfer = messages.OntologyTransfer(
            asset=2,
            amount=12000000,
            from_address="AGn8JFPGM5S4jkWhTC89Xtz1Y76sPz29Rc",
            to_address="AcyLq3tokVpkMBMLALVMWRdVJ83TTgBUwU",
        )

        signature = ontology.sign_transfer(
            self.client, parse_path("m/44'/1024'/0'/0/0"), transaction, transfer
        )
        assert (
            signature.signature.hex()
            == "01ad88061a6cf5f4960cf9d311adb6dec4925d368b0fa9b7f56269f2a4078bea2367469af50c70260142d2ce3cc2d1e7fd0b2923df659c994412ff18f138438e9d"
        )
