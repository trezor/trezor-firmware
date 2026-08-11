#!/usr/bin/env python3
"""
Find firmware binaries in artifacts produced by `core_firmware` jobs in the `core.yml` workflow and copy them into directory structure used by release tooling.
Only models in the latest entry in `common/releases.json` are copied.
"""

import json
import shutil
from pathlib import Path

import click


@click.command(help=__doc__)
@click.argument(
    "artifact_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="firmware",
)
@click.option(
    "-r",
    "--releases",
    "releases_json",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="common/releases.json",
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
    releases_json: str | Path,
    translations_dir: str | Path,
) -> None:
    artifact_dir = Path(artifact_dir)
    output_dir = Path(output_dir)
    releases_json = Path(releases_json)
    translations_dir = Path(translations_dir)

    releases = json.loads(releases_json.read_text())["firmware"]
    latest, models = max(
        releases.items(), key=lambda item: [int(n) for n in item[0].split(".")]
    )
    click.echo(f"Version: {latest}")
    click.echo(f"Models: {', '.join(models)}")

    for model in models:
        # firmware
        model_dir = output_dir / "unsigned" / model.lower()
        model_dir.mkdir(parents=True, exist_ok=True)

        for coins in ("universal", "btconly"):
            source_dir = artifact_dir / f"core-firmware-{model}-{coins}-normal" / "pub"
            matching = list(source_dir.glob(f"firmware-{model}-*.bin"))
            assert len(matching) == 1, f"{source_dir}: {matching}"
            fw_file = matching[0]

            click.echo(f"{fw_file} -> {model_dir / fw_file.name}")
            shutil.copy(fw_file, model_dir / fw_file.name)

        # translations
        model_dir = output_dir / "unsigned" / "translations" / model.lower()
        model_dir.mkdir(parents=True, exist_ok=True)

        for f in translations_dir.glob(f"translation-{model}-*-unsigned.bin"):
            fname = f.name
            click.echo(f"{f} -> {model_dir / fname}")
            shutil.copy(f, model_dir / fname)


if __name__ == "__main__":
    main()
