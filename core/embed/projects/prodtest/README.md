# Production Test Firmware
This document outlines the production test firmware (prodtest) and its protocol.

The prodtest serves two primary purposes:

* Testing and initial provisioning of Trezor devices during production.
* Device bring-up and testing during development.

## Command Line Interface

The prodtest includes a simple text-based command-line interface that can be controlled either by automatic test equipment in a production environment or manually via a terminal application.

Pressing the ENTER key twice switches the interface to interactive mode, enabling basic line editing, autocomplete functionality (using the TAB key), and text coloring.

To exit from interactive mode type `.+ENTER`.

### Commands
These commands begin with the command name and may optionally include parameters separated by spaces.
Parameters are marked with angle brackets (`<...>`), square brackets (`[<...>]`) indicate optional parameters.

Command Format:
`command <arg1> <arg2> [<optional_arg3>]...`

Example:
```
haptic-test 500
```

To retrieve a list of all available commands, type `help`.

### Final Responses
The Trezor device responds to all commands with single-line text responses, which start with either `OK` or `ERROR`.

An `OK` response may include additional parameters separated by spaces. The number and type of parameters depend on the specific command.

Example:
```
OK 2.1.7
```

An `ERROR` response includes an error code and an optional error description enclosed in quotation marks.

Example:
```
ERROR invalid-arg "Expecting x-coordinate."
```

#### Predefined Error Codes:

While commands may define custom error codes as needed, the following are predefined:

* `error` - Unspecified error; additional details may be provided in the error description.
* `invalid-cmd` - The command name is invalid.
* `invalid-arg` - Invalid command argument.
* `abort` - Operation aborted by the user (e.g., pressing CTRL+C).
* `timeout` - The command execution timed out.

### Progress response

When a command needs to send structured data that does not fit within `OK` messages, it can use the `PROGRESS` response. A progress response line starts with `PROGRESS`, followed by any number of parameters separated by spaces.

Example:
```
PROGRESS move 107 164 24824185
PROGRESS move 107 170 24824195
PROGRESS move 107 176 24824204
PROGRESS move 107 180 24824213
PROGRESS move 107 184 24824222
```

### Debug Messages

In addition to lines beginning with `OK`, `ERROR`, or `PROGRESS`, the prodtest firmware may issue lines starting with `#`. These lines contain debug or informational traces and should be ignored by automation scripts in a production environment.

Example:
```
rgbled-set 0 255 0
# Setting the RGB LED color to [0, 255, 0]...
OK
```

## List of commands

### help
Displays a list of available commands. The command optionally accepts a prefix to filter and display only commands starting with the specified characters.

Example:
```
help otp
# Available commands (filtered):
#  otp-batch-write - Write the device batch info into OTP memory
#  otp-batch-read - Read the device batch info from OTP memory
#  otp-variant-write - Write the device variant info into OTP memory
#  otp-variant-read - Read the device variant info from OTP memory
OK
```

### ping
The `ping` command serves as a no-operation request, and the device responds with `OK` to acknowledge receipt.

`ping [<text>]`

Example:
```
ping ABC
OK ABC
```

### reboot
This command initiates device reboot.

Example:
```
reboot
OK
```


### reboot-to-bootloader
This command initiates device reboot to bootloader.

Example:
```
reboot-to-bootloader
OK
```


### boardloader-version
Retrieves the version of the boardloader. The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
boardloader-version
OK 0.2.6
```

### boardloader-update
Updates the boardloader to the supplied binary file. Only works on development boards, not in production firmware.
Use `core/tools/bin_update.py` script to update the boardloader binary.


### bootloader-version
Retrieves the version of the bootloader. The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
bootloader-version
OK 2.1.7
```

### bootloader-update
Updates the bootloader to the supplied binary file.
Use `core/tools/bld_update.py` script to update the bootloader binary.


### ble-adv-start
Starts BLE advertising. Accepts one parameter, advertising name. The command returns `OK` if the operation is successful.

`ble-adv-start <name>`

Example:
```
ble-adv-start TREZOR_BLE
# Advertising started.
OK
```

### ble-adv-stop
Stops BLE advertising. The command returns `OK` if the operation is successful.

`ble-adv-stop`

Example:
```
ble-adv-stop
# Advertising stopped.
OK
```

### ble-info
Reads info about BLE. Currently, it returns only MAC address.
The advertising needs to be started before the MAC can be read,
otherwise the address will be random and will not correspond to actual MAC used.

`ble-info`

Example:
```
ble-info
# MAC: 56:0b:b8:99:32:23
OK
```

### ble-erase-bonds
Erases all BLE bonds from the device.

Example:
```
ble-erase-bonds
# Erased 2 bonds.
OK
```

### ble-get-bonds
Retrieves all BLE bonds from the device.

Example:
```
ble-get-bonds
# Initializing the BLE...
# Got 1 bonds.
# Bond 1: 5c:dc:49:d1:8d:35
OK
```

### ble-unpair
Unpairs a BLE device. It accepts one parameter, which is index returned by the `ble-get-bonds` command.

`ble-unpair <index>`

Example:
```
ble-unpair 1
# Initializing the BLE...
# Unpaired.
OK
```

