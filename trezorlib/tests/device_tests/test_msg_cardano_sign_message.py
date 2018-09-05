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

from binascii import hexlify

import pytest

from trezorlib.cardano import sign_message
from trezorlib.tools import parse_path

from .common import TrezorTest
from .conftest import TREZOR_VERSION


@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.xfail(TREZOR_VERSION == 2, reason="T2 support is not yet finished")
class TestMsgCardanoSignMessage(TrezorTest):
    @pytest.mark.parametrize(
        "message,path,expected_signature",
        [
            (
                "Test message to sign",
                "m/44'/1815'/0'/0/0",
                "dfb89d2b22c20ac7270e7640f9b27fee030c30d72afc342f83f6cb79a2522e17142597dbfb979462fc9fbf6ea17b4eba3b7cbf582e41b6ac31cb491e7cd1e308",
            ),
            (
                "New Test message to sign",
                "m/44'/1815'/0'/0/1",
                "d2c68818859f94138ad28a59aa3419a96394008bd38657fe5e74b299df33e70ff7de1b2091ba4a4351153ce4b6beb7eb7316d917ed9303b9f7de57f76e4e1307",
            ),
            (
                "Another Test message to sign",
                "m/44'/1815'/0'/0/2",
                "cfb1a8f76e566d387ed727e3eefbb3a0d280917045f2fc82ff381f296a17344d520c00882bc0656bf04c9e95f8138540d4b6d10ddf34d80e27704d1b0cbd0f05",
            ),
            (
                "Just another Test message to sign",
                "m/44'/1815'/0'/0/3",
                "a1aadbea98fc4075affb0e0b166b71934ac19420688b80e2ac2cfe3cf0d66404da19a0ab4a9f23335c080dc4cc76d1fd4fdfbb44289a50707d3fcf122a96060d",
            ),
        ],
    )
    def test_cardano_sign_message(self, message, path, expected_signature):
        self.setup_mnemonic_allallall()

        signature = sign_message(self.client, parse_path(path), message)
        assert expected_signature == hexlify(signature.signature).decode("utf8")
