#!/usr/bin/env python3

import click


def process_line(infile, outfile):
    line = infile.readline()
    data = [x.strip().lower() for x in line.split(',')]
    for c in data:
        if len(c) == 4:
            outfile.write(bytes((int(c, 16),)))


def jpeg_to_header(infile, outfile, name):
    outfile.write("// clang-format off\n")
    outfile.write(f'static const uint8_t {name}[] = {{\n', )

    hex_data = infile.read(1).hex()
    first = True
    while hex_data:
        if not first:
            outfile.write(' ')
        first = False
        outfile.write(f'0x{hex_data},')
        hex_data = infile.read(1).hex()
    outfile.write("\n};\n")

    byte = infile.read(1)


@click.command()
@click.argument("infile", type=click.File("rb"))
@click.argument("outfile", type=click.File("w"))
@click.argument("name", type=click.STRING)
def gen_jpeg_header(infile, outfile, name):
    jpeg_to_header(infile, outfile, name)


if __name__ == "__main__":
    gen_jpeg_header()
