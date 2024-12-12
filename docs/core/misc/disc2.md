DISC 2

DISC2 is an evaluation board STM32U5G9J used for firmware development of Trezor models with the STM32U5.

The kit has accessible pins, a display, and an embedded ST-Link.

To build and flash firmware to the DISC2 target, follow these instructions:

1. Compile the firmware for the target with TREZOR_MODEL=DISC2 and BOOTLOADER_DEVEL=1

```sh
cd core
TREZOR_MODEL=DISC2 BOOTLOADER_DEVEL=1 make vendor build_boardloader build_bootloader build_firmware
```

2. Ensure that TrustZone is enabled on the DISC2 device, as explained here.

3. Connect the DISC2 ST-Link to the PC using a micro-USB cable (connector CN5).

4. Erase the DISC2 flash.
```sh
TREZOR_MODEL=DISC2 make flash_erase
```
5. Flash the freshly compiled firmware from step 1.

```sh
TREZOR_MODEL=DISC2 make flash
````
6. Reset the device (you may need to do this a couple of times) until it boots up.
