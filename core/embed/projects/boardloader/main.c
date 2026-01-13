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
#include <sec/board_capabilities.h>
#include <sec/option_bytes.h>
#include <sec/secret.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/reset_flags.h>
#include <sys/rng.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/rsod.h>

#ifdef USE_BOOT_UCB
#include <sec/boot_header.h>
#include <sec/boot_ucb.h>
#else
#include <sec/image.h>
#endif

#ifdef USE_PMIC
#include <io/pmic.h>
#endif

#ifdef USE_PVD
#include <sys/pvd.h>
#endif

#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif

#ifdef USE_TAMPER
#include <sec/tamper.h>
#endif

#include "bld_version.h"
#include "version.h"

#ifdef USE_SD_CARD
#include "sd_update.h"
#endif

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

// The function adds a small non-deterministic delay before returning the
// original value. The delay length is randomised to any value from 0us to
// 127us.
static uint32_t __attribute((no_stack_protector)) fih_delay(uint32_t value) {
  systick_delay_us(rng_get() % 128);
  return value;
}

// Hardened conditional check
//
// The expression ​cond​ is first passed through fih_delay(), which inserts
// the random delay described above, and is then cast to ​secbool​ before
// being handed to the usual ensure() macro.  The extra jitter makes
// external timing probes much less able to distinguish whether the test
// passed or failed.
#define fih_ensure(cond, msg)                          \
  do {                                                 \
    ensure((secbool)fih_delay((uint32_t)(cond)), msg); \
  } while (0)

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

#ifdef USE_BOOT_UCB

static void try_bootloader_update(void) {
  boot_ucb_t ucb;

  // Start with some non-deterministic delay
  fih_delay(0);

  // Check if the bootloader UCB (update control block) is present and valid
  if (sectrue != boot_ucb_read(&ucb)) {
    return;
  }

  // Check if the new boot header is present and valid
  const boot_header_auth_t* hdr = boot_header_auth_get(ucb.header_address);
  if (hdr == NULL) {
    return;
  }

  // Check monotonic version
  uint8_t min_monotonic_version = get_bootloader_min_version();
  if (hdr->monotonic_version < min_monotonic_version) {
    // If the new bootloader is downgraded, we don't proceed with the update
    return;
  }

  // Get address of the bootloader code
  // If the code address in UCB is 0, it means that the code is not present
  // and we change only the boot header. In such case, we
  // use the current bootloader code to calculate the Merkle root.
  uint32_t code_address = ucb.code_address;
  if (code_address == 0) {
    // Just changing the header, no bootloader code is present
    code_address = BOOTLOADER_START + hdr->header_size;
  }

  // Check if the new bootloader is the same as the old one
  // (just prevents unnecessary flash erase/write)
  if (sectrue != bootloader_area_needs_update(hdr, code_address)) {
    return;
  }

  // Calculate the Merkle root
  merkle_proof_node_t merkle_root;
  boot_header_calc_merkle_root(hdr, code_address, &merkle_root);

  // Check whether the new bootloader is properly signed
  if (sectrue != boot_header_check_signature(hdr, &merkle_root)) {
    return;
  }

  // Check that the source data does not overlap with the destination location
  // (this condition is also double-checked in boot_ucb_read)
  uint32_t min_address =
      NONBOARDLOADER_START + hdr->header_size + hdr->code_size;
  if ((uintptr_t)hdr < min_address) {
    // Boot header overlaps with the destination location
    return;
  }
  if ((ucb.code_address != 0 && ucb.code_address < min_address)) {
    // Bootloader code overlaps with the destination location
    return;
  }

  // Now we have verified that the new bootloader is valid and signed
  // and we can proceed with the update.

  // Write boot header
  const uint8_t* src = (const uint8_t*)hdr;
  uint32_t dst = 0;
  uint32_t dst_end = hdr->header_size;
  uint32_t bytes_erased = 0;

  const flash_area_t* area = &NONBOARDLOADER_AREA;

  while (dst < dst_end) {
    ensure(flash_area_erase_partial(area, dst, &bytes_erased), NULL);
    uint32_t bytes_to_copy = MIN(dst_end - dst, bytes_erased);
    ensure(flash_unlock_write(), NULL);
    ensure(flash_area_write_data(area, dst, src, bytes_to_copy), NULL);
    ensure(flash_lock_write(), NULL);
    dst += bytes_to_copy;
    src += bytes_to_copy;
  }

  // Write bootloader code
  if (ucb.code_address != 0) {
    dst = hdr->header_size;
    dst_end = dst + hdr->code_size;
    src = (const uint8_t*)(ucb.code_address);

    while (dst < dst_end) {
      ensure(flash_area_erase_partial(area, dst, &bytes_erased), NULL);
      uint32_t bytes_to_copy = MIN(dst_end - dst, bytes_erased);
      ensure(flash_unlock_write(), NULL);
      ensure(flash_area_write_data(area, dst, src, bytes_to_copy), NULL);
      ensure(flash_lock_write(), NULL);
      dst += bytes_to_copy;
      src += bytes_to_copy;
    }
  }
}

