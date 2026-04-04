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

"""UI tests for the fuel gauge (battery indicator) on the Eckhart homescreen.

Each test sets an emulated battery state and captures the homescreen appearance
via the screen-recording infrastructure (--ui=record / --ui=test).
"""

import pytest

from trezorlib.debuglink import DebugSession as Session

# T3W1 (TS7) only - the only model with a fuel gauge on homescreen
pytestmark = [pytest.mark.models("t3w1"), pytest.mark.emulator]

# SOC boundary values that map to distinct battery icons in the UI:
#   <  10 % - EMPTY  (red)
#   10-19 % - LOW    (yellow)
#   20-39 % - MID_MINUS (grey)
#   40-89 % - MID_PLUS  (grey)
#   ≥  90 % - FULL   (grey)
SOC_LEVELS = [5, 15, 25, 50, 95]


@pytest.mark.setup_client(pin=None)
def test_fuel_gauge(session: Session) -> None:
    """Homescreen shows the correct battery icon for each SOC threshold and charging state."""
    layout = session.debug.read_layout()
    assert layout.main_component() == "Homescreen"

    try:
        # start at default state (usb disconnected = discharging)
        session.debug.set_battery_state(soc=100, usb_connected=False)

        for soc in SOC_LEVELS:
            session.debug.set_battery_state(soc=soc)
            layout = session.debug.read_layout()
            assert layout.main_component() == "Homescreen"
            assert layout.find_unique_value_by_key("soc", -1, int) == soc

        for usb_connected in [True, False]:
            session.debug.set_battery_state(soc=50, usb_connected=usb_connected)
            layout = session.debug.read_layout()
            assert layout.main_component() == "Homescreen"
            assert layout.find_unique_value_by_key("soc", -1, int) == 50
    finally:
        # restore default state
        session.debug.set_battery_state(soc=100, usb_connected=False)
