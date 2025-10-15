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

import functools
import logging
import os
import re
import sys
import typing as t
from contextlib import contextmanager
from enum import Enum

import click

from .. import exceptions, protocol_v1, transport, ui
from ..client import (
    AppManifest,
    PassphraseSetting,
    Session,
    TrezorClient,
    get_client,
    get_default_session,
)
from ..thp import client as thp_client
from ..transport import Transport
from . import credentials

LOG = logging.getLogger(__name__)

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

    def convert(self, value: t.Any, param: t.Any, ctx: click.Context | None) -> t.Any:
        if value in self.typemap.values():
            return value
        value = super().convert(value, param, ctx)
        if isinstance(value, str) and not self.case_sensitive:
            value = value.lower()
        return self.typemap[value]


class PassphraseSource(Enum):
    AUTO = "auto"
    PROMPT = "prompt"
    EMPTY = "empty"
    DEVICE = "device"

    def ok_if_disabled(self) -> bool:
        return self in (self.AUTO, self.EMPTY)


def get_passphrase() -> str:
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


def get_code_entry_code() -> str:
    while True:
        try:
            code_input = ui.prompt(
                "Enter code from Trezor",
                hide_input=False,
                default="",
                show_default=False,
            )

            # Keep only digits 0-9, ignore all other symbols
            code_str = re.sub(r"\D", "", code_input)

            if len(code_str) != 6:
                ui.echo("Code must be 6-digits long.")
                continue
            return code_str
        except click.Abort:
            raise exceptions.Cancelled from None


