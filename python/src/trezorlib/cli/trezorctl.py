#!/usr/bin/env python3

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

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, TypeVar, cast

import click

from .. import __version__, log, messages, protobuf, ui
from ..client import TrezorClient
from ..transport import DeviceIsBusy, enumerate_devices
from ..transport.udp import UdpTransport
from . import (
    AliasedGroup,
    TrezorConnection,
    binance,
    btc,
    cardano,
    cosi,
    crypto,
    debug,
    device,
    eos,
    ethereum,
    fido,
    firmware,
    monero,
    nem,
    ripple,
    settings,
    solana,
    stellar,
    tezos,
    with_client,
)

F = TypeVar("F", bound=Callable)

if TYPE_CHECKING:
    from ..transport import Transport

LOG = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "change-pin": settings.pin,
    "enable-passphrase": settings.passphrase_on,
    "disable-passphrase": settings.passphrase_off,
    "wipe-device": device.wipe,
    "reset-device": device.setup,
    "recovery-device": device.recover,
    "backup-device": device.backup,
    "sd-protect": device.sd_protect,
    "load-device": device.load,
    "prodtest-t1": debug.prodtest_t1,
    "get-entropy": crypto.get_entropy,
    "encrypt-keyvalue": crypto.encrypt_keyvalue,
    "decrypt-keyvalue": crypto.decrypt_keyvalue,
    # currency name aliases:
    "bnb": binance.cli,
    "eth": ethereum.cli,
    "ada": cardano.cli,
    "sol": solana.cli,
    "xmr": monero.cli,
    "xrp": ripple.cli,
    "xlm": stellar.cli,
    "xtz": tezos.cli,
    # firmware aliases:
    "fw": firmware.cli,
    "update-firmware": firmware.update,
    "upgrade-firmware": firmware.update,
    "firmware-upgrade": firmware.update,
    "firmware-update": firmware.update,
}


