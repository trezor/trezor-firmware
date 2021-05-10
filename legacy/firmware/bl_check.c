/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 Pavol Rusnak <stick@satoshilabs.com>
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

#include <libopencm3/stm32/flash.h>
#include <stdint.h>
#include <string.h>
#include "bl_data.h"
#include "gettext.h"
#include "layout.h"
#include "memory.h"
#include "util.h"

#if MEMORY_PROTECT

static int known_bootloader(int r, const uint8_t *hash) {
  if (r != 32) return 0;
  if (0 ==
      memcmp(hash,
             "\xbf\x72\xe2\x5e\x2c\x2f\xc1\xba\x57\x04\x50\xfa\xdf\xb6\x6f\xaa"
             "\x5a\x71\x6d\xcd\xc0\x33\x35\x88\x55\x7b\x77\x54\x0a\xb8\x7e\x98",
             32))
    return 1;  // 1.2.0a
  if (0 ==
      memcmp(hash,
             "\x77\xb8\xe2\xf2\x5f\xaa\x8e\x8c\x7d\x9f\x5b\x32\x3b\x27\xce\x05"
             "\x6c\xa3\xdb\xc2\x3f\x56\xc3\x7e\xe3\x3f\x97\x7c\xa6\xeb\x4d\x3e",
             32))
    return 1;  // 1.2.0b
  if (0 ==
      memcmp(hash,
             "\xc4\xc3\x25\x39\xb4\xa0\x25\xa8\xe7\x53\xa4\xc4\x62\x64\x28\x59"
             "\x11\xa4\x5f\xcb\x14\xf4\x71\x81\x79\xe7\x11\xb1\xce\x99\x05\x24",
             32))
    return 1;  // 1.2.5
  if (0 ==
      memcmp(hash,
             "\x42\x59\x66\x94\xa0\xf2\x9d\x1e\xc2\x35\x71\x29\x2d\x54\x39\xd8"
             "\x2f\xa1\x8c\x07\x37\xcb\x10\x7e\x98\xf6\x1e\xf5\x93\x4d\xe7\x16",
             32))
    return 1;  // 1.3.0a
  if (0 ==
      memcmp(hash,
             "\x3a\xcf\x2e\x51\x0b\x0f\xe1\x56\xb5\x58\xbb\xf7\x9c\x7e\x48\x5e"
             "\xb0\x26\xe5\xe0\x8c\xb4\x4d\x15\x2d\x44\xd6\x4e\x0c\x6a\x41\x37",
             32))
    return 1;  // 1.3.0b
  if (0 ==
      memcmp(hash,
             "\x15\x85\x21\x5b\xc6\xe5\x5a\x34\x07\xa8\xb3\xee\xe2\x79\x03\x4e"
             "\x95\xb9\xc4\x34\x00\x33\xe1\xb6\xae\x16\x0c\xe6\x61\x19\x67\x15",
             32))
    return 1;  // 1.3.1
  if (0 ==
      memcmp(hash,
             "\x76\x51\xb7\xca\xba\x5a\xae\x0c\xc1\xc6\x5c\x83\x04\xf7\x60\x39"
             "\x6f\x77\x60\x6c\xd3\x99\x0c\x99\x15\x98\xf0\xe2\x2a\x81\xe0\x07",
             32))
    return 1;  // 1.3.2
  // note to those verifying these values: bootloader versions above this
  // comment are aligned/padded to 32KiB with trailing 0xFF bytes and versions
  // below are padded with 0x00.
  //                                       for more info, refer to "make -C
  //                                       bootloader align" and
  //                                       "firmware/bl_data.py".
  if (0 ==
      memcmp(hash,
             "\x8c\xe8\xd7\x9e\xdf\x43\x0c\x03\x42\x64\x68\x6c\xa9\xb1\xd7\x8d"
             "\x26\xed\xb2\xac\xab\x71\x39\xbe\x8f\x98\x5c\x2a\x3c\x6c\xae\x11",
             32))
    return 1;  // 1.3.3
  if (0 ==
      memcmp(hash,
             "\x63\x30\xfc\xec\x16\x72\xfa\xd3\x0b\x42\x1b\x60\xf7\x4f\x83\x9a"
             "\x39\x39\x33\x45\x65\xcb\x70\x3b\x2b\xd7\x18\x2e\xa2\xdd\xa0\x19",
             32))
    return 1;  // 1.4.0 shipped with fw 1.6.1
  if (0 ==
      memcmp(hash,
             "\xaf\xb4\xcf\x7a\x4a\x57\x96\x10\x0e\xd5\x41\x6b\x75\x12\x1b\xc7"
             "\x10\x08\xc2\xa2\xfd\x54\x49\xbd\x8f\x63\xcc\x22\xa6\xa7\xd6\x80",
             32))
    return 1;  // 1.5.0 shipped with fw 1.6.2
  if (0 ==
      memcmp(hash,
             "\x51\x12\x90\xa8\x72\x3f\xaf\xe7\x34\x15\x25\x9d\x25\x96\x76\x54"
             "\x06\x32\x5c\xe2\x4b\x4b\x80\x03\x2c\x0b\x70\xb0\x5d\x98\x46\xe9",
             32))
    return 1;  // 1.5.1 shipped with fw 1.6.3
  if (0 ==
      memcmp(hash,
             "\x3e\xc4\xbd\xd5\x77\xea\x0c\x36\xc7\xba\xb7\xb9\xa3\x5b\x87\x17"
             "\xb3\xf1\xfc\x2f\x80\x9e\x69\x0c\x8a\xbe\x5b\x05\xfb\xc2\x43\xc6",
             32))
    return 1;  // 1.6.0 shipped with fw 1.7.0
  if (0 ==
      memcmp(hash,
             "\x8e\x83\x02\x3f\x0d\x4f\x82\x4f\x64\x71\x20\x75\x2b\x6c\x71\x6f"
             "\x55\xd7\x95\x70\x66\x8f\xd4\x90\x65\xd5\xb7\x97\x6e\x7a\x6e\x19",
             32))
    return 1;  // 1.6.0 shipped with fw 1.7.1 and 1.7.2
  if (0 ==
      memcmp(hash,
             "\xa2\x36\x6e\x77\xde\x8e\xfd\xfd\xc9\x99\xf4\x72\x20\xc0\x16\xe3"
             "\x3f\x6d\x24\x24\xe2\x45\x90\x79\x11\x7a\x90\xb3\xa8\x88\xba\xdd",
             32))
    return 1;  // 1.6.1 shipped with fw 1.7.3
  if (0 ==
      memcmp(hash,
             "\xf7\xfa\x16\x5b\xe6\xd7\x80\xf3\xe1\xaf\x00\xab\xc0\x7d\xf8\xb3"
             "\x07\x6b\xcd\xad\x72\xd7\x0d\xa2\x2a\x63\xd8\x89\x6b\x63\x91\xd8",
             32))
    return 1;  // 1.8.0 shipped with fw 1.8.0 and 1.8.1
  if (0 ==
      memcmp(hash,
             "\x74\x47\xa4\x17\x17\x02\x2e\x3e\xb3\x20\x11\xb0\x0b\x2a\x68\xeb"
             "\xb9\xc7\xf6\x03\xcd\xc7\x30\xe7\x30\x78\x50\xa3\xf4\xd6\x2a\x5c",
             32))
    return 1;  // 1.10.0 shipped with fw 1.10.0
  return 0;
}
#endif

