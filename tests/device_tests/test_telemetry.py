# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

from trezorlib import device
from trezorlib.debuglink import DebugSession as Session

pytestmark = pytest.mark.models("t3w1")


def test_basic(session: Session):
    res = device.get_telemetry(session)
    assert res.min_temp_c is not None
    assert res.max_temp_c is not None
    assert res.min_temp_c <= res.max_temp_c
    assert res.battery_errors is not None
    assert res.battery_cycles is not None
