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


@pytest.mark.ethereum
class TestMsgEthereumSignmessage(TrezorTest):

    PATH = [H_(44), H_(60), H_(0), 0]
    ADDRESS = "0xEa53AF85525B1779eE99ece1a5560C0b78537C3b"
    VECTORS = [
        (
            "This is an example of a signed message.",
            "9bacd833b51fde010bab53bafd9d832eadd3b175d2af2e629bb2944fcc987dce7ff68bb3571ed25a720c220f2f9538bc8d04f582bee002c9af086590a49805901c",
        ),
        (
            "VeryLongMessage!" * 64,
            "752d283b3aea1eb44fd09203f4d5c430a6544e399b8500b02722b54325f6d8d457fd83460a31045cb0d6e8356240954ba072fdfe5cdb3f16d416e2acf1a180a51c",
        ),
    ]

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        for msg, sig in self.VECTORS:
            res = ethereum.sign_message(self.client, self.PATH, msg)
            assert res.address == self.ADDRESS
            assert res.signature.hex() == sig
