from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO, TextIO

from trezorlib import toif

HERE = Path(__file__).parent
CORE_DIR = HERE.parent.parent


def process_line(infile: TextIO, outfile: BinaryIO) -> None:
    line = infile.readline()
    data = [x.strip().lower() for x in line.split(',')]
    for c in data:
        if len(c) == 4:
            outfile.write(bytes((int(c, 16),)))


def header_to_toif(path: str | Path) -> str:
    with open(path, "r") as infile, open('tmp.toif', "wb") as outfile:
        infile.readline()
        name_line = infile.readline()
        name = name_line.split(" ")[3].split("[")[0]
        infile.readline()
        magic_line = infile.readline().split(',')[3]

        outfile.write(bytes((0x54,)))
        outfile.write(bytes((0x4f,)))
        outfile.write(bytes((0x49,)))
        if "g" in magic_line:
            outfile.write(bytes((ord('g'),)))
        elif "G" in magic_line:
            outfile.write(bytes((ord('G'),)))
        elif "f" in magic_line:
            outfile.write(bytes((ord('f'),)))
        elif "F" in magic_line:
            outfile.write(bytes((ord('F'),)))
        else:
            print(magic_line)
            raise Exception("Unknown format")

        infile.readline()
        process_line(infile, outfile)
        infile.readline()
        process_line(infile, outfile)
        infile.readline()
        process_line(infile, outfile)
        infile.readline()
    return name


def toif_to_header(path: str | Path, name: str) -> None:
    with open('tmp_c.toif', "rb") as infile, open(path, "w") as outfile:
        b = infile.read(4)
        outfile.write("// clang-format off\n")
        outfile.write(f'static const uint8_t {name}[] = {{\n',)
        outfile.write("    // magic\n",)
        if b[3] == ord('f'):
            outfile.write("    'T', 'O', 'I', 'f',\n",)
        elif b[3] == ord('F'):
            outfile.write("    'T', 'O', 'I', 'F',\n",)
        elif b[3] == ord('g'):
            outfile.write("    'T', 'O', 'I', 'g',\n",)
        elif b[3] == ord('G'):
            outfile.write("    'T', 'O', 'I', 'G',\n",)
        else:
            raise Exception("Unknown format")

        outfile.write("    // width (16-bit), height (16-bit)\n",)
        outfile.write("    ")
        for i in range(4):
            hex_data = infile.read(1).hex()
            outfile.write(f'0x{hex_data},')
            if i != 3:
                outfile.write(' ')
        outfile.write("\n")

        outfile.write("    // compressed data length (32-bit)\n",)
        outfile.write("    ")
        for i in range(4):
            hex_data = infile.read(1).hex()
            outfile.write(f'0x{hex_data},')
            if i != 3:
                outfile.write(' ')
        outfile.write("\n")

        outfile.write("    // compressed data\n",)
        outfile.write("    ")
        hex_data = infile.read(1).hex()
        first = True
        while hex_data:
            if not first:
                outfile.write(' ')
            first = False
            outfile.write(f'0x{hex_data},')
            hex_data = infile.read(1).hex()
        outfile.write("\n};\n")

        _byte = infile.read(1)


def reformat_c_icon(path: str | Path) -> None:
    name = header_to_toif(path)
    with open("tmp.toif", "rb") as f:
        toi = toif.from_bytes(f.read())
        im = toi.to_image()
    with open("tmp_c.toif", "wb") as f:
        toi = toif.from_image(im)
        f.write(toi.to_bytes())
    toif_to_header(path, name)

    os.remove("tmp.toif")
    os.remove("tmp_c.toif")


def reformat_c_icons(p: str | Path) -> None:
    files = os.listdir(p)
    for file in files:
        if file.startswith("icon_") and file.endswith(".h"):
            reformat_c_icon(os.path.join(p, file))


def reformat_toif_icon(p: str | Path) -> None:
    with open(p, "rb") as f:
        toi = toif.from_bytes(f.read())
        im = toi.to_image()
    with open(p, "wb") as f:
        toi = toif.from_image(im)
        f.write(toi.to_bytes())


def reformat_toif_icons(p: str | Path) -> None:
    files = os.listdir(p)
    for file in files:
        if file.endswith(".toif"):
            reformat_toif_icon(os.path.join(p, file))


def change_icon_format():
    # bootloader icons
    reformat_c_icons(CORE_DIR / "embed/projects/bootloader")

    # bootloader_ci icons
    reformat_c_icons(CORE_DIR / "embed/projects/bootloader_ci")

    # rust icons
    reformat_toif_icons(CORE_DIR / "embed/rust/src/ui/layout_caesar/res")
    reformat_toif_icons(CORE_DIR / "embed/rust/src/ui/layout_bolt/res")

    # python icons
    reformat_toif_icons(CORE_DIR / "src/trezor/res")
    reformat_toif_icons(CORE_DIR / "src/trezor/res/header_icons")

    # vendor header icons
    reformat_toif_icon(CORE_DIR / "embed/vendorheader/vendor_satoshilabs.toif")
    reformat_toif_icon(CORE_DIR / "embed/vendorheader/vendor_unsafe.toif")

    # additional python icons
    # reformat_toif_icon(CORE_DIR / "src/apps/homescreen/res/bg.toif") - unchanged - using as avatar
    reformat_toif_icon(CORE_DIR / "src/apps/management/res/small-arrow.toif")
    reformat_toif_icon(CORE_DIR / "src/apps/webauthn/res/icon_webauthn.toif")


if __name__ == "__main__":
    change_icon_format()
