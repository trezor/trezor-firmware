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
import requests

from trezorlib import cosi, definitions, merkle_tree, messages, protobuf
from trezorlib.testing.common import PRIVATE_KEYS_DEV

PROD_URL = "https://data.trezor.io/firmware/definitions/v2/"
DEV_URL = "https://dev.firmware.sldev.cz/unsigned/v2/definitions/"

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

# trezor/definitions dev-signs with all three development keys (sigmask 0b111),
# unlike `Definition.verify(dev=True)`, which expects a single combined key.
# TODO: definitions should also sign with a single key, for dev.
DEV_DEPLOY_PUBLIC_KEYS = [cosi.pubkey_from_privkey(k) for k in PRIVATE_KEYS_DEV]


def verify_dev(definition: definitions.Definition) -> None:
    """Verify a definition signed by the dev deployment of trezor/definitions,
    or by the local test helpers."""
    if definition.sigmask != 0b111:
        definition.verify(dev=True)
        return
    root = merkle_tree.evaluate_proof(definition.payload.build(), definition.proof)
    cosi.verify(
        definition.signature,
        root,
        len(DEV_DEPLOY_PUBLIC_KEYS),
        DEV_DEPLOY_PUBLIC_KEYS,
        definition.sigmask,
    )


def dat_to_dict(dat: bytes, dev: bool = False) -> dict:
    """Verify a signed definition (production keys unless `dev`) and decode it
    into the JSON fixture format (definition type and message)."""
    definition = definitions.Definition.parse(dat)
    if len(definition.build()) != len(dat):
        raise ValueError("trailing data after the definition")
    if dev:
        verify_dev(definition)
    else:
        definition.verify()
    payload = definition.payload
    msg_type = MESSAGE_TYPES[payload.data_type]
    msg = protobuf.load_message(io.BytesIO(payload.data), msg_type)
    # unknown fields are silently skipped when loading, so make sure that
    # re-encoding yields the signed bytes, i.e. nothing was left unread
    reencoded = io.BytesIO()
    protobuf.dump_message(reencoded, msg)
    if reencoded.getvalue() != payload.data:
        raise ValueError("definition has fields unknown to trezorlib")
    return {"data_type": payload.data_type.name, "message": protobuf.to_dict(msg)}


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=DEFAULT_DIR,
)
@click.option(
    "-u",
    "--url",
    help=f"Base URL. [default: {PROD_URL}, or {DEV_URL} with --dev]",
)
@click.option(
    "--dev",
    is_flag=True,
    help="Fetch the dev definitions",
)
def refresh(directory: Path, url: str | None, dev: bool) -> None:
    """Refresh the JSON definitions under DIRECTORY with the latest ones
    published at URL, i.e. what customers currently see (or, with --dev, what
    the dev deployment currently serves; internal network only).

    Only existing files are refreshed; definitions that are missing upstream
    are left untouched and reported. DIRECTORY defaults to the Ethereum
    definitions in the common test fixtures."""
    source = definitions.UrlSource(url or (DEV_URL if dev else PROD_URL))
    updated, missing, denied = [], [], 0
    json_files = sorted(directory.rglob("*.json"))
    for json_path in json_files:
        rel = json_path.relative_to(directory)
        try:
            dat = source.fetch_path(*rel.with_suffix(".dat").parts)
        except requests.HTTPError as e:
            # the dev bucket answers 403 (not 404) for objects that do not exist
            if dev and e.response is not None and e.response.status_code in (401, 403):
                denied += 1
                dat = None
            else:
                raise click.ClickException(f"{rel}: {e}") from e
        if dat is None:
            missing.append(rel)
            continue
        try:
            converted = dat_to_dict(dat, dev=dev)
        except Exception as e:
            raise click.ClickException(f"{rel}: {e}") from e
        new_text = json.dumps(converted, indent=2) + "\n"
        if json_path.read_text() != new_text:
            json_path.write_text(new_text)
            updated.append(rel)

    if json_files and denied == len(json_files):
        raise click.ClickException(
            "Dev definitions can only be accessed from the internal network."
        )

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
