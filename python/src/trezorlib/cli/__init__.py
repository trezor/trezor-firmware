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
from contextlib import contextmanager

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

    @contextmanager
    def client_context(self):
        """Get a client instance as a context manager. Handle errors in a manner
        appropriate for end-users.

        Usage:
        >>> with obj.client_context() as client:
        >>>     do_your_actions_here()
        """
        try:
            client = self.get_client()
        except Exception:
            click.echo("Failed to find a Trezor device.")
            if self.path is not None:
                click.echo("Using path: {}".format(self.path))
            sys.exit(1)

        try:
            yield client
        except exceptions.Cancelled:
            # handle cancel action
            click.echo("Action was cancelled.")
            sys.exit(1)
        except exceptions.TrezorException as e:
            # handle any Trezor-sent exceptions as user-readable
            raise click.ClickException(str(e)) from e
            # other exceptions may cause a traceback


def with_client(func):
    """Wrap a Click command in `with obj.client_context() as client`.

    Sessions are handled transparently. The user is warned when session did not resume
    cleanly. The session is closed after the command completes - unless the session
    was resumed, in which case it should remain open.
    """

    @click.pass_obj
    @functools.wraps(func)
    def trezorctl_command_with_client(obj, *args, **kwargs):
        with obj.client_context() as client:
            session_was_resumed = obj.session_id == client.session_id
            if not session_was_resumed and obj.session_id is not None:
                # tried to resume but failed
                click.echo("Warning: failed to resume session.", err=True)

            try:
                return func(client, *args, **kwargs)
            finally:
                if not session_was_resumed:
                    try:
                        client.end_session()
                    except Exception:
                        pass

    return trezorctl_command_with_client
