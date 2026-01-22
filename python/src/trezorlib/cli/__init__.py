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
import json
import base64
import logging
import os
import random
import re
import sys
import typing as t
from contextlib import contextmanager
import dataclasses
from enum import Enum
from pathlib import Path

import click
from typing_extensions import Self

from .. import exceptions, messages, protocol_v1, transport, ui
from ..client import AppManifest, PassphraseSetting, Session, TrezorClient, get_client
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
    """Passphrase source configured by the user."""

    AUTO = "auto"
    """If passphrase is enabled and the device supports it, request passphrase
    entry on the device. Otherwise, open the default wallet with no
    passphrase."""
    PROMPT = "prompt"
    """Request passphrase entry on the host."""
    EMPTY = "empty"
    """Open the default wallet with no passphrase."""
    DEVICE = "device"
    """Request passphrase entry on the device."""

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


@dataclasses.dataclass
class SessionIdentifier:
    path: str
    sid: str
    type: str

    @classmethod
    def from_session(cls, session: Session) -> Self:
        path = session.client.transport.get_path()
        if isinstance(session, protocol_v1.SessionV1):
            if session.id is None:
                raise click.ClickException("This Trezor session does not have an ID.")
            return cls(path=path, sid=session.id.hex(), type="v1")
        if isinstance(session, thp_client.ThpSession):
            return cls(path=path, sid=str(session.id), type="thp")
        raise ValueError(f"Unsupported session type: {type(session).__name__}")

    @classmethod
    def from_session_str(cls, session_str: str) -> Self:
        session_str_decoded = base64.b64decode(session_str).decode()
        LOG.info(f"Decoded session string: {session_str_decoded}")
        dict = json.loads(session_str_decoded)
        return cls(**dict)

    def to_session_str(self) -> str:
        session_str_plain = json.dumps(dataclasses.asdict(self))
        LOG.info(f"Decoded ession string: {session_str_plain}")
        return base64.b64encode(session_str_plain.encode()).decode()

    def resume(self, client: TrezorClient) -> Session:
        if self.type == "v1":
            if not isinstance(client, protocol_v1.TrezorClientV1):
                raise click.ClickException(
                    f"Protocol mismatch: resuming a v1 session with a {type(client).__name__} client"
                )
            LOG.info(f"Resuming v1 session with id: {self.sid}")
            return protocol_v1.SessionV1(client, id=bytes.fromhex(self.sid))
        if self.type == "thp":
            if not isinstance(client, thp_client.TrezorClientThp):
                raise click.ClickException(
                    f"Protocol mismatch: resuming a THP session with a {type(client).__name__} client"
                )
            LOG.info(f"Resuming THP session with id: {self.sid}")
            return thp_client.ThpSession(client, id=int(self.sid))
        raise ValueError(f"Unsupported session type: {self.type}")


ENV_TREZOR_SESSION_ID = os.environ.get("TREZOR_SESSION_ID")


