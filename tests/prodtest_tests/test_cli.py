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

"""Tests for the CLI framework behaviour shared by all commands."""

from __future__ import annotations

from trezorlib._internal.prodtest_client import ProdtestClient, ProdtestCommand

from . import CLI_ERROR_INVALID_CMD, assert_command_fails


def test_unknown_command_rejected(client: ProdtestClient) -> None:
    """An unrecognized command name is rejected with INVALID_CMD."""
    resp = assert_command_fails(client, ProdtestCommand("no-such-command"))
    assert resp.error_code == CLI_ERROR_INVALID_CMD
