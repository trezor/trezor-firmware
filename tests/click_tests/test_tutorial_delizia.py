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
    pytest.mark.models("delizia"),
    pytest.mark.setup_client(uninitialized=True),
]


def test_tutorial_ignore_menu(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__welcome_safe5
    layout = debug.click(buttons.TAP_TO_CONFIRM)
    assert layout.title() == TR.tutorial__title_lets_begin
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_easy_navigation
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_handy_menu
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_hold
    layout = debug.click(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    assert layout.title() == TR.tutorial__title_well_done
    debug.swipe_up()

    device_handler.result()


def test_tutorial_menu_open_close(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__welcome_safe5
    layout = debug.click(buttons.TAP_TO_CONFIRM)
    assert layout.title() == TR.tutorial__title_lets_begin
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_easy_navigation
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_handy_menu

    layout = debug.click(buttons.CORNER_BUTTON)
    assert TR.tutorial__did_you_know in layout.text_content()
    layout = debug.click(buttons.CORNER_BUTTON)
    assert layout.title() == TR.tutorial__title_handy_menu

    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_hold
    layout = debug.click(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    assert layout.title() == TR.tutorial__title_well_done
    debug.swipe_up()

    device_handler.result()


def test_tutorial_menu_exit(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__welcome_safe5
    layout = debug.click(buttons.TAP_TO_CONFIRM)
    assert layout.title() == TR.tutorial__title_lets_begin
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_easy_navigation
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_handy_menu

    layout = debug.click(buttons.CORNER_BUTTON)
    assert TR.tutorial__did_you_know in layout.text_content()
    layout = debug.click(buttons.VERTICAL_MENU[2])
    assert TR.instructions__hold_to_exit_tutorial in layout.footer()
    layout = debug.click(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    assert layout.title() == TR.tutorial__title_well_done
    debug.swipe_up()

    device_handler.result()


def test_tutorial_menu_repeat(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__welcome_safe5
    layout = debug.click(buttons.TAP_TO_CONFIRM)
    assert layout.title() == TR.tutorial__title_lets_begin
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_easy_navigation
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_handy_menu

    layout = debug.click(buttons.CORNER_BUTTON)
    assert TR.tutorial__did_you_know in layout.text_content()
    layout = debug.click(buttons.VERTICAL_MENU[1])

    assert layout.title() == TR.tutorial__title_lets_begin
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_easy_navigation
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_handy_menu
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_hold
    layout = debug.click(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    assert layout.title() == TR.tutorial__title_well_done
    debug.swipe_up()

    device_handler.result()


def test_tutorial_menu_funfact(device_handler: "BackgroundDeviceHandler"):
    debug = device_handler.debuglink()
    device_handler.run(device.show_device_tutorial)

    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__welcome_safe5
    layout = debug.click(buttons.TAP_TO_CONFIRM)
    assert layout.title() == TR.tutorial__title_lets_begin
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_easy_navigation
    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_handy_menu

    layout = debug.click(buttons.CORNER_BUTTON)
    assert TR.tutorial__did_you_know in layout.text_content()
    layout = debug.click(buttons.VERTICAL_MENU[0])
    assert layout.text_content() in TR.tutorial__first_wallet.replace("\n", " ")

    layout = debug.click(buttons.CORNER_BUTTON)
    assert TR.tutorial__did_you_know in layout.text_content()
    layout = debug.click(buttons.CORNER_BUTTON)
    assert layout.title() == TR.tutorial__title_handy_menu

    layout = debug.swipe_up()
    assert layout.title() == TR.tutorial__title_hold
    layout = debug.click(buttons.TAP_TO_CONFIRM, hold_ms=1000)
    assert layout.title() == TR.tutorial__title_well_done
    debug.swipe_up()

    device_handler.result()
