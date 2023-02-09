# Trezor firmware on STM32F429I-DISC1

The
[STM32F429I-DISC1](https://www.st.com/en/evaluation-tools/32f429idiscovery.html)
evaluation board has similar MCU to Trezor Model T as well as compatible touchscreen.

On the board, mini-USB is used to flash the firmware using the integrated ST-Link, as well
as power the board. The micro-USB connector is used by the firmware to communicate with
the trezor client. I.e. normally you need both cables connected.

Make sure JP1, JP2, JP3, and CN4 are fitted with jumpers (board is in this state by
default).

## Building and flashing

Follow the [normal build instructions](../build/embedded.md) however pass
`TREZOR_MODEL=DISC1` to `make`:

```
# build firmware images
make build_boardloader build_bootloader build_firmware TREZOR_MODEL=DISC1
# use openocd to flash everything through st-link
make flash
```

Reset board after command finishes.
