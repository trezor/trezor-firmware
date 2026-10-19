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

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest

from trezorlib import device
from trezorlib.exceptions import Cancelled
from trezorlib.testing import translations as TR

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.testing.device_handler import BackgroundDeviceHandler


# Safe family only
pytestmark = [pytest.mark.models("safe3"), pytest.mark.setup_client(uninitialized=True)]


@contextmanager
def prepare_tutorial_and_cancel_after_it(
    device_handler: "BackgroundDeviceHandler", cancelled: bool = False
) -> Generator["DebugLink", None, None]:
    debug = device_handler.debuglink()
    session = device_handler.client.get_seedless_session()
    device_handler.run_with_provided_session(session, device.show_device_tutorial)

    yield debug

    try:
        device_handler.result()
    except Cancelled:
        if not cancelled:
            raise


def go_to_menu_intro(debug: "DebugLink") -> None:
    """From the welcome screen to the screen introducing the menu."""
    # Welcome
    debug.press_right()
    go_to_menu_intro_from_buttons(debug)


def go_to_menu_intro_from_buttons(debug: "DebugLink") -> None:
    """From the screen about the buttons to the screen introducing the menu."""
    # Use Trezor by pressing left and right buttons
    debug.press_right()
    # Hold to confirm
    debug.press_right(hold_ms=1000)
    # Middle button
    debug.press_middle()
    # Try scrolling
    debug.press_right()
    # Need to go back? - Shift + right
    assert debug.read_layout().title() == TR.tutorial__title_go_back
    debug.press_right_with_shift()
    # Remember
    assert debug.read_layout().title() == TR.tutorial__title_remember
    debug.press_right()
    assert debug.read_layout().title() == TR.tutorial__title_handy_menu


def go_through_tutorial_tr(debug: "DebugLink") -> None:
    go_to_menu_intro(debug)
    # Menu - "Complete tutorial"
    debug.press_left()
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
        assert debug.read_layout().title() == TR.tutorial__title_skip
        debug.press_right()


def test_tutorial_skip_declined(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler) as debug:
        # SKIP, then back to the welcome screen
        debug.press_left()
        debug.press_left()
        assert debug.read_layout().title() == TR.tutorial__title_welcome

        go_through_tutorial_tr(debug)
        debug.press_right()


def test_tutorial_again_and_skip(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler, cancelled=True) as debug:
        # CLICK THROUGH
        go_through_tutorial_tr(debug)

        # AGAIN
        debug.press_left()
        assert debug.read_layout().title() == TR.tutorial__title_welcome

        # SKIP
        debug.press_left()
        debug.press_right()


def test_tutorial_menu_info(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler) as debug:
        debug.press_right()
        # Use Trezor - the menu button shows information about the menu
        debug.press_left()
        layout = debug.read_layout()
        assert layout.title() == TR.tutorial__title_handy_menu
        assert TR.regexp("tutorial__menu_later").match(layout.text_content())
        # closing it goes back
        debug.press_left()
        assert TR.regexp("tutorial__use_trezor").match(
            debug.read_layout().text_content()
        )

        go_to_menu_intro_from_buttons(debug)
        debug.press_left()
        debug.press_middle()
        debug.press_right()


def test_tutorial_middle_button_hint(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler) as debug:
        debug.press_right()
        debug.press_right()
        debug.press_right(hold_ms=1000)
        assert debug.read_layout().title() == TR.tutorial__title_middle_button

        # one button alone shows the hint and stays on the screen
        debug.press_left()
        layout = debug.read_layout()
        assert layout.title() == TR.tutorial__title_middle_button
        assert TR.regexp("tutorial__press_both").match(layout.text_content())
        debug.press_right()
        assert debug.read_layout().title() == TR.tutorial__title_middle_button

        debug.press_middle()
        assert debug.read_layout().title() == TR.tutorial__title_screen_scroll

        debug.press_right()
        debug.press_right_with_shift()
        debug.press_right()
        debug.press_left()
        debug.press_middle()
        debug.press_right()


def test_tutorial_go_back(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler) as debug:
        debug.press_right()
        debug.press_right()
        debug.press_right(hold_ms=1000)
        debug.press_middle()
        debug.press_right()

        # the right button alone does nothing
        debug.press_right()
        assert debug.read_layout().title() == TR.tutorial__title_go_back

        debug.press_right_with_shift()
        assert debug.read_layout().title() == TR.tutorial__title_remember
        # Shift + right goes back from the following screens
        debug.press_right_with_shift()
        assert debug.read_layout().title() == TR.tutorial__title_go_back
        debug.press_right_with_shift()
        debug.press_right()
        assert debug.read_layout().title() == TR.tutorial__title_handy_menu
        debug.press_right_with_shift()
        assert debug.read_layout().title() == TR.tutorial__title_remember

        debug.press_right()
        debug.press_left()
        debug.press_middle()
        debug.press_right()


def test_tutorial_menu(device_handler: "BackgroundDeviceHandler"):
    with prepare_tutorial_and_cancel_after_it(device_handler) as debug:
        go_to_menu_intro(debug)

        # closing the menu goes back
        debug.press_left()
        debug.press_left()
        assert debug.read_layout().title() == TR.tutorial__title_handy_menu

        # "Restart tutorial"
        debug.press_left()
        debug.press_right()
        debug.press_middle()
        assert debug.read_layout().title() == TR.tutorial__title_welcome

        go_through_tutorial_tr(debug)
        debug.press_right()
