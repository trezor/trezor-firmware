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

## Version compatibility

Each translation blob carries a format version encoded in its magic bytes (`TRTR00`, `TRTR01`, `TRTR02`, ...). Firmware validates the magic and will reject blobs whose version it does not support. This means that **downgrading firmware may result in translations being dropped**: for example, if the currently installed translation blob is v2 but the older firmware you are downgrading to only supports v0 and v1, it will not accept the blob and will fall back to English until a compatible blob is installed.

# Translations blob format (v2)

| offset | length                           | name                           | description                                       | hash   |
|-------:|---------------------------------:|--------------------------------|---------------------------------------------------|--------|
| 0x0000 |                                6 | magic                          | blob magic `TRTR02`                               |        |
| 0x0006 |                                4 | container\_len                 | total length (up to padding)                      |        |
| 0x000A |                                2 | header\_len                    | header length                                     |        |
| 0x000C |                                2 | header\_magic                  | header magic `TR`                                 |        |
| 0x000E |                                8 | language\_tag                  | BCP 47 language tag (e.g. `cs-CZ`, `en-US`, ...)  | header |
| 0x0016 |                                4 | model                          | 4-byte model identifier (e.g. `T2T1`, `T2B1`, ...) | header |
| 0x001A |                                4 | version                        | 4 bytes of version (major, minor, patch, build)   | header |
| 0x001E |                                4 | data\_len                      | length of the raw data, i.e. translations + fonts + kernings | header |
| 0x0022 |                               32 | data\_hash                     | SHA-256 hash of the data                          | header |
| 0x0042 |                `header_len - 54` | ignored                        | reserved for forward compatibility                | header |
|      ? |                                2 | proof\_len                     | length of merkle proof and signature in bytes     |        |
|      ? |                                1 | proof\_count                   | number of merkle proof items following            |        |
|      ? |               `proof_count * 32` | proof                          | array of SHA-256 hashes                           |        |
|      ? |                                1 | sig\_mask                      | CoSi signature mask                               |        |
|      ? |                               64 | sig                            | ed25519 CoSi signature of merkle root             |        |
|      ? |                                2 | translations\_chunks\_count    | number of translated strings chunks               | data   |
|      ? |                                2 | 1st\_translations\_chunk\_len  | length of the 1st translated strings chunk        | data   |
|      ? |    1st\_translations\_chunk\_len | 1st\_translations\_chunk       | 1st translated string chunk data                  | data   |
|      ? |                                2 | 2nd\_translations\_chunk\_len  | length of the 2nd translated strings chunk        | data   |
|      ? |    2nd\_translations\_chunk\_len | 2nd\_translations\_chunk       | 2nd translated string chunk data                  | data   |
|      ? |                              ... | ...                            | ...                                               | data   |
|      ? |                                2 | last\_translations\_chunk\_len | last translated string chunk data                 | data   |
|      ? |   last\_translations\_chunk\_len | last\_translations\_chunk      | length of the last translated strings chunk       | data   |
|      ? |                                2 | fonts\_len                     | length of the font data                           | data   |
|      ? |                       fonts\_len | fonts                          | font data                                         | data   |
|      ? |                                2 | kernings\_len                  | length of the kerning data                        | data   |
|      ? |                    kernings\_len | kernings                       | kerning data                                      | data   |
|      ? |                                ? | padding                        | `0xff` bytes padding to flash sector boundary     |        |

The v2 format extends v1 by appending a kerning section (`kernings_len` + `kernings`) after the font data, and the `data_hash` covers translations + fonts + kernings together. The blob magic changes from `TRTR01` to `TRTR02`.

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

## Kernings

The kerning section uses the same outer table structure as the fonts section:
ids are font ids in increasing order, each value is a kerning list for that
font. First offset must be 0.

| offset | length                               | name              | description                                                        |
|-------:|-------------------------------------:|-------------------|--------------------------------------------------------------------|
| 0x0000 | 2                                    | count             | number of items in the offset table, excluding the sentinel        |
| 0x0002 | 2                                    | id[0]             | numeric id of the first font with kerning data                     |
| 0x0004 | 2                                    | offset[0]         | offset of the first kerning list in the `kernings` field           |
| ...    | ...                                  | ...               |                                                                    |
| ?      | ?                                    | id[count - 1]     | numeric id of the last font with kerning data                      |
| ?      | ?                                    | offset[count - 1] | offset of the last kerning list in the `kernings` field            |
| ?      | ?                                    | sentinel\_id      | sentinel `0xffff`                                                  |
| ?      | ?                                    | sentinel\_offset  | offset past the end of last element                                |
|        | ?                                    | kernings          | concatenation of kerning lists, format defined in the next section |
| ?      | 0-3                                  | padding           | padding (any value) for alignment purposes                         |

