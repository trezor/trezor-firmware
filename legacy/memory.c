/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "memory.h"
#include <libopencm3/stm32/flash.h>
#include <stdint.h>
#include "sha2.h"

#define FLASH_OPTION_BYTES_1 (*(const uint64_t *)0x1FFFC000)
#define FLASH_OPTION_BYTES_2 (*(const uint64_t *)0x1FFFC008)

void memory_protect(void) {
#if MEMORY_PROTECT
  // Reference STM32F205 Flash programming manual revision 5
  // http://www.st.com/resource/en/programming_manual/cd00233952.pdf Section 2.6
  // Option bytes
  //                     set RDP level 2                   WRP for sectors 0 and
  //                     1            flash option control register matches
  if (((FLASH_OPTION_BYTES_1 & 0xFFEC) == 0xCCEC) &&
      ((FLASH_OPTION_BYTES_2 & 0xFFF) == 0xFFC) &&
      (FLASH_OPTCR == 0x0FFCCCED)) {
    return;  // already set up correctly - bail out
  }

  flash_unlock();
  for (int i = FLASH_STORAGE_SECTOR_FIRST; i <= FLASH_STORAGE_SECTOR_LAST;
       i++) {
    flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
  }
  flash_lock();

  flash_unlock_option_bytes();
  // Section 2.8.6 Flash option control register (FLASH_OPTCR)
  //   Bits 31:28 Reserved, must be kept cleared.
  //   Bits 27:16 nWRP: Not write protect: write protect bootloader code in
  //   flash main memory sectors 0 and 1 (Section 2.3; table 2) Bits 15:8 RDP:
  //   Read protect: level 2 chip read protection active Bits 7:5 USER: User
  //   option bytes: no reset on standby, no reset on stop, software watchdog
  //   Bit 4 Reserved, must be kept cleared.
  //   Bits 3:2 BOR_LEV: BOR reset Level: BOR off
  //   Bit 1 OPTSTRT: Option start: ignored by flash_program_option_bytes
  //   Bit 0 OPTLOCK: Option lock: ignored by flash_program_option_bytes
  flash_program_option_bytes(0x0FFCCCEC);
  flash_lock_option_bytes();
#endif
}

// Remove write-protection on all flash sectors.
//
// This is an undocumented feature/bug of STM32F205/F405 microcontrollers,
// where flash controller reads its write protection bits from FLASH_OPTCR
// register not from OPTION_BYTES, rendering write protection useless.
// This behaviour is fixed in future designs of flash controller used for
// example in STM32F427, where the protection bits are read correctly
// from OPTION_BYTES and not form FLASH_OPCTR register.
//
// Read protection is unaffected and always stays locked to the desired value.
void memory_write_unlock(void) {
  flash_unlock_option_bytes();
  flash_program_option_bytes(0x0FFFCCEC);
  flash_lock_option_bytes();
}

int memory_bootloader_hash(uint8_t *hash) {
  sha256_Raw(FLASH_PTR(FLASH_BOOT_START), FLASH_BOOT_LEN, hash);
  sha256_Raw(hash, 32, hash);
  return 32;
}
