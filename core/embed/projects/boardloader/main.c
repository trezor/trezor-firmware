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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <sec/secret.h>
#include <sys/bootutils.h>
#include <sys/reset_flags.h>
#include <sys/system.h>
#include <util/board_capabilities.h>
#include <util/flash.h>
#include <util/flash_utils.h>
#include <util/image.h>
#include <util/option_bytes.h>
#include <util/rsod.h>

#ifdef USE_POWERCTL
#include <sys/powerctl.h>
#endif

#ifdef USE_PVD
#include <sys/pvd.h>
#endif

#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#ifdef USE_TAMPER
#include <sys/tamper.h>
#endif

#include "bld_version.h"
#include "version.h"

#ifdef USE_SD_CARD
#include "sd_update.h"
#endif

const uint8_t BOARDLOADER_KEY_M = 2;
const uint8_t BOARDLOADER_KEY_N = 3;
static const uint8_t * const BOARDLOADER_KEYS[] = {
#if !PRODUCTION
    (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
    (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
    (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",
#else
    MODEL_BOARDLOADER_KEYS
#endif
};

static void drivers_init(void) {
#ifdef USE_POWERCTL
  powerctl_init();
#endif
#ifdef USE_PVD
  pvd_init();
#endif
#ifdef USE_TAMPER
  tamper_init();
#endif
  secret_init();
#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif
#ifndef FIXED_HW_DEINIT
  // only skip this if deinit was fixed,
  // as some old bootloaders rely on display being initialized
  // (skipping alows faster boot time so generally a good idea)
  display_init(DISPLAY_RESET_CONTENT);
#endif
}

static void drivers_deinit(void) {
#ifdef FIXED_HW_DEINIT
  // TODO
#endif
  display_deinit(DISPLAY_JUMP_BEHAVIOR);
#ifdef USE_POWERCTL
  powerctl_deinit();
#endif
}

struct BoardCapabilities capabilities
    __attribute__((section(".capabilities_section"))) = {
        .header = CAPABILITIES_HEADER,
        .model_tag = TAG_MODEL_NAME,
        .model_length = sizeof(uint32_t),
        .model_name = HW_MODEL,
        .version_tag = TAG_BOARDLOADER_VERSION,
        .version_length = sizeof(struct BoardloaderVersion),
        .version = {.version_major = VERSION_MAJOR,
                    .version_minor = VERSION_MINOR,
                    .version_patch = VERSION_PATCH,
                    .version_build = VERSION_BUILD},
        .terminator_tag = TAG_TERMINATOR,
        .terminator_length = 0};

int main(void) {
  system_init(&rsod_panic_handler);

  reset_flags_reset();

  if (sectrue != flash_configure_option_bytes()) {
    // display is not initialized so don't call ensure
    erase_storage(NULL);
    return 2;
  }

#ifdef USE_TRUSTZONE
  tz_init_boardloader();
#endif

  drivers_init();

#ifdef USE_SD_CARD
  sd_update_check_and_update(BOARDLOADER_KEYS, BOARDLOADER_KEY_M,
                             BOARDLOADER_KEY_N);
#endif

  const image_header *hdr = read_image_header(
      (const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC,
      flash_area_get_size(&BOOTLOADER_AREA));

  ensure(hdr == (const image_header *)BOOTLOADER_START ? sectrue : secfalse,
         "invalid bootloader header");

  ensure(check_image_header_sig(hdr, BOARDLOADER_KEY_M, BOARDLOADER_KEY_N,
                                BOARDLOADER_KEYS),
         "invalid bootloader signature");

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE, &BOOTLOADER_AREA),
         "invalid bootloader hash");

  uint8_t bld_min_version = get_bootloader_min_version();
  ensure((hdr->monotonic >= bld_min_version) * sectrue,
         "BOOTLOADER DOWNGRADED");
  // Write the bootloader version to the secret area.
  // This includes the version of bootloader potentially updated from SD card.
  write_bootloader_min_version(hdr->monotonic);

  drivers_deinit();

  system_deinit();

  // g_boot_command is preserved on STM32U5
  jump_to_next_stage(IMAGE_CODE_ALIGN(BOOTLOADER_START + IMAGE_HEADER_SIZE));

  return 0;
}
