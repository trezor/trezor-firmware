/*
 * Copyright (c) 2025 Trezor Company s.r.o.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of
 * this software and associated documentation files (the "Software"), to deal in
 * the Software without restriction, including without limitation the rights to
 * use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 * the Software, and to permit persons to whom the Software is furnished to do so,
 * subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include <trezor_rtl.h>

#include "memzero.h"
#include "py/obj.h"
#include "py/objint.h"
#include "py/objstr.h"
#include "py/runtime.h"

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

  } else if (mp_obj_is_int(obj)) {
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

mp_obj_t trezor_obj_call_protected(void (*func)(void *), void *arg) {
  nlr_buf_t nlr;
  if (nlr_push(&nlr) == 0) {
    (*func)(arg);
    nlr_pop();
    return NULL;
  } else {
    return MP_OBJ_FROM_PTR(nlr.ret_val);
  }
}

mp_obj_t trezor_obj_str_from_rom_text(const char *str) {
  // taken from mp_obj_new_exception_msg
  mp_obj_str_t *o_str = m_new_obj_maybe(mp_obj_str_t);
  if (o_str == NULL) return NULL;

  o_str->base.type = &mp_type_str;
  o_str->len = strlen(str);
  o_str->data = (const byte *)str;
#if MICROPY_ROM_TEXT_COMPRESSION
  o_str->hash = 0;  // will be computed only if string object is accessed
#else
  o_str->hash = qstr_compute_hash(o_str->data, o_str->len);
#endif
  return MP_OBJ_FROM_PTR(o_str);
}
