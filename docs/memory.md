#Memory Layout

##Flash

| sector    | range                   |  size   | function
|-----------|-------------------------|--------:|----------------------
| Sector  0 | 0x08000000 - 0x08003FFF |  16 KiB | bootloader 1st stage (write-protected)
| Sector  1 | 0x08004000 - 0x08007FFF |  16 KiB | bootloader 1st stage (write-protected)
| Sector  2 | 0x08008000 - 0x0800BFFF |  16 KiB | storage area
| Sector  3 | 0x0800C000 - 0x0800FFFF |  16 KiB | storage area
| Sector  4 | 0x08010000 - 0x0801FFFF |  64 KiB | bootloader 2nd stage
| Sector  5 | 0x08020000 - 0x0803FFFF | 128 KiB | firmware
| Sector  6 | 0x08040000 - 0x0805FFFF | 128 KiB | firmware
| Sector  7 | 0x08060000 - 0x0807FFFF | 128 KiB | firmware
| Sector  8 | 0x08080000 - 0x0809FFFF | 128 KiB | firmware
| Sector  9 | 0x080A0000 - 0x080BFFFF | 128 KiB | firmware
| Sector 10 | 0x080C0000 - 0x080DFFFF | 128 KiB | firmware
| Sector 11 | 0x080E0000 - 0x080FFFFF | 128 KiB | firmware

##RAM

| region  | range                   |  size   | function
|---------|-------------------------|--------:|----------------------
| CCM RAM | 0x10000000 - 0x1000FFFF |  64 KiB | Core Coupled Memory
| SRAM1   | 0x20000000 - 0x2001BFFF | 112 KiB | General Purpose SRAM
| SRAM2   | 0x2001C000 - 0x2001FFFF |  16 KiB | General Purpose SRAM
