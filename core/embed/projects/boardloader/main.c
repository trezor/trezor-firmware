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

#ifdef USE_PMIC
#include <sys/pmic.h>
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

#include <util/signblock.h>
#include "slh_dsa.h"

static void drivers_init(void) {
#ifdef USE_PMIC
  pmic_init();
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
#ifdef USE_PMIC
  pmic_deinit();
#endif
}

board_capabilities_t capabilities
    __attribute__((section(".capabilities_section"))) = {
        .header = CAPABILITIES_HEADER,
        .model_tag = TAG_MODEL_NAME,
        .model_length = sizeof(uint32_t),
        .model_name = HW_MODEL,
        .version_tag = TAG_BOARDLOADER_VERSION,
        .version_length = sizeof(boardloader_version_t),
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
  tz_init();
#endif

  drivers_init();

#ifdef USE_SD_CARD
  sd_update_check_and_update();
#endif

  const image_header *hdr = read_image_header(
      (const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC,
      flash_area_get_size(&BOOTLOADER_AREA));

  ensure(hdr == (const image_header *)BOOTLOADER_START ? sectrue : secfalse,
         "invalid bootloader header");

  ensure(check_bootloader_header_sig(hdr), "invalid bootloader signature");

#ifdef USE_SIGNATURE_BLOCK
  {
    // Development public key
    static const uint8_t pk[32] = {
        0xec, 0x01, 0xe6, 0x02, 0x63, 0x02, 0x4f, 0x7e, 0x71, 0x72, 0x80,
        0x13, 0xb7, 0x31, 0xf7, 0xba, 0x12, 0x99, 0xf5, 0x18, 0xc2, 0x7b,
        0xa3, 0xed, 0x8f, 0x4a, 0x21, 0x99, 0x74, 0x12, 0x7c, 0x62};

    const signblock_t *signblock = (const signblock_t *)SIGNATURE_BLOCK_START;

    mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SIGNATURE_BLOCK);
    bool ok = slh_verify((const uint8_t *)hdr, sizeof(*hdr),
                         signblock->signature1, pk, &slh_dsa_sha2_128s);
    ensure(sectrue * ok, "invalid bootloader pq signature");
    mpu_restore(mpu_mode);
  }
#endif  // USE_SIGNATURE_BLOCK

  ensure(check_image_model(hdr), "incompatible bootloader model");

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
