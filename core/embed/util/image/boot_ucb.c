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

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sys/flash.h>
#include <sys/mpu.h>
#include <util/boot_header.h>
#include <util/boot_ucb.h>
#include <util/image_hash_conf.h>

#define BOOT_UCB_MAGIC 0x5A8C7BF3

#if defined(BOOTLOADER) || defined(BOARDLOADER)
void adjust_to_secure_flash(uint32_t* address) {
  if (*address < FLASH_BASE_S) {
    // Address is in the non-secure flash region, adjust it to point to the
    // secure flash region.
    *address += FLASH_BASE_S - FLASH_BASE_NS;
  }
}
#endif

secbool boot_ucb_read(boot_ucb_t* ucb) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUCB);
  *ucb = *((const boot_ucb_t*)BOOTUCB_START);
  mpu_restore(mpu_mode);

  if (ucb->magic != BOOT_UCB_MAGIC) {
    return secfalse;
  }

#if defined(BOOTLOADER) || defined(BOARDLOADER)
  // Addresses in the UCB block may reside in both non-secure and secure
  // flash regions.  We need to adjust them to point to the secure flash
  // region in order to proceed.
  adjust_to_secure_flash(&ucb->header_address);
  adjust_to_secure_flash(&ucb->code_address);
#endif

  // Before reading the boot header fields, we need to ensure that it's
  // located in the valid address range.
  uint32_t min_address = NONBOARDLOADER_START;
  uint32_t max_address = NONBOARDLOADER_START + NONBOARDLOADER_MAXSIZE;

  if (ucb->header_address < min_address ||
      ucb->header_address > max_address - sizeof(boot_header_auth_t)) {
    return secfalse;
  }

  const boot_header_auth_t* hdr = (boot_header_auth_t*)ucb->header_address;

  // Get address range where the header and code can be located.
  // Both header and code must be inside flash area reserved for the
  // firmware and must not overlap with the address range where
  // the new bootloader will be written.
  min_address = NONBOARDLOADER_START + hdr->header_size + hdr->code_size;
  max_address = NONBOARDLOADER_START + NONBOARDLOADER_MAXSIZE;

  // Check if the entire boot header is within the valid address range
  if (ucb->header_address < min_address || hdr->header_size > max_address ||
      ucb->header_address > max_address - hdr->header_size) {
    return secfalse;
  }

  // Check if code (if present) is within the valid address range
  if (ucb->code_address != 0) {
    if (ucb->code_address < min_address || hdr->code_size > max_address ||
        ucb->code_address > max_address - hdr->code_size) {
      return secfalse;
    }
  }

  uint8_t hash[IMAGE_HASH_DIGEST_LENGTH];  // Hash of the header

  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)hdr, hdr->header_size);
  IMAGE_HASH_FINAL(&ctx, hash);

  if (memcmp(hash, ucb->hash, sizeof(hash)) != 0) {
    // Header hash does not match the one stored in UCB
    // This can happen if the header was modified after the UCB was written.
    return secfalse;
  }

  return sectrue;
}

secbool boot_ucb_write(uint32_t header_address, uint32_t code_address) {
  boot_ucb_t ucb = {
      .magic = BOOT_UCB_MAGIC,
      .header_address = header_address,
      .code_address = code_address,
  };

  // Calculate the hash of the header
  boot_header_auth_t* hdr = (boot_header_auth_t*)header_address;

  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)hdr, hdr->header_size);
  IMAGE_HASH_FINAL(&ctx, ucb.hash);

  secbool result = secfalse;

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUCB);

  // Erase the UCB area
  if (sectrue != flash_area_erase(&BOOTUCB_AREA, NULL)) {
    goto cleanup;
  }

  if (sectrue != flash_unlock_write()) {
    goto cleanup;
  }

  // Write the UCB
  if (sectrue !=
      flash_area_write_data(&BOOTUCB_AREA, 0, (const void*)&ucb, sizeof(ucb))) {
    goto cleanup;
  }

  ensure(flash_lock_write(), NULL);

  result = sectrue;

cleanup:

  mpu_restore(mpu_mode);
  return result;
}

secbool boot_ucb_erase(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUCB);
  secbool result = flash_area_is_erased(&BOOTUCB_AREA);
  if (sectrue != result) {
    result = flash_area_erase(&BOOTUCB_AREA, NULL);
  }
  mpu_restore(mpu_mode);
  return result;
}

#endif  // SECURE_MODE
