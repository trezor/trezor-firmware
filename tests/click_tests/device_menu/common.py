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

from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

from trezorlib.messages import BackupAvailability

from ... import translations as TR

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler

PIN4 = "1234"

REGULATORY_AREAS = [
    "United States",
    "",  # additional information to the US regulations
    "Canada",
    "Europe",
    "Australia",
    "Ukraine",
    # "Japan",
    "South Korea",
    "Taiwan",
]

AUTOLOCK_DELAY_USB_DEFAULT_MS = 10 * 60 * 1000  # 10 minutes
AUTOLOCK_DELAY_BATT_DEFAULT_MS = 40 * 1000  # 40 seconds


def format_duration_ms(milliseconds: int) -> str:
    """
    Returns a human-friendly representation of a duration. Truncates all decimals.
    """

    assert milliseconds >= 0

    unit_plurals = {
        "millisecond": TR.plurals__lock_after_x_milliseconds,
        "second": TR.plurals__lock_after_x_seconds,
        "minute": TR.plurals__lock_after_x_minutes,
        "hour": TR.plurals__lock_after_x_hours,
    }

    # Pick appropriate unit and divisor
    units: tuple[tuple[str, int], ...] = (
        (unit_plurals["hour"], 60 * 60 * 1000),
        (unit_plurals["minute"], 60 * 1000),
        (unit_plurals["second"], 1000),
    )
    for unit, divisor in units:
        if milliseconds >= divisor:
            break
    else:
        unit = unit_plurals["millisecond"]
        divisor = 1

    count = milliseconds // divisor

    # Inline plural formatting
    plural_options = unit.split("|")
    if len(plural_options) not in (2, 3):
        raise ValueError("Unit plurals must have 2 or 3 forms separated by '|'")

    if count == 1:
        plural = plural_options[0]
    else:
        plural = plural_options[-1]

    if len(plural_options) == 3 and 1 < count < 5:
        plural = plural_options[1]

    return f"{count} {plural}"


