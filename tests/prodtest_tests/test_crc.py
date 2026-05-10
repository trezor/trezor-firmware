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

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestClient, ProdtestCommand


def test_crc_status_returns_0_or_1(prodtest_client: ProdtestClient) -> None:
    """crc-status should return '0' or '1'."""
    resp = prodtest_client.command_ok(ProdtestCommand(Cmd.CRC_STATUS))
    assert resp.args in ("0", "1")


def test_crc_enable_disable_cycle(prodtest_client: ProdtestClient) -> None:
    """Enabling then disabling CRC should leave it disabled."""
    pytest.xfail("Running CRC test breaks the test suite. TODO fix")
    prodtest_client.command_ok(ProdtestCommand(Cmd.CRC_ENABLE))
    assert prodtest_client.command_ok(ProdtestCommand(Cmd.CRC_STATUS)).args == "1"

    prodtest_client.command_ok(ProdtestCommand(Cmd.CRC_DISABLE))
    assert prodtest_client.command_ok(ProdtestCommand(Cmd.CRC_STATUS)).args == "0"