## Kerning list data

Each entry in the kerning table is a two-level kerning list for one font.

| offset | length                  | name                  | description                                                                     |
|-------:|------------------------:|-----------------------|---------------------------------------------------------------------------------|
| 0x0000 | 2                        | data\_bytes           | total byte length of the remaining kerning data (index + pairs)                 |
| 0x0002 | 2                        | index\_count          | number of index entries                                                         |
| 0x0004 | `4 * index_count`        | index entries         | sorted by `left_cp`; each entry is `u16 left_cp, u16 count` (4 bytes)          |
| ?      | 2                        | pair\_count           | number of kerning pair entries                                                  |
| ?      | `4 * pair_count`         | pairs                 | each entry is `u16 right_cp, i8 kern_val, u8 pad` (4 bytes)                    |
| ?      | 0-1                      | padding               | padding (any value) for alignment purposes                                      |

For a given left codepoint, its index entry gives a `count` of consecutive pair
entries. The start offset into the pairs array for index entry `i` is the sum of
`count` values for all preceding index entries. `kern_val` is a signed pixel
adjustment to apply between the left and right glyph.

# Previous versions

## Translations blob format (v1)

| offset | length                           | name                           | description                                       | hash   |
|-------:|---------------------------------:|--------------------------------|---------------------------------------------------|--------|
| 0x0000 |                                6 | magic                          | blob magic `TRTR01`                               |        |
| 0x0006 |                                4 | container\_len                 | total length (up to padding)                      |        |
| 0x000A |                                2 | header\_len                    | header length                                     |        |
| 0x000C |                                2 | header\_magic                  | header magic `TR`                                 |        |
| 0x000E |                                8 | language\_tag                  | BCP 47 language tag (e.g. `cs-CZ`, `en-US`, ...)  | header |
| 0x0016 |                                4 | version                        | 4 bytes of version (major, minor, patch, build)   | header |
| 0x001A |                                4 | data\_len                      | length of the raw data, i.e. translations + fonts | header |
| 0x001E |                               32 | data\_hash                     | SHA-256 hash of the data                          | header |
| 0x003E |                `header_len - 46` | ignored                        | reserved for forward compatibility                | header |
|      ? |                                2 | proof\_len                     | length of merkle proof and signature in bytes     |        |
|      ? |                                1 | proof\_count                   | number of merkle proof items following            |        |
|      ? |               `proof_count * 32` | proof                          | array of SHA-256 hashes                           |        |
|      ? |                                1 | sig\_mask                      | CoSi signature mask                               |        |
|      ? |                               64 | sig                            | ed25519 CoSi signature of merkle root             |        |
|      ? |                                2 | translations\_chunks\_count    | number of translated strings chunks               | data   |
|      ? |                                2 | 1st\_translations\_chunk\_len  | length of the 1st translated strings chunk        | data   |
|      ? |    1st\_translations\_chunk\_len | 1st\_translations\_chunk       | 1st translated string chunk data                  | data   |
|      ? |                                2 | 2nd\_translations\_chunk\_len  | length of the 2nd translated strings chunk        | data   |
|      ? |    2nd\_translations\_chunk\_len | 2nd\_translations\_chunk       | 2nd translated string chunk data                  | data   |
|      ? |                              ... | ...                            | ...                                               | data   |
|      ? |                                2 | last\_translations\_chunk\_len | last translated string chunk data                 | data   |
|      ? |   last\_translations\_chunk\_len | last\_translations\_chunk      | length of the last translated strings chunk       | data   |
|      ? |                                2 | fonts\_len                     | length of the font data                           | data   |
|      ? |                       fonts\_len | fonts                          | font data                                         | data   |
|      ? |                                ? | padding                        | `0xff` bytes padding to flash sector boundary     |        |

## Translations blob format (v0)

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
|      ? | `proof_count * 32` | proof             | array of SHA-256 hashes                           |        |