### ble-radio-test
Runs radio test proxy-client. It requires special nRF radio test firmware, see https://docs.nordicsemi.com/bundle/sdk_nrf5_v17.0.2/page/nrf_radio_test_example.html for usage.


### ble-direct-test-mode
Runs direct-test-mode test proxy-client. It requires special nRF direct-test-mode firmware. To exit, hard reset is required.


### button-test
The `button-test` command tests the functionality of the device's hardware buttons. It waits for the user to press and release a specified button in a designated timeout period.

`button-test <button> <timeout>`

* `button` specifies the expected button or combination of buttons, with possible values: `left`, `right`, `left+right`, `power`.
* `timeout` specifies the timeout duration in milliseconds

If the specified button or button combination is not detected within the timeout, the command will respond with `timeout` error.

Example (to wait for 5 seconds for the left button):
```
button-test left 5000
# Waiting for the button press...
# Waiting for the button release...
OK
```

### display-border
The `display-border` command draws a single white border around the screen on a black background.

Example:
```
display-border
# Drawing display border...
OK
```

### display-text
The `display-text` command draws text to the screen

Example:
```
display-text hello_world
OK
```

### display-bars
Draws vertical color bars on the screen according to a specified string of color codes.

`display-bars <color-string>`

* `color-string` - A string where each character represents one vertical bar and its corresponding color.

Each character in the parameter represents a vertical bar and its corresponding color (R for red, B for blue, W for white, and any other character for black). The total number of characters determines the number of bars.

NOTE: On monochromatic displays, the characters R, G, and B are all interpreted as white.

Example (to draw 6 vertical bars - red, black, green, black, blue and black):
```
display-bars RxGxBx
# Drawing 6 vertical bars...
OK
```

### display-set-backlight
Adjusts the display backlight level.

`display-set-backlight <level>`

* `level` - A value between 0 (0%) and 255 (100%).

Example:
```
display-set-backlight 128
# Updating display backlight level to 128...
OK
```

### get-cpuid
Reads a 96-bit long unique ID stored in the device's CPU. The command returns `OK` followed by a 24-digit hexadecimal value representing the unique ID.

Example:
```
get-cpuid
OK 2F0079001951354861125762
```

### haptic-test
Test the functionality of the device's haptic actuator. It takes one input parameter, representing the duration of the vibration in milliseconds.

The device only vibrates if there is motor connected to the haptic driver, otherwise the effect needs to be measured by an oscilloscope.

Example (runs the driver for 3s):
```
haptic-test 3000
# Running haptic feedback test for 3000 ms...
OK
```

### hw-revision
Retrieves the hardware revision of the device. The command returns `OK` followed by the hardware revision.

Example:
```
hw-revision
OK 1
```

### nrf-communication
Tests the internal communication between the main MCU and NRF MCU. The command returns `OK` if the communication is successful.

Example:
```
nrf-communication
# Testing SPI communication...
# Testing UART communication...
# Testing reboot to bootloader...
# Testing GPIO TRZ ready...
# Testing GPIO stay in bootloader...
# Testing GPIO reserved...
OK
```

