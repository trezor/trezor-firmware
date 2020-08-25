#!/usr/bin/env python3

from pathlib import Path
import sys

import click
from PIL import Image

from trezorlib import toif

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent

ICON_SIZE = (64, 64)
DESTINATION = ROOT / "core" / "src" / "apps" / "webauthn" / "res"
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
def build_icons(check, remove):
    """Build FIDO app icons in the source tree."""

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
        resized = im.resize(ICON_SIZE, Image.BOX)
        toi = toif.from_image(resized)
        dest_path = DESTINATION / f"icon_{app['key']}.toif"

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

    print(f"Total icon size: {total_size} bytes")

    keys = EXCLUDE | {"icon_" + app["key"] for app in apps}
    unrecognized_files = False
    for icon_file in DESTINATION.glob("*.toif"):
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
