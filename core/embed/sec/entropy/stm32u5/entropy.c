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

#include <sec/entropy.h>
#include <sec/secret_keys.h>
#include <sys/mpu.h>
#include <util/flash_otp.h>
#include <util/image.h>
#include "rand.h"

#include "stm32u5xx_ll_utils.h"

#ifdef SECURE_MODE

static entropy_data_t g_entropy = {0};

#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT

// Entropy derived from master key
void entropy_init(void) {
  entropy_data_t* ent = &g_entropy;

  vendor_header vhdr = {0};
  ensure(read_vendor_header((const uint8_t*)FIRMWARE_START, &vhdr), NULL);

  _Static_assert(SECRET_KEY_STORAGE_SALT_SIZE <= sizeof(ent->bytes));
  secbool retval = secret_key_storage_salt(vhdr.fw_type, ent->bytes);

#if PRODUCTION
  ensure(retval, "Failed to get storage salt");
#else
  // In non-production builds, we allow failure to retrieve the storage salt,
  // so we don't need to set up the master key every time the flash is erased.
  (void)retval;
#endif

  ent->size = SECRET_KEY_STORAGE_SALT_SIZE;
}

#else

// Legacy entropy generated from CPUID & radnom data in OTP
void entropy_init(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  entropy_data_t* ent = &g_entropy;

  // collect entropy from UUID
  uint32_t w = LL_GetUID_Word0();
  memcpy(&ent->bytes[0], &w, 4);
  w = LL_GetUID_Word1();
  memcpy(&ent->bytes[4], &w, 4);
  w = LL_GetUID_Word2();
  memcpy(&ent->bytes[8], &w, 4);

  mpu_restore(mpu_mode);

  // set entropy in the OTP randomness block
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
    uint8_t rnd_bytes[FLASH_OTP_BLOCK_SIZE];
    random_buffer(rnd_bytes, FLASH_OTP_BLOCK_SIZE);
    ensure(flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, rnd_bytes,
                           FLASH_OTP_BLOCK_SIZE),
           NULL);
  }
  // collect entropy from OTP randomness block
  ensure(flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, &ent->bytes[12],
                        FLASH_OTP_BLOCK_SIZE),
         NULL);

  ent->size = 12 + FLASH_OTP_BLOCK_SIZE;
}

#endif

void entropy_get(entropy_data_t* entropy) { *entropy = g_entropy; }

#endif  // SECURE_MODE
