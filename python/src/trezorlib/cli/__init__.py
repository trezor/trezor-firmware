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

import functools
import sys

import click

from .. import exceptions
from ..client import TrezorClient
from ..transport import get_transport
from ..ui import ClickUI


class ChoiceType(click.Choice):
    def __init__(self, typemap):
        super().__init__(typemap.keys())
        self.typemap = typemap

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        return self.typemap[value]


class TrezorConnection:
    def __init__(self, path, session_id, passphrase_on_host):
        self.path = path
        self.session_id = session_id
        self.passphrase_on_host = passphrase_on_host

    def get_transport(self):
        try:
            # look for transport without prefix search
            return get_transport(self.path, prefix_search=False)
        except Exception:
            # most likely not found. try again below.
            pass

        # look for transport with prefix search
        # if this fails, we want the exception to bubble up to the caller
        return get_transport(self.path, prefix_search=True)

    def get_ui(self):
        return ClickUI(passphrase_on_host=self.passphrase_on_host)

    def get_client(self):
        transport = self.get_transport()
        ui = self.get_ui()
        return TrezorClient(transport, ui=ui, session_id=self.session_id)


def with_client(func):
    @click.pass_obj
    @functools.wraps(func)
    def trezorctl_command_with_client(obj, *args, **kwargs):
        try:
            client = obj.get_client()
        except Exception:
            click.echo("Failed to find a Trezor device.")
            if obj.path is not None:
                click.echo("Using path: {}".format(obj.path))
            sys.exit(1)

        try:
            return func(client, *args, **kwargs)
        except exceptions.Cancelled:
            click.echo("Action was cancelled.")
            sys.exit(1)
        except exceptions.TrezorException as e:
            raise click.ClickException(str(e)) from e

    return trezorctl_command_with_client
