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

import click

from .. import device
from . import with_session

if t.TYPE_CHECKING:
    from ..transport.session import Session

BATTERY_ERRORS = {
    0x01: "NTC disconnected",
    0x02: "Charging limited",
    0x04: "Temperature control active",
    0x08: "Battery disconnected",
    0x10: "Battery temperature jump detected",
    0x20: "Battery OCV jump detected",
}


@click.group(name="telemetry")
def cli() -> None:
    """Telemetry commands."""


@cli.command()
@with_session(seedless=True)
def get(session: Session) -> None:
    """Read telemetry data from the device."""
    res = device.get_telemetry(session)

    if res.min_temp_c is not None:
        click.echo(f"Min temperature: {res.min_temp_c / 1000:.2f} °C")
    if res.max_temp_c is not None:
        click.echo(f"Max temperature: {res.max_temp_c / 1000:.2f} °C")

    if res.battery_errors is not None:
        if res.battery_errors == 0:
            click.echo("Battery errors: None")
        else:
            click.echo("Battery errors:")
            for bit, name in BATTERY_ERRORS.items():
                if res.battery_errors & bit:
                    click.echo(f" - {name}")