/**
 * If bootloader is older and known, replace with newer bootloader.
 * If bootloader is unknown, halt with error message.
 *
 * @param shutdown_on_replace: if true, shuts down device instead of return
 */
void check_and_replace_bootloader(bool shutdown_on_replace) {
#if MEMORY_PROTECT
  uint8_t hash[32] = {0};
  int r = memory_bootloader_hash(hash);

  if (!known_bootloader(r, hash)) {
    layoutDialog(&bmp_icon_error, NULL, NULL, NULL, _("Unknown bootloader"),
                 _("detected."), NULL, _("Unplug your Trezor"),
                 _("contact our support."), NULL);
    shutdown();
  }

  if (is_mode_unprivileged()) {
    return;
  }

  if (r == 32 && 0 == memcmp(hash, bl_hash, 32)) {
    // all OK -> done
    return;
  }

  // ENABLE THIS AT YOUR OWN RISK
  // ATTEMPTING TO OVERWRITE BOOTLOADER WITH UNSIGNED FIRMWARE MAY BRICK
  // YOUR DEVICE.

  layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, _("Updating bootloader"),
               NULL, NULL, _("DO NOT UNPLUG"), _("YOUR TREZOR!"), NULL);

  // unlock sectors
  memory_write_unlock();

  for (int tries = 0; tries < 10; tries++) {
    // replace bootloader
    flash_wait_for_last_operation();
    flash_clear_status_flags();
    flash_unlock();
    for (int i = FLASH_BOOT_SECTOR_FIRST; i <= FLASH_BOOT_SECTOR_LAST; i++) {
      flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
    }
    for (int i = 0; i < FLASH_BOOT_LEN / 4; i++) {
      const uint32_t *w = (const uint32_t *)(bl_data + i * 4);
      flash_program_word(FLASH_BOOT_START + i * 4, *w);
    }
    flash_wait_for_last_operation();
    flash_lock();
    // check whether the write was OK
    r = memory_bootloader_hash(hash);
    if (r == 32 && 0 == memcmp(hash, bl_hash, 32)) {
      if (shutdown_on_replace) {
        // OK -> show info and halt
        layoutDialog(&bmp_icon_info, NULL, NULL, NULL, _("Update finished"),
                     _("successfully."), NULL, _("Please reconnect"),
                     _("the device."), NULL);
        shutdown();
      }
      return;
    }
  }
  // show info and halt
  layoutDialog(&bmp_icon_error, NULL, NULL, NULL, _("Bootloader update"),
               _("broken."), NULL, _("Unplug your Trezor"),
               _("contact our support."), NULL);
  shutdown();
#endif
  // prevent compiler warning when MEMORY_PROTECT==0
  (void)shutdown_on_replace;
}
