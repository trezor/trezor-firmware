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

from trezorlib._internal.prodtest_client import Cmd, ProdtestClient, ProdtestCommand


def test_ping_no_args(client: ProdtestClient) -> None:
    """ping with no arguments should return OK with empty args."""
    resp = client.command_ok(ProdtestCommand(Cmd.PING))
    assert resp.args == ""


def test_ping_with_text(client: ProdtestClient) -> None:
    """ping should echo back the provided text."""
    resp = client.command_ok(ProdtestCommand(Cmd.PING, "hello"))
    assert resp.args == "hello"


def test_ping_with_long_text(client: ProdtestClient) -> None:
    """ping echoes text up to the CLI line buffer, truncating anything beyond."""
    long_text = 512 * "longtext"
    resp = client.command_ok(ProdtestCommand(Cmd.PING, long_text))
    assert resp.args == long_text
    too_long_text = long_text + "A"
    resp = client.command_ok(ProdtestCommand(Cmd.PING, too_long_text))
    assert resp.args == long_text
