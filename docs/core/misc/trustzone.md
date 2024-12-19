

# TrustZone

New Trezor models are built on the STM32U5 series microcontrollers, which are based on the ARM Cortex-M33 and provide advanced security features, such as TrustZone.

When building firmware for such a device (Blank Trezor device or DISC2 evaluation kit), you need to ensure that TrustZone is enabled in the STM32 microcontroller’s option bytes.

## Enable TrustZone in STM32 Option Bytes

1.  Download and install [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html#st-get-software).


2.  Connect the device via ST-Link (DISC2 has an embedded ST-Link; for Trezor devices, use an external one).

3.  Power on the device (connect via USB).

4.  Open STM32CubeProgrammer and connect to the device.

5.  Open the Option Bytes (OB) tab.

6.  In the User Configuration tab, enable TZEN, then press Apply.

7.  In the Boot Configuration tab, change the SECBOOTADD0 address to 0x0C004000, then press Apply.

8.  Disconnect the ST-Link and reset the device.
