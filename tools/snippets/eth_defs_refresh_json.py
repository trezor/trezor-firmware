#!/usr/bin/env python3

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

import io
import json
from pathlib import Path

import click

from trezorlib import definitions, messages, protobuf

PROD_URL = "https://data.trezor.io/firmware/definitions/v2/"

MESSAGE_TYPES: dict[messages.DefinitionType, type[protobuf.MessageType]] = {
    messages.DefinitionType.ETHEREUM_NETWORK: messages.EthereumNetworkInfo,
    messages.DefinitionType.ETHEREUM_TOKEN: messages.EthereumTokenInfo,
    messages.DefinitionType.SOLANA_TOKEN: messages.SolanaTokenInfo,
    messages.DefinitionType.ETHEREUM_DISPLAY_FORMAT: messages.EthereumDisplayFormatInfo,
}

DEFAULT_DIR = (
    Path(__file__).resolve().parents[2]
    / "common"
    / "tests"
    / "fixtures"
    / "ethereum"
    / "definitions"
)


def dat_to_dict(dat: bytes) -> dict:
    """Verify a production-signed definition and decode it into the JSON
    fixture format (definition type and message)."""
    definition = definitions.Definition.parse(dat)
    definition.verify()
    payload = definition.payload
    msg_type = MESSAGE_TYPES[payload.data_type]
    msg = protobuf.load_message(io.BytesIO(payload.data), msg_type)
    return {"data_type": payload.data_type.name, "message": protobuf.to_dict(msg)}


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=DEFAULT_DIR,
)
@click.option("-u", "--url", default=PROD_URL, show_default=True, help="Base URL.")
def refresh(directory: Path, url: str) -> None:
    """Refresh the JSON definitions under DIRECTORY with the latest ones
    published at URL, i.e. what customers currently see.

    Only existing files are refreshed; definitions that are missing upstream
    are left untouched and reported. DIRECTORY defaults to the Ethereum
    definitions in the common test fixtures."""
    source = definitions.UrlSource(url)
    updated, missing = [], []
    json_files = sorted(directory.rglob("*.json"))
    for json_path in json_files:
        rel = json_path.relative_to(directory)
        dat = source.fetch_path(*rel.with_suffix(".dat").parts)
        if dat is None:
            missing.append(rel)
            continue
        try:
            converted = dat_to_dict(dat)
        except Exception as e:
            raise click.ClickException(f"{rel}: {e}") from e
        new_text = json.dumps(converted, indent=2) + "\n"
        if json_path.read_text() != new_text:
            json_path.write_text(new_text)
            updated.append(rel)

    for rel in updated:
        click.echo(f"updated: {rel}")
    for rel in missing:
        click.echo(f"missing upstream: {rel}")
    click.echo(
        f"{len(json_files)} files: {len(updated)} updated, {len(missing)} missing, "
        f"{len(json_files) - len(updated) - len(missing)} unchanged."
    )


if __name__ == "__main__":
    refresh()
