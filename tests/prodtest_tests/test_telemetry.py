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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import re

import pytest

from trezorlib._internal.prodtest_client import Cmd, ProdtestClient, ProdtestCommand


@pytest.mark.requires_command(Cmd.TELEMETRY_READ)
def test_telemetry_read(client: ProdtestClient) -> None:
    """telemetry-read returns 'min_temp max_temp battery_errors battery_cycles'.

    Format is `%d %d 0x%02X %d`: the temperatures and cycle count are (possibly
    negative) integers, and the battery-error field is a hex bitmask.
    """
    resp = client.command_ok(ProdtestCommand(Cmd.TELEMETRY_READ))
    fields = resp.args.split()
    assert len(fields) == 4, f"unexpected telemetry format: {resp.args!r}"

    min_temp, max_temp, battery_errors, battery_cycles = fields
    int(min_temp)  # raises if not an integer
    int(max_temp)
    int(battery_cycles)
    assert re.fullmatch(r"0x[0-9A-Fa-f]+", battery_errors), battery_errors
