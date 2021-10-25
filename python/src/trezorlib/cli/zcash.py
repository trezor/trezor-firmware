# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import click

from .. import zcash, messages, tools
from . import with_client

@click.group(name="zcash")
def cli():
    """Zcash commands."""


@cli.command()
@click.option("-i", "--ins",  required=False, default="0", help="Diag message instruction.")
@click.option("-d", "--data", required=False, default="hello", help="Diag message data.")
@with_client
def diag(client, ins, data):
    """Get Zcash diagnotic message."""
    return zcash.diag(client, int(ins), data.encode("utf-8"))

@cli.command()
@click.option(
    "-n",
    "--account",
    type=int,
    required=False,
    default=0,
    help="Account number. default = 0",
)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client, account, show_display):
    """Get Zcash diversified public address."""
    return zcash.get_address(client, account=account, show_display=show_display)    
