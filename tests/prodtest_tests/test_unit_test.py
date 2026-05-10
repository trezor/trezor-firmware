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


def test_unit_test_list(client: ProdtestClient) -> None:
    """unit-test-list should succeed and emit a listing header trace."""
    resp = client.command_ok(ProdtestCommand(Cmd.UNIT_TEST_LIST))
    assert resp.traces is not None
    assert any("registered unit tests" in line for line in resp.traces)


def test_unit_test_run(client: ProdtestClient) -> None:
    """unit-test-run should run all registered on-device unit tests and pass.

    The command returns OK only if every unit test passes; a failure surfaces
    here as a non-OK response.
    """
    resp = client.command_ok(ProdtestCommand(Cmd.UNIT_TEST_RUN))
    assert resp.traces is not None
    assert not any("FAILED" in line for line in resp.traces)
