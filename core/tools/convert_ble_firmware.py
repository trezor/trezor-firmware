import click
import zipfile


def convert_file(archive, infile, outfile, name):
    data = archive.read(infile)
    with open(outfile, "w") as outfile:
        outfile.write("// Firmware BLOB - automatically generated\n")
        outfile.write("\n")
        outfile.write(f"#ifndef __FW_BLOB_{name}_H__\n")
        outfile.write(f"#define __FW_BLOB_{name}_H__ 1\n")
        outfile.write("\n")

        outfile.write(f"uint8_t {name}[] = " + "{")

        for i, byte in enumerate(data):
            if i % 16 == 0:
                outfile.write("\n    ")
            outfile.write("0x{:02x}, ".format(byte))

        outfile.write("\n};\n")
        outfile.write("\n")
        outfile.write("#endif\n")


@click.command()
@click.argument("infile", type=click.File("rb"))
def convert(infile):
    with zipfile.ZipFile(infile) as archive:
        convert_file(archive, "ble_firmware.bin", "./embed/firmware/dfu/ble_firmware_bin.h", "binfile")
        convert_file(archive, "ble_firmware.dat", "./embed/firmware/dfu/ble_firmware_dat.h", "datfile")


if __name__ == "__main__":
    convert()
