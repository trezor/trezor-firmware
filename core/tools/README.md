# Scripts for managing the project

This directory contains various scripts that are used either in some of the make
targets, or manually, to generate code, check its size, etc.

## Most used tools

### `headertool`

Lives in `trezor_core_tools/headertool.py` and is exposed as a CLI tool by the same
name.

Headertool can generate, analyze, and modify vendor and firmware headers. Use
`headertool --help` to get the full list of commands.

The most common usage is `headertool somefile.bin` that will dump header information.

Another useful feature is `headertool -V vendor_header.bin firmware.bin`, which will
replace the embedded vendor header in `firmware.bin` with the one in
`vendor_header.bin`.

### `build_mocks`

Generate `.pyi` stubs from C and Rust source files.

### `build_templates`

Regenerate sources from Mako templates.

### `build_vendorheader`

Generate a vendor header binary from a json description.

### `combine_firmware`

Combine a flashable image from a boardloader, bootloader, and firmware.

## Everything else

### `codegen`

Code generation tool for fonts, the loader graphic (deprecated) and cryptographic keys
(also deprecated).

### `dialog-designer`

Deprecated tool to visually preview multi-line dialogs in the old Trezor T UI.

### `gdb_scripts`

Scripts for GDB debugger.

### `hid-bridge`

Tool that creates a virtual HID device bridged to a UDP. This allows using the emulator
as a FIDO/U2F authenticator in a browser.

### `size`

Scripts to examine size of firmware.

### `snippets`

Ad-hoc scripts for various one-off tasks that could become useful again.

(the whole thing is prooobably deprecated by LLMs, which will regenerate any script on
demand).

### `translations`

Tools for checking validity of translation data and its usage.

### `trezor_core_tools`

A Python package that exposes certain functionalities as CLI commands.

`headertool` and `combine_firmware` live here, more may be moved or added.

Additional tools are `layout_parser`, which is used to extract memory layout
information from a model `.h` file, and related tool `lsgen` to generate linker script files
from the model `.h`.

### `alloc.py`

Generate a HTML report of allocation count per line of code, as captured when running
`emu.py -p`.

### `analyze-memory-dump.py`

Generate a HTML report of a state of the Micropython GC heap, as captured by
`trezor.utils.mem_dump` at some execution point.

### `build_icons.py`

Regenerate embedded TOIF icons for webauthn apps from png files.

### `coverage-report`

Combine coverage reports from multiple CI jobs and generate a report.

### `frozen_mpy_translator.py`

Translate bytecode instructions in frozen_mpy.c to human readable form.

### `generate_vendorheader.sh`

Uses `build_vendorheader` to rebuild all vendor headers for all models.

### `jpg_to_h.py`

Convert a JPG image to a C array that can be embedded into the firmware.

(TODO could we replace it with xxd -i?)

### `display_image_converter.py`

Converts a regular image into a sequence of `display-image begin/chunk/end`
commands for prodtest.

Example:

`python core/tools/display_image_converter.py input.png --width 240 --height 320 > upload.txt`

Then paste `upload.txt` content into the prodtest CLI session.

You can also send commands directly to a connected prodtest CLI tty:

`python core/tools/display_image_converter.py input.png --width 240 --height 320 --tty /dev/ttyACM1`

To generate a C header for embedding an image into the firmware (see `display-slideshow` below):

`python core/tools/display_image_converter.py input.png --width 240 --height 320 --output-c prodtest_img_NAME.h --symbol prodtest_img_NAME`

### `display_image_upload.py`

Uploads a single image to prodtest over serial by issuing `display-image begin/chunk/end`
commands.

Example:

`python core/tools/display_image_upload.py /dev/ttyACM1 input.png --width 240 --height 320`

Key options: `--chunk-size` controls bytes per chunk (default: 4085), `--timings`
prints conversion and transfer throughput statistics.

### `display_image_slideshow.py`

Sends a directory of images to prodtest one by one as a slideshow, with a configurable
pause between each image.  The serial port is kept open for the entire run.

Example:

`python core/tools/display_image_slideshow.py /dev/ttyACM1 images/ --width 240 --height 320`

Key options: `--delay 5` changes the pause between images (default: 10 s), `--loop`
cycles indefinitely, `--backlight LEVEL` sets the display backlight (0–255) before the
slideshow starts.

### `display-slideshow` prodtest command

The prodtest firmware has a built-in `display-slideshow` command that cycles through
images embedded directly in the firmware.  Advance to the next image by touching the
screen or pressing a button; pass a timeout in milliseconds to advance automatically.
Send any input from the terminal to exit early at any time:

```
display-slideshow                           # wait for touch/button input
display-slideshow 3000                      # advance every 3 seconds automatically
display-slideshow --loop                    # loop indefinitely, manual advance; send any terminal input to exit
display-slideshow 3000 --loop               # loop indefinitely, auto-advance every 3 s; send any terminal input to exit
display-slideshow --backlight 200           # set backlight to 200 before starting
display-slideshow 3000 --loop --backlight 200  # combine options freely
```

#### Adding an image to the slideshow

1. Convert the source image to a C header:

   ```
   cd core/tools
   python display_image_converter.py MY_IMAGE.png \
       --width 240 --height 320 \
       --output-c ../embed/projects/prodtest/cmd/prodtest_img_MY_IMAGE.h \
       --symbol prodtest_img_MY_IMAGE
   ```

2. Add an `#include` line in `core/embed/projects/prodtest/cmd/prodtest_display_images.h`:

   ```c
   #include "prodtest_img_MY_IMAGE.h"
   ```

3. Add an entry to the `PRODTEST_IMAGES[]` array in the same file:

   ```c
   {"My Image Label", prodtest_img_MY_IMAGE_WIDTH, prodtest_img_MY_IMAGE_HEIGHT, prodtest_img_MY_IMAGE},
   ```

4. Rebuild the prodtest firmware:

   ```
   .venv/bin/xtask build --model T3W1 --board lx200d2406a prodtest
   ```

#### Removing an image from the slideshow

Remove the corresponding `#include` line and the entry from `PRODTEST_IMAGES[]` in
`prodtest_display_images.h`, then delete the `.h` file and rebuild.

### `make_cmakelists.py`

Generate a CMakeLists.txt file for the core.

### `provision_device.py`

Run the provisioning flow on a prodtest firmware, against a staging provisioning server.
