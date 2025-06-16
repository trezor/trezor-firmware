# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING, Union

import click

from ..debuglink import TrezorClientDebugLink
from ..debuglink import optiga_set_sec_max as debuglink_optiga_set_sec_max
from ..debuglink import prodtest_t1 as debuglink_prodtest_t1
from ..debuglink import record_screen
from ..transport.session import Session
from . import with_session

if TYPE_CHECKING:
    from . import TrezorConnection


@click.group(name="debug")
def cli() -> None:
    """Miscellaneous debug features."""


@cli.command()
@click.argument("directory", required=False)
@click.option("-s", "--stop", is_flag=True, help="Stop the recording")
@click.pass_obj
def record(obj: "TrezorConnection", directory: Union[str, None], stop: bool) -> None:
    """Record screen changes into a specified directory.

    Recording can be stopped with `-s / --stop` option.
    """
    record_screen_from_connection(obj, None if stop else directory)


def record_screen_from_connection(
    obj: "TrezorConnection", directory: Union[str, None]
) -> None:
    """Record screen helper to transform TrezorConnection into TrezorClientDebugLink."""
    transport = obj.get_transport()
    debug_client = TrezorClientDebugLink(transport, auto_interact=False)
    record_screen(debug_client, directory, report_func=click.echo)
    debug_client.close_transport()


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
    debuglink_optiga_set_sec_max(session)
