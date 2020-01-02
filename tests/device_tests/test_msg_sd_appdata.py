# This file is part of the Trezor project.
#
# Copyright (C) 2012-2020 SatoshiLabs and contributors
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

import os

import pytest

from trezorlib import device
from trezorlib.exceptions import TrezorFailure

pytestmark = [pytest.mark.skip_t1, pytest.mark.sd_card]


def test_set_get(client):
    for _ in range(16):
        key = os.urandom(128)
        value = os.urandom(1024)
        device.sd_appdata_set(client, app="test1", key=key, value=value)
        value2 = device.sd_appdata_get(client, app="test1", key=key)
        assert value2 == value


def test_set_del_get(client):
    for _ in range(16):
        key = os.urandom(128)
        value = os.urandom(1024)
        device.sd_appdata_set(client, app="test2", key=key, value=value)
        device.sd_appdata_delete(client, app="test2", key=key)
        with pytest.raises(TrezorFailure):
            _ = device.sd_appdata_get(client, app="test2", key=key)
