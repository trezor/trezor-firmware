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

from trezorlib import device, exceptions
from trezorlib.debuglink import DebugLink

from .. import translations as TR

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


# Trezor Safe 7 only
pytestmark = [
    pytest.mark.models("eckhart"),
    pytest.mark.setup_client(uninitialized=True),
]


def _paginated_text(debug: "DebugLink") -> str:
    """Get the text content of the current layout"""

    layout = debug.read_layout()
    pages = layout.page_count()
    text = layout.text_content()
    for _ in range(pages - 1):
        debug.click(debug.screen_buttons.ok())
        text += " "
        text += debug.read_layout().text_content()
    return text.strip()


def _assert_tropic_info(debug: "DebugLink"):
    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__what_is_tropic
    text = _paginated_text(debug)
    assert TR.tutorial__tropic_info in text

    debug.click(debug.screen_buttons.menu())


def _wait_for_welcome_animation(debug: "DebugLink"):
    """Wait for the welcome animation to finish."""
    debug.synchronize_at("TextScreen")


def _assert_begin_screen_and_proceed(debug: "DebugLink"):
    layout = debug.read_layout()
    assert layout.text_content() == TR.tutorial__welcome_safe7.replace("\n", " ")
    assert TR.tutorial__tap_to_start in layout.action_bar()
    debug.click(debug.screen_buttons.ok())


def _assert_navigation_screen_and_proceed(debug: "DebugLink"):
    assert debug.read_layout().text_content() == TR.tutorial__navigation_ts7
    debug.click(debug.screen_buttons.ok())


def _assert_instructions_and_proceed_to_menu(debug: "DebugLink"):
    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__title_handy_menu
    assert TR.tutorial__menu in layout.text_content()
    debug.click(debug.screen_buttons.menu())


def _assert_menu(debug: "DebugLink"):
    assert "VerticalMenuScreen" in debug.read_layout().all_components()


def _assert_htc_screen(debug: "DebugLink"):
    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__last_one
    assert TR.tutorial__title_hold in layout.text_content()


def _assert_final_screen(debug: "DebugLink"):
    layout = debug.read_layout()
    assert layout.title() == TR.tutorial__title_well_done
    assert TR.tutorial__ready_to_use_safe5 in layout.text_content()


def test_tutorial_full_completion(device_handler: "BackgroundDeviceHandler"):
    """Test basic flow of the tutorial."""
    debug = device_handler.debuglink()
    device_handler.run_with_session(device.show_device_tutorial, seedless=True)

    _wait_for_welcome_animation(debug)
    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - continue
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # htc menu - confirm tutorial
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.ok())

    # final screen - confirm
    _assert_final_screen(debug)
    debug.click(debug.screen_buttons.ok())

    device_handler.result()


def test_tutorial_cancel_from_main_menu(device_handler: "BackgroundDeviceHandler"):
    """Cancel the tutorial from the main menu."""
    debug = device_handler.debuglink()
    device_handler.run_with_session(device.show_device_tutorial, seedless=True)

    _wait_for_welcome_animation(debug)
    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - exit
    _assert_menu(debug)
    # due to overflowing menu, we need to swipe up to see the exit option
    for _ in range(3):
        debug.swipe_up()
    debug.button_actions.navigate_to_menu_item(0)

    # exit screen - confirm
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.ok())

    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


def test_tutorial_cancel_from_confirm_menu(device_handler: "BackgroundDeviceHandler"):
    """Cancel the tutorial from the hold-to-confirm screen."""
    debug = device_handler.debuglink()
    device_handler.run_with_session(device.show_device_tutorial, seedless=True)

    _wait_for_welcome_animation(debug)
    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - continue
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # hold to confirm screen - go to menu
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # htc menu - cancel tutorial
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(2)

    # exit screen - exit tutorial
    debug.click(debug.screen_buttons.ok())
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


def test_tutorial_menu_close(device_handler: "BackgroundDeviceHandler"):
    """Test all occurences of the menu close action in the tutorial."""
    debug = device_handler.debuglink()
    device_handler.run_with_session(device.show_device_tutorial, seedless=True)

    _wait_for_welcome_animation(debug)
    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen
    _assert_menu(debug)
    # close and open again
    debug.click(debug.screen_buttons.menu())
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - continue
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # hold to confirm screen - go to menu
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # close menu and reopen
    _assert_menu(debug)
    debug.click(debug.screen_buttons.menu())
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # htc menu - exit tutorial
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(2)

    # exit screen
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # exit menu - close
    _assert_menu(debug)
    debug.click(debug.screen_buttons.menu())

    # exit menu - exit tutorial
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.ok())
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


def test_tutorial_menu_tropic(device_handler: "BackgroundDeviceHandler"):
    """Test all occurences of the tropic info screen in the tutorial."""
    debug = device_handler.debuglink()
    device_handler.run_with_session(device.show_device_tutorial, seedless=True)

    _wait_for_welcome_animation(debug)
    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)

    # main menu tropic info
    _assert_tropic_info(debug)

    # menu screen - continue
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # hold to confirm screen
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # htc menu - show tropic
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # htc menu tropic info
    _assert_tropic_info(debug)

    # htc menu - exit tutorial
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(2)

    # exit screen
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # exit menu - show tropic
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # exit menu tropic info
    _assert_tropic_info(debug)

    # exit menu - go back
    debug.click(debug.screen_buttons.menu())

    # exit screen - exit tutorial
    debug.click(debug.screen_buttons.ok())
    with pytest.raises(exceptions.Cancelled):
        device_handler.result()


def test_tutorial_restart(device_handler: "BackgroundDeviceHandler"):
    """Test all occurences of the restart action in the tutorial."""
    debug = device_handler.debuglink()
    device_handler.run_with_session(device.show_device_tutorial, seedless=True)

    _wait_for_welcome_animation(debug)
    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - restart
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(2)

    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - continue
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # hold to confirm screen - go to menu
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # htc menu - restart tutorial
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)

    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - exit
    _assert_menu(debug)
    # due to overflowing menu, we need to swipe up to see the exit option
    for _ in range(3):
        debug.swipe_up()
    debug.button_actions.navigate_to_menu_item(0)

    # exit screen - go to menu
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.menu())

    # exit menu - restart tutorial
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)

    _assert_begin_screen_and_proceed(debug)
    _assert_navigation_screen_and_proceed(debug)
    _assert_instructions_and_proceed_to_menu(debug)

    # menu screen - continue
    _assert_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)

    # htc menu - confirm tutorial
    _assert_htc_screen(debug)
    debug.click(debug.screen_buttons.ok())

    # final screen - confirm
    _assert_final_screen(debug)
    debug.click(debug.screen_buttons.ok())

    device_handler.result()
