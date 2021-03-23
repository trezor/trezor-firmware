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

#include <string.h>

#include "memzero.h"
#include "py/objint.h"

bool trezor_obj_get_ll_checked(mp_obj_t obj, long long *value) {
  if (mp_obj_is_small_int(obj)) {
    // Value is fitting in a small int range. Return it directly.
    *value = MP_OBJ_SMALL_INT_VALUE(obj);
    return true;

  } else if (mp_obj_is_type(obj, &mp_type_int)) {
    // Value is not fitting into small int range, but is an integer.
    mp_obj_int_t *self = MP_OBJ_TO_PTR(obj);
    if (mpz_max_num_bits(&self->mpz) <= sizeof(long long) * 8) {
      // Value is fitting into long long, copy it out as bytes.
      uint8_t bytes[sizeof(long long)];
      memzero(bytes, sizeof(bytes));
      mpz_as_bytes(&self->mpz, false, sizeof(bytes), bytes);
      memcpy(value, bytes, sizeof(long long));
      return true;
    } else {
      // Value is not fitting into long long.
      *value = 0;
      return false;
    }

  } else {
    // Value is not integer.
    *value = 0;
    return false;
  }
}
