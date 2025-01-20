
Current command list
------------------------------------------------------------------------

H8     - 8-bit number (hexadecimal upper-case)
b      -  bool (decimal - 0 or 1)
u8     - 8-bit number (decimal)
ts     - time in seconds (decimal)
tms    - time in milliseconds (decimal)
str    - ascii string
dd     - two decimal numbers
bb     - two binary numbers
nxH8   - n 8-bit numbers (hexadecimal upper-case)
x, y, w, h - coordinates and dimensions in pixels (decimal)

(++) unstructured data

PING                               -> OK
CPUID READ                         -> OK {3xH8}
BORDER                             -> OK
DISP {[RGBW]*}                     -> OK
BUTTON {LEFT|RIGHT|BOTH} {ms}      -> OK | ERROR TIMEOUT
TOUCH VERSION                      -> OK {u8}
TOUCH {dd}                         -> OK {x} {y} | ERROR TIMEOUT
TOUCH_CUSTOM {x} {y} {w} {h} {ts}  -> {++} OK | ERROR PARAM | ERROR TIMEOUT
TOUCH_IDLE {ts}                    -> OK | ERROR TOUCH DETECTED
TOUCH_POWER {tms}                  -> OK | ERROR PARAM
SENS {u8_d}                        -> no-response
PWM {u8_d}                         -> OK
SD                                 -> OK | ERROR {NOCARD| POWER ON | read | write | DATA MISMATCH}
SBU {bb}                           -> OK
HAPTIC {tms}                       -> OK | ERROR HAPTIC DURATION | ERROR HAPTIC
OPTIGAID READ                      -> OK {27xH8} | ERROR optiga_...
CERTINF READ                       -> OK {nxH8} | ERROR optiga_...
CERTDEV READ                       -> OK {nxH8} | ERROR optiga_...
CERTDEV WRITE {nxH8}               -> OK | ERROR optiga_... | no-response
CERTFIDO READ                      -> OK {nxH8} | ERROR optiga_...
CERTFIDO WRITE {nxH8}              -> OK | ERROR optiga_... | no-response
KEYFIDO WRITE {32xH8}              -> OK | ERROR optiga_... | no-response
KEYFIDO READ                       -> OK {32xH8} | ERROR optiga_... | no-response
LOCK                               -> OK | ERROR | no-response
CHECK LOCKED                       -> OK {YES|NO}
SEC READ                           -> OK {H8} | ERROR optiga_...
OTP READ                           -> OK {str} | OK (null)
OTP WRITE {str}                    -> OK | OK ALREADY WRITTEN
VARIANT READ                       -> OK {u8 u8 ... u8} | ERROR
VARIANT {u8 u8 ... u8}             -> OK | ERROR NOT LOCKED | ERROR {optiga...}
FIRWMARE VERSION                   -> OK {u8.u8.u8}
BOOTLOADER VERSION                 -> OK {u8.u8.u8}
WIPE                               -> OK
REBOOT                             -> no-response
PMIC INIT                          -> OK | ERROR
PMIC CHGSTART                      -> OK | ERROR
PMIC CHGSTOP                       -> OK | ERROR
PMIC CHGLIMIT {mA}                 -> OK | ERROR
PMIC BUCK {PWM|PFM|AUTO}           -> OK | ERROR
PMIC MEASURE {ts}                  -> (++) OK | ERROR
WPC EN                             -> OK | ERROR
WPC DIS                            -> OK | ERROR
WPC VEN                            -> OK | ERROR
WPC VDIS                           -> OK | ERROR
WPC MEASURE {ts}                   -> (++) OK | ERROR
WPC UPDATE                         -> (++) OK | ERROR
WPC CHIPINFO                       -> (++) OK | ERROR
SUSPEND                            -> OK


Suggested improvements
------------------------------------------------------------------------

-- unify timeouts - use milliseconds everywhere
-- never ends up without response
-- (++) progress responses prefix with PROGRESS
-- introduce comments prefixed with #...
-- get rid of inconsitency in names
-- SBU - split single {bb} argument to two arguments {b} {b}
-- TOUCH - split single {dd} argument to two arguments {dd} -> {d} {d}
-- REBOOT - response with OK and then reboot after 1-2s

Command names proposal
------------------------------------------------------------------------

ping
get-cpuid
reboot
suspend

bootloader-get-version
firmware-get-version
firmware-wipe

display-border
display-colors 
display-set-backlight

button-test

touch-get-version
touch-test
touch-test-custom
touch-test-idle
touch-set-sensitivity

haptic-test {ms}
haptic-play {ms}

sbu-set {b} {b}

optiga-get-id
optiga-get-certinf
optiga-get-certdev
optiga-set-certdev
optiga-get-certfido
optiga-set-certfido
optiga-get-keyfido
optiga-set-keyfido
optiga-lock
optiga-check-locked
optiga-get-counter

otp-get-batch
otp-set-batch
otp-get-variant
otp-set-variant

pmic-init   
pmic-start-charge
pmic-stop-charge
pmic-set-charge-limit {mA}
pmic-set-buck-mode {pwm|pfm|auto}
pmic-measure

wpc-init
wpc-enable
wpc-disable
wpc-enable-out
wpc-disable-out
wpc-measure
wpc-update 
wpc-get-info

sd-test

Error codes
------------------------------------------------------------------------

ERROR {reason-code}  - expected error
ERROR-ABORTED        - aborted by user by ctrl+c
ERROR-ARG            - invalid input argument
ERROR-FATAL          - unexpected/fatal error


Examples
------------------------------------------------------------------------

optiga-get-id
OK 55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA55AA

reboot
OK

touch-test-custom 0 0 120 120 5000
PROGRESS down 120 130
PROGRESS move 125 130
ERROR timeout



