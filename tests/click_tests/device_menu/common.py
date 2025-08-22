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

from ... import translations as TR

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink
    from trezorlib.messages import Features

    from ...device_handler import BackgroundDeviceHandler

PIN4 = "1234"

REGULATORY_AREAS = [
    "United States",
    "Canada",
    "Europe / UK",
    "Australia / New Zealand",
    "Ukraine",
    "South Korea",
]


class Menu(Enum):
    ROOT = auto()
    CONNECTION = auto()
    SETTINGS = auto()
    SECURITY = auto()
    DEVICE = auto()
    PIN = auto()
    WIPE_CODE = auto()

    def path_from_root(self) -> list[str]:
        """
        Return the sequence of labels to click from ROOT to reach this Menu.
        """
        paths = {
            Menu.ROOT: [],
            Menu.CONNECTION: [TR.ble__pair_title],
            Menu.SETTINGS: [TR.words__settings],
            Menu.SECURITY: [TR.words__settings, TR.words__security],
            Menu.PIN: [TR.words__settings, TR.words__security, TR.pin__title],
            Menu.WIPE_CODE: [
                TR.words__settings,
                TR.words__security,
                TR.wipe_code__title,
            ],
            Menu.DEVICE: [TR.words__settings, TR.words__device],
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

        def root_content():
            content: list[str] = []
            if initialized and unfinished_backup:
                content.append(TR.homescreen__title_backup_failed)
            if initialized and not has_pin:
                content.append(TR.homescreen__title_pin_not_set)
            content.extend([TR.ble__pair_title, TR.words__settings])
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
            content.append(TR.reset__check_backup_title)
            return content

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
            content.extend(
                [TR.regulatory_certification__title, TR.words__about, TR.wipe__title]
            )
            return content

        def pin_content():
            if initialized and has_pin:
                return [TR.pin__change, TR.pin__remove]
            return None

        def wipe_code_content():
            if initialized and has_wipe_code:
                return [TR.wipe_code__change, TR.wipe_code__remove]
            return None

        lookup: dict["Menu", Callable[[], list[str] | None]] = {
            Menu.ROOT: root_content,
            Menu.CONNECTION: connection_content,
            Menu.SETTINGS: settings_content,
            Menu.SECURITY: security_content,
            Menu.DEVICE: device_content,
            Menu.PIN: pin_content,
            Menu.WIPE_CODE: wipe_code_content,
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
        if self == Menu.CONNECTION:
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
        assert len(matches) == 1
        start_idx = matches[0][0]

        # Follow the path
        for label in self.path_from_root()[start_idx:]:
            menu = debug.read_layout().vertical_menu_content()
            idx = menu.index(label)
            debug.button_actions.navigate_to_menu_item(idx)

        # After navigation, we should be at the target menu
        menu = debug.read_layout().vertical_menu_content()
        expected = self.content(features)
        if self == Menu.CONNECTION:
            # The connection menu has two permanent items at the end
            assert menu[-2:] == expected
        else:
            assert menu == expected
        return menu

    @classmethod
    def assert_menu_exists(cls, features: "Features"):
        """
        Assert that the menu content is as expected depending on the feature flags.
        """
        # Always exist
        assert Menu.ROOT.content(features)
        assert Menu.SETTINGS.content(features)
        assert Menu.CONNECTION.content(features)
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

        wipe_code = Menu.WIPE_CODE.content(features)
        if features.initialized and features.wipe_code_protection:
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

        root_child = cls.CONNECTION
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
                regulatory_idx = menu.index(TR.regulatory_certification__title)
                debug.button_actions.navigate_to_menu_item(regulatory_idx)
                debug.synchronize_at("RegulatoryScreen")
                layout = debug.read_layout()
                assert TR.regulatory_certification__title in layout.title()
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


def enter_pin(device_handler: "BackgroundDeviceHandler", pin: str = PIN4):
    debug = device_handler.debuglink()
    device_handler.get_session()
    debug.synchronize_at("PinKeyboard")
    debug.input(pin)
    device_handler.result()