class TrezorctlGroup(AliasedGroup):
    """Command group that handles compatibility for trezorctl.

    With trezorctl 0.11.5, we started to convert old-style long commands
    (such as "binance-sign-tx") to command groups ("binance") with subcommands
    ("sign-tx"). The `TrezorctlGroup` can perform subcommand lookup: if a command
    "binance-sign-tx" does not exist in the default group, it tries to find "sign-tx"
    subcommand of "binance" group.
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        cmd = super().get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # the subsequent lookups rely on dash-separated command names
        cmd_name = cmd_name.replace("_", "-")
        # look for subcommand in btc - "sign-tx" is now "btc sign-tx"
        cmd = btc.cli.get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # Old-style top-level commands looked like this: binance-sign-tx.
        # We are moving to 'binance' command with 'sign-tx' subcommand.
        try:
            command, subcommand = cmd_name.split("-", maxsplit=1)
            # get_command can return None and the following line will fail.
            # We don't care, we ignore the exception anyway.
            return super().get_command(ctx, command).get_command(ctx, subcommand)  # type: ignore ["get_command" is not a known member of "None";;Cannot access member "get_command" for type "Command"]
        except Exception:
            pass

        return None

    def set_result_callback(self) -> Callable[[F], F]:
        """Set a function called to format the return value of a command.

        Compatibility wrapper for Click 7.x `resultcallback` and >=8.1 `result_callback`
        """
        # Click 7.x uses `resultcallback` to configure the callback, and
        #   `result_callback` to store its value.
        # Click 8.x uses `result_callback` to configure the callback, and
        #   `_result_callback` to store its value.
        # Click 8.0 has a `resultcallback` function that emits a warning and delegates
        #   to `result_callback`. Click 8.1 removes this function.
        #
        # This means that there is no reasonable way to use `hasattr` to detect where we
        # are, unless we want to look at the private `_result_callback` attribute.
        # Instead, we look at Click version and hope for the best.
        from click import __version__ as click_version

        if click_version.startswith("7."):
            return super().resultcallback()  # type: ignore [Cannot access member]
        else:
            return super().result_callback()


def configure_logging(verbose: int) -> None:
    if verbose:
        log.enable_debug_output(verbose)
        log.OMITTED_MESSAGES.add(messages.Features)


@click.command(
    cls=TrezorctlGroup,
    context_settings={"max_content_width": 400},
    aliases=COMMAND_ALIASES,
)
@click.option(
    "-p",
    "--path",
    help="Select device by specific path.",
    default=os.environ.get("TREZOR_PATH"),
)
@click.option("-v", "--verbose", count=True, help="Show communication messages.")
@click.option(
    "-j", "--json", "is_json", is_flag=True, help="Print result as JSON object"
)
@click.option(
    "-P",
    "--passphrase-on-host",
    is_flag=True,
    help="Enter passphrase on host.",
)
@click.option(
    "-S",
    "--script",
    is_flag=True,
    help="Use UI for usage in scripts.",
)
@click.option(
    "-s",
    "--session-id",
    metavar="HEX",
    help="Resume given session ID.",
    default=os.environ.get("TREZOR_SESSION_ID"),
)
@click.option(
    "-r",
    "--record",
    help="Record screen changes into a specified directory.",
)
@click.version_option(version=__version__)
@click.pass_context
def cli_main(
    ctx: click.Context,
    path: str,
    verbose: int,
    is_json: bool,
    passphrase_on_host: bool,
    script: bool,
    session_id: Optional[str],
    record: Optional[str],
) -> None:
    configure_logging(verbose)

    bytes_session_id: Optional[bytes] = None
    if session_id is not None:
        try:
            bytes_session_id = bytes.fromhex(session_id)
        except ValueError:
            raise click.ClickException(f"Not a valid session id: {session_id}")

    ctx.obj = TrezorConnection(path, bytes_session_id, passphrase_on_host, script)

    # Optionally record the screen into a specified directory.
    if record:
        debug.record_screen_from_connection(ctx.obj, record)


# Creating a cli function that has the right types for future usage
cli = cast(TrezorctlGroup, cli_main)


@cli.set_result_callback()
def print_result(res: Any, is_json: bool, script: bool, **kwargs: Any) -> None:
    if is_json:
        if isinstance(res, protobuf.MessageType):
            res = protobuf.to_dict(res, hexlify_bytes=True)

        # No newlines for scripts, pretty-print for users
        if script:
            click.echo(json.dumps(res))
        else:
            click.echo(json.dumps(res, sort_keys=True, indent=4))
    else:
        if isinstance(res, list):
            for line in res:
                click.echo(line)
        elif isinstance(res, dict):
            for k, v in res.items():
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        click.echo(f"{k}.{kk}: {vv}")
                else:
                    click.echo(f"{k}: {v}")
        elif isinstance(res, protobuf.MessageType):
            click.echo(protobuf.format_message(res))
        elif res is not None:
            click.echo(res)


@cli.set_result_callback()
@click.pass_obj
def stop_recording_action(obj: TrezorConnection, *args: Any, **kwargs: Any) -> None:
    """Stop recording screen changes when the recording was started by `cli_main`.

    (When user used the `-r / --record` option of `trezorctl` command.)

    It allows for isolating screen directories only for specific actions/commands.
    """
    if kwargs.get("record"):
        debug.record_screen_from_connection(obj, None)


def format_device_name(features: messages.Features) -> str:
    model = features.model or "1"
    if features.bootloader_mode:
        return f"Trezor {model} bootloader"

    label = features.label or "(unnamed)"
    return f"{label} [Trezor {model}, {features.device_id}]"


#
# Common functions
#


@cli.command(name="list")
@click.option("-n", "no_resolve", is_flag=True, help="Do not resolve Trezor names")
def list_devices(no_resolve: bool) -> Optional[Iterable["Transport"]]:
    """List connected Trezor devices."""
    if no_resolve:
        return enumerate_devices()

    for transport in enumerate_devices():
        try:
            client = TrezorClient(transport, ui=ui.ClickUI())
            description = format_device_name(client.features)
            client.end_session()
        except DeviceIsBusy:
            description = "Device is in use by another process"
        except Exception:
            description = "Failed to read details"
        click.echo(f"{transport} - {description}")
    return None


@cli.command()
def version() -> str:
    """Show version of trezorctl/trezorlib."""
    return __version__


#
# Basic device functions
#


@cli.command()
@click.argument("message")
@click.option("-b", "--button-protection", is_flag=True)
@with_client
def ping(client: "TrezorClient", message: str, button_protection: bool) -> str:
    """Send ping message."""
    return client.ping(message, button_protection=button_protection)


@cli.command()
@click.pass_obj
def get_session(obj: TrezorConnection) -> str:
    """Get a session ID for subsequent commands.

    Unlocks Trezor with a passphrase and returns a session ID. Use this session ID with
    `trezorctl -s SESSION_ID`, or set it to an environment variable `TREZOR_SESSION_ID`,
    to avoid having to enter passphrase for subsequent commands.

    The session ID is valid until another client starts using Trezor, until the next
    get-session call, or until Trezor is disconnected.
    """
    # make sure session is not resumed
    obj.session_id = None

    with obj.client_context() as client:
        if client.features.model == "1" and client.version < (1, 9, 0):
            raise click.ClickException(
                "Upgrade your firmware to enable session support."
            )

        client.ensure_unlocked()
        if client.session_id is None:
            raise click.ClickException("Passphrase not enabled or firmware too old.")
        else:
            return client.session_id.hex()


@cli.command()
@with_client
def clear_session(client: "TrezorClient") -> None:
    """Clear session (remove cached PIN, passphrase, etc.)."""
    return client.clear_session()


@cli.command()
@with_client
def get_features(client: "TrezorClient") -> messages.Features:
    """Retrieve device features and settings."""
    return client.features


@cli.command()
def usb_reset() -> None:
    """Perform USB reset on stuck devices.

    This can fix LIBUSB_ERROR_PIPE and similar errors when connecting to a device
    in a messed state.
    """
    from ..transport.webusb import WebUsbTransport

    WebUsbTransport.enumerate(usb_reset=True)


@cli.command()
@click.option("-t", "--timeout", type=float, default=10, help="Timeout in seconds")
@click.pass_obj
def wait_for_emulator(obj: TrezorConnection, timeout: float) -> None:
    """Wait until Trezor Emulator comes up.

    Tries to connect to emulator and returns when it succeeds.
    """
    path = obj.path
    if path:
        if not path.startswith("udp:"):
            raise click.ClickException(f"You must use UDP path, not {path}")
        path = path.replace("udp:", "")

    start = time.monotonic()
    UdpTransport(path).wait_until_ready(timeout)
    end = time.monotonic()

    LOG.info(f"Waited for {end - start:.3f} seconds")


#
# Basic coin functions
#

cli.add_command(binance.cli)
cli.add_command(btc.cli)
cli.add_command(cardano.cli)
cli.add_command(cosi.cli)
cli.add_command(crypto.cli)
cli.add_command(device.cli)
cli.add_command(eos.cli)
cli.add_command(ethereum.cli)
cli.add_command(fido.cli)
cli.add_command(monero.cli)
cli.add_command(nem.cli)
cli.add_command(ripple.cli)
cli.add_command(settings.cli)
cli.add_command(solana.cli)
cli.add_command(stellar.cli)
cli.add_command(tezos.cli)

cli.add_command(firmware.cli)
cli.add_command(debug.cli)

#
# Main
#


if __name__ == "__main__":
    cli()  # pylint: disable=E1120
