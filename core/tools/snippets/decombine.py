import io
import sys
from pathlib import Path

from trezorlib._internal import firmware_headers
from trezorlib.firmware.core import FirmwareHeader, HeaderType

INFILE = Path(sys.argv[1])
DATA = INFILE.read_bytes()

READER = io.BytesIO(DATA)

# boardloader is first 3 16kB sectors
BOARDLOADER = READER.read(3 * 16 * 1024)

# following 16kB is unused
UNUSED = READER.read(16 * 1024)
if all(b == 0 for b in UNUSED):
    print("Unused space is all zero")
elif all(b == 0xFF for b in UNUSED):
    print("Unused space is all 0xFF")
else:
    print("WARNING: Unused space is noise!!")

# following 64kB is storage area 1, should be empty
STORAGE1 = READER.read(64 * 1024)
if all(b == 0 for b in STORAGE1):
    print("Storage area 1 is all zero")
elif all(b == 0xFF for b in STORAGE1):
    print("Storage area 1 is all 0xFF")
else:
    print("WARNING: Storage area 1 is noise!!")

# following 128 kB is bootloader
BOOTLOADER_SECTOR = READER.read(128 * 1024)
BOOTLOADER_HEADER = FirmwareHeader.parse(BOOTLOADER_SECTOR)
assert BOOTLOADER_HEADER.magic == HeaderType.BOOTLOADER
length = BOOTLOADER_HEADER.header_len + BOOTLOADER_HEADER.code_length
BOOTLOADER = BOOTLOADER_SECTOR[:length]
BOOTLOADER_AFTER = BOOTLOADER_SECTOR[length:]

BOOTLOADER_PARSED = firmware_headers.parse_image(BOOTLOADER)
print("Bootloader parses OK:")
print(BOOTLOADER_PARSED.format())
if all(b == 0 for b in BOOTLOADER_AFTER):
    print("Bootloader padding is all zero")
elif all(b == 0xFF for b in BOOTLOADER_AFTER):
    print("Bootloader padding is all 0xFF")
else:
    print("WARNING: Bootloader padding is noise!!")

# rest of the image is prodtest
PRODTEST = READER.read()
PRODTEST_PARSED = firmware_headers.parse_image(PRODTEST)
print("Prodtest parses OK:")
print(PRODTEST_PARSED.format())

# save results:
Path("boardloader.bin").write_bytes(BOARDLOADER)
Path("bootloader.bin").write_bytes(BOOTLOADER)
Path("prodtest.bin").write_bytes(PRODTEST)
