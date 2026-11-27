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

#ifdef PQ_SECURE_BOOT
#include <sec/firmware_manifest.h>
#endif

#include "blake2s.h"

#define FW_HASHING_CHUNK_SIZE 1024

_Static_assert(BLAKE2S_DIGEST_LENGTH == sizeof(firmware_hash_t),
               "Unexpected BLAKE2S digest length");

typedef struct {
  bool initialized;
  BLAKE2S_CTX blake;
  uint32_t fw_offset;
  uint32_t fw_size;

} firmware_hash_context_t;

static firmware_hash_context_t g_hash_context[SYSTASK_MAX_TASKS];

ts_t firmware_hash_start(const uint8_t* challenge, size_t challenge_len) {
  TSH_DECLARE;

  firmware_hash_context_t* ctx = &g_hash_context[systask_id(systask_active())];

  ctx->initialized = false;

  if (challenge_len != 0) {
    int err = blake2s_InitKey(&ctx->blake, BLAKE2S_DIGEST_LENGTH, challenge,
                              challenge_len);
    TSH_CHECK(err == 0, TS_EINVAL);
  } else {
    int err = blake2s_Init(&ctx->blake, BLAKE2S_DIGEST_LENGTH);
    TSH_CHECK(err == 0, TS_EINVAL);
  }

  ctx->fw_offset = 0;
  ctx->fw_size = flash_area_get_size(&FIRMWARE_AREA);

  ensure((ctx->fw_size % FW_HASHING_CHUNK_SIZE == 0) * sectrue,
         "Cannot compute FW hash.");

  ctx->initialized = true;

cleanup:
  TSH_RETURN;
}

ts_t firmware_hash_continue(firmware_hash_t* hash, int32_t* progress) {
  TSH_DECLARE;

  firmware_hash_context_t* ctx = &g_hash_context[systask_id(systask_active())];

  memset(hash, 0, sizeof(firmware_hash_t));

  *progress = 0;

  TSH_CHECK(ctx->initialized, TS_ENOINIT);

  int n_chunks = 128;

  while (ctx->fw_offset < ctx->fw_size && n_chunks > 0) {
    const void* chunk_ptr = flash_area_get_address(
        &FIRMWARE_AREA, ctx->fw_offset, FW_HASHING_CHUNK_SIZE);

    int err = blake2s_Update(&ctx->blake, chunk_ptr, FW_HASHING_CHUNK_SIZE);
    if (err != 0) {
      ctx->initialized = false;
      TSH_RAISE(TS_EINVAL);
    }

    ctx->fw_offset += FW_HASHING_CHUNK_SIZE;
    --n_chunks;
  }

  *progress = (100 * ctx->fw_offset) / ctx->fw_size;

  if (ctx->fw_offset >= ctx->fw_size) {
    ctx->initialized = false;
    int err = blake2s_Final(&ctx->blake, hash, sizeof(firmware_hash_t));
    TSH_CHECK(err == 0, TS_EINVAL);
  }

cleanup:
  TSH_RETURN;
}

#ifdef PQ_SECURE_BOOT
// Merkle-tree layout: no vendor header in the image. Report a vendor only when
// a manifest is present, derived from the firmware_type the bootloader
// persisted into the write-protected boot header. Must agree with the
// bootloader's tree_vendor_str and the UNSAFE-prefix test in
// reboot_to_bootloader.py.
ts_t firmware_get_vendor(char* buff, size_t buff_size) {
  TSH_DECLARE;
  const void* data = flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  memset(buff, 0, buff_size);

  TSH_CHECK(data != NULL, TS_EINVAL);
  TSH_CHECK(*(const uint32_t*)data == FW_MANIFEST_MAGIC, TS_EBADMSG);

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
  TSH_CHECK(buff_size >= len + 1, TS_EINVAL);
  memcpy(buff, vendor, len);

cleanup:
  TSH_RETURN;
}
#else
ts_t firmware_get_vendor(char* buff, size_t buff_size) {
  TSH_DECLARE;
  const void* data = flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  vendor_header vhdr = {0};

  memset(buff, 0, buff_size);

  TSH_CHECK(data != NULL, TS_EINVAL);

  secbool ret = read_vendor_header(data, VENDOR_HEADER_MAX_SIZE, &vhdr);
  TSH_CHECK(ret == sectrue, TS_EBADMSG);

  TSH_CHECK(buff_size >= (size_t)(vhdr.vstr_len + 1), TS_EINVAL);

  memcpy(buff, vhdr.vstr, vhdr.vstr_len);

cleanup:
  TSH_RETURN;
}
#endif

#endif  // SECURE_MODE
