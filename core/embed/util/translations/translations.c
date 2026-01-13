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

#ifdef KERNEL_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/flash.h>
#include <sys/mpu.h>
#include <util/translations.h>

bool translations_write(const uint8_t* data, uint32_t offset, uint32_t len) {
  uint32_t size = translations_area_bytesize();
  if (offset > size || size - offset < len) {
    return false;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_ASSETS);

  ensure(flash_unlock_write(), "translations_write unlock");
  // todo consider alignment
  ensure(flash_area_write_data_padded(&ASSETS_AREA, offset, data, len, 0xFF,
                                      FLASH_ALIGN(len)),
         "translations_write write");
  ensure(flash_lock_write(), "translations_write lock");

  mpu_restore(mpu_mode);

  return true;
}

const uint8_t* translations_read(uint32_t* len, uint32_t offset) {
  // TODO: _Static_assert was not happy with ASSETS_AREA.num_subareas == 1
  // error: expression in static assertion is not constant
  assert(ASSETS_AREA.num_subareas == 1);
  *len = flash_area_get_size(&ASSETS_AREA) - offset;
  return flash_area_get_address(&ASSETS_AREA, offset, 0);
}

void translations_erase(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_ASSETS);
  ensure(flash_area_erase(&ASSETS_AREA, NULL), "translations erase");
  mpu_restore(mpu_mode);
}

uint32_t translations_area_bytesize(void) {
  return flash_area_get_size(&ASSETS_AREA);
}

#endif  // KERNEL_MODE
