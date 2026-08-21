#!/usr/bin/env python3
"""
Find firmware binaries in artifacts produced by `core_firmware` jobs in the `core.yml` workflow and copy them into directory structure used by release tooling.
Only models in the latest entry in `common/releases.json` are copied.
"""

import json
import shutil
from pathlib import Path

import click

ALL_MODELS = ["T2T1", "T3B1", "T3T1", "T3W1"]
# FIXME ALL_MODELS = ["T2B1", "T2T1", "T3B1", "T3T1", "T3W1"]


@click.command(help=__doc__)
@click.argument(
    "artifact_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="firmware/unsigned",
)
@click.option(
    "-r",
    "--releases",
    "releases_json",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.option(
    "-v",
    "--version",
    "version",
    help="manually specify version instead of using releases.json",
)
@click.option(
    "-t",
    "--translations",
    "translations_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="core/translations",
)
def main(
    artifact_dir: str | Path,
    output_dir: str | Path,
    releases_json: str | Path | None,
    translations_dir: str | Path,
    version: str | None,
) -> None:
    artifact_dir = Path(artifact_dir)
    output_dir = Path(output_dir)
    translations_dir = Path(translations_dir)

    if releases_json is not None:
        releases_json = Path(releases_json)
        releases = json.loads(releases_json.read_text())["firmware"]
        version, models = max(
            releases.items(), key=lambda item: [int(n) for n in item[0].split(".")]
        )
    elif version is not None:
        models = ALL_MODELS
    else:
        raise click.ClickException("Either --releases or --version is required")
    click.echo(f"Version: {version}")
    click.echo(f"Models: {', '.join(models)}")

    for model in models:
        # firmware
        model_dir = output_dir / model.lower()
        model_dir.mkdir(parents=True, exist_ok=True)

        for coins in ("universal", "btconly"):
            source_dir = artifact_dir / f"core-firmware-{model}-{coins}-normal" / "pub"
            matching = list(source_dir.glob(f"firmware-{model}-*.bin"))
            assert len(matching) == 1, f"{source_dir}: {matching}"
            fw_file = matching[0]

            click.echo(f"{fw_file} -> {model_dir / fw_file.name}")
            shutil.copy(fw_file, model_dir / fw_file.name)

        # translations
        model_dir = output_dir / "translations" / model.lower()
        model_dir.mkdir(parents=True, exist_ok=True)

        for f in translations_dir.glob(f"translation-{model}-*-unsigned.bin"):
            fname = f.name
            click.echo(f"{f} -> {model_dir / fname}")
            shutil.copy(f, model_dir / fname)


if __name__ == "__main__":
    main()
