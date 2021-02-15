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

from trezorlib import lisk
from trezorlib.tools import parse_path

LISK_PATH = parse_path("m/44h/134h/0h")
LISK_PUBKEY = "68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c"


@pytest.mark.altcoin
@pytest.mark.lisk
@pytest.mark.parametrize(
    "message, signature",
    (
        pytest.param(
            "This is an example of a signed message.",
            "96dbdc588b6ec21a17b3d6d6c3c323179376302094c1125f106c9df2d44df9e8f579c8ea241caed7796feb490a7f3ffb8ff4a54a1f8cc437fa59381c32a01408",
            id="short",
        ),
        pytest.param(
            "VeryLongMessage!" * 64,
            "fdac2a32d0d2f39a5ad189daa843ccae6816f0cee17f54667edbbc4119aea2dbce2877e4c660ec4d9a916cb122674efdb435ff0de08a1950e71958b4ae450609",
            id="long",
        ),
    ),
)
def test_sign(client, message, signature):
    sig = lisk.sign_message(client, LISK_PATH, message)
    assert sig.public_key.hex() == LISK_PUBKEY
    assert sig.signature.hex() == signature
