/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include STM32_HAL_H

#include "fwutils.h"
#include "error_handling.h"
#include "flash.h"
#include "flash_area.h"
#include "model.h"

void invalidate_firmware(void) {
#ifdef STM32U5
  // on stm32u5, we need to disable the instruction cache before erasing the
  // firmware - otherwise, the write check will fail
  ICACHE->CR &= ~ICACHE_CR_EN;
#endif

  // erase start of the firmware (metadata) -> invalidate FW
  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < (1024 / FLASH_BLOCK_SIZE); i += FLASH_BLOCK_SIZE) {
    flash_block_t data = {0};
    ensure(flash_area_write_block(&FIRMWARE_AREA, i * FLASH_BLOCK_SIZE, data),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
}