### nrf-version
Retrieves the version of the NRF52 MCU. The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>.<tweak>`.

Example:
```
nrf-version
OK 0.1.2.3
```

### nrf-update
Updates the nRF firmware. Use `core/tools/bin_update.py` script to update the nRF application binary.


### nrf-pair
Writes the pairing secret to the nRF chip to pair it with the MCU.
This command may be called only after `secrets-init` was executed and before `secrets-lock` is executed.

Example:
```
nrf-pair
OK
```

### nrf-verify-pairing
Verifies the pairing between the main MCU and the nRF chip. The command returns `OK` if the pairing is valid, or `ERROR` if it is not.
Example:
```
nrf-verify-pairing
OK
```


### touch-draw
Starts a drawing canvas, where user can draw with finger on pen. Canvas is exited by sending CTRL+C command.
```
touch-draw
# Starting drawing canvas...
# Press CTRL+C for exit.
ERROR abort
```

### touch-test
Tests the functionality of the display's touch screen. It draws a filled rectangle in one of the four display quadrants and waits for user interaction.

`touch-test <quadrant> <timeout>`

* `quadrant` - A value between 0 and 3, determining the quadrant where the rectangle will be drawn.
* `timeout` - The timeout duration in milliseconds.

If the display is not touched within the specified timeout, the command will return a `timeout` error.

The command does not check whether the touch point lies within the quadrant or not. It only returns the x and y coordinate of the touch point.

Example (drawing a rectangle in the top-left quadrant and waiting for 5 seconds for touch input):
```
touch-test 0 5000
# Initializing the touch controller...
# Waiting for a touch for 5000 ms...
OK 68 246
```

### touch-test-custom
Tests the functionality of the display's touch screen by drawing a filled rectangle at custom coordinates and waiting for user interaction.

`touch-test-custom <x> <y> <width> <height> <timeout>`

* `x` - The x-coordinate of the top-left corner of the rectangle.
* `y` - The y-coordinate of the top-left corner of the rectangle.
* `width` - The width of the rectangle.
* `height` - The height of the rectangle.
* `timeout` - The timeout duration in milliseconds.

If the display is not touched within the specified timeout, the command returns a `timeout` error.

The device reports touch events, including coordinates and timestamps (in milliseconds). The correctness of the touch point is not validated and is left to the test equipment.

The test ends after the first lift-up event.

Example (drawing a 100x100 rectangle at position (10,10) and waiting for 15 seconds for touch input):
```
touch-test-custom 10 10 100 100 15000
# Initializing the touch controller...
# Drawing a rectangle at [10, 10] with size [100 x 100]...
# Waiting for a touch for 15000 ms...
PROGRESS start 86 76 29585228
PROGRESS move 86 77 29585738
PROGRESS move 86 88 29585811
PROGRESS end 86 90 29586085
OK
```

### touch-test-idle
Tests the functionality of the display's touch screen by verifying that no touch activity occurs within a specified time period.

`touch-test-idle <timeout>`

* `timeout` - The duration to wait, in milliseconds, during which no touch input should be detected.

If any touch activity is detected within the specified timeout, the command returns an error.

Example (wait 10 seconds to ensure no touch input is detected):
```
> touch-test-idle 10000
# Initializing the touch controller...
# Don't touch the screen for 10000 ms...
OK
```

### touch-test-power
Tests the functionality of the touch layer's power supply. This command powers up the touch layer and waits for a specified time period, allowing test equipment to perform measurements.

`touch-test-power <timeout>`

* `timeout` - The duration to keep the touch layer powered, in milliseconds.

Example (power the touch layer for 10 seconds for measurement)t):
```
> touch-test-power 10000
# Setting touch controller power for 10000 ms...
OK
```

### touch-test-sensitivity
This command evaluates the touch screen's sensitivity by drawing a filled box around the touch coordinates.

`touch-test-sensitivity <sensitivity>`

* `sensitivity` - A decimal value representing the sensitivity level, ranging from 0 to 255.

NOTE: The sensitivity value is model-dependent and may vary based on the device.

This command does not produce any output. To stop the test, you must press CTRL+C or reboot the device.

Example:
```
touch-test-sensitivity 12
# Initializing the touch controller...
# Setting touch controller sensitivity to 12...
# Running touch controller test...
# Press CTRL+C for exit.
ERROR abort
```

### touch-version
Retrieves the version of the touch screen controller if supported by the device. The command returns `OK`, followed by the version number.

Example:
```
touch-version
# Initializing the touch controller...
# Reading the touch controller version...
OK 1
```

### sdcard-test
Initiates a basic test of the SD card by writing a few blocks of data, reading them back, and verifying their integrity through comparison.

Possible error return codes are:

- `no-card` - Indicates that no SD card is present
- `error` - An I/O error occured (with additional details provided in the description field)

Example:
```
sdcard-test
OK
```

### sbu-set
Sets the logical states of SBU1 and SBU2 pins. It takes tow input parameters, representing the state (0 or 1) of each pin.

`sbu-set <sbu1> <sbu2>`

Example:
```
SBU 1 0
# Setting SBU1 to 1 and SBU2 to 0...
OK
```

### rgbled-set
The `rgbled-set` command allows you to test the functionality of the device's RGB LED. It takes three input parameters, representing the intensity of the red, green, and blue color components.
Each component is a decimal value between 0 and 255.

`rgbled-set <r> <g> <b>`

Example:
```
rgbled-set 255 0 0
# Setting the RGB LED color to [255, 0, 0]...
OK
```

### rgbled-effect-start
Start the rgb effect from the predefined list. Command takes two arguments, first argument defines a number of the rgbled effect, second argument then defines number of requested cycles for which the effect should run. `requested_cycles` argument is optional, calling the command without it will run effect indefinitely.

`rgbled-effect-start <effect_num> <requested_cycles>`

Example:
```
rgbled-effect-start 0 2
# Start RGB LED effect #0 for 2 cycles
OK
```

### rgbled-effect-stop
Stop the ongoing rgbled effect.

Examples:
```
rgbled-effect-stop
# Stop ongoing RGB LED effect
OK
```

### otp-batch-read
Retrieves the batch string from the device's OTP memory. The batch string identifies the model and production batch of the device.

If the OTP memory has not been written yet, it returns error code `no-data`.

Example:
```
otp-batch-read
# Reading device OTP memory...
# Bytes read: <hexadecimal string>
ERROR no-data "OTP block is empty."
```

### otp-batch-write
Writes the batch string to the device's OTP memory. The batch string identifies the model and production batch of the device.

The batch string can be up to 31 characters in length. The standard format is `<internal_model>-<YYMMDD>`, where YYMMDD represents the provisioning date. For Model T, the `internal_model` is `TREZOR2`.

In non-production firmware, you must include `--execute` as the last parameter to write the data to the OTP memory. Conversely, in production firmware, you can use `--dry-run` as the last parameter to simulate the command without actually writing to the OTP memory.

Example:
```
otp-batch-write T2B1-231231 --dry-run
#
# !!! It's a dry run, OTP will be left unchanged.
# !!! Use '--execute' switch to write to OTP memory.
#
# Writing info into OTP memory...
# Bytes written: 543242312D323331323331000000000000000000000000000000000000000000
# Locking OTP block...
```


### otp-device-sn-read
Retrieves the device's serial number from the device's OTP memory. The device serial number is unique for each device.
A QR code with the serial number is displayed on the prodtest screen and printed on the packaging.

If the OTP memory has not been written yet, it returns error code `no-data`.

Example:
```
otp-device-sn-read
# Reading device OTP memory...
# Bytes read: <hexadecimal string>
ERROR no-data "OTP block is empty."
```

### otp-device-sn-write
Writes the device serial number to the device's OTP memory. The device serial number is unique for each device.
A QR code with the serial number is displayed on the prodtest screen and printed on the packaging.

The serial number can be up to 31 characters in length.

In non-production firmware, you must include `--execute` as the last parameter to write the data to the OTP memory. Conversely, in production firmware, you can use `--dry-run` as the last parameter to simulate the command without actually writing to the OTP memory.

Example:
```
otp-device-sn-write 123456ABCD --dry-run
#
# !!! It's a dry run, OTP will be left unchanged.
# !!! Use '--execute' switch to write to OTP memory.
#
# Writing info into OTP memory...
# Bytes written: 3132333435364142434400000000000000000000000000000000000000000000
# Locking OTP block...
```

### otp-variant-write
Writes up to 31 decimal values, each representing device variant options, to device's OTP memory. Each value must range from 0 to 255.

This command should be called after the `optiga-lock` command was successfully completed.

Currently, three values are required during production:
`otp-variant-write <unit_color> <unit_btconly> <unit_packaging>`.

In non-production firmware, you must include `--execute` as the last parameter to write the data to the OTP memory. Conversely, in production firmware, you can use `--dry-run` as the last parameter to simulate the command without actually writing to the OTP memory.
You can also use `--rework` to fix an incorrectly written value. This is only usable once.

Example (to write 3 bytes into OTP memory):
```
otp-variant-write 2 3 5 --dry-run
#
# !!! It's a dry run, OTP will be left unchanged.
# !!! Use '--execute' switch to write to OTP memory.
#
# Writing device batch info into OTP memory...
# Bytes written: 0102030500000000000000000000000000000000000000000000000000000000
# Locking OTP block...
OK
```

### otp-variant-read
Retrieves 32 bytes stored in the device's OTP memory block, representing device variant options. Each value ranges from 0 to 255. The first byte indicates the format version, followed by the bytes written using the `otp-variant-write command`, and padded with zero bytes.

Example:
```
otp-variant-read
# Reading device OTP memory...
# Bytes read: <hexadecimal string>
OK 1 2 3 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

