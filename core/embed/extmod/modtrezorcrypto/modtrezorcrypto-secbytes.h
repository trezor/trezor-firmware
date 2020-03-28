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

// #include "py/objstr.h"

#include "memzero.h"

/// package: trezorcrypto.__init__

#define SECBYTES_DEBUG 1

#if SECBYTES_DEBUG
STATIC uint32_t id_counter = 0;
#endif

/// class secbytes:
///     """
///     secbytes
///     """
typedef struct _mp_obj_secbytes_t {
  mp_obj_base_t base;
#if SECBYTES_DEBUG
  uint32_t id;
#endif
  uint32_t len;
  byte *ptr;
} mp_obj_secbytes_t;

STATIC const mp_obj_type_t secbytes_type; // forward declaration

STATIC mp_obj_secbytes_t *m_new_secbytes(const byte *data, uint32_t len) {
  mp_obj_secbytes_t *o = m_new_obj_with_finaliser(mp_obj_secbytes_t);
  o->base.type = &secbytes_type;
#if SECBYTES_DEBUG
  o->id = ++id_counter;
#endif
  o->len = len;
  o->ptr = m_new(byte, o->len);
  if (data) {
    memcpy(o->ptr, data, len);
  }
  return o;
}

/// def __init__(self) -> None:
///     """
///     Creates a secbytes object.
///     """
STATIC mp_obj_t secbytes_make_new(const mp_obj_type_t *type, size_t n_args,
                                  size_t n_kw, const mp_obj_t *args) {
  (void)type;
  if (n_args != 1) {
    mp_raise_ValueError("missing argument");
  }
  mp_buffer_info_t input;
  mp_get_buffer_raise(args[0], &input, MP_BUFFER_READ);
  mp_obj_secbytes_t *o = m_new_secbytes(input.buf, input.len);
  return MP_OBJ_FROM_PTR(o);
}

STATIC void secbytes_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    (void)kind;
    mp_obj_secbytes_t *self = MP_OBJ_TO_PTR(self_in);
#if SECBYTES_DEBUG
    mp_printf(print, "secbytes{id=" UINT_FMT ", len=" UINT_FMT ", data=\"", self->id, self->len);
    for (uint32_t i = 0; i < self->len; i++) {
      mp_printf(print, "%02x", self->ptr[i]);
    }
    mp_printf(print, "\"}");
#else
    mp_printf(print, "secbytes{}");
#endif
}

STATIC mp_obj_t secbytes_binary_op(mp_binary_op_t op, mp_obj_t lhs_in,
                                   mp_obj_t rhs_in) {
  mp_obj_type_t *lhs_type = mp_obj_get_type(lhs_in);
  mp_obj_type_t *rhs_type = mp_obj_get_type(rhs_in);
  if (lhs_type != &secbytes_type) {
    mp_raise_TypeError("lhs");
  }
  if (rhs_type != &secbytes_type) {
    mp_raise_TypeError("rhs");
  }

  switch (op) {
    case MP_BINARY_OP_ADD:
    case MP_BINARY_OP_INPLACE_ADD: {
      mp_obj_secbytes_t *lhs = MP_OBJ_TO_PTR(lhs_in);
      mp_obj_secbytes_t *rhs = MP_OBJ_TO_PTR(rhs_in);
      mp_obj_secbytes_t *o = m_new_secbytes(NULL, lhs->len + rhs->len);
      memcpy(o->ptr, lhs->ptr, lhs->len);
      memcpy(o->ptr + lhs->len, rhs->ptr, rhs->len);
      return MP_OBJ_FROM_PTR(o);
    }
    default:
      return MP_OBJ_NULL; // op not supported
  }
}

STATIC mp_obj_t secbytes___del__(mp_obj_t self) {
  mp_obj_secbytes_t *o = MP_OBJ_TO_PTR(self);
#if SECBYTES_DEBUG
  mp_printf(&mp_stderr_print, "del secbytes{id=%u}\n", o->id);
#endif
  memzero(&(o->ptr), o->len);
#if SECBYTES_DEBUG
  o->id = 0;
#endif
  o->len = 0;
  // o->ptr should be freed by MicroPython
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(secbytes___del___obj, secbytes___del__);

STATIC const mp_rom_map_elem_t secbytes_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&secbytes___del___obj)},
};
STATIC MP_DEFINE_CONST_DICT(secbytes_locals_dict, secbytes_locals_dict_table);

STATIC const mp_obj_type_t secbytes_type = {
    {&mp_type_type},
    .name = MP_QSTR_secbytes,
    .print = secbytes_print,
    .make_new = secbytes_make_new,
    .binary_op = secbytes_binary_op,
    .locals_dict = (void *)&secbytes_locals_dict,
};
