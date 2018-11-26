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

from .common import TrezorTest


@pytest.mark.ethereum
class TestMsgEthereumVerifymessage(TrezorTest):

    ADDRESS = "cb3864960e8db1a751212c580af27ee8867d688f"
    VECTORS = [
        (
            "This is an example of a signed message.",
            "b7837058907192dbc9427bf57d93a0acca3816c92927a08be573b785f2d72dab65dad9c92fbe03a358acdb455eab2107b869945d11f4e353d9cc6ea957d08a871b",
        ),
        (
            "VeryLongMessage!" * 64,
            "da2b73b0170479c2bfba3dd4839bf0d67732a44df8c873f3f3a2aca8a57d7bdc0b5d534f54c649e2d44135717001998b176d3cd1212366464db51f5838430fb31c",
        ),
    ]

    def test_verify(self):
        self.setup_mnemonic_nopin_nopassphrase()
        for msg, sig in self.VECTORS:
            res = ethereum.verify_message(
                self.client, bytes.fromhex(self.ADDRESS), bytes.fromhex(sig), msg
            )
            assert res is True

    def test_verify_invalid(self):
        self.setup_mnemonic_nopin_nopassphrase()
        signature = bytes.fromhex(self.VECTORS[0][1])
        res = ethereum.verify_message(
            self.client, bytes.fromhex(self.ADDRESS), signature, "another message"
        )
        assert res is False
