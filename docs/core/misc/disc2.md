DISC 2

DISC2 is an evaluation board STM32U5G9J used for firmware development of Trezor models with the STM32U5.

The kit has accessible pins, a display, and an embedded ST-Link.

To build and flash firmware to the DISC2 target, follow these instructions:

1. Compile the firmware for the target with `-m d002` and `--bootloader-devel`

```sh
xtask build boardloader -m d002 --bootloader-devel
xtask build bootloader -m d002 --bootlaoder-devel
xtask build firmware -m d002 --bootloader-devel
```

2. Ensure that TrustZone is enabled on the DISC2 device, as explained here.

3. Connect the DISC2 ST-Link to the PC using a micro-USB cable (connector CN5).

4. Erase the DISC2 flash.
```sh
xtask flash-erase -m d002
```
5. Flash the freshly compiled firmware from step 1.

```sh
xtask flash boardloader -m d002
xtask flash bootloader -m d002
xtask flash firmware -m d002
````
6. Reset the device (you may need to do this a couple of times) until it boots up.