class Menu(Enum):
    ROOT = 0
    PAIR_AND_CONNECT = auto()
    SETTINGS = auto()
    SECURITY = auto()
    PIN = auto()
    AUTO_LOCK = auto()
    WIPE_CODE = auto()
    DEVICE = auto()
    POWER = auto()

    def path_from_root(self) -> list[str]:
        """
        Return the sequence of labels to click from ROOT to reach this Menu.
        """
        paths = {
            Menu.ROOT: [],
            Menu.PAIR_AND_CONNECT: [TR.ble__pair_title],
            Menu.SETTINGS: [TR.words__settings],
            Menu.SECURITY: [TR.words__settings, TR.words__security],
            Menu.PIN: [TR.words__settings, TR.words__security, TR.pin__title],
            Menu.AUTO_LOCK: [
                TR.words__settings,
                TR.words__security,
                TR.auto_lock__title,
            ],
            Menu.WIPE_CODE: [
                TR.words__settings,
                TR.words__security,
                TR.wipe_code__title,
            ],
            Menu.DEVICE: [TR.words__settings, TR.words__device],
            Menu.POWER: [TR.words__power],
        }
        try:
            return paths[self]
        except KeyError:
            raise ValueError(f"No path defined for menu {self}")

    def content(self, features: "Features") -> list[str] | None:
        """
        Expected vertical menu content for this Menu, given device features.
        """
        initialized = features.initialized
        has_pin = features.pin_protection
        has_wipe_code = features.wipe_code_protection
        unfinished_backup = features.unfinished_backup
        needs_backup = features.backup_availability == BackupAvailability.Required
        no_backup = features.no_backup

        def root_content():
            content: list[str] = []
            if initialized:
                if unfinished_backup:
                    content.append(TR.homescreen__title_backup_failed)
                if needs_backup:
                    content.append(TR.homescreen__title_backup_needed)
                if not has_pin:
                    content.append(TR.homescreen__title_pin_not_set)
            content.extend([TR.ble__pair_title, TR.words__settings, TR.words__power])

            return content

        def connection_content():
            return [TR.ble__pair_new, TR.ble__forget_all]

        def settings_content():
            content = [TR.words__bluetooth]
            if initialized:
                content.append(TR.words__security)
            content.append(TR.words__device)
            return content

        def security_content():
            if not initialized:
                return None
            content: list[str] = [TR.pin__title]
            if has_pin:
                content.append(TR.auto_lock__title)
                content.append(TR.wipe_code__title)
            if not needs_backup and not no_backup and not unfinished_backup:
                content.append(TR.reset__check_backup_title)
            return content

        def pin_content():
            if initialized and has_pin:
                return [TR.pin__change, TR.pin__remove]
            return None

        def auto_lock_content():
            if initialized and has_pin:

                auto_lock_batt = (
                    features.auto_lock_delay_battery_ms
                    or AUTOLOCK_DELAY_BATT_DEFAULT_MS
                )
                auto_lock_usb = (
                    features.auto_lock_delay_ms or AUTOLOCK_DELAY_USB_DEFAULT_MS
                )

                return [
                    format_duration_ms(auto_lock_batt),
                    format_duration_ms(auto_lock_usb),
                ]
            return None

        def wipe_code_content():
            if initialized and has_wipe_code:
                return [TR.wipe_code__change, TR.wipe_code__remove]
            return None

        def device_content():
            content: list[str] = []
            if initialized:
                content.extend(
                    [
                        TR.words__name,
                        TR.brightness__title,
                    ]
                )
                if features.haptic_feedback is not None:
                    content.append(TR.haptic_feedback__title)
                content.append(TR.led__title)
            content.extend([TR.regulatory__title, TR.words__about, TR.wipe__title])
            return content

        lookup: dict["Menu", Callable[[], list[str] | None]] = {
            Menu.ROOT: root_content,
            Menu.PAIR_AND_CONNECT: connection_content,
            Menu.SETTINGS: settings_content,
            Menu.SECURITY: security_content,
            Menu.PIN: pin_content,
            Menu.AUTO_LOCK: auto_lock_content,
            Menu.WIPE_CODE: wipe_code_content,
            Menu.DEVICE: device_content,
        }

        return lookup[self]()

    def navigate_back(self, debug: "DebugLink", features: "Features"):
        """
        Press back button if the Header has one.

        Returns the vertical menu content of the target screen.
        Raises error if the back button isn't present.
        """

        # Ensure we start at the current menu
        expected = self.content(features)
        menu = debug.read_layout().vertical_menu_content()
        if self == Menu.PAIR_AND_CONNECT:
            # The connection menu has two permanent items at the end
            assert menu[-2:] == expected
        else:
            assert expected == menu

        # Navigate back to the previous menu
        assert debug.read_layout().find_unique_value_by_key(
            "left_button", default={}, only_type=dict
        )
        debug.click(debug.screen_buttons.back())

        # After navigation, we should be at the target menu
        return debug.read_layout().vertical_menu_content()

    def navigate_to(self, debug: "DebugLink", features: "Features"):
        """
        Navigate UI from the current menu to the target menu using the debug
        interface without pressing any back buttons.

        Returns the vertical menu content of the target screen.
        Raises error if there is no direct path to the target menu.
        """
        # Ensure we the target menu can be directly navigated to
        menu = debug.read_layout().vertical_menu_content()
        path = self.path_from_root()
        matches = [(idx, x) for idx, x in enumerate(path) if x in menu]

        if len(matches) < 1:
            raise PathNotFound(self.name)
        elif len(matches) > 1:
            raise PathNotUnique(self.name)
        start_idx = matches[0][0]

        # Follow the path
        for label in self.path_from_root()[start_idx:]:
            menu = debug.read_layout().vertical_menu_content()
            idx = menu_idx(label, menu)
            debug.button_actions.navigate_to_menu_item(idx)
        assert_device_screen(debug, self)

        # After navigation, we should be at the target menu
        menu = debug.read_layout().vertical_menu_content()
        expected = self.content(features)
        if self == Menu.PAIR_AND_CONNECT:
            # The connection menu has two permanent items at the end
            if menu[-2:] != expected:
                raise MenuContentNotMatching(menu[-2:], expected)
        else:
            if menu != expected:
                raise MenuContentNotMatching(menu, expected)
        return menu

    @classmethod
    def assert_menu_exists(cls, features: "Features"):
        """
        Assert that the menu content is as expected depending on the feature flags.
        """
        # Always exist
        assert Menu.ROOT.content(features)
        assert Menu.SETTINGS.content(features)
        assert Menu.PAIR_AND_CONNECT.content(features)
        assert Menu.DEVICE.content(features)

        security = Menu.SECURITY.content(features)
        if features.initialized:
            assert security is not None
        else:
            assert security is None

            pin = Menu.PIN.content(features)
            if features.initialized and features.pin_protection:
                assert pin is not None
            else:
                assert pin is None

        auto_lock = Menu.AUTO_LOCK.content(features)
        if features.initialized and features.pin_protection:
            assert auto_lock is not None
        else:
            assert auto_lock is None

        wipe_code = Menu.WIPE_CODE.content(features)
        if (
            features.initialized
            and features.pin_protection
            and features.wipe_code_protection
        ):
            assert wipe_code is not None
        else:
            assert wipe_code is None

    @classmethod
    def traverse(cls, debug: "DebugLink", features: "Features") -> None:
        """
        Traverse the entire menu from the root.
        """

        # Assert that all required menus exist because traversing skips non-existing menus
        cls.assert_menu_exists(features)

        # Start at the root menu
        menu = debug.read_layout().vertical_menu_content()
        assert menu == cls.ROOT.content(features)

        root_child = cls.PAIR_AND_CONNECT
        if root_child.content(features) is not None:
            menu = root_child.navigate_to(debug, features)

            # Check if the last two items match the expected content
            assert menu[-2:] == root_child.content(features)

            # TODO traverse through connected devices
            # for item in menu[:-2]:
            #     assert item in child.content(features)

            # Go back to root
            menu = root_child.navigate_back(debug, features)

        root_child = cls.SETTINGS
        if root_child.content(features) is not None:
            menu = root_child.navigate_to(debug, features)

            child_1 = cls.SECURITY
            if child_1.content(features) is not None:
                menu = child_1.navigate_to(debug, features)

                child_2 = cls.PIN
                if child_2.content(features) is not None:
                    menu = child_2.navigate_to(debug, features)
                    # Go back to security
                    menu = child_2.navigate_back(debug, features)

                child_2 = cls.AUTO_LOCK
                if child_2.content(features) is not None:
                    menu = child_2.navigate_to(debug, features)
                    # Go back to security
                    menu = child_2.navigate_back(debug, features)

                child_2 = cls.WIPE_CODE
                if child_2.content(features) is not None:
                    menu = child_2.navigate_to(debug, features)
                    # Go back to security
                    menu = child_2.navigate_back(debug, features)

                # Go back to settings
                menu = child_1.navigate_back(debug, features)

            child_1 = cls.DEVICE
            if child_1.content(features) is not None:
                menu = child_1.navigate_to(debug, features)

                # Regulatory screen
                regulatory_idx = menu.index(TR.regulatory__title)
                debug.button_actions.navigate_to_menu_item(regulatory_idx)
                debug.synchronize_at("RegulatoryScreen")
                layout = debug.read_layout()
                assert TR.regulatory__title in layout.title()
                assert layout.page_count() == len(REGULATORY_AREAS)
                # Scroll through all regulatory areas
                assert REGULATORY_AREAS[0] in debug.read_layout().subtitle()
                for area in REGULATORY_AREAS[1:]:
                    debug.click(debug.screen_buttons.ok())
                    assert area in debug.read_layout().subtitle()
                # Close the regulatory screen
                debug.click(debug.screen_buttons.menu())
                menu = debug.read_layout().vertical_menu_content()
                assert menu == child_1.content(features)

                # Go to about screen
                about_idx = menu.index(TR.words__about)
                debug.button_actions.navigate_to_menu_item(about_idx)
                debug.synchronize_at("TextScreen")
                layout = debug.read_layout()
                assert layout.title() == TR.words__about
                assert TR.homescreen__firmware_version in layout.text_content()
                assert TR.homescreen__firmware_type in layout.text_content()
                assert TR.ble__version in layout.text_content()
                # Close the about screen
                debug.click(debug.screen_buttons.menu())
                menu = debug.read_layout().vertical_menu_content()
                assert menu == child_1.content(features)
                # Go back to settings
                menu = child_1.navigate_back(debug, features)

            # Go back to root
            menu = root_child.navigate_back(debug, features)


