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

from trezorlib import lisk
from trezorlib.tools import parse_path

from .common import TrezorTest

LISK_PATH = parse_path("m/44h/134h/0h/0h")


@pytest.mark.lisk
class TestMsgLiskSignmessage(TrezorTest):
    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = lisk.sign_message(
            self.client, LISK_PATH, "This is an example of a signed message."
        )
        assert (
            sig.public_key.hex()
            == "eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294"
        )
        assert (
            sig.signature.hex()
            == "7858ae7cd52ea6d4b17e800ca60144423db5560bfd618b663ffbf26ab66758563df45cbffae8463db22dc285dd94309083b8c807776085b97d05374d79867d05"
        )

    def test_sign_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = lisk.sign_message(self.client, LISK_PATH, "VeryLongMessage!" * 64)
        assert (
            sig.public_key.hex()
            == "eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294"
        )
        assert (
            sig.signature.hex()
            == "19c26f4b6f2ecf2feef57d22237cf97eb7862fdc2fb8c303878843f5dd728191f7837cf8d0ed41f8e470b15181223a3a5131881add9c22b2453b01be4edef104"
        )
