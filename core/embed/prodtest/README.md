# Production Test Firmware
This document outlines the protocol used during production for testing and the initial provisioning of Trezor devices.

## Commands and Responses
In the production environment, the test equipment sends single-line text commands.
These commands start with the command name and can optionally be followed by parameters separated by spaces.

Command Format:

`COMMAND [INARG1 [INARG2 [INARG3 ...]]]`

Example:
```
CPUID READ
```

The Trezor device responds with single-line text responses that start with either `OK` or `ERROR`, followed by output values separated by spaces.
If the device receives an unrecognized command, it responds with the text `UNKNOWN`.

Device responds with single line text response starting with words `OK` or `ERROR` optionally followed by output values delimited by spaces.
In case of unrecognized command, device responds with text `UNKNOWN`.

Response Format:

`OK [OUTARG1 [OUTARG2 [OUTARG3 ...]]]`

Example:
```
OK 2F0079001951354861125762
```

## List of commands

### PING
The `PING` command serves as a no-operation request, and the device responds with `OK` to acknowledge receipt.

Example:
```
PING
OK
```

### CPUID READ
The `CPUID READ` command reads a 96-bit long unique ID stored in the device's CPU.
The command always returns `OK` followed by a 24-digit hexadecimal value representing the unique ID.

Example:
```
CPUID READ
OK 2F0079001951354861125762
```

### BORDER
The `BORDER` command draws a single white border around the screen on a black background. This command has no input parameters and always returns `OK`.

Example:
```
BORDER
OK
```

### DISP
The `DISP` command draws vertical color bars on the screen based on a list of specified colors provided as a parameter.
Each character in the parameter represents one vertical bar and its color (R - red, B - blue, W - white, any other character - black).
The number of characters corresponds to the number of bars.

Note: On monochromatic displays R, G, B characters are interpreted as the white color.

Example (to draw 6 vertical bars - red, black, green, black, blue and black):
```
DISP RxGxB
```

### BUTTON
The `BUTTON` command tests the functionality of the device's buttons.
It waits for the user to press and release a specified button in a designated timeout period.

The command required two input parameters:
* The first parameter specifies the expected button or combination of buttons, with possible values: LEFT, RIGHT, BOTH.
* The seconds parameter specifies the timeout duration in seconds in range 1 to 9

If the specified button or button combination is not detected within the timeout, the command will return and `ERROR TIMEOUT`.

Example (to wait for 9 seconds for the left button):
```
BUTTON LEFT 9
OK
```

### TOUCH
The `TOUCH` command test the functionality of the display's touch screen.
It draws a filled rectangle in one of the four display quadrants and waits for user interaction.

The command requires two input parameters:

* The first parameter, which should be a value between 0 and 3, determines the quadrant where the rectangle will be drawn.
* The second parameter, a value between 1 and 9, represents the timeout in seconds.

If the display is not touched within the specified timeout, the command will return an `ERROR TIMEOUT`.

The command does not check whether the touch point lies within the quadrant or not. It only returns the x and y coordinate of the touch point.

Example (to draw a rectangle in the top-left quadrant and wait for 9 seconds for touch input):
```
TOUCH 09
OK 50 90
```

### SENS
The `SENS` command is used to evaluating the touch screen sensitivity.
It draws a filled box around the touch coordinates.
It takes one input parameter, a sensitivity, a decimal value representing sensitivity.
Please note that the sensitivity value is model-dependent.

It's important to mention that this command does not return any output.
A device restart is required to stop this operation.

Example:
```
SENS 12
```

### TOUCH VERSION
Allows you to read the version of the touch screen controller, if its supported by the device.
The command returns `OK` followed by the version number.

Example:
```
TOUCH VERSION
OK 167
```

### PWM
The `PWM` command sets the display backlight using PWM (Pulse Width Modulation).
This command takes one input parameter, a decimal value between 0 to 255, and adjusts the PWM output to control the display LED backlight.

Example::
```
DISP 128
OK
```

### SD
The `SD` command initiates a simple test of the SD card.
The test includes writing and reading back a few blocks of data and comparing them for equality.

Possible error return codes are:

- `ERROR NOCARD` - Indicates that no SD card is present
- `ERROR sdcard_write_blocks (n)` - Indicates a write failure to the N-th block
- `ERROR sdcard_read_blocks (n)` - Indicates a read failure from the N-th block
- `ERROR DATA MISMATCH` - Indicates a mismatch between the read data and the written data
- `OK` - Indicates that the test has passed successfully

Note: the command returns `UNKNOWN` for models without the SD card support

Example:
```
SD
OK
```

### SBU
The `SBU` command allows you to set the states of SBU1 and SBU2 pins.
It takes one input parameter, representing the state of both pins (00, 01, 10 or 11), and sets the corresponding output pins accordingly.

