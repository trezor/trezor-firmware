# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING

import pytest

from trezorlib import device
from trezorlib.debuglink import LayoutType

if TYPE_CHECKING:
    from ...device_handler import BackgroundDeviceHandler


@pytest.mark.invalidate_client
def test_bootloader(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()

    device_handler.get_session()

    session = device_handler.result()

    features = device_handler.features()

    assert features.bootloader_mode is True

    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        debug.click((200, 500))
    else:
        debug.press_left()

    device_handler.run_with_provided_session(session, device.wipe)  # type: ignore

    if debug.layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        debug.click((200, 500))
    else:
        debug.press_right()

    device_handler.result()

    features = device_handler.features()

    assert features.bootloader_mode is True
