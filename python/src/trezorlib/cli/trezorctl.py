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
from typing import TYPE_CHECKING, Any, Iterable, Optional, cast

import click

from .. import log, messages, protobuf, ui
from ..client import TrezorClient
from ..transport import enumerate_devices
from ..transport.udp import UdpTransport
from . import (
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
    stellar,
    tezos,
    with_client,
)

if TYPE_CHECKING:
    from ..transport import Transport

LOG = logging.getLogger(__name__)

COMMAND_ALIASES = {
    "change-pin": settings.pin,
    "enable-passphrase": settings.passphrase_enable,
    "disable-passphrase": settings.passphrase_disable,
    "wipe-device": device.wipe,
    "reset-device": device.setup,
    "recovery-device": device.recover,
    "backup-device": device.backup,
    "sd-protect": device.sd_protect,
    "load-device": device.load,
    "self-test": device.self_test,
    "get-entropy": crypto.get_entropy,
    "encrypt-keyvalue": crypto.encrypt_keyvalue,
    "decrypt-keyvalue": crypto.decrypt_keyvalue,
    # currency name aliases:
    "bnb": binance.cli,
    "eth": ethereum.cli,
    "ada": cardano.cli,
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


class TrezorctlGroup(click.Group):
    """Command group that handles compatibility for trezorctl.

    The purpose is twofold: convert underscores to dashes, and ensure old-style commands
    still work with new-style groups.

    Click 7.0 silently switched all underscore_commands to dash-commands.
    This implementation of `click.Group` responds to underscore_commands by invoking
    the respective dash-command.

    With trezorctl 0.11.5, we started to convert old-style long commands
    (such as "binance-sign-tx") to command groups ("binance") with subcommands
    ("sign-tx"). The `TrezorctlGroup` can perform subcommand lookup: if a command
    "binance-sign-tx" does not exist in the default group, it tries to find "sign-tx"
    subcommand of "binance" group.
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        cmd_name = cmd_name.replace("_", "-")
        # try to look up the real name
        cmd = super().get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # look for a backwards compatibility alias
        if cmd_name in COMMAND_ALIASES:
            return COMMAND_ALIASES[cmd_name]

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
            return super().get_command(ctx, command).get_command(ctx, subcommand)  # type: ignore ["get_command" is not a known member of "None"]
        except Exception:
            pass

        return None


def configure_logging(verbose: int) -> None:
    if verbose:
        log.enable_debug_output(verbose)
        log.OMITTED_MESSAGES.add(messages.Features)


@click.command(cls=TrezorctlGroup, context_settings={"max_content_width": 400})
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
    "-s",
    "--session-id",
    metavar="HEX",
    help="Resume given session ID.",
    default=os.environ.get("TREZOR_SESSION_ID"),
)
@click.version_option()
@click.pass_context
def cli_main(
    ctx: click.Context,
    path: str,
    verbose: int,
    is_json: bool,
    passphrase_on_host: bool,
    session_id: Optional[str],
) -> None:
    configure_logging(verbose)

    bytes_session_id: Optional[bytes] = None
    if session_id is not None:
        try:
            bytes_session_id = bytes.fromhex(session_id)
        except ValueError:
            raise click.ClickException(f"Not a valid session id: {session_id}")

    ctx.obj = TrezorConnection(path, bytes_session_id, passphrase_on_host)


# Creating a cli function that has the right types for future usage
cli = cast(TrezorctlGroup, cli_main)


@cli.resultcallback()
def print_result(res: Any, is_json: bool, **kwargs: Any) -> None:
    if is_json:
        if isinstance(res, protobuf.MessageType):
            click.echo(json.dumps({res.__class__.__name__: res.__dict__}))
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
        client = TrezorClient(transport, ui=ui.ClickUI())
        click.echo(f"{transport} - {format_device_name(client.features)}")
        client.end_session()
    return None


@cli.command()
def version() -> str:
    """Show version of trezorctl/trezorlib."""
    from .. import __version__ as VERSION

    return VERSION


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
cli.add_command(stellar.cli)
cli.add_command(tezos.cli)

cli.add_command(firmware.cli)
cli.add_command(debug.cli)

#
# Main
#


if __name__ == "__main__":
    cli()  # pylint: disable=E1120
