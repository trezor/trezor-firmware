# Trezor T Memory Layout

## Flash

| sector    | range                   |  size   | function
|-----------|-------------------------|--------:|----------------------
| Sector  0 | 0x08000000 - 0x08003FFF |  16 KiB | boardloader (1st stage) (write-protected)
| Sector  1 | 0x08004000 - 0x08007FFF |  16 KiB | boardloader (1st stage) (write-protected)
| Sector  2 | 0x08008000 - 0x0800BFFF |  16 KiB | boardloader (1st stage) (write-protected)
| Sector  3 | 0x0800C000 - 0x0800FFFF |  16 KiB | unused
| Sector  4 | 0x08010000 - 0x0801FFFF |  64 KiB | storage area #1
| Sector  5 | 0x08020000 - 0x0803FFFF | 128 KiB | bootloader (2nd stage)
| Sector  6 | 0x08040000 - 0x0805FFFF | 128 KiB | firmware
| Sector  7 | 0x08060000 - 0x0807FFFF | 128 KiB | firmware
| Sector  8 | 0x08080000 - 0x0809FFFF | 128 KiB | firmware
| Sector  9 | 0x080A0000 - 0x080BFFFF | 128 KiB | firmware
| Sector 10 | 0x080C0000 - 0x080DFFFF | 128 KiB | firmware
| Sector 11 | 0x080E0000 - 0x080FFFFF | 128 KiB | firmware
| Sector 12 | 0x08100000 - 0x08103FFF |  16 KiB | unused
| Sector 13 | 0x08104000 - 0x08107FFF |  16 KiB | unused
| Sector 14 | 0x08108000 - 0x0810BFFF |  16 KiB | unused
| Sector 15 | 0x0810C000 - 0x0810FFFF |  16 KiB | unused
| Sector 16 | 0x08110000 - 0x0811FFFF |  64 KiB | storage area #2
| Sector 17 | 0x08120000 - 0x0813FFFF | 128 KiB | firmware extra
| Sector 18 | 0x08140000 - 0x0815FFFF | 128 KiB | firmware extra
| Sector 19 | 0x08160000 - 0x0817FFFF | 128 KiB | firmware extra
| Sector 20 | 0x08180000 - 0x0819FFFF | 128 KiB | firmware extra
| Sector 21 | 0x081A0000 - 0x081BFFFF | 128 KiB | firmware extra
| Sector 22 | 0x081C0000 - 0x081DFFFF | 128 KiB | firmware extra
| Sector 23 | 0x081E0000 - 0x081FFFFF | 128 KiB | firmware extra

## OTP

| block    | range                   | size | function
|----------|-------------------------|------|--------------------------------
| block  0 | 0x1FFF7800 - 0x1FFF781F | 32 B | device batch (week of manufacture)
| block  1 | 0x1FFF7820 - 0x1FFF783F | 32 B | bootloader downgrade protection
| block  2 | 0x1FFF7840 - 0x1FFF785F | 32 B | vendor keys lock
| block  3 | 0x1FFF7860 - 0x1FFF787F | 32 B | entropy/randomness
| block  4 | 0x1FFF7880 - 0x1FFF789F | 32 B | unused
| block  5 | 0x1FFF78A0 - 0x1FFF78BF | 32 B | unused
| block  6 | 0x1FFF78C0 - 0x1FFF78DF | 32 B | unused
| block  7 | 0x1FFF78E0 - 0x1FFF78FF | 32 B | unused
| block  8 | 0x1FFF7900 - 0x1FFF791F | 32 B | unused
| block  9 | 0x1FFF7920 - 0x1FFF793F | 32 B | unused
| block 10 | 0x1FFF7940 - 0x1FFF795F | 32 B | unused
| block 11 | 0x1FFF7960 - 0x1FFF797F | 32 B | unused
| block 12 | 0x1FFF7980 - 0x1FFF799F | 32 B | unused
| block 13 | 0x1FFF79A0 - 0x1FFF79BF | 32 B | unused
| block 14 | 0x1FFF79C0 - 0x1FFF79DF | 32 B | unused
| block 15 | 0x1FFF79E0 - 0x1FFF79FF | 32 B | unused

## RAM

| region  | range                   |  size   | function
|---------|-------------------------|--------:|----------------------
| CCMRAM  | 0x10000000 - 0x1000FFFF |  64 KiB | Core Coupled Memory
| SRAM1   | 0x20000000 - 0x2001BFFF | 112 KiB | General Purpose SRAM
| SRAM2   | 0x2001C000 - 0x2001FFFF |  16 KiB | General Purpose SRAM
| SRAM3   | 0x20020000 - 0x2002FFFF |  64 KiB | General Purpose SRAM
