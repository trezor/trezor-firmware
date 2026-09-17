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

#include <sec/boot_header.h>
#include <sec/fwutils.h>
#include <sec/image.h>
#include <sys/flash.h>
#include <sys/mpu.h>
#include <sys/systask.h>

#include "blake2s.h"

#define FW_HASHING_CHUNK_SIZE 1024

typedef struct {
  bool initialized;
  BLAKE2S_CTX blake;
  uint32_t fw_offset;
  uint32_t fw_size;

} firmware_hash_context_t;

static firmware_hash_context_t g_hash_context[SYSTASK_MAX_TASKS];

int firmware_hash_start(const uint8_t* challenge, size_t challenge_len) {
  firmware_hash_context_t* ctx = &g_hash_context[systask_id(systask_active())];

  int err;

  if (challenge_len != 0) {
    err = blake2s_InitKey(&ctx->blake, BLAKE2S_DIGEST_LENGTH, challenge,
                          challenge_len);
  } else {
    err = blake2s_Init(&ctx->blake, BLAKE2S_DIGEST_LENGTH);
  }

  if (err != 0) {
    return -1;
  }

  ctx->fw_offset = 0;
  ctx->fw_size = flash_area_get_size(&FIRMWARE_AREA);

  ensure((ctx->fw_size % FW_HASHING_CHUNK_SIZE == 0) * sectrue,
         "Cannot compute FW hash.");

  ctx->initialized = true;
  return 0;
}

int firmware_hash_continue(uint8_t* hash, size_t hash_len) {
  firmware_hash_context_t* ctx = &g_hash_context[systask_id(systask_active())];

  memset(hash, 0, hash_len);

  if (!ctx->initialized) {
    return -1;
  }

  int n_chunks = 128;

  while (ctx->fw_offset < ctx->fw_size && n_chunks > 0) {
    const void* chunk_ptr = flash_area_get_address(
        &FIRMWARE_AREA, ctx->fw_offset, FW_HASHING_CHUNK_SIZE);

    int err = blake2s_Update(&ctx->blake, chunk_ptr, FW_HASHING_CHUNK_SIZE);
    if (err != 0) {
      ctx->initialized = false;
      return -1;
    }

    ctx->fw_offset += FW_HASHING_CHUNK_SIZE;
    --n_chunks;
  }

  if (ctx->fw_offset >= ctx->fw_size) {
    ctx->initialized = false;
    int err = blake2s_Final(&ctx->blake, hash, hash_len);
    if (err != 0) {
      return -1;
    }
  }

  return (100 * ctx->fw_offset) / ctx->fw_size;
}

#ifdef PQ_SECURE_BOOT
// Merkle-tree layout: no vendor header in the image. Report a vendor only when
// a manifest is present, derived from the firmware_type the bootloader
// persisted into the write-protected boot header. Must agree with the
// bootloader's tree_vendor_str and the UNSAFE-prefix test in
// reboot_to_bootloader.py.
secbool firmware_get_vendor(char* buff, size_t buff_size) {
  const void* data = flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  memset(buff, 0, buff_size);

  if (data == NULL || *(const uint32_t*)data != FW_MANIFEST_MAGIC) {
    return secfalse;
  }

  // The bootloader area is unmapped in the secmon's default MPU mode.
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTLOADER);
  // Via the flash area, not BOOTLOADER_START: sec/ is shared with the emulator,
  // where the raw constant is not a valid pointer.
  const boot_header_auth_t* bl =
      boot_header_auth_get((uintptr_t)flash_area_get_address(
          &BOOTLOADER_AREA, 0, sizeof(boot_header_auth_t)));
  const boot_header_unauth_t* unauth =
      (bl != NULL) ? boot_header_unauth_get(bl) : NULL;
  const fw_variant_sec_t variant =
      (unauth != NULL) ? unauth->firmware_type : FW_VARIANT_SEC_INVALID;
  mpu_restore(mpu_mode);

  const char* vendor = firmware_vendor_str(variant);

  size_t len = strlen(vendor);
  if (buff_size < len + 1) {
    return secfalse;
  }
  memcpy(buff, vendor, len);
  return sectrue;
}
#else
secbool firmware_get_vendor(char* buff, size_t buff_size) {
  const void* data = flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  vendor_header vhdr = {0};

  memset(buff, 0, buff_size);

  if (data == NULL ||
      sectrue != read_vendor_header(data, VENDOR_HEADER_MAX_SIZE, &vhdr)) {
    return secfalse;
  }

  if (buff_size < vhdr.vstr_len + 1) {
    return secfalse;
  }

  memcpy(buff, vhdr.vstr, vhdr.vstr_len);

  return sectrue;
}
#endif

#endif  // SECURE_MODE
