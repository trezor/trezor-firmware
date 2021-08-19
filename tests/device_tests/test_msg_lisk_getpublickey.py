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


@pytest.mark.altcoin
@pytest.mark.lisk
def test_lisk_get_public_key(client):
    sig = lisk.get_public_key(client, parse_path("m/44h/134h/0h"))
    assert (
        sig.public_key.hex()
        == "68ffcc8fd29675264ba2c01e0926697b66b197179e130d4996ee07cd13892c1c"
    )
