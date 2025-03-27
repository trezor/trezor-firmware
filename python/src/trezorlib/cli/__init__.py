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

from __future__ import annotations

import atexit
import functools
import logging
import os
import sys
import typing as t
from contextlib import contextmanager

import click

from .. import exceptions, transport, ui
from ..client import PASSPHRASE_ON_DEVICE, ProtocolVersion, TrezorClient
from ..messages import Capability
from ..transport import Transport
from ..transport.session import Session, SessionV1

LOG = logging.getLogger(__name__)

_TRANSPORT: Transport | None = None

if t.TYPE_CHECKING:
    # Needed to enforce a return value from decorators
    # More details: https://www.python.org/dev/peps/pep-0612/

    from typing_extensions import Concatenate, ParamSpec

    P = ParamSpec("P")
    R = t.TypeVar("R")
    FuncWithSession = t.Callable[Concatenate[Session, P], R]


class ChoiceType(click.Choice):

    def __init__(
        self, typemap: t.Dict[str, t.Any], case_sensitive: bool = True
    ) -> None:
        super().__init__(list(typemap.keys()))
        self.case_sensitive = case_sensitive
        if case_sensitive:
            self.typemap = typemap
        else:
            self.typemap = {k.lower(): v for k, v in typemap.items()}

    def convert(self, value: t.Any, param: t.Any, ctx: click.Context) -> t.Any:
        if value in self.typemap.values():
            return value
        value = super().convert(value, param, ctx)
        if isinstance(value, str) and not self.case_sensitive:
            value = value.lower()
        return self.typemap[value]


def get_passphrase(
    available_on_device: bool, passphrase_on_host: bool
) -> t.Union[str, object]:
    if available_on_device and not passphrase_on_host:
        return PASSPHRASE_ON_DEVICE

    env_passphrase = os.getenv("PASSPHRASE")
    if env_passphrase is not None:
        ui.echo("Passphrase required. Using PASSPHRASE environment variable.")
        return env_passphrase

    while True:
        try:
            passphrase = ui.prompt(
                "Passphrase required",
                hide_input=True,
                default="",
                show_default=False,
            )
            # In case user sees the input on the screen, we do not need confirmation
            if not ui.CAN_HANDLE_HIDDEN_INPUT:
                return passphrase
            second = ui.prompt(
                "Confirm your passphrase",
                hide_input=True,
                default="",
                show_default=False,
            )
            if passphrase == second:
                return passphrase
            else:
                ui.echo("Passphrase did not match. Please try again.")
        except click.Abort:
            raise exceptions.Cancelled from None


def get_client(transport: Transport) -> TrezorClient:
    return TrezorClient(transport)


