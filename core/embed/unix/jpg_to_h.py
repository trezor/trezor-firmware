"""
Creates a header file containing image data.
"""

background_image = "background_R.jpg"

h_file_name = "background_R.h"

h_file_template = """\
// clang-format off
unsigned char background_R_jpg[] = {content};
unsigned int background_R_jpg_len = {length};
"""

with open(background_image, "rb") as f:
    image_data = f.read()

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
    f.write(h_file_template.format(content=content.format(image_bytes=image_bytes), length=len(image_data)))
