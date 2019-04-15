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
class TestMsgMoneroGetwatchkey(TrezorTest):
    def test_monero_getwatchkey(self):
        self.setup_mnemonic_nopin_nopassphrase()
        res = monero.get_watch_key(self.client, parse_path("m/44h/128h/0h"))
        assert (
            res.address
            == b"4Ahp23WfMrMFK3wYL2hLWQFGt87ZTeRkufS6JoQZu6MEFDokAQeGWmu9MA3GFq1yVLSJQbKJqVAn9F9DLYGpRzRAEXqAXKM"
        )
        assert (
            res.watch_key.hex()
            == "8722520a581e2a50cc1adab4a1692401effd37b0d63b9d9b60fd7f34ea2b950e"
        )
        res = monero.get_watch_key(self.client, parse_path("m/44h/128h/1h"))
        assert (
            res.address
            == b"44iAazhoAkv5a5RqLNVyh82a1n3ceNggmN4Ho7bUBJ14WkEVR8uFTe9f7v5rNnJ2kEbVXxfXiRzsD5Jtc6NvBi4D6WNHPie"
        )
        assert (
            res.watch_key.hex()
            == "1f70b7d9e86c11b7a5bee883b75c43d6be189c8f812726ea1ecd94b06bb7db04"
        )
        res = monero.get_watch_key(self.client, parse_path("m/44h/128h/2h"))
        assert (
            res.address
            == b"47ejhmbZ4wHUhXaqA4b7PN667oPMkokf4ZkNdWrMSPy9TNaLVr7vLqVUQHh2MnmaAEiyrvLsX8xUf99q3j1iAeMV8YvSFcH"
        )
        assert (
            res.watch_key.hex()
            == "e0671fbed2c9231fe4f286962862813a4a4d153c793bf5d0e3742119723f3000"
        )
