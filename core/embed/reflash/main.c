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

#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#include STM32_HAL_H

#include "bootutils.h"
#include "common.h"
#include "display.h"
#include "display_draw.h"
#include "flash.h"
#include "image.h"
#include "model.h"
#include "rng.h"
#include "rsod.h"
#include "sbu.h"
#include "sdcard.h"
#include "secbool.h"
#include "system.h"
#include "systimer.h"
#include "terminal.h"
#include "touch.h"

#ifdef USE_HASH_PROCESSOR
#include "hash_processor.h"
#endif

static void progress_callback(int pos, int len) { term_printf("."); }

static void flash_from_sdcard(const flash_area_t *area, uint32_t source,
                              uint32_t length) {
  static uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

  _Static_assert(SDCARD_BLOCK_SIZE % FLASH_BLOCK_SIZE == 0);
  ensure(sectrue * (source % SDCARD_BLOCK_SIZE == 0),
         "source not a multiple of block size");
  ensure(sectrue * (length % SDCARD_BLOCK_SIZE == 0),
         "length not a multiple of block size");

  for (uint32_t i = 0; i < length / SDCARD_BLOCK_SIZE; i++) {
    term_printf("read %d\n", (unsigned int)(i + source / SDCARD_BLOCK_SIZE));

    ensure(sdcard_read_blocks(buf, i + source / SDCARD_BLOCK_SIZE, 1),
           "sdcard_read_blocks");

    for (uint32_t j = 0; j < SDCARD_BLOCK_SIZE / FLASH_BLOCK_SIZE; j++) {
      ensure(flash_area_write_block(
                 area, i * SDCARD_BLOCK_SIZE + j * FLASH_BLOCK_SIZE,
                 &buf[j * FLASH_BLOCK_WORDS]),
             NULL);
    }
  }
}

int main(void) {
  system_init(&rsod_panic_handler);

  sdcard_init();
  touch_init();

#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

  display_orientation(0);
  display_clear();
  display_backlight(255);

  ensure(sdcard_is_present(), "sdcard_is_present");

  term_printf("updating boardloader + bootloader\n");

  term_printf("erasing sectors");
  ensure(flash_area_erase(&BOARDLOADER_AREA, progress_callback),
         "flash_erase_sectors");
  ensure(flash_area_erase(&BOOTLOADER_AREA, progress_callback),
         "flash_erase_sectors");
  term_printf("\n");
  term_printf("erased\n");

  ensure(flash_unlock_write(), NULL);

  ensure(sdcard_power_on(), NULL);

#define BOARDLOADER_CHUNK_SIZE (16 * 1024)
#define BOARDLOADER_TOTAL_SIZE (3 * BOARDLOADER_CHUNK_SIZE)
#define BOOTLOADER_TOTAL_SIZE (128 * 1024)

  flash_from_sdcard(&BOARDLOADER_AREA, 0, BOARDLOADER_TOTAL_SIZE);
  flash_from_sdcard(&BOOTLOADER_AREA, BOARDLOADER_TOTAL_SIZE,
                    BOOTLOADER_TOTAL_SIZE);

  term_printf("done\n");
  sdcard_power_off();
  ensure(flash_lock_write(), NULL);

  return 0;
}
