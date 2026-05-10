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

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestClient, ProdtestCommand


def test_cpuid_is_hex(client: ProdtestClient) -> None:
    """get-cpuid should return a non-empty, whole-byte hex string."""
    resp = client.command_ok(ProdtestCommand(Cmd.GET_CPUID))
    assert re.fullmatch(r"[0-9A-Fa-f]+", resp.args), f"Not a hex string: {resp.args}"
    assert len(resp.args) % 2 == 0, f"Not a whole number of bytes: {resp.args}"


def test_cpuid_is_stable(client: ProdtestClient) -> None:
    """get-cpuid should return the same value on repeated calls."""
    resp1 = client.command_ok(ProdtestCommand(Cmd.GET_CPUID))
    resp2 = client.command_ok(ProdtestCommand(Cmd.GET_CPUID))
    assert resp1.args == resp2.args
