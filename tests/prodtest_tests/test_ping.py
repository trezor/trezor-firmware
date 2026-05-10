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


def test_ping_no_args(prodtest_client: ProdtestClient) -> None:
    """ping with no arguments should return OK with empty args."""
    resp = prodtest_client.command_ok(ProdtestCommand(Cmd.PING))
    assert resp.args == ""


def test_ping_with_text(prodtest_client: ProdtestClient) -> None:
    """ping should echo back the provided text."""
    resp = prodtest_client.command_ok(ProdtestCommand(Cmd.PING, "hello"))
    assert resp.is_ok
    assert resp.args == "hello"
