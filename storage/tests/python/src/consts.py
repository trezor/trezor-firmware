# ----- PIN and encryption related ----- #

# App ID where PIN log is stored.
PIN_APP_ID = 0x00

# Storage key of the combined salt, EDEK, ESEK and PIN verification code entry.
EDEK_ESEK_PVC_KEY = (PIN_APP_ID << 8) | 0x02

# Storage key of the PIN set flag.
PIN_NOT_SET_KEY = (PIN_APP_ID << 8) | 0x03

# Norcow storage key of the storage version.
VERSION_KEY = (PIN_APP_ID << 8) | 0x04

# Norcow storage key of the storage authentication tag.
SAT_KEY = (PIN_APP_ID << 8) | 0x05

# Norcow storage key of the wipe code data.
WIPE_CODE_DATA_KEY = (PIN_APP_ID << 8) | 0x06

# Norcow storage key of the storage upgrade flag.
STORAGE_UPGRADED_KEY = (PIN_APP_ID << 8) | 0x07

# The PIN value corresponding to an invalid PIN.
PIN_INVALID = 0

# The PIN value corresponding to an empty PIN.
PIN_EMPTY = 1

# Maximum number of failed unlock attempts.
PIN_MAX_TRIES = 16

# The total number of iterations to use in PBKDF2.
PIN_ITER_COUNT = 20000

# The length of the data encryption key in bytes.
DEK_SIZE = 32

# The length of the storage authentication key in bytes.
SAK_SIZE = 16

# The length of the storage authentication tag in bytes.
SAT_SIZE = 16

# The length of the random salt in bytes.
PIN_SALT_SIZE = 4
PIN_HARDWARE_SALT_SIZE = 32

# The length of the PIN verification code in bytes.
PVC_SIZE = 8

# The length of KEK in bytes.
KEK_SIZE = 32

# The length of KEIV in bytes.
KEIV_SIZE = 12

# The byte length of the salt used in checking the wipe code.
WIPE_CODE_SALT_SIZE = 8

# The byte length of the tag used in checking the wipe code.
WIPE_CODE_TAG_SIZE = 8

# The value corresponding to an unconfigured wipe code.
# NOTE: This is intentionally different from PIN_EMPTY so that we don't need
# special handling when both the PIN and wipe code are not set.
WIPE_CODE_EMPTY = 0

# Size of counter. 4B integer and 8B tail.
COUNTER_TAIL = 12
COUNTER_TAIL_SIZE = 8
COUNTER_MAX_TAIL = 64

# ----- PIN logs ----- #

# Storage key of the PIN entry log and PIN success log.
PIN_LOG_KEY = (PIN_APP_ID << 8) | 0x01

# Length of items in the PIN entry log
PIN_LOG_GUARD_KEY_SIZE = 4

# Values used for the guard key integrity check.
GUARD_KEY_MODULUS = 6311
GUARD_KEY_REMAINDER = 15
GUARD_KEY_RANDOM_MAX = (0xFFFFFFFF // GUARD_KEY_MODULUS) + 1

# Length of both success log and entry log
PIN_LOG_SIZE = 64

# Used for in guard bits operations.
LOW_MASK = 0x55555555

# Log initialized to all FFs.
ALL_FF_LOG = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

# ----- Bytes -----

# If the top bit of APP is set, then the value is not encrypted.
FLAG_PUBLIC = 0x80

# If the top two bits of APP are set, then the value is not encrypted and it
# can be written even when the storage is locked.
FLAGS_WRITE = 0xC0

# Length of word in bytes.
WORD_SIZE = 4

# Boolean values are stored as a simple 0/1 int.
TRUE_BYTE = b"\x01"
FALSE_BYTE = b"\x00"
TRUE_WORD = b"\xA5\x69\x5A\xC3"
FALSE_WORD = b"\x5A\x96\xA5\x3C"

# ----- Crypto ----- #

# The length of the Poly1305 MAC in bytes.
POLY1305_MAC_SIZE = 16

# The length of the ChaCha20 IV (aka nonce) in bytes as per RFC 7539.
CHACHA_IV_SIZE = 12

# ----- Norcow ----- #

NORCOW_SECTOR_COUNT = 2
NORCOW_SECTOR_SIZE = 64 * 1024

# Magic flag at the beggining of an active sector.
NORCOW_MAGIC = b"NRC2"

# Norcow version, set in the storage header, but also as an encrypted item.
NORCOW_VERSION = b"\x02\x00\x00\x00"

# Norcow magic combined with the version, which is stored as its negation.
NORCOW_MAGIC_AND_VERSION = NORCOW_MAGIC + bytes(
    [
        ~NORCOW_VERSION[0] & 0xFF,
        ~NORCOW_VERSION[1] & 0xFF,
        ~NORCOW_VERSION[2] & 0xFF,
        ~NORCOW_VERSION[3] & 0xFF,
    ]
)

# Signalizes free storage.
NORCOW_KEY_FREE = 0xFFFF


# |-----------|-------------------|
# | Private   | APP = 0           |
# | Protected | 1 <= APP <= 127   |
# | Public    | 128 <= APP <= 255 |


def is_app_public(app: int):
    if app & FLAG_PUBLIC:
        return True
    return False


def is_app_protected(app: int):
    if is_app_public(app):
        return False
    if is_app_private(app):
        return False
    return True


def is_app_private(app: int):
    return app == PIN_APP_ID


def is_app_lock_writable(app: int):
    if app & FLAGS_WRITE == FLAGS_WRITE:
        return True
    return False
