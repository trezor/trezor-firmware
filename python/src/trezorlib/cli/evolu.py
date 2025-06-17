# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from .. import evolu, messages
from . import with_session

if t.TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="evolu")
def cli() -> None:
    """Evolu commands. Evolu is a local first storage framework. See https://github.com/evoluhq/evolu"""


@cli.command()
@with_session
def get_node(
    session: "Session",
) -> dict[str, str]:
    """Return the SLIP-21 node for Evolu."""

    node: messages.EvoluNode = evolu.get_evolu_node(
        session,
    )
    return {
        "data": node.data.hex(),
    }
