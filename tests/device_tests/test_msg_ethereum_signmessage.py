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
        (
            "MsgLenIs9",
            "6570bd48d38a68ade78273fca18943ed36ec48cb2eb5b6792bc56f20588b1c75020f04b86740321e562eb2ec2022eec4ad673dc120c6895983856e5437cb95c91c",
        ),
        (
            "MsgLenIs10",
            "5f26de400e53a333479ce9518ef0724b81615b3e3842c3205754f48a9ff1a3fc0e383ccb7dabdfd8e284abe69c0065f15f033f37210f5efeccfc9a6b0813a2af1b",
        ),
        (
            "MsgLenIs11!",
            "7d8c1deec29c01c1982f46a91e1d9d99e399374b8aac875703ca947583ec6d944e7579d3934ac10e910a2959daa9e89fa5f4c0fc62bacdc8ec788d09b22e2ad61c",
        ),
        (
            "This message has length 99" + 73 * "!",
            "ac255920b53788eb81f5debd3792554ee4666d38059c8c39f74abd4032483fce2365af2236b8edf83801ad6e57f1e126e55a7757f2a2ebc991efe495b48d16d01c",
        ),
        (
            "This message has length 100" + 73 * "!",
            "47a70be8e7161a2c597de2237ba3846218e86561e9b5115b7fe9604ab63c05f85456204ba309e11e3b242a8c09a166ce611fb34bf1c54598162bbcce749549ea1b",
        ),
        (
            "This message has length 101" + 74 * "!",
            "0f413d3eff519c52ba01333b8bd132d20c2e62e3a77483e6a803dc3b711e3c2e11548f21687764a7290347079c00fc9dd976e060600d774bf1ae2f99bd8803bf1c",
        ),
    ]

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        for msg, sig in self.VECTORS:
            res = ethereum.sign_message(self.client, self.PATH, msg)
            assert res.address == self.ADDRESS
            assert res.signature.hex() == sig
