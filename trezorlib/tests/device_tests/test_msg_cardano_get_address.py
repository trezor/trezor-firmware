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

from trezorlib.cardano import get_address
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgCardanoGetAddress(TrezorTest):
    @pytest.mark.parametrize(
        "path,expected_address",
        [
            (
                "m/44'/1815'/0'/0/0",
                "Ae2tdPwUPEZLCq3sFv4wVYxwqjMH2nUzBVt1HFr4v87snYrtYq3d3bq2PUQ",
            ),
            (
                "m/44'/1815'/0'/0/1",
                "Ae2tdPwUPEZEY6pVJoyuNNdLp7VbMB7U7qfebeJ7XGunk5Z2eHarkcN1bHK",
            ),
            (
                "m/44'/1815'/0'/0/2",
                "Ae2tdPwUPEZ3gZD1QeUHvAqadAV59Zid6NP9VCR9BG5LLAja9YtBUgr6ttK",
            ),
        ],
    )
    def test_cardano_get_address(self, path, expected_address):
        # data from https://iancoleman.io/bip39/#english
        self.setup_mnemonic_nopin_nopassphrase()

        address = get_address(self.client, parse_path(path))
        assert address == expected_address
