if not __debug__:
    raise ImportError('This module can be loaded only in DEBUG mode')

from TrezorDebug import Debug

_utils = Debug()

MEM_FLASH_BASE = const(0x08000000)
MEM_FLASH_SIZE = const(1024 * 1024)
MEM_FLASH_END = const(MEM_FLASH_BASE + MEM_FLASH_SIZE - 1)
MEM_CCM_BASE = const(0x10000000)
MEM_CCM_SIZE = const(64 * 1024)
MEM_CCM_END = const(MEM_CCM_BASE + MEM_CCM_SIZE - 1)
MEM_SRAM_BASE = const(0x20000000)
MEM_SRAM_SIZE = const(128 * 1024)
MEM_SRAM_END = const(MEM_SRAM_BASE + MEM_SRAM_SIZE - 1)

def memaccess(address, length):
    return _utils.memaccess(address, length)
