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

import typing as t
from datetime import datetime
from pathlib import Path

import click

from ..client import Session
from ..debuglink import DebugLink
from ..debuglink import optiga_set_sec_max as debuglink_optiga_set_sec_max
from ..debuglink import prodtest_t1 as debuglink_prodtest_t1
from ..debuglink import set_log_filter as debuglink_set_log_filter
from ..transport import Timeout
from ..transport.udp import UdpTransport
from . import with_session

if t.TYPE_CHECKING:
    from ..transport import Transport
    from . import TrezorConnection


def _get_session_screenshot_dir(base_dir: Path) -> Path:
    """Create and return screenshot dir for the current session, according to datetime."""
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir = base_dir / timestamp_str
    ctr = 1
    while session_dir.exists() and any(session_dir.iterdir()):
        session_dir = base_dir / f"{timestamp_str}_{ctr}"
        ctr += 1

    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def record_screen(transport: Transport, base_dir: Path | None) -> None:
    """Record screen changes into a specified directory.

    Passing `None` as `directory` stops the recording.

    Creates subdirectories inside a specified directory, one for each session
    (for each new call of this function).
    (So that older screenshots are not overwritten by new ones.)

    Is available only for emulators, hardware devices are not capable of that.
    """
    if not isinstance(transport, UdpTransport):
        raise click.ClickException("Recording is only supported on emulator.")

    debug_transport = transport.find_debug()
    with debug_transport:
        try:
            debug_transport.wait_until_ready(timeout=1)
        except Timeout:
            raise click.ClickException("Debuglink is not responding.") from None

        debug = DebugLink(transport=debug_transport)

        if base_dir is None:
            debug.stop_recording()
            click.echo("Recording stopped.")
        else:
            current_session_dir = _get_session_screenshot_dir(base_dir)
            debug.start_recording(str(current_session_dir.resolve()))
            click.echo(f"Recording started into {current_session_dir}.")


@click.group(name="debug")
def cli() -> None:
    """Miscellaneous debug features."""


@cli.command()
@click.argument(
    "directory",
    required=False,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
@click.option("-s", "--stop", is_flag=True, help="Stop the recording")
@click.pass_obj
def record(obj: "TrezorConnection", directory: Path | None, stop: bool) -> None:
    """Record screen changes into a specified directory.

    Recording can be stopped with `-s / --stop` option.
    """
    if not stop and directory is None:
        raise click.ClickException("Specify either a directory path or --stop.")
    record_screen(obj.transport, None if stop else directory)


@cli.command()
@with_session(seedless=True)
def prodtest_t1(session: "Session") -> None:
    """Perform a prodtest on Model One.

    Only available on PRODTEST firmware and on T1B1. Formerly named self-test.
    """
    debuglink_prodtest_t1(session)


@cli.command()
@with_session(seedless=True)
def optiga_set_sec_max(session: "Session") -> None:
    """Set Optiga's security event counter to maximum."""
    debug_transport = session.client.transport.find_debug()
    debug_transport.open()
    debug = DebugLink(transport=debug_transport)
    debuglink_optiga_set_sec_max(debug)
    debug_transport.close()


@cli.command()
@click.argument("filter", required=False)
@with_session(seedless=True)
def set_log_filter(session: "Session", filter: str) -> None:
    """Set logging filter string."""
    debug_transport = session.client.transport.find_debug()
    debug_transport.open()
    debug = DebugLink(transport=debug_transport)
    debuglink_set_log_filter(debug, filter)
    debug_transport.close()


@cli.command()
@click.option(
    "--soc",
    type=click.IntRange(0, 100),
    default=None,
    help="State of charge percentage (0-100)",
)
@click.option(
    "--usb/--no-usb", "usb_connected", default=None, help="USB cable connected"
)
@click.option(
    "--wireless/--no-wireless",
    "wireless_connected",
    default=None,
    help="Wireless charger connected",
)
@click.option(
    "--ntc/--no-ntc", "ntc_connected", default=None, help="Temperature sensor connected"
)
@click.option(
    "--charging-limited/--no-charging-limited",
    default=None,
    help="Charging current is limited",
)
@click.option(
    "--temp-control/--no-temp-control",
    "temp_control_active",
    default=None,
    help="Temperature control active",
)
@click.option(
    "--battery/--no-battery",
    "battery_connected",
    default=None,
    help="Battery physically connected",
)
@with_session(seedless=True)
def set_battery_state(
    session: "Session",
    soc: int | None,
    usb_connected: bool | None,
    wireless_connected: bool | None,
    ntc_connected: bool | None,
    charging_limited: bool | None,
    temp_control_active: bool | None,
    battery_connected: bool | None,
) -> None:
    """Set emulated battery/power state (emulator only).

    All options are optional — only specified values are changed.
    Charging status and power status are derived from connection states.

    Examples:

      trezorctl debug set-battery-state --soc 50 --usb

      trezorctl debug set-battery-state --no-usb --wireless --soc 30

      trezorctl debug set-battery-state --no-battery
    """
    debug_transport = session.client.transport.find_debug()
    debug_transport.open()
    debug = DebugLink(transport=debug_transport)
    flags = dict(
        usb_connected=usb_connected,
        wireless_connected=wireless_connected,
        ntc_connected=ntc_connected,
        charging_limited=charging_limited,
        temp_control_active=temp_control_active,
        battery_connected=battery_connected,
    )
    debug.set_battery_state(soc=soc, **flags)
    debug_transport.close()

    parts = []
    if soc is not None:
        parts.append(f"soc={soc}%")

    if usb_connected is not None:
        parts.append(f"usb={'on' if usb_connected else 'off'}")
    for name, value in flags.items():
        if value is not None:
            parts.append(f"{name}={'on' if value else 'off'}")

    if parts:
        click.echo(f"Battery state updated: {', '.join(parts)}")
    else:
        click.echo("No battery state parameters specified. Nothing changed.")
