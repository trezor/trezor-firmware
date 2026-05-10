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

import pytest

from trezorlib._internal.prodtest_client import Cmd, ProdtestClient, ProdtestCommand

# Interactive touch commands (touch-test, touch-draw, ...) block waiting for
# physical input and are not exercised here; touch-version is a passive read.


@pytest.mark.requires_command(Cmd.TOUCH_VERSION)
def test_touch_version_is_integer(client: ProdtestClient) -> None:
    """touch-version should initialize the controller and return its version."""
    resp = client.command_ok(ProdtestCommand(Cmd.TOUCH_VERSION))
    assert resp.args.isdigit()
