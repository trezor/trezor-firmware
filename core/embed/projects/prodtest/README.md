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

Example:
```
ping
OK
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

### bootloader-version
Retrieves the version of the bootloader. The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
bootloader-version
OK 2.1.7
```

### bootloader-update
Updates the bootloader to the supplied binary file.


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


### ble-radio-test
Runs radio test proxy-client. It requires special nRF radio test firmware, see https://docs.nordicsemi.com/bundle/sdk_nrf5_v17.0.2/page/nrf_radio_test_example.html for usage.


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
Updates the nRF firmware.


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
# Writing device batch info into OTP memory...
# Bytes written: 543242312D323331323331000000000000000000000000000000000000000000
# Locking OTP block...
```


### otp-device-id-read
Retrieves the device ID string from the device's OTP memory. The device ID string is unique for each device.

If the OTP memory has not been written yet, it returns error code `no-data`.

Example:
```
otp-device-id-read
# Reading device OTP memory...
# Bytes read: <hexadecimal string>
ERROR no-data "OTP block is empty."
```

### otp-device-id-write
Writes the device ID string to the device's OTP memory. The device ID string is unique for each device.

The batch string can be up to 31 characters in length.

In non-production firmware, you must include `--execute` as the last parameter to write the data to the OTP memory. Conversely, in production firmware, you can use `--dry-run` as the last parameter to simulate the command without actually writing to the OTP memory.

Example:
```
otp-device-id-write 123456ABCD --dry-run
#
# !!! It's a dry run, OTP will be left unchanged.
# !!! Use '--execute' switch to write to OTP memory.
#
# Writing device batch info into OTP memory...
# Bytes written: 3132333435364142434400000000000000000000000000000000000000000000
# Locking OTP block...
```

### otp-variant-write
Writes up to 31 decimal values, each representing device variant options, to device's OTP memory. Each value must range from 0 to 255.

This command should be called after the `optiga-lock` command was successfully completed.

Currently, three values are required during production:
`otp-variant-write <unit_color> <unit_btconly> <unit_packaging>`.

In non-production firmware, you must include `--execute` as the last parameter to write the data to the OTP memory. Conversely, in production firmware, you can use `--dry-run` as the last parameter to simulate the command without actually writing to the OTP memory.

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

### optiga-certinf-write
Writes the X.509 certificate issued by the Trezor Company for the device.

Example:
```
optiga-certinf-write <hexadecimal string>
OK
```

### optiga-certdev-red
Retrieves the X.509 certificate issued by the Trezor Company for the device.

Example:
```
optiga-certdev-read
OK <hexadecimal string>
```

### optiga-certfido-write
Writes the X.509 certificate issued by the Trezor Company for the FIDO attestation key.

Example:
```
optiga-certfido-write <hexadecimal string>
OK
```

### optiga-certfido-read
Retrieves the X.509 certificate issued by the Trezor Company for the FIDO attestation key.

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

### pm-set-soc-limit
Sets the battery state of charge (SOC) limit. The SOC limit is a percentage value between 10 and 100.

The command returns `OK` if the operation is successful.

```
pm-set-soc-limit 50
# Set SOC limit to 50%
OK

```

### pm-precharge
Enables the battery charging and precharge the battery to the 3.45V. Then it disables charging and terminates.
During the precharge, command will print out power manager report into the console. CTRL+C will terminate the precharge.

Example:
```
pm-precharge
# Precharging the device ...
# Precharging the device to 3.450 V
# Power manager report:
# Power state 5
#   USB connected
#   WLC disconnected
#   Battery voltage: 3.435 V
#   Battery current: -191.700 mA
#   Battery temperature: 31.541 C
#   Battery SoC: 68.92
#   Battery SoC latched: 69.00
#   PMIC die temperature: 49.096 C
#   WLC voltage: 0.000 V
#   WLC current: 0.000 mA
#   WLC die temperature: 0.000 C
#   System voltage: 4.449 V
PROGRESS 5 USB_connected WLC_disconnected 3.435 -191.700 31.541 68.92 69.00 49.096 0.000 0.000 0.000 4.449
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

Reads the Tropic chip ID. The command returns `OK` followed by the chip ID.

Example:
```
tropic-get-chip-id
OK 00000001000000000000000000000000000000000000000000000000000000000000000001000000054400000000FFFFFFFFFFFF01F00F000544545354303103001300000B54524F50494330312D4553FFFFFFFF000100000000FFFF000100000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF13000300
```

### wpc-info
Retrieves detailed information from the wireless power receiver, including chip identification, firmware version, configuration settings, and error status.

WARNING: The command will only succeed if the receiver is externally powered (5V present on the VOUT/VRECT test point).

Example:
```
> wpc-info
# Reading STWLC38 info...
# chip_id    0x38
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
PROGRESS 0x38 0x4 0x0 0x161 0x1645 0x1D7C 0xC 0x1 0x52353038385055AA09446D0655AA55AA 0x0
OK
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



