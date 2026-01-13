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

#include <sec/secret.h>
#include <sec/secret_keys.h>
#include "../secret_keys_common.h"

#include <sec/rng_strong.h>
#include <sys/mpu.h>
#include <util/flash_otp.h>
#include "memzero.h"

#ifdef USE_OPTIGA

secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]) {
  return secret_key_get(SECRET_OPTIGA_SLOT, dest, OPTIGA_PAIRING_SECRET_SIZE);
}

#endif  // USE_OPTIGA

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  secret_key_derive_nist256p1(UNUSED_KEY_SLOT, KEY_INDEX_DELEGATED_IDENTITY,
                              dest);
  return sectrue;
}

secbool secret_key_master_key_get(secret_key_master_key_t* master_key) {
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_MASTER_KEY)) {
    uint8_t rnd_bytes[SECRET_KEY_MASTER_KEY_SIZE];
    if (!rng_fill_buffer_strong(rnd_bytes, SECRET_KEY_MASTER_KEY_SIZE)) {
      memzero(rnd_bytes, sizeof(rnd_bytes));
      return secfalse;
    }
    ensure(flash_otp_write(FLASH_OTP_BLOCK_MASTER_KEY, 0, rnd_bytes,
                           SECRET_KEY_MASTER_KEY_SIZE),
           NULL);
    ensure(flash_otp_lock(FLASH_OTP_BLOCK_MASTER_KEY), NULL);
  }
  ensure(flash_otp_read(FLASH_OTP_BLOCK_MASTER_KEY, 0, &master_key->bytes[0],
                        SECRET_KEY_MASTER_KEY_SIZE),
         NULL);

  master_key->size = SECRET_KEY_MASTER_KEY_SIZE;
  return sectrue;
}

#endif  // SECURE_MODE
