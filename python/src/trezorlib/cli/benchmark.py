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

from fnmatch import fnmatch
from typing import TYPE_CHECKING, List, Optional

import click

from .. import benchmark
from . import with_session

if TYPE_CHECKING:

    from ..transport.session import Session


def list_names_patern(session: "Session", pattern: Optional[str] = None) -> List[str]:
    names = list(benchmark.list_names(session).names)
    if pattern is None:
        return names
    return [name for name in names if fnmatch(name, pattern)]


@click.group(name="benchmark")
def cli() -> None:
    """Benchmark commands."""


@cli.command()
@click.argument("pattern", required=False)
@with_session(empty_passphrase=True)
def list_names(session: "Session", pattern: Optional[str] = None) -> None:
    """List names of all supported benchmarks"""
    names = list_names_patern(session, pattern)
    if len(names) == 0:
        click.echo("No benchmark satisfies the pattern.")
    else:
        for name in names:
            click.echo(name)


@cli.command()
@click.argument("pattern", required=False)
@with_session(empty_passphrase=True)
def run(session: "Session", pattern: Optional[str]) -> None:
    """Run benchmark"""
    names = list_names_patern(session, pattern)
    if len(names) == 0:
        click.echo("No benchmark satisfies the pattern.")
    else:
        for name in names:
            result = benchmark.run(session, name)
            click.echo(f"{name}: {result.value} {result.unit}")
