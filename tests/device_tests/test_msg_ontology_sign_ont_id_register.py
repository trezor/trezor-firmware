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

from trezorlib import messages, ontology
from trezorlib.tools import parse_path

from ..common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.ontology
@pytest.mark.skip_t1
@pytest.mark.skip(reason="bad testing data")
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_ontology_sign_ont_id_register(client):
    client.set_input_flow(input_flow(client, num_pages=2))
    transaction = messages.OntologyTransaction(
        version=0x00,
        nonce=0x7F7F1CEB,
        gas_price=500,
        gas_limit=30000,
        payer="AGn8JFPGM5S4jkWhTC89Xtz1Y76sPz29Rc",
        tx_attributes=[],
    )

    ont_id_register = messages.OntologyOntIdRegister(
        ont_id="did:ont:AGVn4NZNEQ7RawHTDxjaTjZ3R8h8q1aq9h",
        public_key=bytes.fromhex(
            "03a8269b0dad311d98195e76729bc57003348a315fd17b6bf4f90ba8b86735fa33"
        ),
    )

    signature = ontology.sign(
        client, parse_path("m/44'/1024'/0'/0/0"), transaction, ont_id_register
    )
    assert (
        signature.hex()
        == "015d6abe231352d1ab32f0b0de0222cfb9a7a13f467a2bf8a369b61aa1f933dc3a6a2ba7831c8a15984fe0958d24cbca05d8e0736510c1734d773145ce3eac9e9b"
    )


def input_flow(client, num_pages):
    yield
    time.sleep(1)
    for _ in range(num_pages - 1):
        client.debug.swipe_down()
        time.sleep(1)
    client.debug.press_yes()
