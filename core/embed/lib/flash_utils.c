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

#include TREZOR_BOARD

#include "flash_utils.h"
#include "common.h"
#include "flash_area.h"
#include "model.h"
#include "mpu.h"
#include "secbool.h"

typedef struct {
  const flash_area_t* area;
  mpu_mode_t mpu_mode;
} flash_area_ref_t;

// Erases the given list of flash areas.
//
// Invokes the progress_cb after each erased sector or page.
static secbool erase_areas(const flash_area_ref_t* areas, int area_count,
                           flash_progress_callback_t progress_cb) {
  int total = 0;
  int progress = 0;

  for (int i = 0; i < area_count; i++) {
    total += flash_area_get_size(areas[i].area);
  }

  mpu_mode_t mpu_mode = mpu_get_mode();

  for (int i = 0; i < area_count; i++) {
    const flash_area_t* area = areas[i].area;
    uint32_t offset = 0;
    uint32_t bytes_erased = 0;

    mpu_reconfig(areas[i].mpu_mode);

    do {
      if (progress_cb) {
        progress_cb(progress, total);
      }

      if (sectrue != flash_area_erase_partial(area, offset, &bytes_erased)) {
        mpu_restore(mpu_mode);
        return secfalse;
      }

      offset += bytes_erased;
      progress += bytes_erased;

    } while (bytes_erased > 0);
  }

  mpu_restore(mpu_mode);
  return sectrue;
}

secbool erase_storage(flash_progress_callback_t progress_cb) {
  _Static_assert(STORAGE_AREAS_COUNT == 2,
                 "Unsupported number of storage areas");

  static const flash_area_ref_t areas[] = {
      {.area = &STORAGE_AREAS[0], .mpu_mode = MPU_MODE_STORAGE},
      {.area = &STORAGE_AREAS[1], .mpu_mode = MPU_MODE_STORAGE},
  };

  return erase_areas(areas, ARRAY_LENGTH(areas), progress_cb);
}

secbool erase_device(flash_progress_callback_t progress_cb) {
  _Static_assert(STORAGE_AREAS_COUNT == 2,
                 "Unsupported number of storage areas");

  static const flash_area_ref_t areas[] = {
    {.area = &STORAGE_AREAS[0], .mpu_mode = MPU_MODE_STORAGE},
    {.area = &STORAGE_AREAS[1], .mpu_mode = MPU_MODE_STORAGE},
    {.area = &ASSETS_AREA, .mpu_mode = MPU_MODE_ASSETS},
#if defined(BOARDLOADER) || defined(BOOTLOADER)
    {.area = &FIRMWARE_AREA, .mpu_mode = MPU_MODE_DEFAULT},
#endif
#if defined(BOARDLOADER) && defined(USE_SD_CARD)
    {.area = &BOOTLOADER_AREA, .mpu_mode = MPU_MODE_DEFAULT},
    {.area = &UNUSED_AREA, .mpu_mode = MPU_MODE_UNUSED_FLASH},
#endif
  };

  return erase_areas(areas, ARRAY_LENGTH(areas), progress_cb);
}