class TrezorConnection:
    def __init__(
        self,
        path: str,
        session_id: str | None,
        passphrase_source: PassphraseSource,
        script: bool,
        *,
        app_name: str = "trezorctl",
    ) -> None:
        self.path = path
        self.session_id = session_id
        self.passphrase_source = passphrase_source
        self.script = script
        self.credentials = credentials.CredentialStore(app_name)
        self.app = AppManifest(app_name=app_name, credentials=self.credentials.list)
        if self.script:
            self.app.button_callback = ui.ScriptUI.button_request
            self.app.pin_callback = ui.ScriptUI.get_pin
        else:
            click_ui = ui.ClickUI()
            self.app.button_callback = click_ui.button_request
            self.app.pin_callback = click_ui.get_pin

    def get_session(
        self,
        use_passphrase: bool = True,
        seedless: bool = False,
        derive_cardano: bool = False,
    ) -> Session:
        client = self.get_client()
        client.ensure_unlocked()
        if (
            not client.features.passphrase_protection
            and not self.passphrase_source.ok_if_disabled()
        ):
            raise click.ClickException("Passphrase protection is not enabled")

        # if empty passphrase is requested, do not try to resume and instead
        # create a new session
        if not use_passphrase or self.passphrase_source == PassphraseSource.EMPTY:
            return client.get_session(passphrase=PassphraseSetting.STANDARD_WALLET)
        if seedless:
            return client.get_session(passphrase=None)

        # Try resume session from id
        if self.session_id is not None:
            try:
                if isinstance(client, protocol_v1.TrezorClientV1):
                    session = protocol_v1.SessionV1(
                        client, id=bytes.fromhex(self.session_id)
                    )
                    session.initialize()
                elif isinstance(client, thp_client.TrezorClientThp):
                    session = thp_client.ThpSession(client, id=int(self.session_id))
                    # TODO what here?
                else:
                    raise click.ClickException(
                        f"Unsupported client type: {type(client).__name__}"
                    )
            except exceptions.InvalidSessionError:
                LOG.error("Failed to resume session", exc_info=True)
                env_var = os.environ.get("TREZOR_SESSION_ID")
                if env_var != self.session_id:
                    click.echo(
                        "Session-id stored in TREZOR_SESSION_ID is no longer valid. Call\n"
                        "  unset TREZOR_SESSION_ID\n"
                        "to clear it."
                    )
                raise
            else:
                return session

        if self.passphrase_source == PassphraseSource.PROMPT:
            passphrase = get_passphrase()
            return client.get_session(passphrase=passphrase)
        if self.passphrase_source == PassphraseSource.DEVICE:
            return client.get_session(passphrase=PassphraseSetting.ON_DEVICE)
        if self.passphrase_source == PassphraseSource.AUTO:
            return get_default_session(client, derive_cardano=derive_cardano)
        raise NotImplementedError(
            f"Passphrase source {self.passphrase_source} not implemented"
        )

    def get_transport(self) -> Transport:
        try:
            # look for transport without prefix search
            return transport.get_transport(self.path, prefix_search=False)
        except Exception:
            # most likely not found. try again below.
            pass

        # look for transport with prefix search
        # if this fails, we want the exception to bubble up to the caller
        return transport.get_transport(self.path, prefix_search=True)

    def get_client(self) -> TrezorClient:
        client = get_client(self.app, self.get_transport())
        if not client.pairing.is_paired():
            from ..thp import pairing

            credential = pairing.default_pairing_flow(
                client.pairing, code_entry_callback=get_code_entry_code
            )
            if credential is not None:
                self.credentials.add(credential)

        return client

    def _connection_context(
        self,
        connect_fn: t.Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> t.Generator[R, None, None]:
        try:
            conn = connect_fn(*args, **kwargs)
        except Exception as e:
            self._print_exception(e, "Failed to connect")
            sys.exit(1)

        try:
            yield conn
        except exceptions.Cancelled:
            # handle cancel action
            click.echo("Action was cancelled.")
            sys.exit(1)
        except exceptions.TrezorException as e:
            # handle any Trezor-sent exceptions as user-readable
            raise click.ClickException(str(e)) from e
            # other exceptions may cause a traceback

    @contextmanager
    def client_context(self) -> t.Generator[TrezorClient, None, None]:
        """Get a client instance as a context manager. Handle errors in a manner
        appropriate for end-users.

        Usage:
        >>> with obj.client_context() as client:
        >>>     do_your_actions_here()
        """
        yield from self._connection_context(self.get_client)

    @contextmanager
    def session_context(
        self,
        *,
        use_passphrase: bool = True,
        derive_cardano: bool = False,
        seedless: bool = False,
    ) -> t.Generator[Session, None, None]:
        yield from self._connection_context(
            self.get_session,
            use_passphrase=use_passphrase,
            derive_cardano=derive_cardano,
            seedless=seedless,
        )

    def _print_exception(self, exc: Exception, message: str) -> None:
        LOG.debug(message, exc_info=True)
        message = f"{message}: {exc.__class__.__name__}"
        if description := str(exc):
            message = f"{message} ({description})"

        click.echo(message)
        if self.path is not None:
            click.echo(f"Using path: {self.path}")


@t.overload
def with_session(func: t.Callable[Concatenate[Session, P], R]) -> t.Callable[P, R]: ...


@t.overload
def with_session(
    *,
    passphrase: bool = True,
    cardano: bool = False,
    seedless: bool = False,
) -> t.Callable[[FuncWithSession[P, R]], t.Callable[P, R]]: ...


def with_session(
    func: t.Callable[Concatenate[Session, P], R] | None = None,
    *,
    passphrase: bool = True,
    cardano: bool = False,
    seedless: bool = False,
) -> t.Callable[[FuncWithSession[P, R]], t.Callable[P, R]] | t.Callable[P, R]:
    """Provides a Click command with parameter `session=obj.get_session(...)`
    based on the parameters provided:

    * if `passphrase` is set to False, a standard wallet is always used for this session
    * if `cardano` is set to True, Cardano-specific operations are enabled for this session
    * if `seedless` is set to True, a seedless session is used for this session

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
            with obj.session_context(
                use_passphrase=passphrase,
                derive_cardano=cardano,
                seedless=seedless,
            ) as session:
                try:
                    return func(session, *args, **kwargs)

                finally:
                    if obj.session_id is None and not session.features.bootloader_mode:
                        session.close()

        return function_with_session

    # If the decorator @get_session is used without parentheses
    if func and callable(func):
        return decorator(func)

    return decorator


def with_client(func: t.Callable[Concatenate[TrezorClient, P], R]) -> t.Callable[P, R]:
    @click.pass_obj
    @functools.wraps(func)
    def function_with_client(
        obj: TrezorConnection, *args: P.args, **kwargs: P.kwargs
    ) -> R:
        with obj.client_context() as client:
            return func(client, *args, **kwargs)

    return function_with_client


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
