
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/terminal.h>

#include <io/display.h>
#include <sec/image.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/systick.h>

#include "memzero.h"

#include "bld_version.h"

#ifdef USE_SD_CARD
#include <io/sdcard.h>
#endif

#include "sd_update.h"

#ifdef USE_BOOT_UCB
#error "SD card update is not compatible with boot UCB"
#endif

// we use SRAM as SD card read buffer (because DMA can't access the CCMRAM)
__attribute__((section(".buf")))
uint32_t sdcard_buf[BOOTLOADER_MAXSIZE / sizeof(uint32_t)];

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

    if (sectrue != check_bootloader_header_sig(hdr)) {
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

static void progress_callback(int pos, int len) { term_print("."); }

static secbool copy_sdcard(void) {
  display_set_backlight(255);

  term_print("Trezor Boardloader\n");
  term_print("==================\n\n");

  term_print("bootloader found on the SD card\n\n");
  term_print("applying bootloader in 10 seconds\n\n");
  term_print("unplug now if you want to abort\n\n");

  uint32_t codelen;

  for (int i = 10; i >= 0; i--) {
    term_print_int32(i);
    term_print(" ");

    hal_delay(1000);
    codelen = check_sdcard();
    if (0 == codelen) {
      term_print("\n\nno SD card, aborting\n");
      return secfalse;
    }
  }

  term_print("\n\nerasing flash:\n\n");

  // erase all flash (except boardloader)
  if (sectrue != erase_device(progress_callback)) {
    term_print(" failed\n");
    return secfalse;
  }
  term_print(" done\n\n");

  ensure(flash_unlock_write(), NULL);

  // copy bootloader from SD card to Flash
  term_print("copying new bootloader from SD card\n\n");

  ensure(flash_area_write_data(&BOOTLOADER_AREA, 0, sdcard_buf,
                               IMAGE_HEADER_SIZE + codelen),
         NULL);

  ensure(flash_lock_write(), NULL);

  term_print("\ndone\n\n");
  term_print("Unplug the device and remove the SD card\n");

  return sectrue;
}

void sd_update_check_and_update(void) {
  sdcard_init();

  // If the bootloader is being updated from SD card, we need to preserve the
  // monotonic counter from the old bootloader. This is in case that the old
  // bootloader did not have the chance yet to write its monotonic counter to
  // the secret area - which normally happens later in the flow.
  const image_header *old_hdr = read_image_header(
      (const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC,
      flash_area_get_size(&BOOTLOADER_AREA));

  if ((old_hdr != NULL) && (sectrue == check_bootloader_header_sig(old_hdr)) &&
      (sectrue ==
       check_image_contents(old_hdr, IMAGE_HEADER_SIZE, &BOOTLOADER_AREA))) {
    write_bootloader_min_version(old_hdr->monotonic);
  }

  if (check_sdcard() != 0) {
#ifdef FIXED_HW_DEINIT
    display_init(DISPLAY_RESET_CONTENT);
#endif
    copy_sdcard();
#ifdef FIXED_HW_DEINIT
    display_deinit(DISPLAY_RETAIN_CONTENT);
#endif
    reboot_or_halt_after_rsod();
  }
}
