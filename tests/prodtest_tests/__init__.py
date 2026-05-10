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

from trezorlib.prodtest.prodtest_client import (
    ProdtestClient,
    ProdtestCommand,
    ProdtestResponse,
    ResponseNotOkError,
)

# CLI framework codes — core/embed/rtl/inc/rtl/cli.h
CLI_ERROR_INVALID_CMD = 10
CLI_ERROR_INVALID_ARG = 11
CLI_ERROR_INVALID_CRC = 14

# Prodtest command codes — core/embed/projects/prodtest/prodtest_error_codes.h
PRODTEST_ERR_BACKUP_RAM_KEY_NOT_FOUND = 1014
PRODTEST_ERR_OTP_EMPTY = 10012
PRODTEST_ERR_TROPIC_UPDATE_WRONG_REVISION = 20075
PRODTEST_ERR_TROPIC_TEST_RNG_REPEAT = 20152


def assert_command_fails(
    client: ProdtestClient, command: ProdtestCommand
) -> ProdtestResponse:
    """Run a command expected to fail and return its error response.

    Wraps the common negative-path boilerplate: the command must raise
    ResponseNotOkError carrying a response, which is returned so the caller can
    assert on error_code / args.
    """
    with pytest.raises(ResponseNotOkError) as exc_info:
        client.command_ok(command)
    response = exc_info.value.response
    assert response is not None
    return response


def assert_hexdata(response: ProdtestResponse, num_bytes: int | None = None) -> bytes:
    """Assert the response args are `cli_ok_hexdata` output and return the bytes.

    The device formats binary payloads as an even-length run of uppercase hex
    digits (see `cli_ok_hexdata`). This checks the args are valid, non-empty hex
    and — when *num_bytes* is given — of the expected length, then returns the
    decoded bytes for any further, non-fragile structural checks. It deliberately
    does not compare the value itself, which is device-specific.
    """
    args = response.args
    assert args, "expected hex data, got empty response"
    try:
        data = bytes.fromhex(args)
    except ValueError:
        raise AssertionError(f"response is not valid hex data: {args!r}")
    if num_bytes is not None:
        assert (
            len(data) == num_bytes
        ), f"expected {num_bytes} bytes of hex data, got {len(data)}: {args!r}"
    return data
