# This file is part of the Trezor project.
#
# Copyright (C) 2012-2023 SatoshiLabs and contributors
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

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

import pytest

from trezorlib import device
from trezorlib.exceptions import Cancelled

from .. import translations as TR

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ..device_handler import BackgroundDeviceHandler


# Safe family only
pytestmark = [pytest.mark.models("safe3"), pytest.mark.setup_client(uninitialized=True)]


@contextmanager
def prepare_tutorial_and_cancel_after_it(
    device_handler: "BackgroundDeviceHandler", cancelled: bool = False
) -> Generator["DebugLink", None, None]:
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    yield debug

    try:
        device_handler.result()
    except Cancelled:
        if not cancelled:
            raise


def go_through_tutorial_tr(debug: "DebugLink") -> None:
    debug.press_right()
    debug.press_right()
    debug.press_right(hold_ms=1000)
    debug.press_right()
    debug.press_right()
    debug.press_middle()
    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__title_tutorial_complete


def test_tutorial_finish(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler) as debug:
        # CLICK THROUGH
        go_through_tutorial_tr(debug)

        # FINISH
        debug.press_right()


def test_tutorial_skip(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler, cancelled=True) as debug:
        # SKIP
        debug.press_left()
        debug.press_right()


def test_tutorial_again_and_skip(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler, cancelled=True) as debug:
        # CLICK THROUGH
        go_through_tutorial_tr(debug)

        # AGAIN
        debug.press_left()

        # SKIP
        debug.press_left()
        debug.press_right()
