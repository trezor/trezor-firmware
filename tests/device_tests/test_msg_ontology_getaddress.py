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

from trezorlib import ontology
from trezorlib.tools import parse_path

from ..common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.ontology
@pytest.mark.skip_t1
class TestMsgOntologyGetaddress:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ontology_get_ont_address(self, client):
        assert (
            ontology.get_address(client, parse_path("m/44'/1024'/0'/0/0"))
            == "ANzeepWmi9hoLBA3UiwVhUm7Eku196VUHk"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ontology_get_neo_address(self, client):
        assert (
            ontology.get_address(client, parse_path("m/44'/888'/0'/0/0"))
            == "AZEMburLePcdfqBFnVfdbsXKiBSnmtgFZr"
        )
