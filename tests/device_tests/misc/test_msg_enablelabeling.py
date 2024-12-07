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

from trezorlib import misc
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...common import MNEMONIC12


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
@pytest.mark.models("core")
def test_encrypt(client: Client):
    misc.encrypt_keyvalue(
        client,
        [],
        "Enable labeling?",
        b"",
    )