class TrezorConnection:
    _client: TrezorClient | None = None
    _features: messages.Features | None = None
    _transport: Transport | None = None
    _standard_session: Session | None = None

    def __init__(
        self,
        *,
        session_str: str | None = None,
        path: str | None = None,
        passphrase_source: PassphraseSource = PassphraseSource.AUTO,
        script: bool = False,
        app_name: str = "trezorctl",
        record_dir: Path | None = None,
    ) -> None:
        self.session_str = session_str

        if session_str is None:
            self.session = None
            self.path = path
        else:
            self.session = SessionIdentifier.from_session_str(session_str)
            if path is not None and self.session.path != path:
                click.echo("Attempting to resume a session on a different device.")
                click.echo(
                    "Hint: omit -p or unset TREZOR_PATH to use the appropriate device for this session."
                )
                if ENV_TREZOR_SESSION_ID == self.session_str:
                    click.echo(
                        "Hint: unset TREZOR_SESSION_ID to avoid resuming a session."
                    )
                raise click.ClickException(
                    "Session path does not match the provided path"
                )
            self.path = self.session.path

        self.passphrase_source = passphrase_source
        self.script = script
        self.record_dir = record_dir
        self.credentials = credentials.CredentialStore(app_name)
        self.app = AppManifest(app_name=app_name, credentials=self.credentials.list)
        if self.script:
            self.app.button_callback = ui.ScriptUI.button_request
            self.app.pin_callback = ui.ScriptUI.get_pin
        else:
            click_ui = ui.ClickUI()
            self.app.button_callback = click_ui.button_request
            self.app.pin_callback = click_ui.get_pin

    def ensure_unlocked(self) -> None:
        """Ensure that the device is unlocked.

        Separate from `client.ensure_unlocked()` because we want to reuse the
        standard session.
        """
        with self.client_context() as client:
            if not client.features.initialized:
                # uninitialized device cannot be locked
                return
            # query the standard session instead
            self.standard_session.ensure_unlocked()

    @property
    def standard_session(self) -> Session:
        if self._standard_session is None:
            with self.client_context() as client:
                self._standard_session = client.get_session(
                    passphrase=PassphraseSetting.STANDARD_WALLET
                )
        # seems to be a weird typechecker limitation that it still thinks that
        # session could be None here
        return self._standard_session  # type: ignore ["None" is not assignable]

    @property
    def features(self) -> messages.Features:
        if self._features is None:
            self.ensure_unlocked()
            assert self._client is not None  # after ensure_unlocked
            self._features = self._client.features
        return self._features

    @property
    def version(self) -> tuple[int, int, int]:
        if self._version is None:
            with self.client_context() as client:
                self._version = client.version
        return self._version

    @property
    def transport(self) -> Transport:
        if self._transport is None:
            self.open()
        assert self._transport is not None
        return self._transport

    def _record_screen(self, start: bool) -> None:
        """Helper wrapping `debug.record_screen()` to avoid circular import."""
        from .debug import record_screen

        if self.record_dir is None:
            return

        assert self._transport is not None
        record_screen(self._transport, self.record_dir if start else None)

    def open(self) -> None:
        if self._transport is None:
            self._transport = self._get_transport()
            self._transport.open()
            self._record_screen(True)

    def close(self) -> None:
        self._record_screen(False)
        if self._transport is not None:
            self._transport.close()
        self._transport = None
        self._client = None
        self._features = None
        self._standard_session = None

    def _passphrase_source_resolved(self) -> PassphraseSource:
        """Resolve PassphraseSource.AUTO to a concrete PassphraseSource.

        Assumes that `self.features` is already populated.

        Returns:
        * `self.passphrase_source` if it is not `PassphraseSource.AUTO`
        * `PassphraseSource.EMPTY` if passphrase protection is disabled
        * `PassphraseSource.DEVICE` if passphrase entry is supported
        * `PassphraseSource.PROMPT` otherwise
        """
        if (
            not self.features.passphrase_protection
            and not self.passphrase_source.ok_if_disabled()
        ):
            raise click.ClickException("Passphrase protection is not enabled")

        if self.passphrase_source != PassphraseSource.AUTO:
            return self.passphrase_source
        if not self.features.passphrase_protection:
            return PassphraseSource.EMPTY
        if messages.Capability.PassphraseEntry in self.features.capabilities:
            return PassphraseSource.DEVICE
        return PassphraseSource.PROMPT

    def get_session(
        self,
        use_passphrase: bool = True,
        seedless: bool = False,
        derive_cardano: bool = False,
    ) -> Session:
        """Get a session from this connection.

        Arguments:
        - use_passphrase: if True, user should get a passphrase prompt
          (either on host or on device)
        - seedless: if True, create a session without a derived seed
        - derive_cardano: whether to derive a Cardano session
        """
        client = self.get_client()

        # seedless sessions are never resumed
        if seedless:
            return client.get_session(passphrase=None)

        passphrase_source = self._passphrase_source_resolved()

        # if empty passphrase is requested, do not try to resume and just use
        # the standard session that we already have
        if not use_passphrase or passphrase_source == PassphraseSource.EMPTY:
            return self.standard_session

        # Try resume session from id
        if self.session is not None:
            try:
                return self.session.resume(client)
            except exceptions.InvalidSessionError:
                LOG.error("Failed to resume session", exc_info=True)
                raise

        # if all else fails, allocate a new session
        return self.get_new_session(derive_cardano=derive_cardano)

    def get_new_session(
        self, derive_cardano: bool = False, randomize_id: bool = False
    ) -> Session:
        """Allocate a new session.

        By default, every THP session is counted from 1 based on
        `client._session_id_counter`. If `randomize_id` is True, the returned
        session will instead pick a random ID between 128 and 255, avoiding the
        id that is currently set on `self.session`. This should match what the user
        expects from `trezorctl get-session`.
        """
        client = self.get_client()
        if randomize_id and isinstance(client, thp_client.TrezorClientThp):
            if self.session is None:
                session_id = 1
            else:
                session_id = int(self.session.sid)
            random_value = session_id
            while random_value == session_id:
                random_value = random.randint(128, 255)
            client._session_id_counter = random_value - 1

        passphrase_source = self._passphrase_source_resolved()
        if passphrase_source == PassphraseSource.EMPTY:
            return client.get_session(
                passphrase=PassphraseSetting.STANDARD_WALLET,
                derive_cardano=derive_cardano,
            )
        if passphrase_source == PassphraseSource.PROMPT:
            passphrase = get_passphrase()
            return client.get_session(
                passphrase=passphrase,
                derive_cardano=derive_cardano,
            )
        if passphrase_source == PassphraseSource.DEVICE:
            return client.get_session(
                passphrase=PassphraseSetting.ON_DEVICE,
                derive_cardano=derive_cardano,
            )
        raise NotImplementedError(
            f"Passphrase source {self.passphrase_source} not implemented"
        )

    def _get_transport(self) -> Transport:
        try:
            # look for transport without prefix search
            return transport.get_transport(self.path, prefix_search=False)
        except Exception:
            # most likely not found. try again below.
            pass

        # look for transport with prefix search
        try:
            return transport.get_transport(self.path, prefix_search=True)
        except Exception:
            if self.path:
                raise click.ClickException(
                    f"Could not find device by path: {self.path}"
                )
            else:
                raise click.ClickException("No Trezor device found")

    def _get_client(self) -> TrezorClient:
        client = get_client(self.app, self.transport)
        if not client.pairing.is_paired():
            from ..thp import pairing

            credential = pairing.default_pairing_flow(
                client.pairing, code_entry_callback=get_code_entry_code
            )
            if credential is not None:
                self.credentials.add(credential)

        return client

    def get_client(self) -> TrezorClient:
        if self._client is None:
            self._client = self._get_client()
        return self._client

    def _connection_context(
        self,
        connect_fn: t.Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> t.Generator[R, None, None]:
        try:
            conn = connect_fn(*args, **kwargs)
        except click.ClickException as e:
            raise
        except Exception as e:
            self._print_exception(e, "Failed to connect")
            sys.exit(1)

        try:
            yield conn
        except exceptions.Cancelled:
            # handle cancel action
            click.echo("Action was cancelled.")
            sys.exit(1)
        except exceptions.InvalidSessionError as e:
            if ENV_TREZOR_SESSION_ID == self.session_str:
                click.echo(
                    "Session-id stored in TREZOR_SESSION_ID is no longer valid. Call\n"
                    "  unset TREZOR_SESSION_ID\n"
                    "to clear it."
                )
            raise click.ClickException(
                f"Invalid session: {self.session_str or e.session_id}"
            ) from e
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
                    if obj.session is None and not session.features.bootloader_mode:
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
