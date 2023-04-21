# Core-specific snippets

## [decombine.py](decombine.py)

Take a `combined.bin` file which is the output of `core/tools/combine_firmware`,
split it back into original parts, and verify that there is no unnaccounted for noise.

## [change_icon_format.py](change_icon_format.py)

Converts all TOIF icons from the old endianity to the new one.
