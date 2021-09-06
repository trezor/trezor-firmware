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
@pytest.mark.parametrize(
    "path, address",
    (
        ("m/44h/134h/0h", "lskbarvjr5co3rtbjgun4hu4mj5bst6jouedp5ko4"),
        ("m/44h/134h/1h", "lskcf6zpxcpfufxj7hx2d8qccg796qvpupcwu5efy"),
        ("m/44h/134h/100h", "lskbdacwa4qwsnbbv8wfz98q3h42t2ndgfbr83mxd"),
        ("m/44h/1h/0h", "lskk46y4d6gzzon3gz6ampchxk8kbak3gxxanntkn"),
    ),
)
def test_lisk_getaddress(client, path, address):
    address_n = parse_path(path)
    assert lisk.get_address(client, address_n) == address
