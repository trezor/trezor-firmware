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

from ..common import MNEMONIC12


@pytest.mark.altcoin
@pytest.mark.ethereum
class TestMsgEthereumGetaddress:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ethereum_getaddress(self, client):
        assert (
            ethereum.get_address(client, [H_(44), H_(60)])
            == "0xE025dfbE2C53638E547C6487DED34Add7b8Aafc1"
        )
        assert (
            ethereum.get_address(client, [H_(44), H_(60), 1])
            == "0xeD46C856D0c79661cF7d40FFE0C0C5077c00E898"
        )
        assert (
            ethereum.get_address(client, [H_(44), H_(60), 0, H_(1)])
            == "0x6682Fa7F3eC58581b1e576268b5463B4b5c93839"
        )
        assert (
            ethereum.get_address(client, [H_(44), H_(60), H_(9), 0])
            == "0xFb3BE0F9717fF5fCF3C58EB49a9Ed67F1BD89D4E"
        )
        assert (
            ethereum.get_address(client, [H_(44), H_(60), 0, 9999999])
            == "0x6b909b50d88c9A8E02453A87b3662E3e7a5E0CF1"
        )
        assert (
            ethereum.get_address(client, [H_(44), H_(6060), 0, 9999999])
            == "0x98b8e926bd224764De2A0E4f4CBe1521474050AF"
        )
        # Wanchain SLIP44 id
        assert (
            ethereum.get_address(client, [H_(44), H_(5718350), H_(0)])
            == "0x4d643B1b556E14A27143a38bcE61230FFf5AFca8"
        )
