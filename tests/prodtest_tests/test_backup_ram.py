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

from . import PRODTEST_ERR_BACKUP_RAM_KEY_NOT_FOUND, assert_command_fails

# A key that is never provisioned, so a read of it always misses.
_UNUSED_KEY = "42"


@pytest.mark.requires_command(Cmd.BACKUP_RAM_LIST)
def test_backup_ram_list(client: ProdtestClient) -> None:
    """backup-ram-list should initialize backup RAM and succeed (even if empty)."""
    client.command_ok(ProdtestCommand(Cmd.BACKUP_RAM_LIST))


@pytest.mark.requires_command(Cmd.BACKUP_RAM_READ)
def test_backup_ram_read_missing_key(client: ProdtestClient) -> None:
    """Reading an unprovisioned key reports the dedicated 'key not found' error.

    A write→read round-trip cannot be exercised on the emulator: its
    backup_ram_write() is a no-op stub, so we only cover the read/miss path here.
    """
    resp = assert_command_fails(
        client, ProdtestCommand(Cmd.BACKUP_RAM_READ, _UNUSED_KEY)
    )
    assert resp.error_code == PRODTEST_ERR_BACKUP_RAM_KEY_NOT_FOUND
