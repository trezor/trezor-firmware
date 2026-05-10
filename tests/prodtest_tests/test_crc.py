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

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestClient, ProdtestCommand

from . import CLI_ERROR_INVALID_CRC


def test_crc_status_returns_0_or_1(client: ProdtestClient) -> None:
    """crc-status should return '0' or '1'."""
    resp = client.command_ok(ProdtestCommand(Cmd.CRC_STATUS))
    assert resp.args in ("0", "1")


def test_crc_enable_disable_cycle(client: ProdtestClient) -> None:
    """Enabling then disabling CRC should leave it disabled."""
    try:
        client.command_ok(ProdtestCommand(Cmd.CRC_ENABLE))
        assert client.crc_enabled
        assert client.command_ok(ProdtestCommand(Cmd.CRC_STATUS)).args == "1"

        client.command_ok(ProdtestCommand(Cmd.CRC_DISABLE))
        assert not client.crc_enabled
        assert client.command_ok(ProdtestCommand(Cmd.CRC_STATUS)).args == "0"
    finally:
        if client.crc_enabled:
            client.command_ok(ProdtestCommand(Cmd.CRC_DISABLE))


def test_crc_rejects_bad_checksum(client: ProdtestClient) -> None:
    """A `checked-` command with a wrong CRC is rejected with INVALID_CRC.

    The per-command `checked-` prefix validates a CRC without enabling global
    CRC, so no device state lingers. The rejection response carries no CRC
    suffix, so we read it directly off the transport rather than via command().
    """
    client.transport.writeline("checked-ping deadbeef")
    line = client.transport.readline(client.DEFAULT_TIMEOUT)
    assert line.startswith("ERROR"), line
    assert int(line.split()[1]) == CLI_ERROR_INVALID_CRC
