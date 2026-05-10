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

from trezorlib._internal.prodtest_client import (
    Cmd,
    ProdtestClient,
    ProdtestCommand,
    ResponseNotOkError,
)

from . import PRODTEST_ERR_OTP_EMPTY


def test_otp_variant_read(client: ProdtestClient) -> None:
    """otp-variant-read returns the block as a list of byte values (0-255)."""
    resp = client.command_ok(ProdtestCommand(Cmd.OTP_VARIANT_READ))
    values = resp.args.split()
    assert values, "expected at least one byte value"
    assert all(v.isdigit() and 0 <= int(v) <= 255 for v in values)


@pytest.mark.parametrize("cmd", [Cmd.OTP_BATCH_READ, Cmd.OTP_DEVICE_SN_READ])
def test_otp_text_block_read(client: ProdtestClient, cmd: str) -> None:
    """A text OTP block is either populated (OK) or reported empty.

    On an unprovisioned (emulator) device the block is blank, so the command
    fails with the dedicated 'OTP block is empty' error rather than a generic
    read failure.
    """
    try:
        resp = client.command_ok(ProdtestCommand(cmd))
        assert resp.args
    except ResponseNotOkError as exc:
        assert exc.response
        assert exc.response.error_code == PRODTEST_ERR_OTP_EMPTY
