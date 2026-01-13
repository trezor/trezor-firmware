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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/secret_keys.h>
#include <sys/flash_otp.h>
#include <sys/mpu.h>
#include <sys/rng.h>
#include <util/image.h>

#include "stm32u5xx_ll_utils.h"

#include "../storage_salt.h"

#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT

void storage_salt_get(storage_salt_t* salt) {
  memset(salt, 0, sizeof(*salt));

  vendor_header vhdr = {0};
  ensure(read_vendor_header((const uint8_t*)FIRMWARE_START, &vhdr), NULL);

  _Static_assert(SECRET_KEY_STORAGE_SALT_SIZE <= sizeof(salt->bytes));
  secbool retval = secret_key_storage_salt(vhdr.fw_type, salt->bytes);

#if PRODUCTION
  ensure(retval, "Failed to get storage salt");
#else
  // In non-production builds, we allow failure to retrieve the storage salt,
  // so we don't need to set up the master key every time the flash is erased.
  (void)retval;
#endif

  salt->size = SECRET_KEY_STORAGE_SALT_SIZE;
}

#else

// Legacy entropy generated from CPUID & radnom data in OTP
void storage_salt_get(storage_salt_t* salt) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  // collect entropy from UUID
  uint32_t w = LL_GetUID_Word0();
  memcpy(&salt->bytes[0], &w, 4);
  w = LL_GetUID_Word1();
  memcpy(&salt->bytes[4], &w, 4);
  w = LL_GetUID_Word2();
  memcpy(&salt->bytes[8], &w, 4);

  mpu_restore(mpu_mode);

  // set entropy in the OTP randomness block
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
    uint8_t rnd_bytes[FLASH_OTP_BLOCK_SIZE];
    rng_fill_buffer(rnd_bytes, FLASH_OTP_BLOCK_SIZE);
    ensure(flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, rnd_bytes,
                           FLASH_OTP_BLOCK_SIZE),
           NULL);
  }
  // collect entropy from OTP randomness block
  ensure(flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, &salt->bytes[12],
                        FLASH_OTP_BLOCK_SIZE),
         NULL);

  salt->size = 12 + FLASH_OTP_BLOCK_SIZE;
}

#endif

#endif  // SECURE_MODE
