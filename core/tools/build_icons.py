#!/usr/bin/env python3

from pathlib import Path
import sys

import click
from PIL import Image

from trezorlib import toif

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

L_BOLT = "layout_bolt"
L_DELIZIA = "layout_delizia"
DESTINATIONS = {
    ROOT / "core" / "embed" / "rust" / "src" / "ui" / L_BOLT / "res" / "fido": 64,
    ROOT / "core" / "embed" / "rust" / "src" / "ui" / L_DELIZIA / "res" / "fido": 32,
}
EXCLUDE = {"icon_webauthn"}

# insert ../../common/tools to sys.path, so that we can import coin_info
# XXX this is hacky, but we want to keep coin_info in the common/ subdir for the purpose
# of exporting it to e.g. Connect
# And making a special python package out of it seems needless

COMMON_TOOLS_PATH = ROOT / "common" / "tools"
sys.path.insert(0, str(COMMON_TOOLS_PATH))

import coin_info


@click.command()
@click.option("-c", "--check", is_flag=True, help="Do not write, only check.")
@click.option("-r", "--remove", is_flag=True, help="Remove unrecognized files.")
def build_icons(check: bool, remove: bool):
    """Build FIDO app icons in the source tree."""

    for path, size in DESTINATIONS.items():
        build_icons_size(path, size, check, remove)


def build_icons_size(destination: Path, size: int, check: bool, remove: bool):
    icon_size = (size, size)
    checks_ok = True
    apps = coin_info.fido_info()

    total_size = 0

    for app in apps:
        if app["icon"] is None:
            if not app.get("no_icon"):
                raise click.ClickException(f"Icon not found for: {app['key']}")
            else:
                continue

        im = Image.open(app["icon"])
        resized = im.resize(icon_size, Image.BOX)
        toi = toif.from_image(resized)
        dest_path = destination / f"icon_{app['key']}.toif"

        total_size += len(toi.to_bytes())

        if not check:
            toi.save(dest_path)
        else:
            if not dest_path.exists():
                print(f"Missing TOIF: {dest_path}")
                checks_ok = False
                continue
            data = dest_path.read_bytes()
            if data != toi.to_bytes():
                print(f"Icon different from source: {dest_path}")
                checks_ok = False

    print(f"{destination.parts[-3]} icon size: {total_size} bytes")

    keys = EXCLUDE | {"icon_" + app["key"] for app in apps}
    unrecognized_files = False
    for icon_file in destination.glob("*.toif"):
        name = icon_file.stem
        if name not in keys:
            unrecognized_files = True
            if remove:
                print(f"Removing unrecognized file: {icon_file}")
                icon_file.unlink()
            else:
                print(f"Unrecognized file: {icon_file}")
                checks_ok = False

    if not remove and unrecognized_files:
        raise click.ClickException(
            "Unrecognized files found in icon directory.\n"
            "Use 'build_icons.py -r' to remove them automatically."
        )
    if not checks_ok:
        raise click.ClickException("Some checks have failed.")


if __name__ == "__main__":
    build_icons()
