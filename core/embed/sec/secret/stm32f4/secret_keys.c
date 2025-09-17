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

#ifdef USE_OPTIGA
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]) {
  return secret_key_get(SECRET_OPTIGA_SLOT, dest, OPTIGA_PAIRING_SECRET_SIZE);
}
#endif // USE_OPTIGA

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  // TODO: this is a placeholder value
  static const uint8_t key[32] = {
      0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b,
      0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16,
      0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20};
  memcpy(dest, key, ECDSA_PRIVATE_KEY_SIZE);
  return sectrue;
}

#endif // SECURE_MODE
