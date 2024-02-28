from typing import *
from . import FlashArea
BOARDLOADER: FlashArea
BOOTLOADER: FlashArea
FIRMWARE: FlashArea
TRANSLATIONS: FlashArea
if __debug__:
    STORAGE_A: FlashArea
    STORAGE_B: FlashArea