### prodtest-version
Retrieves the version of the prodtest firmware.
The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>.<build>`.

Example:
```
prodtest-version
OK 0.2.6.1
```

### prodtest-wipe
This command invalidates the current firmware in the flash memory by erasing its header, preventing it from starting after the next reboot. After completing this operation, it displays the text "WIPED" on the screen.

Example:
```
prodtest-wipe
OK
```


### prodtest-homescreen
Shows prodtest homescreen, which displays essential information about the device.

Example:
```
prodtest-homescreen
OK
```

### secrets-init
Generates random secrets and stores them in the protected storage.

Example:
```
secrets-init
OK
```

### secrets-lock
Locks the secret sector.

Example:
```
secrets-lock
Lock successful
OK
```

### secrets-get-mcu-device-key
Returns a cryptogram that encrypts and authenticates the device attestation public key stored in MCU. The commands `secrets-init` and `secure-channel-handshake-2` must be executed before calling this command.

Example:
```
secrets-get-mcu-device-key
OK 638c8a83ddc8fd84cddf5a0a4fa3d9615146cd341685dca942bab1132c2bc99b
```

### secrets-certdev-write
Writes the X.509 device attestation certificate issued by the Trezor Company for the attestation key stored in the MCU.
The `otp-device-sn-write` command must be executed before calling this command.

Example:
```
secrets-certdev-write <hexadecimal string>
OK
```

### secrets-certdev-read
Retrieves the X.509 device attestation certificate issued by the Trezor Company for the attestation key stored in the MCU.

Example:
```
secrets-certdev-read
OK <hexadecimal string>
```

### optiga-pair
Writes the pairing secret to the Optiga chip to pair it with the MCU. The command `secrets-init` must be executed before calling this command.

Example:
```
optiga-pair
OK
```

### optiga-id-read
Retrieves the coprocessor UID of the Optiga chip as a 27 byte hexadecimal string.

Example:
```
optiga-id-read
OK CD16339401001C000100000A023EA600190057006E801010712440
```

### optiga-certinf-read
Retrieves the X.509 certificate issued by Infineon for the Optiga chip.

Example:
```
optiga-certinf-read
OK <hexadecimal string>
```

### optiga-certdev-write
Writes the X.509 certificate issued by the Trezor Company for the device attestation key stored in Optiga.
The `otp-device-sn-write` command must be executed before calling this command.

Example:
```
optiga-certdev-write <hexadecimal string>
OK
```

### optiga-certdev-read
Retrieves the X.509 certificate issued by the Trezor Company for the device attestation key stored in Optiga.

Example:
```
optiga-certdev-read
OK <hexadecimal string>
```

### optiga-certfido-write
Writes the X.509 certificate issued by the Trezor Company for the FIDO attestation key stored in Optiga.

Example:
```
optiga-certfido-write <hexadecimal string>
OK
```

### optiga-certfido-read
Retrieves the X.509 certificate issued by the Trezor Company for the FIDO attestation key stored in Optiga.

Example:
```
optiga-certfido-read
OK <hexadecimal string>
```

### optiga-keyfido-write
Decrypts and stores an encrypted FIDO attestation private key into Optiga. No return value.

Example:
```
optiga-keyfido-write <hexadecimal string>
OK
```

### optiga-keyfido-read
Retrieves the x-coordinate of the FIDO attestation public key stored in Optiga. Can be executed only before the LOCK command is called.

This command can be used to verify that the FIDO attestation key was decrypted and stored correctly by verifying that the returned string of bytes appears in the FIDO attestation certificate.

Example:
```
optiga-keyfido-read
OK 0D35A613358EDAB4CA04D05DD716546CD97973DE58516AF6A8F69BEE89BEFAA1
```

### optiga-lock
Configures the metadata for Optiga's data objects that should be set up during provisioning and locks them.

Example:
```
optiga-lock
OK
```

### optiga-lock-check
Returns `YES` if all of Optiga's data objects that should be set up during provisioning are locked. If not, then `NO` is returned.

Example:
```
optiga-lock-check
OK YES
```

### optiga-counter-read
Retrieves the value of Optiga's security event counter as a 1 byte hexadecimal value.

Example:
```
optiga-counter-read
OK 0E
```

### pm-new-soc-estimate
Erase power manager recovery data from the backup RAM and immediately reboot the device to run new battery SoC estimate.

Example:
```
pm-new-soc-estimate
# Erasing backup RAM and rebooting...
OK
```

### pm-set-soc-target
Sets the battery state of charge (SOC) target. The SOC limit is a percentage value between 10 and 100.

The command returns `OK` if the operation is successful.

```
pm-set-soc-target 50
# Set SOC target to 50%
OK

