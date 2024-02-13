# Translations

## Overview

`Trezor` stores translated strings in `.json` files in [core/translations directory](../../../core/translations) - e.g. [de.json](../../../core/translations/de.json).

When no foreign-language is present, the English version is used - [en.json](../../../core/translations/en.json).

Translations files contain the translated strings and also all the special font characters as a link to `.json` files in [fonts](../../../core/translations/fonts) directory. Font files are not needed for `english`, which uses just default/built-in `ASCII` characters.

## Generating blobs

To generate up-to-date blobs, use `python core/translations/cli.py gen` - they will appear in `core/translations` as `translations-*.bin` files. The files contain information about the specific hardware model, language and device version.

## Uploading blobs

To upload blobs with foreign-language translations, use `trezorctl set language <blob_location>` command.

To switch the language back into `english`, use `trezorctl set language -r`.

# Translations blob format

| offset | length             | name              | description                                       | hash   |
|-------:|-------------------:|-------------------|---------------------------------------------------|--------|
| 0x0000 |                  6 | magic             | blob magic `TRTR00`                               |        |
| 0x0006 |                  2 | container\_len    | total length (up to padding)                      |        |
| 0x0008 |                  2 | header\_len       | header length                                     |        |
| 0x000A |                  2 | header\_magic     | header magic `TR`                                 |        |
| 0x000C |                  8 | language\_tag     | BCP 47 language tag (e.g. `cs-CZ`, `en-US`, ...)  | header |
| 0x0014 |                  4 | version           | 4 bytes of version (major, minor, patch, build)   | header |
| 0x0018 |                  2 | data\_len         | length of the raw data, i.e. translations + fonts | header |
| 0x001A |                 32 | data\_hash        | SHA-256 hash of the data                          | header |
| 0x003A |  `header_len - 48` | ignored           | reserved for forward compatibility                | header |
|      ? |                  2 | proof\_len        | length of merkle proof and signature in bytes     |        |
|      ? |                  1 | proof\_count      | number of merkle proof items following            |        |
|      ? | `proof_count * 20` | proof             | array of SHA-256 hashes                           |        |
|      ? |                  1 | sig\_mask         | CoSi signature mask                               |        |
|      ? |                 64 | sig               | ed25519 CoSi signature of merkle root             |        |
|      ? |                  2 | translations\_len | length of the translated strings                  | data   |
|      ? | `translations_len` | translations      | translated string data                            | data   |
|      ? |                  2 | fonts\_len        | length of the font data                           | data   |
|      ? |        `fonts_len` | fonts             | font data                                         | data   |
|      ? |                  ? | padding           | `0xff` bytes padding to flash sector boundary     |        |

## Translation data

Offsets refer to the strings field, up to the following offset. First offset is
always 0, following offset must always be equal or greater (equal denotes empty
string).

| offset | length                               | name              | description                                            |
|-------:|-------------------------------------:|-------------------|--------------------------------------------------------|
| 0x0000 | 2                                    | count             | number of offsets, excluding the sentinel              |
| 0x0002 | 2                                    | offset[0]         | offset of string id 0 in the `strings` field           |
| ...    | 2                                    | ...               |                                                        |
| ?      | 2                                    | offset[count - 1] | offset of string id `count - 1` in the `strings` field |
| ?      | 2                                    | offset[count]     | offset past the last element                           |
| ?      | `translations_len - 2 * (count + 2)` | strings           | concatenation of UTF-8 strings                         |

## Fonts

Ids must be in increasing order, offsets must be in non-decreasing order. First
offset must be 0.

| offset | length                               | name              | description                                                 |
|-------:|-------------------------------------:|-------------------|-------------------------------------------------------------|
| 0x0000 | 2                                    | count             | number of items in the offset table, excluding the sentinel |
| 0x0002 | 2                                    | id[0]             | numeric id of the first font                                |
| 0x0004 | 2                                    | offset[0]         | offset of the first font in the `fonts` field               |
| ...    | ...                                  | ...               |                                                             |
| ?      | ?                                    | id[count - 1]     | numeric id of the last font                                 |
| ?      | ?                                    | offset[count - 1] | offset of the last font in the `fonts` field                |
| ?      | ?                                    | sentinel\_id      | sentinel `0xffff`                                           |
| ?      | ?                                    | sentinel\_offset  | offset past the end of last element                         |
|        | ?                                    | fonts             | concatenation of fonts, format defined in the next section  |
| ?      | 0-3                                  | padding           | padding (any value) for alignment purposes                  |

## Font data

The format is exactly the same as the previous table, the only difference is
the interpretation of the payload.

| offset | length                               | name              | description                                                 |
|-------:|-------------------------------------:|-------------------|-------------------------------------------------------------|
| 0x0000 | 2                                    | count             | number of items in the offset table, excluding the sentinel |
| 0x0002 | 2                                    | id[0]             | id (Unicode code point) of the first glyph                  |
| 0x0004 | 2                                    | offset[0]         | offset of the first glyph in the `glyphs` field             |
| ...    | ...                                  | ...               |                                                             |
| ?      | ?                                    | id[count - 1]     | id (Unicode code point) of the last glyph                   |
| ?      | ?                                    | offset[count - 1] | offset of the last glyph in the `glyphs` field              |
| ?      | ?                                    | sentinel\_id      | sentinel `0xffff`                                           |
| ?      | ?                                    | sentinel\_offset  | offset past the end of last element                         |
|        | ?                                    | glyphs            | concatenation of glyph bitmaps                              |
| ?      | 0-3                                  | padding           | padding (any value) for alignment purposes                  |
