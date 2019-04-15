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

from trezorlib import monero
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.monero
@pytest.mark.skip_t1
class TestMsgMoneroGetaddress(TrezorTest):
    def test_monero_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            monero.get_address(self.client, parse_path("m/44h/128h/0h"))
            == b"4Ahp23WfMrMFK3wYL2hLWQFGt87ZTeRkufS6JoQZu6MEFDokAQeGWmu9MA3GFq1yVLSJQbKJqVAn9F9DLYGpRzRAEXqAXKM"
        )
        assert (
            monero.get_address(self.client, parse_path("m/44h/128h/1h"))
            == b"44iAazhoAkv5a5RqLNVyh82a1n3ceNggmN4Ho7bUBJ14WkEVR8uFTe9f7v5rNnJ2kEbVXxfXiRzsD5Jtc6NvBi4D6WNHPie"
        )
        assert (
            monero.get_address(self.client, parse_path("m/44h/128h/2h"))
            == b"47ejhmbZ4wHUhXaqA4b7PN667oPMkokf4ZkNdWrMSPy9TNaLVr7vLqVUQHh2MnmaAEiyrvLsX8xUf99q3j1iAeMV8YvSFcH"
        )
