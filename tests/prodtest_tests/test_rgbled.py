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

import typing as t

import pytest

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestClient, ProdtestCommand

from . import CLI_ERROR_INVALID_ARG, assert_command_fails


@pytest.fixture(autouse=True)
def _restore_rgbled(
    client: ProdtestClient, available_commands: set[str]
) -> t.Iterator[None]:
    """Leave the RGB LED as it was on entry (off) after each test.

    These tests share the session emulator, and — with tests running in random
    order — must not leave the LED lit for whatever runs next. The prodtest main
    loop turns the LED off and disables automatic control once its start-up
    animation finishes, so ``off`` is the state tests see on entry. There is no
    command to read the current color, so we reset to off (0, 0, 0) to match it.
    """
    yield
    if Cmd.RGBLED_SET in available_commands:
        client.command_ok(ProdtestCommand(Cmd.RGBLED_SET, "0", "0", "0"))


@pytest.mark.requires_command(Cmd.RGBLED_SET)
@pytest.mark.parametrize(
    ("r", "g", "b"),
    [
        ("0", "255", "0"),
        ("0", "0", "255"),
        ("255", "0", "0"),
        ("255", "255", "255"),
        ("15", "55", "129"),
    ],
)
def test_rgbled_set(client: ProdtestClient, r: str, g: str, b: str) -> None:
    """rgbled-set should accept an R/G/B triple in the 0-255 range."""
    client.command_ok(ProdtestCommand(Cmd.RGBLED_SET, r, g, b))


@pytest.mark.parametrize(
    ("r", "g", "b"),
    [("0", "256", "0"), ("-1", "0", "0"), ("-15", "55", "129")],
)
@pytest.mark.requires_command(Cmd.RGBLED_SET)
def test_rgbled_set_rejects_out_of_range(
    client: ProdtestClient, r: str, g: str, b: str
) -> None:
    """rgbled-set should reject a channel value above 255."""
    resp = assert_command_fails(
        client, ProdtestCommand(Cmd.RGBLED_SET, "256", "0", "0")
    )
    assert resp.error_code == CLI_ERROR_INVALID_ARG


@pytest.mark.requires_command(Cmd.RGBLED_EFFECT_START, Cmd.RGBLED_EFFECT_STOP)
def test_rgbled_effect_start_stop(client: ProdtestClient) -> None:
    """An RGB LED effect should start and stop successfully."""
    client.command_ok(ProdtestCommand(Cmd.RGBLED_EFFECT_START, "0"))
    client.command_ok(ProdtestCommand(Cmd.RGBLED_EFFECT_STOP))
