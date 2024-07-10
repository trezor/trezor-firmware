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

#include <string.h>

#include TREZOR_BOARD
#include "board_capabilities.h"
#include "buffers.h"
#include "common.h"
#include "compiler_traits.h"
#include "display.h"
#include "display_draw.h"
#include "fault_handlers.h"
#include "flash.h"
#include "image.h"
#include "model.h"
#include "mpu.h"
#include "rng.h"
#include "terminal.h"

#ifdef USE_SD_CARD
#include "sdcard.h"
#endif
#ifdef USE_SDRAM
#include "sdram.h"
#endif
#ifdef USE_HASH_PROCESSOR
#include "hash_processor.h"
#endif

#include "lowlevel.h"
#include "model.h"
#include "version.h"

#include "memzero.h"

#ifdef STM32U5
#include "secret.h"
#include "tamper.h"
#include "trustzone.h"
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

#ifdef STM32U5
uint8_t get_bootloader_min_version(void) {
  const uint8_t *counter_addr =
      flash_area_get_address(&SECRET_AREA, SECRET_MONOTONIC_COUNTER_OFFSET,
                             SECRET_MONOTONIC_COUNTER_LEN);

  ensure((counter_addr != NULL) * sectrue, "counter_addr is NULL");

  int counter = 0;

  for (int i = 0; i < SECRET_MONOTONIC_COUNTER_LEN / 16; i++) {
    secbool not_cleared = sectrue;
    for (int j = 0; j < 16; j++) {
      if (counter_addr[i * 16 + j] != 0xFF) {
        not_cleared = secfalse;
        break;
      }
    }

    if (not_cleared != sectrue) {
      counter++;
    } else {
      break;
    }
  }

  return counter;
}

void write_bootloader_min_version(uint8_t version) {
  if (version > get_bootloader_min_version()) {
    for (int i = 0; i < version; i++) {
      uint32_t data[4] = {0};
      secret_write((uint8_t *)data, SECRET_MONOTONIC_COUNTER_OFFSET + i * 16,
                   16);
    }
  }
}
#endif

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
BUFFER_SECTION uint32_t sdcard_buf[BOOTLOADER_IMAGE_MAXSIZE / sizeof(uint32_t)];

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

  const secbool read_status = sdcard_read_blocks(
      sdcard_buf, 0, BOOTLOADER_IMAGE_MAXSIZE / SDCARD_BLOCK_SIZE);

  sdcard_power_off();

  if (sectrue == read_status) {
    const image_header *hdr =
        read_image_header((const uint8_t *)sdcard_buf, BOOTLOADER_IMAGE_MAGIC,
                          BOOTLOADER_IMAGE_MAXSIZE);

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

    _Static_assert(IMAGE_CHUNK_SIZE >= BOOTLOADER_IMAGE_MAXSIZE,
                   "BOOTLOADER IMAGE MAXSIZE too large for IMAGE_CHUNK_SIZE");

    if (sectrue != (check_single_hash(
                       hdr->hashes, ((const uint8_t *)sdcard_buf) + hdr->hdrlen,
                       hdr->codelen))) {
      return 0;
    }

    for (int i = IMAGE_HASH_DIGEST_LENGTH; i < sizeof(hdr->hashes); i++) {
      if (hdr->hashes[i] != 0) {
        return 0;
      }
    }

#ifdef STM32U5
    if (hdr->monotonic < get_bootloader_min_version()) {
      return 0;
    }
#endif

    return hdr->codelen;
  }

  return 0;
}

static void progress_callback(int pos, int len) { term_printf("."); }

static secbool copy_sdcard(void) {
  display_backlight(255);

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
  if (sectrue != flash_area_erase(&ALL_WIPE_AREA, progress_callback)) {
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
  reset_flags_reset();

  // need the systick timer running before many HAL operations.
  // want the PVD enabled before flash operations too.
  periph_init();

  if (sectrue != flash_configure_option_bytes()) {
    // display is not initialized so don't call ensure
    const secbool r =
        flash_area_erase_bulk(STORAGE_AREAS, STORAGE_AREAS_COUNT, NULL);
    (void)r;
    return 2;
  }

#ifdef STM32U5
  tamper_init();

  trustzone_init_boardloader();

  secret_ensure_initialized();
#endif

#ifdef STM32F4
  clear_otg_hs_memory();
#endif

  mpu_config_boardloader();

  fault_handlers_init();

#ifdef USE_SDRAM
  sdram_init();
#endif

#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

  display_init();
  display_clear();
  display_refresh();

#if defined USE_SD_CARD
  sdcard_init();

#ifdef STM32U5
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
#endif

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

#ifdef STM32U5
  uint8_t bld_min_version = get_bootloader_min_version();
  ensure((hdr->monotonic >= bld_min_version) * sectrue,
         "BOOTLOADER DOWNGRADED");
  // Write the bootloader version to the secret area.
  // This includes the version of bootloader potentially updated from SD card.
  write_bootloader_min_version(hdr->monotonic);
#endif

  ensure_compatible_settings();

  mpu_config_off();

  // g_boot_command is preserved on STM32U5
  jump_to(IMAGE_CODE_ALIGN(BOOTLOADER_START + IMAGE_HEADER_SIZE));

  return 0;
}
