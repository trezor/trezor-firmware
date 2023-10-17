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

import functools
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import click

from .. import exceptions, transport
from ..client import TrezorClient
from ..ui import ClickUI, ScriptUI

if TYPE_CHECKING:
    # Needed to enforce a return value from decorators
    # More details: https://www.python.org/dev/peps/pep-0612/
    from typing import TypeVar

    from typing_extensions import Concatenate, ParamSpec

    from ..transport import Transport
    from ..ui import TrezorClientUI

    P = ParamSpec("P")
    R = TypeVar("R")


class ChoiceType(click.Choice):
    def __init__(self, typemap: Dict[str, Any], case_sensitive: bool = True) -> None:
        super().__init__(list(typemap.keys()))
        self.case_sensitive = case_sensitive
        if case_sensitive:
            self.typemap = typemap
        else:
            self.typemap = {k.lower(): v for k, v in typemap.items()}

    def convert(self, value: Any, param: Any, ctx: click.Context) -> Any:
        if value in self.typemap.values():
            return value
        value = super().convert(value, param, ctx)
        if isinstance(value, str) and not self.case_sensitive:
            value = value.lower()
        return self.typemap[value]


class TrezorConnection:
    def __init__(
        self,
        path: str,
        session_id: Optional[bytes],
        passphrase_on_host: bool,
        script: bool,
    ) -> None:
        self.path = path
        self.session_id = session_id
        self.passphrase_on_host = passphrase_on_host
        self.script = script

    def get_transport(self) -> "Transport":
        try:
            # look for transport without prefix search
            return transport.get_transport(self.path, prefix_search=False)
        except Exception:
            # most likely not found. try again below.
            pass

        # look for transport with prefix search
        # if this fails, we want the exception to bubble up to the caller
        return transport.get_transport(self.path, prefix_search=True)

    def get_ui(self) -> "TrezorClientUI":
        if self.script:
            # It is alright to return just the class object instead of instance,
            # as the ScriptUI class object itself is the implementation of TrezorClientUI
            # (ScriptUI is just a set of staticmethods)
            return ScriptUI
        else:
            return ClickUI(passphrase_on_host=self.passphrase_on_host)

    def get_client(self) -> TrezorClient:
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
        except transport.DeviceIsBusy:
            click.echo("Device is in use by another process.")
            sys.exit(1)
        except Exception:
            click.echo("Failed to find a Trezor device.")
            if self.path is not None:
                click.echo(f"Using path: {self.path}")
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


def with_client(func: "Callable[Concatenate[TrezorClient, P], R]") -> "Callable[P, R]":
    """Wrap a Click command in `with obj.client_context() as client`.

    Sessions are handled transparently. The user is warned when session did not resume
    cleanly. The session is closed after the command completes - unless the session
    was resumed, in which case it should remain open.
    """

    @click.pass_obj
    @functools.wraps(func)
    def trezorctl_command_with_client(
        obj: TrezorConnection, *args: "P.args", **kwargs: "P.kwargs"
    ) -> "R":
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

    # the return type of @click.pass_obj is improperly specified and pyright doesn't
    # understand that it converts f(obj, *args, **kwargs) to f(*args, **kwargs)
    return trezorctl_command_with_client  # type: ignore [cannot be assigned to return type]


class AliasedGroup(click.Group):
    """Command group that handles aliases and Click 6.x compatibility.

    Click 7.0 silently switched all underscore_commands to dash-commands.
    This implementation of `click.Group` responds to underscore_commands by invoking
    the respective dash-command.

    Supply an `aliases` dict at construction time to provide an alternative list of
    command names:

    >>> @click.command(cls=AliasedGroup, aliases={"do_bar", do_foo})
    >>> def cli():
    >>>     ...

    If these commands are not known at the construction time, they can be set later:

    >>> @click.command(cls=AliasedGroup)
    >>> def cli():
    >>>     ...
    >>>
    >>> @cli.command()
    >>> def do_foo():
    >>>     ...
    >>>
    >>> cli.aliases={"do_bar", do_foo}
    """

    def __init__(
        self,
        aliases: Optional[Dict[str, click.Command]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.aliases = aliases or {}

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        cmd_name = cmd_name.replace("_", "-")
        # try to look up the real name
        cmd = super().get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # look for a backwards compatibility alias
        if cmd_name in self.aliases:
            return self.aliases[cmd_name]

        return None
