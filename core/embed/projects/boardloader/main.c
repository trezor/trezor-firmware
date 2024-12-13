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

#include <gfx/gfx_bitblt.h>
#include <gfx/gfx_draw.h>
#include <gfx/terminal.h>
#include <io/display.h>
#include <sec/monoctr.h>
#include <sec/rng.h>
#include <sec/secret.h>
#include <sys/bootutils.h>
#include <sys/mpu.h>
#include <sys/reset_flags.h>
#include <sys/system.h>
#include <sys/systick.h>
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

#ifdef USE_SD_CARD
#include <io/sdcard.h>
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

#include "memzero.h"
#include "version.h"

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
  gfx_bitblt_init();
  display_init(DISPLAY_RESET_CONTENT);
#ifdef USE_SD_CARD
  sdcard_init();
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
  ensure_compatible_settings();
}

static uint8_t get_bootloader_min_version(void) {
  uint8_t version = 0;
  ensure(monoctr_read(MONOCTR_BOOTLOADER_VERSION, &version), "monoctr read");
  return version;
}

static void write_bootloader_min_version(uint8_t version) {
  if (version > get_bootloader_min_version()) {
    ensure(monoctr_write(MONOCTR_BOOTLOADER_VERSION, version), "monoctr write");
  }
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

// we use SRAM as SD card read buffer (because DMA can't access the CCMRAM)
__attribute__((section(".buf")))
uint32_t sdcard_buf[BOOTLOADER_MAXSIZE / sizeof(uint32_t)];

#if defined USE_SD_CARD
static uint32_t check_sdcard(void) {
  if (sectrue != sdcard_power_on()) {
    return 0;
  }

  uint64_t cap = sdcard_get_capacity_in_bytes();
  if (cap < 1024 * 1024) {
    sdcard_power_off();
    return 0;
  }

  memzero(sdcard_buf, IMAGE_HEADER_SIZE);

  const secbool read_status =
      sdcard_read_blocks(sdcard_buf, 0, BOOTLOADER_MAXSIZE / SDCARD_BLOCK_SIZE);

  sdcard_power_off();

  if (sectrue == read_status) {
    const image_header *hdr =
        read_image_header((const uint8_t *)sdcard_buf, BOOTLOADER_IMAGE_MAGIC,
                          BOOTLOADER_MAXSIZE);

    if (hdr != (const image_header *)sdcard_buf) {
      return 0;
    }

    if (sectrue != check_image_model(hdr)) {
      return 0;
    }

    if (sectrue != check_image_header_sig(hdr, BOARDLOADER_KEY_M,
                                          BOARDLOADER_KEY_N,
                                          BOARDLOADER_KEYS)) {
      return 0;
    }

    _Static_assert(IMAGE_CHUNK_SIZE >= BOOTLOADER_MAXSIZE,
                   "BOOTLOADER IMAGE MAXSIZE too large for IMAGE_CHUNK_SIZE");

    const uint32_t headers_end_offset = hdr->hdrlen;
    const uint32_t code_start_offset = IMAGE_CODE_ALIGN(headers_end_offset);

    for (uint32_t i = headers_end_offset; i < code_start_offset; i++) {
      if (((uint8_t *)sdcard_buf)[i] != 0) {
        return 0;
      }
    }

    if (sectrue !=
        (check_single_hash(hdr->hashes,
                           (const uint8_t *)sdcard_buf + code_start_offset,
                           hdr->codelen))) {
      return 0;
    }

    for (int i = IMAGE_HASH_DIGEST_LENGTH; i < sizeof(hdr->hashes); i++) {
      if (hdr->hashes[i] != 0) {
        return 0;
      }
    }

    if (hdr->monotonic < get_bootloader_min_version()) {
      return 0;
    }

    return hdr->codelen;
  }

  return 0;
}

static void progress_callback(int pos, int len) { term_printf("."); }

static secbool copy_sdcard(void) {
  display_set_backlight(255);

  term_printf("Trezor Boardloader\n");
  term_printf("==================\n\n");

  term_printf("bootloader found on the SD card\n\n");
  term_printf("applying bootloader in 10 seconds\n\n");
  term_printf("unplug now if you want to abort\n\n");

  uint32_t codelen;

  for (int i = 10; i >= 0; i--) {
    term_printf("%d ", i);
    hal_delay(1000);
    codelen = check_sdcard();
    if (0 == codelen) {
      term_printf("\n\nno SD card, aborting\n");
      return secfalse;
    }
  }

  term_printf("\n\nerasing flash:\n\n");

  // erase all flash (except boardloader)
  if (sectrue != erase_device(progress_callback)) {
    term_printf(" failed\n");
    return secfalse;
  }
  term_printf(" done\n\n");

  ensure(flash_unlock_write(), NULL);

  // copy bootloader from SD card to Flash
  term_printf("copying new bootloader from SD card\n\n");

  ensure(flash_area_write_data(&BOOTLOADER_AREA, 0, sdcard_buf,
                               IMAGE_HEADER_SIZE + codelen),
         NULL);

  ensure(flash_lock_write(), NULL);

  term_printf("\ndone\n\n");
  term_printf("Unplug the device and remove the SD card\n");

  return sectrue;
}
#endif

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
  // If the bootloader is being updated from SD card, we need to preserve the
  // monotonic counter from the old bootloader. This is in case that the old
  // bootloader did not have the chance yet to write its monotonic counter to
  // the secret area - which normally happens later in the flow.
  const image_header *old_hdr = read_image_header(
      (const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC,
      flash_area_get_size(&BOOTLOADER_AREA));

  if ((old_hdr != NULL) &&
      (sectrue == check_image_header_sig(old_hdr, BOARDLOADER_KEY_M,
                                         BOARDLOADER_KEY_N,
                                         BOARDLOADER_KEYS)) &&
      (sectrue ==
       check_image_contents(old_hdr, IMAGE_HEADER_SIZE, &BOOTLOADER_AREA))) {
    write_bootloader_min_version(old_hdr->monotonic);
  }

  if (check_sdcard()) {
    return copy_sdcard() == sectrue ? 0 : 3;
  }
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
  jump_to(IMAGE_CODE_ALIGN(BOOTLOADER_START + IMAGE_HEADER_SIZE));

  return 0;
}