```

### pm-report
Starts single or continuous reporting of power manager data, including voltage, current and temperature.

`pm-report`

Progress report contains these values in order:
 - power state
 - usb connected indication
 - wireless charger connected indication
 - battery voltage
 - battery current
 - battery temperature
 - battery SOC
 - battery SOC latched
 - PMIC die temperature
 - WLC voltage
 - WLC current
 - WLC die temperature
 - System voltage

Example:
```
pm-report
# Power manager report:
# Power state 5
#   USB connected
#   WLC disconnected
#   Battery voltage: 3.465 V
#   Battery current: -192.150 mA
#   Battery temperature: 32.416 C
#   Battery SoC: 72.11
#   Battery SoC latched: 72.11
#   PMIC die temperature: 58.607 C
#   WLC voltage: 0.000 V
#   WLC current: 0.000 mA
#   WLC die temperature: 0.000 C
#   System voltage: 4.449 V
PROGRESS 5 USB_connected WLC_disconnected 3.465 -192.150 32.416 72.11 72.11 58.607 0.000 0.000 0.000 4.449
OK
```

### pm-fuel-gauge-monitor
Runs continous monitor of the battery measurements and fuel gauge state of charge (vbat, ibat, ntc_temp, soc) and
prints them on display and into console. Monitor is stoped with CTRL+C.

Example:
```
pm-fuel-gauge-monitor
PROGRESS 3.465 -191.475 32.636 73.27
PROGRESS 3.465 -191.925 32.747 73.27
PROGRESS 3.465 -192.150 32.636 73.28
PROGRESS 3.460 -191.925 32.636 73.29
PROGRESS 3.465 -192.600 32.636 73.29
PROGRESS 3.465 -191.925 32.636 73.30
# aborted
OK
```

### pm-charge-enable
Enables battery charging. If a charger is connected, charging starts immediately.

Example:
```
pm-charge-enable
# Enabling battery charging @ 180mA...
OK
```

### pm-charge-disable
Disables battery charging.

Example:
```
pm-charge-disable
# Disabling battery charging...
OK
```

### pm-suspend
Enters low-power mode.

In low-power mode, the CPU retains its state, including SRAM content.

The following wake-up reasons are currently possible:
- BUTTON - the power button was pressed
- POWER - USB or WPC power was detected
- BLE - BLE communication was detected
- RTC - the RTC wake-up timer expired

```
pm-suspend [<wakeup-time>]
```

The command returns OK followed by a list of wake-up reasons, separated
by spaces.

Example:
```
pm-suspend
# Suspending the device to low-power mode...
# Press a button button to resume.

....