Example:
```
// sets SBU1 <- 1, SBU2 <- 0

SBU 10
OK
```


### HAPTIC
The `HAPTIC` command allows you to test the functionality of the device's haptic driver.
It takes one input parameter, representing the duration of the vibration in milliseconds.
The device only vibrates if there is motor connected to the haptic driver, otherwise the effect needs to be
measured by an oscilloscope.

Example:
```
// runs the driver for 3000 ms

HAPTIC 3000
OK
```

### OTP READ
The `OTP READ` command is utilized to retrieve a string parameter from the device's OTP memory.
This string typically contains information identifying the model and production batch of the device.
The command always returns OK followed by the read value.
If the OTP memory has not been written yet, it returns a special response: OK (null).

Example:
```
OTP READ
OK (null)
```

### OTP WRITE
The `OTP WRITE` command enables you to store a string parameter (which can be used to identify the model and production batch, for instance) into the device's OTP memory.
The parameter can be up to 31 characters in length.

The standard format is `<internal_model>-<YYMMDD>`, where YYMMDD represents the provisioning date. In case of Model T the `internal_model` is `TREZOR2`.

Example:
```
OTP WRITE T2B1-231231
OK
```

### VARIANT
The `VARIANT` command writes up to 31 decimal values (representing device variant options), each ranging from 0 to 255, and delimited by spaces, into the OTP memory. This command should be called after the `LOCK` command was successfully executed.

The standard format is `VARIANT <unit_color> <unit_btconly> <unit_packaging>`.

Example (to write 3 bytes into OTP memory):
```
VARIANT 3 0 2
```

### VARIANT READ
The `VARIANT READ` command allows you to read 32 bytes of stored variant data (representing device variant options), each ranging from 0 to 255, and delimited by spaces. The first byte is the format version, followed by the bytes written using the VARIANT command and padded with null bytes.

Example:
```
VARIANT READ
OK 1 3 0 2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

### FIRMWARE VERSION
Returns the version of the prodtest firmware.
The command returns `OK` followed by the version in the format `<major>.<minor>.<patch>`.

Example:
```
FIRMWARE VERSION
OK 0.2.6
```

### WIPE
This command invalidates the current firmware in the flash memory by erasing its beginning, including metadata.
After performing this operation, it displays the text "WIPED" on the screen and returns the response OK.

Example:
```
WIPE
OK
```

### REBOOT
This command initiates device reboot. No response, as the device reboots immediately after receiving the command.
Example:
```
REBOOT
```

### OPTIGAID READ
Returns the coprocessor UID of the Optiga chip as a 27 byte hexadecimal string.

Example:
```
OPTIGAID READ
OK CD16339401001C000100000A023EA600190057006E801010712440
```

### CERTINF READ
Returns the X.509 certificate issued by Infineon for the Optiga chip.

Example:
```
CERTINF READ
OK <hexadecimal string>
```

### CERTDEV WRITE
Writes the X.509 certificate issued by the Trezor Company for the device.

Example:
```
CERTDEV WRITE <hexadecimal string>
OK
```

### CERTDEV READ
Returns the X.509 certificate issued by the Trezor Company for the device.

Example:
```
CERTDEV READ
OK <hexadecimal string>
```

### CERTFIDO WRITE
Writes the X.509 certificate issued by the Trezor Company for the FIDO attestation key.

Example:
```
CERTFIDO WRITE <hexadecimal string>
OK
```

### CERTFIDO READ
Returns the X.509 certificate issued by the Trezor Company for the FIDO attestation key.

Example:
```
CERTFIDO READ
OK <hexadecimal string>
```

### KEYFIDO WRITE
Decrypts and stores an encrypted FIDO attestation private key into Optiga. No return value.

Example:
```
KEYFIDO WRITE <hexadecimal string>
OK
```

### KEYFIDO READ
Returns the x-coordinate of the FIDO attestation public key stored in Optiga. Can be executed only before the LOCK command is called.

This command can be used to verify that the FIDO attestation key was decrypted and stored correctly by verifying that the returned string of bytes appears in the FIDO attestation certificate.

Example:
```
KEYFIDO READ
OK 0D35A613358EDAB4CA04D05DD716546CD97973DE58516AF6A8F69BEE89BEFAA1
```

### LOCK
Configures the metadata for Optiga's data objects that should be set up during provisioning and locks them. No return value.

Example:
```
LOCK
OK
```

### CHECK LOCKED
Returns `YES` if all of Optiga's data objects that should be set up during provisioning are locked. If not, then `NO` is returned.

Example:
```
CHECK LOCKED
OK YES
```

### SEC READ
Returns the value of Optiga's security event counter as a 1 byte hexadecimal value.

Example:
```
SEC READ
OK 0E
```