static inline void ensure_signed_bootloader(
    volatile uint32_t* next_stage_addr) {
  *next_stage_addr = 0;  // FIH

  // Start with some non-deterministic delay
  fih_delay(0);

  // Check if the boot header is present and valid
  const boot_header_auth_t* hdr = boot_header_auth_get(BOOTLOADER_START);
  fih_ensure(sectrue * (hdr != NULL), "invalid boot header");

  // Get address of the bootloader code
  uint32_t code_address = BOOTLOADER_START + hdr->header_size;

  // Calculate the Merkle root from the header and the code
  merkle_proof_node_t merkle_root;
  boot_header_calc_merkle_root(hdr, code_address, &merkle_root);

  // Check the header signature
  fih_ensure(boot_header_check_signature(hdr, &merkle_root),
             "invalid bootloader signature");

  // Ensure the bootloader is not downgraded
  uint8_t min_monotonic_version = get_bootloader_min_version();
  fih_ensure((hdr->monotonic_version >= min_monotonic_version) * sectrue,
             "BOOTLOADER DOWNGRADED");
  // Write the bootloader version to the secret area.
  write_bootloader_min_version(hdr->monotonic_version);

  *next_stage_addr = IMAGE_CODE_ALIGN(code_address);  // FIH
}

#else
static inline void ensure_signed_bootloader(
    volatile uint32_t *next_stage_addr) {
  *next_stage_addr = 0;

  // Start with some non-deterministic delay
  fih_delay(0);

  const image_header *hdr = read_image_header(
      (const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC,
      flash_area_get_size(&BOOTLOADER_AREA));

  fih_ensure(hdr == (const image_header *)BOOTLOADER_START ? sectrue : secfalse,
             "invalid bootloader header");

  fih_ensure(check_bootloader_header_sig(hdr), "invalid bootloader signature");

  fih_ensure(check_image_model(hdr), "incompatible bootloader model");

  fih_ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE, &BOOTLOADER_AREA),
             "invalid bootloader hash");

  uint8_t bld_min_version = get_bootloader_min_version();
  fih_ensure((hdr->monotonic >= bld_min_version) * sectrue,
             "BOOTLOADER DOWNGRADED");
  // Write the bootloader version to the secret area.
  // This includes the version of bootloader potentially updated from SD card.
  write_bootloader_min_version(hdr->monotonic);

  *next_stage_addr = IMAGE_CODE_ALIGN(BOOTLOADER_START + IMAGE_HEADER_SIZE);
}
#endif

int main(void) {
  // Initialize system's core services
  system_init(&rsod_panic_handler);

  reset_flags_reset();

  if (sectrue != flash_configure_option_bytes()) {
    // Option bytes were not configured correctly at startup.
    // This may indicate a first boot after manufacturing,
    // or a potential hardware fault or exploit attempt.

    // Make storage data inaccessible.
    secret_safety_erase();

    // Display an error message on the screen and reset the device.
    return 0;
  }

  // Initialize drivers needed in the boardloader
  drivers_init();

#ifdef USE_SD_CARD
  // Try to update the bootloader form the SD card
  sd_update_check_and_update();
#endif

#ifdef USE_BOOT_UCB
  // Try to update the bootloader from the UCB (update control block) if it
  // is present, valid and points to a new valid/signed bootloader image.
  try_bootloader_update();
#endif

  // Address of the next stage to jump to. It's set at the end of
  // ensure_signed_bootloader() and serves as anti-glitch protection.
  volatile uint32_t next_stage_addr = 0;  // FIH

  // Checks if the bootloader is valid and signed
  ensure_signed_bootloader(&next_stage_addr);

  // Deinitialize the drivers before jumping to the next stage,
  // so we don't leave any peripherals running.
  drivers_deinit();
  system_deinit();

  // Jump to bootloader code
  jump_to_next_stage(next_stage_addr);

  // We should never reach this point, but if we do,
  // we can return anything, as the system will reset anyway.
  return 0;
}