# Resumed to active mode.
OK BUTTON
```

### pm-hibernate
Enters Hibernate mode.

In Hibernate mode, the CPU is powered off, and only the VBAT domain remains
active. The device can be woken by pressing the power button, triggering
a full boot sequence.

Hibernate mode can only be entered if the device is not connected to a USB or
wireless charger.

Example:
```
pm-hibernate
# Hibernating the the device...
# Device is powered externally, hibernation is not possible.
OK
```

### tamper-read
Reads the state of the tamper detection inputs.
Up to 8 inputs can be read, each represented by a single bit in the response.
A set bit indicates active inputs.

Example:
```
tamper-read
OK 2
```

### tropic-get-riscv-fw-version

Reads the version of the RISC-V firmware. The command returns `OK` followed by the version.

Example:
```
tropic-get-riscv-fw-version
OK 00020100
```

### tropic-get-spect-fw-version

Reads the version of the SPECT firmware. The command returns `OK` followed by the version.

Example:
```
tropic-get-spect-fw-version
OK 00000300
```

### tropic-get-chip-id

Reads the Tropic chip ID. The command returns `OK` followed by the 128-byte serialization of `lt_chip_id_t`.

Example:
```
tropic-get-chip-id
OK 00000001000000000000000000000000000000000000000000000000000000000000000001000000054400000000FFFFFFFFFFFF01F00F000544545354303103001300000B54524F50494330312D4553FFFFFFFF000100000000FFFF000100000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF13000300
```


### tropic-update-fw

Updates Tropic firmware to the embedded version.

Example:
```
tropic-update-fw
# Silicon revision: ABAB
# Rebooting into Maintenance mode
# Chip is executing bootloader
# Updating RISC-V FW
# Updating SPECT FW
# Rebooting into Application mode
# Reading RISC-V FW version
# Chip is executing RISC-V application FW version: 1.0.0 (+ .0)
# Reading SPECT FW version
# Chip is executing SPECT FW version: 1.0.0 (+ .0)
OK
```

### tropic-certtropic-read

Reads the X.509 certificate issued by Tropic Square for the Tropic chip.

Example:
```
tropic-certtropic-read
OK  308201CB30820151A00302010202100200110308861906100F32000000045B300A06082A8648CE3D0403033047310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3119301706035504030C1054524F50494330312D54204341207631301E170D3235303730313130353533325A170D3435303730313130353533325A30173115301306035504030C0C54524F504943303120655345302A300506032B656E032100F582E78C4ECCB186D72A29B6B54E8CAD931C765DBA0C3EDE9405602CB1065246A37E307C300C0603551D130101FF04023000300E0603551D0F0101FF040403020308301F0603551D2304183016801433C711060CE80513B5677B019650644E3B43FAE7303B0603551D1F043430323030A02EA02C862A687474703A2F2F706B692E74726F7069637371756172652E636F6D2F6C332F7430312D5476312E63726C300A06082A8648CE3D0403030368003065023100C46E44F9D1FE26A4DC8AC659D1B6A9A82CEEBE9D283726633053FE410FF665073B7FB6ECE235FD8AB7F87336DDBCF96202300F919622C0A1CF6D00CF43CE4229AC44548055030566E8E03CA98B15D6B29B04DF231B9BF7006A9E28C15E88B07141893082025E308201E4A00302010202027531300A06082A8648CE3D0403033045310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3117301506035504030C0E54524F50494330312043412076313020170D3235303333313132303833305A180F32303630303333313132303833305A3047310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3119301706035504030C1054524F50494330312D542043412076313076301006072A8648CE3D020106052B8104002203620004A70C3273AE3227DC767EF0293D95CC106691E5BC9AA6C0282BAA8FD4B37CFAC30FEE0D879C32D8D9CE9B0BD7924B5C10097B8C4A5E7ED68D690185E3D128161256C01033C0293DE39A7188A72CFF9EEAF5B3B5DEE898F954C4F226C2ADE70BC6A381A230819F301D0603551D0E0416041433C711060CE80513B5677B019650644E3B43FAE730120603551D130101FF040830060101FF020100300E0603551D0F0101FF040403020106301F0603551D2304183016801443BAB7BDA7CDE728945CF142CBD2F9CD5588A93F30390603551D1F04323030302EA02CA02A8628687474703A2F2F706B692E74726F7069637371756172652E636F6D2F6C322F74303176312E63726C300A06082A8648CE3D0403030368003065023014AEC525E5E8311B5D6312CF0EBB2286700552EEBA32D641672C20F02A612B77E9FC3709C9657CEC6D82D6CDBDDE57C4023100BB9B77CCBBD9DE11086481D4BA9772C38743591E722B9E4D08A89940D879DA2447A55C15F84175C479946326E0F482AF3082028B308201ECA00302010202020BB9300A06082A8648CE3D040304304F310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3121301F06035504030C1854726F7069632053717561726520526F6F742043412076313020170D3235303333313132303832395A180F32303635303333313132303832395A3045310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3117301506035504030C0E54524F50494330312043412076313076301006072A8648CE3D020106052B81040022036200042301BE5B6ED9A858153F57C6BEBC9F37B858BC2874DDC90C1041BE6D04E7BBF24A7968F2E51173D0ACAC892E65E4FC03EA5BC4381A60154D7CD7CC6DF94591650F5FDC008919157314FC1F8D8295F1A10571DD1573E868BFECA96C92CCBB816FA381A230819F301D0603551D0E0416041443BAB7BDA7CDE728945CF142CBD2F9CD5588A93F30120603551D130101FF040830060101FF020101300E0603551D0F0101FF040403020106301F0603551D230418301680143C18AF711A6699B37914E363963FE25CF304B3BF30390603551D1F04323030302EA02CA02A8628687474703A2F2F706B692E74726F7069637371756172652E636F6D2F6C312F74737276312E63726C300A06082A8648CE3D04030403818C00308188024200BCD02D464329F3FC7DC81723B0C26437E35C2B49782BAE97432789F508B5A220240E6E3E4D12C15C3BDB15A8D3F90CDD19071E2227C4898220B2BEF584B2C20F8F024201EB854F05F9A2C5B466D798FE627C539B98703531735F7AB49546FE5CFB9DF0BF3B6985D700EFBC36DF3FF01692F0ECE98BB8DB2FBB9BF40913EA87EA121A7AD2E730820258308201BBA0030201020202012D300A06082A8648CE3D040304304F310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3121301F06035504030C1854726F7069632053717561726520526F6F742043412076313020170D3235303333313132303832355A180F32303735303333313132303832355A304F310B300906035504061302435A311D301B060355040A0C1454726F7069632053717561726520732E722E6F2E3121301F06035504030C1854726F7069632053717561726520526F6F7420434120763130819B301006072A8648CE3D020106052B8104002303818600040187CCEA62837E23092D8A7135789FCC6FBC3D35E79FC01F4F498FC5C2C409CE772F901340090403E8BA4D97E13F1E7594AC6D2F51FD2239F8D457769F378440A18000712BF16A48EA2025837BEFD0502A562FD93941D52CC40ED9553CA79B145BA585F32492BFD792EB96D949D31676CD099F19CE8848697B8C3430AF016FED985E1EB4A3423040301D0603551D0E041604143C18AF711A6699B37914E363963FE25CF304B3BF300F0603551D130101FF040530030101FF300E0603551D0F0101FF040403020106300A06082A8648CE3D04030403818A0030818602416841837339337C182A4EE896CBFD5DA5925F0026E7A6FA3DEE61F49A46B5D9856858D3D86501BE64B0F2F33B05D856DE96F57B947F49E720E875090B30C337791802412FDDB68D166510451FE4C62DBAE0CCD952DC34E03AE6617818CCD0EA28A9DFF045AA13A248A5F066B51139C9BEF471DD004DAC4F78DB56CF7B3E8D6F8F87D048D2
```

### tropic-lock-check

Returns 'YES' if the Tropic chip has been locked, otherwise returns 'NO'.

Example:
```
tropic-lock-check
OK YES
```

### tropic-pair

Pairs the MCU with the Tropic chip. This command is idempotent, meaning it can be called multiple times without changing the state of the device. This command is irreversible and cannot be undone. The command `secrets-init` must be executed before calling this command.

Example:
```
tropic-pair
OK
```

### tropic-get-access-credential

Returns a cryptogram that encrypts and authenticates the Tropic pairing private key and authenticates the Tropic public key. The commands `secrets-init` and `secure-channel-handshake-2` must be executed before calling this command.

Example:
```
tropic-get-access-credential
OK 03ca0e9d74ef59fa80a06161f3d2fceeb3e0c5e2db8182526d337aac78bad2d2ce4cacf05cdcd879843bcc43ed330199
```

### tropic-get-fido-masking-key

Returns a cryptogram that encrypts and authenticates the FIDO masking key for the Tropic chip. The commands `secrets-init` and `secure-channel-handshake-2` must be executed before calling this command.

Example:
```
tropic-get-fido-masking-key
OK dc106118a32feeef8d9211f54b9c8e9d571abe4cb104dc4ab087531cfee4574283ccf9c6f45e68be712f630d72d4999c
```

### tropic-handshake

Establishes a secure channel with the Tropic chip. Expects a handshake request as input, returns a handshake response.

```
tropic-handshake 648724356a6bb22b258557927287af52133a27b7317d3c919db23395cae03d853422af
OK 09ad6ec70806318313c903094ae8fb63698051210dfa540ea7c7f7e588601dac478eee30432063964574879dee93250d8a5049
```

### tropic-send-command

Sends a command to the Tropic chip and returns the response. The command `tropic-handshake` must be executed before calling this command.

Example:
```
tropic-send-command <hexadecimal string>
OK <hexadecimal string>
```

### tropic-certdev-read

Retrieves the X.509 certificate issued by the Trezor Company for the device attestation key stored in Tropic.

Example:
```
tropic-certdev-read
OK <hexadecimal string>
```

### tropic-certdev-write

Writes the X.509 certificate issued by the Trezor Company for the device attestation key stored in Tropic.
The `otp-device-sn-write` command must be executed before calling this command.

Example:
```
tropic-certdev-write <hexadecimal string>
OK <hexadecimal string>
```

### tropic-certfido-read

Retrieves the X.509 certificate issued by the Trezor Company for the FIDO attestation key stored in Tropic.

Example:
```
tropic-certfido-read
OK <hexadecimal string>
```

### tropic-certfido-write

Writes the X.509 certificate issued by the Trezor Company for the FIDO attestation key stored in Tropic.

Example:
```
tropic-certfido-write <hexadecimal string>
OK <hexadecimal string>
```

### tropic-keyfido-read

Retrieves the FIDO attestation public key stored in Tropic.

This command can be used to verify that the FIDO attestation key was stored correctly by verifying that the returned string of bytes appears in the FIDO attestation certificate.

Example:
```
tropic-keyfido-read
OK <hexadecimal string>
```

### tropic-lock

Configures the Tropic chip. This command is idempotent, meaning it can be called multiple times without changing the state of the device. This command is irreversible and cannot be undone. The command `tropic-pair` must be executed before calling this command.

Example:
```
tropic-lock
OK <hexadecimal string>
```

### secure-channel-handshake-1

Returns the first handshake message for establishing a secure channel between the device and HSM.

Example:
```
secure-channel-handshake-1
OK 1e85285cbf805d0418be1f502a325806f68fa07c78fd63b7b960b2d0416f8b49
```

### secure-channel-handshake-2

Establishes a secure channel between the device and HSM. Expects the second handshake message as input. The command `secure-channel-handshake-1` must be executed before calling this command.

Example:
```
secure-channel-handshake-2 e08e84b91413ad8f7b07853c8ce4c1b5547a12d9dd65f30e3adaa1e2398e0359bd7ba0e9fb2c64130c25d56abb811f72
OK
```

### tropic-stress-test

Runs a Tropic stress test that repeatedly calls `lt_session_start()`, `lt_mac_and_destroy()` and `lt_ecc_key_generate()` to test that Tropic doesn't enter alarm mode.

### wpc-info
Retrieves detailed information from the wireless power receiver, including chip identification, firmware version, configuration settings, and error status.

WARNING: The command will only succeed if the receiver is externally powered (5V present on the VOUT/VRECT test point).

Example:
```
> wpc-info
# Reading STWLC38 info...
# chip_id    0x26
# chip_rev   0x3
# cust_id    0x0
# rom_id     0x161
# patch_id   0x1299
# cfg_id     0x1026
# pe_id      0x7
# op_mode    0x2
# device_id  005A32344D3555AA021F781855AA55AA
#
# sys_err              0x0
#   core_hard_fault:   0x0
#   nvm_ip_err:        0x0
#   nvm_boot_err:      0x0
#   nvm_pe_error:      0x0
#   nvm_config_err:    0x0
#   nvm_patch_err:     0x0
#   nvm_prod_info_err: 0x0
OK 0x26 0x4 0x0 0x161 0x1645 0x1D7C 0xC 0x1 0x52353038385055AA09446D0655AA55AA 0x0
```

### wpc-update
Updates the firmware and configuration of the wireless power receiver.

WARNING: The command will only succeed if the receiver is externally powered (5V present on the VOUT/VRECT test point).

Example:
```
wpc-update
# Updating STWLC38...
# WPC update completed 800 ms
```

### nfc-read-card
Activate the NFC in reader mode for a given time. Read general information from firstly discovered NFC tag or exits on timeout.

When used without a timeout, the command will wait indefinitely for a card to be placed on the reader and will repeat the read operation
each 100ms.

Example:
```
nfc-read-card [<timeout_ms>]
# NFC activated in reader mode for <timeout_ms> ms.
# NFC card detected.
# NFC Type A: UID: %s
OK
```


### nfc-emulate-card
Activate NFC in Card Emulator mode for given time, or infinite time if no timeout is specified.

Example:
```
nfc-emulate-card [<timeout_ms>]
# Emulation started for <timeout_ms>
# Emulation over
OK
```

### nfc-write-card
Activates the NFC reader for given time. Writes the NDEF URI message into the first discovered NFC tag type A or exits on timeout.

When used without a timeout, the command will wait indefinitely for a card to be placed on the reader and will repeat the write operation
each 100ms.

Example:
```
nfc-write-card [<timeout_ms>]
# NFC reader on, put the card on the reader (timeout <timeout_ms> ms)
# Writting URI to NFC tag 7AF403
OK
```

### unit-test-run
Prodtest have capability to verify the overall firmware functionality by running built-in unit tests which should excercise the basic
features of the firmware drivers. This command will run all registered unit tests and return 'OK' if all tests passed.

Example:
```
# Running all unit tests...
# ut-pmic-battery: PASSED
# ut-pmic-init-deinit: PASSED
OK
```

### unit-test-list
List all build-in unit tests

Example:
```
# List of all registered unit tests:
# ut-pmic-battery - Test PMIC battery connection
# ut-pmic-init-deinit - Test PMIC driver initialization and deinitialization
OK
```

### rtc-timestamp
Retrieves the current RTC timestamp as a number of seconds since the device got powered up for the first time.

Example:
```
rtc-timestamp
OK 1886533
```

### rtc-set
Sets the current RTC date and time.

`rtc-set <year> <month> <day> <hour> <minute> <second>`

Example:
```
rtc-set 2025 07 03 14 23 00
OK
```

### rtc-get
Reads the current RTC date and time.

Response format:
`OK <year> <month> <day> <hour> <minute> <second> <day-of-week>`, where `day-of-week` is a number from 1 (Monday) to 7 (Sunday).

Where:

Example:
```
rtc-get
OK 2025 07 03 14 23 00 4
```
