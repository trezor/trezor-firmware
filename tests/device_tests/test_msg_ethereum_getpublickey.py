# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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


@pytest.mark.ethereum
class TestMsgEthereumGetPublicKey(TrezorTest):
    def test_ethereum_getpublickey(self):
        self.setup_mnemonic_nopin_nopassphrase()
        res = ethereum.get_public_node(self.client, [H_(44), H_(60), H_(0)])
        assert res.node.depth == 3
        assert res.node.fingerprint == 0xC10CFFDA
        assert res.node.child_num == 0x80000000
        assert (
            res.node.chain_code.hex()
            == "813d9feda6421f97a6472ff36679aa9e211ff88f6bdee51093af313ce628087e"
        )
        assert (
            res.node.public_key.hex()
            == "0318c22dedce01caca32354f98428e3af06a452f3fa84e6af8f1b6aa362affa641"
        )
        assert (
            res.xpub
            == "xpub6D54vV8eUYHMVBZCnz4SLjuiQngXURVCGKKGoJrWUDRegdMByLTJKfRs64q3UKiQCsSHJPtCQehTvERczdghS7gb8oedWSyNDtBU1zYDJtb"
        )
