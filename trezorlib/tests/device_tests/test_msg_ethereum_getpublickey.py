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

from trezorlib import ethereum
from trezorlib.tools import H_

from .common import TrezorTest
from .conftest import TREZOR_VERSION


@pytest.mark.ethereum
@pytest.mark.xfail(TREZOR_VERSION == 2, reason="Waiting for 2.0.12")
class TestMsgEthereumGetPublicKey(TrezorTest):
    def test_ethereum_getpublickey(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            ethereum.get_public_node(self.client, [H_(44), H_(60), H_(0)]).xpub
            == "xpub6D54vV8eUYHMVBZCnz4SLjuiQngXURVCGKKGoJrWUDRegdMByLTJKfRs64q3UKiQCsSHJPtCQehTvERczdghS7gb8oedWSyNDtBU1zYDJtb"
        )
