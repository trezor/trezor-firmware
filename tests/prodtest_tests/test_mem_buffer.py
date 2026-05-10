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


def test_write_and_read_back(client: ProdtestClient) -> None:
    """Data written with mem-write should be returned verbatim by mem-read."""
    hexdata = "DEADBEEF01020304"
    client.command_ok(ProdtestCommand(Cmd.PRODTEST_MEM_WRITE, hexdata))

    resp = client.command_ok(ProdtestCommand(Cmd.PRODTEST_MEM_READ))
    assert resp.args.upper() == hexdata.upper()
