"""
Creates a header file containing image data.
"""

import click
import pathlib

h_file_template = """\
// clang-format off
unsigned char {name}_jpg[] = {content};
unsigned int {name}_jpg_len = {length};
"""


@click.command()
@click.argument("infile", type=click.File("rb"))
def convert(infile):

    path = pathlib.Path(infile.name)

    img_name = path.stem

    h_file_name = path.with_suffix(".h")

    image_data = infile.read()

    column_count = 12

    content = "{{\n{image_bytes}\n}}"
    image_bytes = "  "  # begin with indent
    for index, byte in enumerate(image_data, start=1):
        image_bytes += f"0x{byte:02x},"
        # If at the end of line, include a newline with indent, otherwise just space
        if index % column_count == 0:
            image_bytes += "\n  "
        else:
            image_bytes += " "

    # Get rid of trailing coma
    image_bytes = image_bytes.rstrip(", \n")

    with open(h_file_name, "w") as f:
        f.write(h_file_template.format(name=img_name, content=content.format(image_bytes=image_bytes), length=len(image_data)))


if __name__ == "__main__":
    convert()
