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

import time

import pytest

from trezorlib import messages
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.xfail
@pytest.mark.ontology
@pytest.mark.skip_t1
class TestMsgOntologySignOntIdAddAttributes(TrezorTest):
    def test_ontology_sign_ont_id_add_attributes(self):
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

        ont_id_add_attributes = messages.OntologyOntIdAddAttributes(
            ont_id="did:ont:AGVn4NZNEQ7RawHTDxjaTjZ3R8h8q1aq9h",
            public_key=bytes.fromhex(
                "03a8269b0dad311d98195e76729bc57003348a315fd17b6bf4f90ba8b86735fa33"
            ),
            ont_id_attributes=[
                messages.OntologyOntIdAttribute(
                    key="firstName", type="json", value="John Sheppard"
                )
            ],
        )

        # not using ontology.sign_add_attr() because of swiping
        signature = self._ontology_sign(
            2, parse_path("m/44'/1024'/0'/0/0"), transaction, ont_id_add_attributes
        )

        assert (
            signature.payload.hex()
            == "bd00c66b2a6469643a6f6e743a4147566e344e5a4e455137526177485444786a61546a5a33523868387131617139686a7cc8516a7cc80966697273744e616d656a7cc8046a736f6e6a7cc80d4a6f686e2053686570706172646a7cc82103a8269b0dad311d98195e76729bc57003348a315fd17b6bf4f90ba8b86735fa336a7cc86c0d616464417474726962757465731400000000000000000000000000000000000000030068164f6e746f6c6f67792e4e61746976652e496e766f6b65"
        )
        assert (
            signature.signature.hex()
            == "01c256dc16d88685fd6652d69b808059f7ed30edadb0ccfe51802702b94b65500922f9ea80e0fd7b77b5c51515e3bc43a495b3e98fb3adb82a0ab5dd47169fcf4e"
        )

    def _ontology_sign(
        self, num_of_swipes, address_n, transaction, ont_id_add_attributes
    ):
        # Sending Ontology message
        msg = messages.OntologySignOntIdAddAttributes(
            address_n=address_n,
            transaction=transaction,
            ont_id_add_attributes=ont_id_add_attributes,
        )

        self.client.transport.write(msg)
        ret = self.client.transport.read()

        # Confirm action
        assert isinstance(ret, messages.ButtonRequest)
        self.client.debug.press_yes()
        self.client.transport.write(messages.ButtonAck())
        time.sleep(1)
        for _ in range(num_of_swipes):
            self.client.debug.swipe_down()
            time.sleep(1)
        self.client.debug.press_yes()
        return self.client.transport.read()
