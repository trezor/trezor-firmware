/*
 * Copyright (c) 2025 Trezor Company s.r.o.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
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
                   MP_ERROR_TEXT("value does not fit into signed int type"));
    }
    return i;
  } else {
    mp_raise_TypeError(MP_ERROR_TEXT("value is not int"));
  }
}

// Casts int object into mp_uint_t, without any conversions. Raises if object is
// not int or if it does not fit into mp_uint_t representation (or is less than
// 0).
static inline mp_uint_t trezor_obj_get_uint(mp_obj_t obj) {
  if (MP_OBJ_IS_SMALL_INT(obj)) {
    mp_int_t i = MP_OBJ_SMALL_INT_VALUE(obj);
    if (i < 0) {
      mp_raise_TypeError(MP_ERROR_TEXT("value is negative"));
    }
    mp_uint_t u = i;
    return u;
  } else if (MP_OBJ_IS_TYPE(obj, &mp_type_int)) {
    mp_uint_t u = 0;
    mp_obj_int_t *self = MP_OBJ_TO_PTR(obj);
    if (!mpz_as_uint_checked(&self->mpz, &u)) {
      mp_raise_msg(&mp_type_OverflowError,
                   MP_ERROR_TEXT("value does not fit into unsigned int type"));
    }
    return u;
  } else {
    mp_raise_TypeError(MP_ERROR_TEXT("value is not int"));
  }
}

static inline uint8_t trezor_obj_get_uint8(mp_obj_t obj) {
  mp_uint_t u = trezor_obj_get_uint(obj);
  if (u > 0xFF) {
    mp_raise_msg(&mp_type_OverflowError,
                 MP_ERROR_TEXT("value does not fit into byte type"));
  }
  return u;
}

static inline uint64_t trezor_obj_get_uint64(mp_const_obj_t obj) {
  if (MP_OBJ_IS_SMALL_INT(obj)) {
    mp_int_t i = MP_OBJ_SMALL_INT_VALUE(obj);
    if (i < 0) {
      mp_raise_TypeError(MP_ERROR_TEXT("value is negative"));
    }
    mp_uint_t u = i;
    return u;
  } else if (MP_OBJ_IS_TYPE(obj, &mp_type_int)) {
    uint64_t u = 0;
    mp_obj_int_t *self = MP_OBJ_TO_PTR(obj);
    if (self->mpz.neg != 0) {
      mp_raise_TypeError(MP_ERROR_TEXT("value is negative"));
    }
    mpz_as_bytes(&self->mpz, MP_ENDIANNESS_BIG, sizeof(uint64_t), (byte *)&u);
    return u;
  } else {
    mp_raise_TypeError(MP_ERROR_TEXT("value is not int"));
  }
}

bool trezor_obj_get_ll_checked(mp_obj_t obj, long long *value);

mp_obj_t trezor_obj_call_protected(void (*func)(void *), void *arg);

mp_obj_t trezor_obj_str_from_rom_text(const char *str);

#endif
