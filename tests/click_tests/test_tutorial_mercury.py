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

from typing import TYPE_CHECKING

import pytest

from trezorlib import device

from .. import buttons
from .. import translations as TR

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


# Trezor Safe 5 only
pytestmark = [
    pytest.mark.models("mercury"),
    pytest.mark.setup_client(uninitialized=True),
]


def test_tutorial_ignore_menu(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.wait_layout()
    TR.assert_equals(layout.title(), "tutorial__welcome_safe5")
    layout = debug.click(buttons.TAP_TO_CONFIRM, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_lets_begin")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_easy_navigation")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_hold")
    layout = debug.click_hold(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    TR.assert_equals(layout.title(), "tutorial__title_well_done")
    debug.swipe_up(wait=True)

    device_handler.result()


def test_tutorial_menu_open_close(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.wait_layout()
    TR.assert_equals(layout.title(), "tutorial__welcome_safe5")
    layout = debug.click(buttons.TAP_TO_CONFIRM, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_lets_begin")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_easy_navigation")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")

    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_in(layout.text_content(), "tutorial__did_you_know")
    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")

    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_hold")
    layout = debug.click_hold(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    TR.assert_equals(layout.title(), "tutorial__title_well_done")
    debug.swipe_up(wait=True)

    device_handler.result()


def test_tutorial_menu_exit(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.wait_layout()
    TR.assert_equals(layout.title(), "tutorial__welcome_safe5")
    layout = debug.click(buttons.TAP_TO_CONFIRM, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_lets_begin")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_easy_navigation")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")

    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_in(layout.text_content(), "tutorial__did_you_know")
    layout = debug.click(buttons.VERTICAL_MENU[2], wait=True)
    TR.assert_in(layout.footer(), "instructions__hold_to_exit_tutorial")
    layout = debug.click_hold(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    TR.assert_equals(layout.title(), "tutorial__title_well_done")
    debug.swipe_up(wait=True)

    device_handler.result()


def test_tutorial_menu_repeat(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.wait_layout()
    TR.assert_equals(layout.title(), "tutorial__welcome_safe5")
    layout = debug.click(buttons.TAP_TO_CONFIRM, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_lets_begin")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_easy_navigation")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")

    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_in(layout.text_content(), "tutorial__did_you_know")
    layout = debug.click(buttons.VERTICAL_MENU[1], wait=True)

    TR.assert_equals(layout.title(), "tutorial__title_lets_begin")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_easy_navigation")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_hold")
    layout = debug.click_hold(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    TR.assert_equals(layout.title(), "tutorial__title_well_done")
    debug.swipe_up(wait=True)

    device_handler.result()


def test_tutorial_menu_funfact(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.wait_layout()
    TR.assert_equals(layout.title(), "tutorial__welcome_safe5")
    layout = debug.click(buttons.TAP_TO_CONFIRM, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_lets_begin")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_easy_navigation")
    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")

    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_in(layout.text_content(), "tutorial__did_you_know")
    layout = debug.click(buttons.VERTICAL_MENU[0], wait=True)
    text_content = [
        s.replace("\n", " ") for s in TR.translate("tutorial__first_wallet")
    ]
    assert layout.text_content() in text_content

    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_in(layout.text_content(), "tutorial__did_you_know")
    layout = debug.click(buttons.CORNER_BUTTON, wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_handy_menu")

    layout = debug.swipe_up(wait=True)
    TR.assert_equals(layout.title(), "tutorial__title_hold")
    layout = debug.click_hold(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    TR.assert_equals(layout.title(), "tutorial__title_well_done")
    debug.swipe_up(wait=True)

    device_handler.result()
