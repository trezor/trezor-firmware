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

#include "py/objint.h"
#include "py/runtime.h"

#ifndef __TREZOROBJ_H__
#define __TREZOROBJ_H__

#if MICROPY_LONGINT_IMPL != MICROPY_LONGINT_IMPL_MPZ
#error Use MPZ for MicroPython long int implementation.
#endif

// Casts int object into mp_int_t, without any conversions. Raises if object is
// not int or if it does not fit into mp_int_t representation.
static inline mp_int_t trezor_obj_get_int(mp_obj_t obj) {
  if (MP_OBJ_IS_SMALL_INT(obj)) {
    mp_int_t i = MP_OBJ_SMALL_INT_VALUE(obj);
    return i;
  } else if (MP_OBJ_IS_TYPE(obj, &mp_type_int)) {
    mp_int_t i = 0;
    mp_obj_int_t *self = MP_OBJ_TO_PTR(obj);
    if (!mpz_as_int_checked(&self->mpz, &i)) {
      mp_raise_msg(&mp_type_OverflowError,
                   "value does not fit into signed int type");
    }
    return i;
  } else {
    mp_raise_TypeError("value is not int");
  }
}

// Casts int object into mp_uint_t, without any conversions. Raises if object is
// not int or if it does not fit into mp_uint_t representation (or is less than
// 0).
static inline mp_uint_t trezor_obj_get_uint(mp_obj_t obj) {
  if (MP_OBJ_IS_SMALL_INT(obj)) {
    mp_int_t i = MP_OBJ_SMALL_INT_VALUE(obj);
    mp_uint_t u = i;
    return u;
  } else if (MP_OBJ_IS_TYPE(obj, &mp_type_int)) {
    mp_uint_t u = 0;
    mp_obj_int_t *self = MP_OBJ_TO_PTR(obj);
    if (!mpz_as_uint_checked(&self->mpz, &u)) {
      mp_raise_msg(&mp_type_OverflowError,
                   "value does not fit into unsigned int type");
    }
    return u;
  } else {
    mp_raise_TypeError("value is not int");
  }
}

static inline uint8_t trezor_obj_get_uint8(mp_obj_t obj) {
  mp_uint_t u = trezor_obj_get_uint(obj);
  if (u > 0xFF) {
    mp_raise_msg(&mp_type_OverflowError, "value does not fit into byte type");
  }
  return u;
}

bool trezor_obj_get_ll_checked(mp_obj_t obj, long long *value);

#endif
