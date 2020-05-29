# Internationalization (i18n) Block

Fixed storage for array of "bytes" values meant to store localization strings
and other internationalization data.

The block consists of 3 logical parts:

1. header (256 bytes)
2. items section (variable size)
3. values section (variable size)

## Header

This section has always 256 bytes.

| offset | length   | name            | description  |
|-------:|---------:|-----------------|--------------|
| 0x0000 | 4        | `magic`         | magic `TRIB` |
| 0x0004 | 4        | `items_count`   | number of stored items |
| 0x0008 | 4        | `values_size`   | length of the values section |
| 0x000C | 32       | `data_hash`     | hash of the items + values sections |
| 0x002C | 4        | `code`          | BCP-47 language code without dash (e.g. "csCZ") |
| 0x0030 | 32       | `label`         | block label (e.g. "Czech") |
| 0x0050 | 112      | `reserved`      | - |
| 0x00C0 | 64       | `sig`           | signature of the header |

## Items Section

This section has size `4 * items_count`

Each item has the following structure:

| offset | length   | name     | description  |
|-------:|---------:|----------|--------------|
| ...    | 2        | `offset` | offset of the data in the values section (divided by 4) |
| ...    | 2        | `length` | length of the data in the values section |

## Values Section

This section has size `values_size`

Each value has the following structure:

| offset | length   | name   | description  |
|-------:|---------:|--------|--------------|
| ...    | variable | `data` | value data (padded to multiple of 4) |
