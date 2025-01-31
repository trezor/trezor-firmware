
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <gfx/terminal.h>

#include <io/display.h>
#include <sys/bootutils.h>
#include <sys/systick.h>
#include <util/flash.h>
#include <util/flash_utils.h>
#include <util/image.h>

#include "memzero.h"

#include "bld_version.h"

#ifdef USE_SD_CARD
#include <io/sdcard.h>
#endif

#include "sd_update.h"

// we use SRAM as SD card read buffer (because DMA can't access the CCMRAM)
__attribute__((section(".buf")))
uint32_t sdcard_buf[BOOTLOADER_MAXSIZE / sizeof(uint32_t)];

static uint32_t check_sdcard(const uint8_t *const *keys, uint8_t key_m,
                             uint8_t key_n) {
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

    if (sectrue != check_image_header_sig(hdr, key_m, key_n, keys)) {
      return 0;
    }

    _Static_assert(IMAGE_CHUNK_SIZE >= BOOTLOADER_MAXSIZE,
                   "BOOTLOADER IMAGE MAXSIZE too large for IMAGE_CHUNK_SIZE");

    const uint32_t code_start_offset = hdr->hdrlen;

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

static secbool copy_sdcard(const uint8_t *const *keys, uint8_t key_m,
                           uint8_t key_n) {
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
    codelen = check_sdcard(keys, key_m, key_n);
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

void sd_update_check_and_update(const uint8_t *const *keys, uint8_t key_m,
                                uint8_t key_n) {
  sdcard_init();

  // If the bootloader is being updated from SD card, we need to preserve the
  // monotonic counter from the old bootloader. This is in case that the old
  // bootloader did not have the chance yet to write its monotonic counter to
  // the secret area - which normally happens later in the flow.
  const image_header *old_hdr = read_image_header(
      (const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC,
      flash_area_get_size(&BOOTLOADER_AREA));

  if ((old_hdr != NULL) &&
      (sectrue == check_image_header_sig(old_hdr, key_m, key_n, keys)) &&
      (sectrue ==
       check_image_contents(old_hdr, IMAGE_HEADER_SIZE, &BOOTLOADER_AREA))) {
    write_bootloader_min_version(old_hdr->monotonic);
  }

  if (check_sdcard(keys, key_m, key_n) != 0) {
#ifdef FIXED_HW_DEINIT
    display_init(DISPLAY_RESET_CONTENT);
#endif
    copy_sdcard(keys, key_m, key_n);
#ifdef FIXED_HW_DEINIT
    display_deinit(DISPLAY_RETAIN_CONTENT);
#endif
    reboot_or_halt_after_rsod();
  }
}
