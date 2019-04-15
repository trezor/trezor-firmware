# TREZOR Protocol

## version 1

Messages are sent in packets of 64 bytes.

First packet has the following structure:

| offset | length | type        | contents                                                                              |
|--------|--------|-------------|---------------------------------------------------------------------------------------|
|      0 |      3 | char[3]     | '?##' magic constant                                                                  |
|      3 |      2 | BE uint16_t | numerical [message type](messages.proto#L14)                                          |
|      5 |      4 | BE uint32_t | message size                                                                          |
|      9 |     55 | uint8_t[55] | first 55 bytes of message encoded in Protocol Buffers (padded with zeroes if shorter) |

Following packets has the following structure:

| offset | length | type        | contents                                                                               |
|--------|--------|-------------|----------------------------------------------------------------------------------------|
|      0 |      1 | char[1]     | '?' magic constant                                                                     |
|      1 |     63 | uint8_t[63] | following bytes of message encoded in Protocol Buffers (padded with zeroes if shorter) |
