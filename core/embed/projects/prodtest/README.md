# Production Test Firmware
This document outlines the production test firmware (prodtest) and its protocol.

The prodtest serves two primary purposes:

* Testing and initial provisioning of Trezor devices during production.
* Device bring-up and testing during development.

## Command Line Interface

The prodtest includes a simple text-based command-line interface that can be controlled either by automatic test equipment in a production environment or manually via a terminal application.

Pressing the ENTER key twice switches the interface to interactive mode, enabling basic line editing, autocomplete functionality (using the TAB key), and text coloring.

### Commands
These commands begin with the command name and may optionally include parameters separated by spaces.

Command Format:
`command <arg1> <arg2> ...`

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

### boardloader-version
Retrieves the version of the boardloader. The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
boardloader-version
OK 0.2.6
```

### bootloader-version
Retrives the version of the bootlaoder. The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
bootloader-version
OK 2.1.7
```

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
The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
prodtest-version
OK 0.2.6
```

### prodtest-wipe
This command invalidates the current firmware in the flash memory by erasing its header, preventing it from starting after the next reboot. After completing this operation, it displays the text "WIPED" on the screen.

Example:
```
prodtest-wipe
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
