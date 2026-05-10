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

from . import CLI_ERROR_INVALID_ARG, assert_command_fails


def test_display_border(client: ProdtestClient) -> None:
    """display-border should succeed with no arguments."""
    client.command_ok(ProdtestCommand(Cmd.DISPLAY_BORDER))


def test_display_text(client: ProdtestClient) -> None:
    """display-text should succeed rendering the given text."""
    client.command_ok(ProdtestCommand(Cmd.DISPLAY_TEXT, "prodtest"))


def test_display_bars(client: ProdtestClient) -> None:
    """display-bars should succeed rendering a valid RGBW color pattern."""
    client.command_ok(ProdtestCommand(Cmd.DISPLAY_BARS, "RGBW"))


def test_display_bars_warns_on_invalid_color(client: ProdtestClient) -> None:
    """display-bars accepts an invalid pattern but warns about it via a trace.

    The command is lenient — it still returns OK — but emits a diagnostic trace
    when the pattern contains characters outside RGBW/rgbw.
    """
    resp = client.command_ok(ProdtestCommand(Cmd.DISPLAY_BARS, "X"))
    assert resp.traces is not None
    assert any("Not valid color pattern" in line for line in resp.traces)


def test_display_set_backlight(client: ProdtestClient) -> None:
    """display-set-backlight should accept a level in the 0-255 range."""
    client.command_ok(ProdtestCommand(Cmd.DISPLAY_SET_BACKLIGHT, "128"))


def test_display_set_backlight_rejects_out_of_range(
    client: ProdtestClient,
) -> None:
    """A backlight level above 255 should be rejected."""
    resp = assert_command_fails(
        client, ProdtestCommand(Cmd.DISPLAY_SET_BACKLIGHT, "256")
    )
    assert resp.error_code == CLI_ERROR_INVALID_ARG