class NoSecuritySettings(Exception):
    pass


class MenuItemNotFound(Exception):
    def __init__(self, item_name: str):
        self.item_name = item_name

    def __str__(self):
        return f"Menu item '{self.item_name}' not found"


class PathNotFound(Exception):
    def __init__(self, item_name: str):
        self.item_name = item_name

    def __str__(self):
        return f"Path to '{self.item_name}' not found"


class PathNotUnique(Exception):
    def __init__(self, item_name: str):
        self.item_name = item_name

    def __str__(self):
        return f"Path to '{self.item_name}' is not unique"


class MenuContentNotMatching(Exception):
    def __init__(self, actual: list[str] | None, expected: list[str] | None):
        self.actual = actual
        self.expected = expected

    def __str__(self):
        return f"Menu content for '{self.actual}' does not match expected '{self.expected}'"


def open_device_menu(debug: "DebugLink"):
    # Start at homescreen
    debug.synchronize_at("Homescreen")

    # Go to device menu
    debug.click(debug.screen_buttons.ok())
    debug.synchronize_at("DeviceMenuScreen")


def close_device_menu(debug: "DebugLink"):
    # Start at device menu
    debug.synchronize_at("DeviceMenuScreen")

    # Close the device menu
    debug.click(debug.screen_buttons.menu())
    debug.synchronize_at("Homescreen")


def assert_device_screen(debug: "DebugLink", menu: Menu):
    assert (
        debug.read_layout().find_unique_value_by_key("MenuId", default=0, only_type=int)
        == menu.value
    )


def menu_idx(item: str, menu: list[str]) -> int:
    if item not in menu:
        raise MenuItemNotFound(item)
    return menu.index(item)


def enter_pin(device_handler: "BackgroundDeviceHandler", pin: str = PIN4):
    debug = device_handler.debuglink()
    device_handler.get_session()
    debug.synchronize_at("PinKeyboard")
    debug.input(pin)
    device_handler.result()
