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

from trezorlib import ble
from trezorlib.debuglink import DebugSession as Session


@pytest.mark.models("t3w1")
def test_ble_unpair_all(session: Session):
    ble.unpair(session, all=True)
    # `Success` is sent before unpairing is done, so we'll send another command just to "flush" the last screen.
    session.client.ping("")
