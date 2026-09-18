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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent

KEYBOARD_COMPONENTS = ("MnemonicKeyboard", "Slip39Keyboard")
MAX_ATTEMPTS = 10


def layout_has_keyboard(layout: "LayoutContent") -> bool:
    components = layout.all_components()
    if any(name in components for name in KEYBOARD_COMPONENTS):
        return True
    return any(name in layout.json_str for name in KEYBOARD_COMPONENTS)


def navigate_to_keyboard(debug: "DebugLink") -> "LayoutContent":
    layout = debug.read_layout()

    for _ in range(MAX_ATTEMPTS):
        if layout_has_keyboard(layout):
            return layout
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()

    raise RuntimeError(
        f"Keyboard not found after {MAX_ATTEMPTS} attempts. "
        f"Expected one of: {', '.join(KEYBOARD_COMPONENTS)}"
    )
