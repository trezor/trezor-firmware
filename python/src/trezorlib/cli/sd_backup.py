from typing import TYPE_CHECKING, Optional

import click

from .. import messages, sd_backup
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="sd-backup")
def cli() -> None:
    """SD backup management commands."""


@cli.command()
@with_client
def check(client: "TrezorClient") -> messages.SdCardBackupHealth:
    """Check health of SD backup."""
    return sd_backup.check(client)

@cli.command()
@with_client
def refresh(client: "TrezorClient") -> messages.Success:
    """Refresh data on the SD backup card."""
    return sd_backup.refresh(client)


@cli.command()
@with_client
def wipe(client: "TrezorClient") -> messages.Success:
    """Wipe the backup from SD card !!!CAUTION: IRREVERSIBLE OPERATION!!!"""
    return sd_backup.wipe(client)

@cli.command()
@with_client
def copy(client: "TrezorClient") -> messages.Success | messages.Failure:
    """Copy a backup SD card to another SD card."""
    return sd_backup.copy(client)
