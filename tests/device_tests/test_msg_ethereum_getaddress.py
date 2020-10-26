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
from trezorlib.tools import parse_path

VECTORS = (  # path, address
    ("m/44'/60'/0'", "0xdA0b608bdb1a4A154325C854607c68950b4F1a34"),
    ("m/44'/60'/100'", "0x93Fb0Ff84F5BB6E7b6a9835C7AA6dE7a76794266"),
    ("m/44'/60'/0'/0/0", "0x73d0385F4d8E00C5e6504C6030F47BF6212736A8"),
    ("m/44'/60'/0'/0/100", "0x1e6E3708a059aEa1241a81c7aAe84b6CDbC54d59"),
    # ETC
    ("m/44'/61'/0'/0/0", "0xF410e37E9C8BCf8CF319c84Ae9dCEbe057804a04"),
    # GoChain
    ("m/44'/6060'/0'/0/0", "0xA26a450ef46a5f11a510eBA2119A3236fa0Aca92"),
    # Wanchain
    ("m/44'/5718350'/0'/0/0", "0xe432a7533D689ceed00B7EE91d9368b8A1693bD2"),
)


@pytest.mark.altcoin
@pytest.mark.ethereum
@pytest.mark.parametrize("path, address", VECTORS)
def test_ethereum_getaddress(client, path, address):
    address_n = parse_path(path)
    assert ethereum.get_address(client, address_n) == address
