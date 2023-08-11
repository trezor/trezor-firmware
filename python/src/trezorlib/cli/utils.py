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

from pathlib import Path

import click

from .. import translations


@click.group(name="utils")
def cli() -> None:
    """Utils commands."""


@cli.command()
@click.option(
    "-f",
    "--file",
    type=str,
    help="Language JSON file with translations.",
    required=True,
)
@click.option("-m", "--model", required=True)
def sign_translations(file: str, model: str) -> None:
    """Sign translations blob."""
    file_path = Path(file)
    if not file_path.exists():
        raise click.ClickException(f"File {file_path} does not exist.")

    file_info = translations.get_file_info(file_path)
    language = file_info["language"]
    version = file_info["version"]
    supported_models = file_info["supported_models"]
    if model not in supported_models:
        raise click.ClickException(
            "Fonts for model {} not found in file. Available models: {}".format(
                model, supported_models
            )
        )
    click.echo(f"Creating blob for language {language} version {version}")

    unsigned_blob = translations.blob_from_file(file_path, model, sign_dev=False)
    signing = translations.Signing(unsigned_blob)
    hash_to_sign = signing.hash_to_sign()
    click.echo("Hash to sign: {}".format(hash_to_sign.hex()))
    click.echo("Please sign this hash and paste the signature below.")
    signature: str = click.prompt("Signature", type=str)
    signature_bytes = bytes.fromhex(signature)
    signed_blob = signing.apply_signature(signature_bytes)

    # TODO: this is a pain point of model name "Safe 3" with a space
    model = model.replace(" ", "")

    output_file_name = f"translations_signed_{model}_{version}.dat"
    output_file_path = file_path.parent / output_file_name
    if output_file_path.exists():
        overwrite = click.confirm(
            f"WARNING: File {output_file_path} already exists. Overwrite?"
        )
        if overwrite:
            click.echo("Overwriting file.")
        else:
            click.echo("Aborting and not overwriting file.")
            return
    with output_file_path.open("wb") as f:
        f.write(signed_blob)
    click.echo(f"Signed blob saved to {output_file_path}")
