# Add-on Block

Fixed storage which stores an immutable binary-search tree of items.
Each item consists of a pair of pointers to binary data of arbitrary length.
These two pointers are interpreted as a `key` and a `value`.
Since items contain only pointers, multiple instances of data are stored just once.

Block contains 3 logical parts:
a) header (256 bytes)
b) binary-search tree (variable size)
c) item data (variable size)

## Header

| offset | length   | name         | description  |
|-------:|---------:|--------------|--------------|
| 0x0000 | 4        | magic        | magic `TRAB` |
| 0x0004 | 64       | sig          | signature of the whole blob (except magic and sig) |
| 0x0044 | 4        | tree_count   | number of elements in the tree |
| 0x0048 | 4        | items_size   | length of the item section |
| 0x004A | 182      | reserved     | - |

## Binary-Search Tree

Each node of the tree has the following structure:

| offset | length   | name         | description  |
|-------:|---------:|--------------|--------------|
| ...    | 2        | key_offset   | key   offset (divided by 4) |
| ...    | 2        | value_offset | value offset (divided by 4) |

# Item Data

Each item has the following structure:

| offset | length   | name         | description  |
|-------:|---------:|--------------|--------------|
| ...    | 2        | item_len     | item (key or value) length |
| ...    | 2        | item_flags   | item (key or value) flags |
| ...    | item_len | item_data    | item (key or value) data (padded to multiple of 4) |
