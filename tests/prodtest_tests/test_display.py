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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

from trezorlib._internal.prodtest_client import Cmd, ProdtestClient, ProdtestCommand

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


def test_display_shapes(client: ProdtestClient) -> None:
    """display-shapes should render at the default and at an explicit angle."""
    client.command_ok(ProdtestCommand(Cmd.DISPLAY_SHAPES))
    resp = client.command_ok(ProdtestCommand(Cmd.DISPLAY_SHAPES, "135"))
    assert resp.traces is not None
    assert any("Frame time" in line for line in resp.traces)


def test_display_shapes_rejects_out_of_range(client: ProdtestClient) -> None:
    """An angle of 360 degrees or more should be rejected."""
    resp = assert_command_fails(client, ProdtestCommand(Cmd.DISPLAY_SHAPES, "360"))
    assert resp.error_code == CLI_ERROR_INVALID_ARG


def test_display_shapes_spin(client: ProdtestClient) -> None:
    """display-shapes-spin should render a full turn and report frame times."""
    resp = client.command_ok(ProdtestCommand(Cmd.DISPLAY_SHAPES_SPIN, "45"))
    assert resp.traces is not None
    assert any("8 frames" in line for line in resp.traces)


def test_display_stripes(client: ProdtestClient) -> None:
    """display-stripes should animate the requested number of frames."""
    resp = client.command_ok(ProdtestCommand(Cmd.DISPLAY_STRIPES, "5", "7"))
    assert resp.traces is not None
    assert any("5 frames" in line for line in resp.traces)


def test_display_stripes_rejects_bad_speed(client: ProdtestClient) -> None:
    """display-stripes should reject a speed out of range."""
    resp = assert_command_fails(client, ProdtestCommand(Cmd.DISPLAY_STRIPES, "5", "0"))
    assert resp.error_code == CLI_ERROR_INVALID_ARG


def test_display_shapes_bench(client: ProdtestClient) -> None:
    """display-shapes-bench should report all measurements."""
    resp = client.command_ok(ProdtestCommand(Cmd.DISPLAY_SHAPES_BENCH))
    assert resp.traces is not None
    # 14 measurements, plus the CPU clock on hardware
    assert len(resp.traces) >= 14
