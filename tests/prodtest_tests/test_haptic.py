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

from . import CLI_ERROR_INVALID_ARG, assert_command_fails


@pytest.mark.requires_command(Cmd.HAPTIC_TEST)
@pytest.mark.parametrize("amplitude", ["", "0", "50", "100"])
def test_haptic_test_runs(client: ProdtestClient, amplitude: str) -> None:
    """haptic-test should run a short feedback pulse and succeed."""
    client.command_ok(ProdtestCommand(Cmd.HAPTIC_TEST, "1", amplitude))


@pytest.mark.requires_command(Cmd.HAPTIC_TEST)
@pytest.mark.parametrize("amplitude", ["-50", "-1", "101", "10000"])
def test_haptic_test_rejects_bad_amplitude(
    client: ProdtestClient, amplitude: str
) -> None:
    """haptic-test should reject an amplitude below 0 / above 100."""
    resp = assert_command_fails(
        client, ProdtestCommand(Cmd.HAPTIC_TEST, "1", amplitude)
    )
    assert resp.error_code == CLI_ERROR_INVALID_ARG
