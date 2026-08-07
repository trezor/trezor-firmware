#!/usr/bin/env python3
"""
Unpacks artifact archives into directory structure used by release tooling.
Only models in the latest entry in `common/releases.json` are copied.
"""

import json
import shutil
import zipfile
from pathlib import Path

import click


@click.command()
@click.argument(
    "artifact_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="firmware",
)
@click.option(
    "-r",
    "--releases",
    "releases_json",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="common/releases.json",
)
def main(
    artifact_dir: str | Path, output_dir: str | Path, releases_json: str | Path
) -> None:
    artifact_dir = Path(artifact_dir)
    output_dir = Path(output_dir)
    releases_json = Path(releases_json)

    releases = json.loads(releases_json.read_text())["firmware"]
    latest = max(map(lambda s: [int(n) for n in s.split(".")], releases.keys()))
    latest = ".".join(str(n) for n in latest)
    click.echo(f"Version: {latest}")
    models = sorted(releases[latest])

    for model in models:
        model_dir = output_dir / "unsigned" / model.lower()
        model_dir.mkdir(parents=True, exist_ok=True)

        for coins in ("universal", "btconly"):
            artifact_zip = artifact_dir / f"core-firmware-{model}-{coins}-normal" / f"core-firmware-{model}-{coins}-normal.zip" # XXX what the fuck github
            print(artifact_zip)

            with zipfile.ZipFile(artifact_zip, "r") as z:
                matching = [
                    fn
                    for fn in z.namelist()
                    if fn.startswith("pub/firmware-") and fn.endswith(".bin")
                ]
                assert len(matching) == 1
                fw_filename = matching[0]

                with z.open(fw_filename, "r") as fw_fh:
                    fw_filename = Path(fw_filename).name
                    click.echo(f"{fw_filename} -> {model_dir / fw_filename}")
                    (model_dir / fw_filename).write_bytes(fw_fh.read())

        # translations
        trans_dir = Path("core/translations")
        model_dir = output_dir / "unsigned" / "translations" / model.lower()

        for f in trans_dir.iterdir():
            fname = f.name
            if fname.startswith(f"translation-{model}-") and fname.endswith(
                f"-unsigned.bin"
            ):
                click.echo(f"{f} -> {model_dir / fname}")
                shutil.copy(f, model_dir / fname)


if __name__ == "__main__":
    main()
