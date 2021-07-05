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

static bool mpz_as_ll_checked(const mpz_t *i, long long *value) {
  // Analogue of `mpz_as_int_checked` from mpz.c

  unsigned long long val = 0;
  mpz_dig_t *d = i->dig + i->len;

  while (d-- > i->dig) {
    if (val > (~0x8000000000000000 >> MPZ_DIG_SIZE)) {
      // will overflow
      *value = 0;
      return false;
    }
    val = (val << MPZ_DIG_SIZE) | *d;
  }

  if (i->neg != 0) {
    val = -val;
  }

  *value = val;
  return true;
}

bool trezor_obj_get_ll_checked(mp_obj_t obj, long long *value) {
  if (mp_obj_is_small_int(obj)) {
    // Value is fitting in a small int range. Return it directly.
    *value = MP_OBJ_SMALL_INT_VALUE(obj);
    return true;

  } else if (mp_obj_is_type(obj, &mp_type_int)) {
    // Value is not fitting into small int range, but is an integer.
    mp_obj_int_t *self = MP_OBJ_TO_PTR(obj);
    // Try to get the long long value out of the MPZ struct.
    return mpz_as_ll_checked(&self->mpz, value);
  } else {
    // Value is not integer.
    *value = 0;
    return false;
  }
}