class TrezorConnection:

    def __init__(
        self,
        path: str,
        session_id: bytes | None,
        passphrase_on_host: bool,
        script: bool,
    ) -> None:
        self.path = path
        self.session_id = session_id
        self.passphrase_on_host = passphrase_on_host
        self.script = script

    def get_session(
        self,
        derive_cardano: bool = False,
        empty_passphrase: bool = False,
        must_resume: bool = False,
    ) -> Session:
        client = self.get_client()
        if must_resume and self.session_id is None:
            click.echo("Failed to resume session - no session id provided")
            raise RuntimeError("Failed to resume session - no session id provided")

        # Try resume session from id
        if self.session_id is not None:
            if client.protocol_version is ProtocolVersion.V1:
                session = SessionV1.resume_from_id(
                    client=client, session_id=self.session_id
                )
            else:
                raise Exception("Unsupported client protocol", client.protocol_version)
            if must_resume:
                if session.id != self.session_id or session.id is None:
                    click.echo("Failed to resume session")
                    env_var = os.environ.get("TREZOR_SESSION_ID")
                    if env_var and bytes.fromhex(env_var) == self.session_id:
                        click.echo(
                            "Session-id stored in TREZOR_SESSION_ID is no longer valid. Call 'unset TREZOR_SESSION_ID' to clear it."
                        )
                    raise exceptions.FailedSessionResumption(
                        received_session_id=session.id
                    )
            return session

        features = client.protocol.get_features()

        passphrase_protection = features.passphrase_protection
        if passphrase_protection is None:
            raise RuntimeError("Device is locked")

        if not passphrase_protection:
            return client.get_session(derive_cardano=derive_cardano)

        if empty_passphrase:
            passphrase = ""
        elif self.script:
            passphrase = None
        else:
            available_on_device = Capability.PassphraseEntry in features.capabilities
            passphrase = get_passphrase(available_on_device, self.passphrase_on_host)
        session = client.get_session(
            passphrase=passphrase, derive_cardano=derive_cardano
        )
        return session

    def get_transport(self) -> "Transport":
        global _TRANSPORT
        if _TRANSPORT is not None:
            return _TRANSPORT

        try:
            # look for transport without prefix search
            _TRANSPORT = transport.get_transport(self.path, prefix_search=False)
        except Exception:
            # most likely not found. try again below.
            pass

        # look for transport with prefix search
        # if this fails, we want the exception to bubble up to the caller
        if not _TRANSPORT:
            _TRANSPORT = transport.get_transport(self.path, prefix_search=True)

        _TRANSPORT.open()
        atexit.register(_TRANSPORT.close)
        return _TRANSPORT

    def get_client(self) -> TrezorClient:
        client = get_client(self.get_transport())
        if self.script:
            client.button_callback = ui.ScriptUI.button_request
            client.pin_callback = ui.ScriptUI.get_pin
        else:
            click_ui = ui.ClickUI()
            client.button_callback = click_ui.button_request
            client.pin_callback = click_ui.get_pin
        return client

    def get_seedless_session(self) -> Session:
        client = self.get_client()
        seedless_session = client.get_seedless_session()
        return seedless_session

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

    @contextmanager
    def session_context(
        self,
        empty_passphrase: bool = False,
        derive_cardano: bool = False,
        seedless: bool = False,
        must_resume: bool = False,
    ):
        """Get a session instance as a context manager. Handle errors in a manner
        appropriate for end-users.

        Usage:
        >>> with obj.session_context() as session:
        >>>     do_your_actions_here()
        """
        try:
            if seedless:
                session = self.get_seedless_session()
            else:
                session = self.get_session(
                    derive_cardano=derive_cardano,
                    empty_passphrase=empty_passphrase,
                    must_resume=must_resume,
                )
        except transport.DeviceIsBusy:
            click.echo("Device is in use by another process.")
            sys.exit(1)
        except exceptions.FailedSessionResumption:
            sys.exit(1)
        except Exception:
            click.echo("Failed to find a Trezor device.")
            if self.path is not None:
                click.echo(f"Using path: {self.path}")
            sys.exit(1)

        try:
            yield session
        except exceptions.Cancelled:
            # handle cancel action
            click.echo("Action was cancelled.")
            sys.exit(1)
        except exceptions.TrezorException as e:
            # handle any Trezor-sent exceptions as user-readable
            raise click.ClickException(str(e)) from e
            # other exceptions may cause a traceback


def with_session(
    func: "t.Callable[Concatenate[Session, P], R]|None" = None,
    *,
    empty_passphrase: bool = False,
    derive_cardano: bool = False,
    seedless: bool = False,
    must_resume: bool = False,
) -> t.Callable[[FuncWithSession], t.Callable[P, R]]:
    """Provides a Click command with parameter `session=obj.get_session(...)`
    based on the parameters provided.

    If default parameters are ok, this decorator can be used without parentheses.
    """

    def decorator(
        func: FuncWithSession,
    ) -> "t.Callable[P, R]":

        @click.pass_obj
        @functools.wraps(func)
        def function_with_session(
            obj: TrezorConnection, *args: "P.args", **kwargs: "P.kwargs"
        ) -> "R":
            is_resume_mandatory = must_resume or obj.session_id is not None

            with obj.session_context(
                empty_passphrase=empty_passphrase,
                derive_cardano=derive_cardano,
                seedless=seedless,
                must_resume=is_resume_mandatory,
            ) as session:
                try:
                    return func(session, *args, **kwargs)

                finally:
                    if not is_resume_mandatory:
                        session.end()

        return function_with_session

    # If the decorator @get_session is used without parentheses
    if func and callable(func):
        return decorator(func)  # type: ignore [Function return type]

    return decorator


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
        aliases: t.Dict[str, click.Command] | None = None,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.aliases = aliases or {}

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        cmd_name = cmd_name.replace("_", "-")
        # try to look up the real name
        cmd = super().get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # look for a backwards compatibility alias
        if cmd_name in self.aliases:
            return self.aliases[cmd_name]

        return None
