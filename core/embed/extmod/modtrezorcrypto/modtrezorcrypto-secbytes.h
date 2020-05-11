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

#include "py/objlist.h"

#include "memzero.h"
#include "secbool.h"

/// package: trezorcrypto.__init__

#define SECBYTES_DEBUG 1

typedef struct _mp_obj_secbytes_t {
  mp_obj_base_t base;
  secbool valid;
  uint32_t len;
  byte *ptr;
} mp_obj_secbytes_t;

STATIC const mp_obj_type_t secbytes_type; // forward declaration

STATIC mp_obj_secbytes_t *m_new_secbytes(const byte *data, uint32_t len) {
  mp_obj_secbytes_t *o = m_new_obj_with_finaliser(mp_obj_secbytes_t);
  o->base.type = &secbytes_type;
  o->len = len;
  o->ptr = m_new(byte, o->len);
  if (data) {
    memcpy(o->ptr, data, len);
  }
  o->valid = sectrue;
  return o;
}

#if SECBYTES_DEBUG

STATIC void secbytes_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    (void)kind;
    mp_obj_secbytes_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "secbytes{valid=" UINT_FMT ", len=" UINT_FMT ", data=\"", self->valid, self->len);
    for (uint32_t i = 0; i < self->len; i++) {
      mp_printf(print, "%02x", self->ptr[i]);
    }
    mp_printf(print, "\"}");
}

#endif

STATIC mp_obj_t secbytes___del__(mp_obj_t self) {
  mp_obj_secbytes_t *o = MP_OBJ_TO_PTR(self);
#if SECBYTES_DEBUG
  mp_printf(&mp_stderr_print, "del secbytes\n");
#endif
  memzero(o->ptr, o->len);
  o->len = 0;
  // o->ptr should be freed by MicroPython
  o->valid = secfalse;
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
#if SECBYTES_DEBUG
    .print = secbytes_print,
#endif
    .locals_dict = (void *)&secbytes_locals_dict,
};

typedef struct _mp_obj_SecureContext_t {
  mp_obj_base_t base;
  mp_obj_list_t list;
} mp_obj_SecureContext_t;

STATIC mp_obj_t SecureContext_make_new(const mp_obj_type_t *type, size_t n_args,
                                  size_t n_kw, const mp_obj_t *args) {
  mp_obj_SecureContext_t *o = m_new_obj(mp_obj_SecureContext_t);
  o->base.type = type;
  mp_obj_list_init(&(o->list), 0);
  return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t SecureContext___exit__(size_t n_args, const mp_obj_t *args) {
  mp_obj_SecureContext_t *o = MP_OBJ_TO_PTR(args[0]);
  // iterate the list and memzero its members
  for (size_t i = 0; i < o->list.len; i++) {
    mp_obj_secbytes_t *b = MP_OBJ_TO_PTR(o->list.items[i]);
    memzero(b->ptr, b->len);
    b->len = 0;
    b->valid = secfalse;
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(SecureContext___exit___obj, 4, 4, SecureContext___exit__);

STATIC mp_obj_t SecureContext_new(mp_obj_t self, mp_obj_t data) {
  mp_buffer_info_t input;
  mp_get_buffer_raise(data, &input, MP_BUFFER_READ);
  mp_obj_secbytes_t *b = m_new_secbytes(input.buf, input.len);
  mp_obj_SecureContext_t *o = MP_OBJ_TO_PTR(self);
  mp_obj_list_append(MP_OBJ_FROM_PTR(&(o->list)), MP_OBJ_FROM_PTR(b));
  return MP_OBJ_FROM_PTR(b);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(SecureContext_new_obj, SecureContext_new);

STATIC mp_obj_t SecureContext_concat(mp_obj_t self, mp_obj_t bytes1, mp_obj_t bytes2) {
  mp_obj_secbytes_t *b1 = MP_OBJ_TO_PTR(bytes1);
  mp_obj_secbytes_t *b2 = MP_OBJ_TO_PTR(bytes2);
  mp_obj_secbytes_t *b = m_new_secbytes(NULL, b1->len + b2->len);
  memcpy(b->ptr, b1->ptr, b1->len);
  memcpy(b->ptr + b1->len, b2->ptr, b2->len);
  mp_obj_SecureContext_t *o = MP_OBJ_TO_PTR(self);
  mp_obj_list_append(MP_OBJ_FROM_PTR(&(o->list)), MP_OBJ_FROM_PTR(b));
  return MP_OBJ_FROM_PTR(b);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(SecureContext_concat_obj, SecureContext_concat);

STATIC const mp_rom_map_elem_t SecureContext_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___enter__), MP_ROM_PTR(&mp_identity_obj)},
    {MP_ROM_QSTR(MP_QSTR___exit__), MP_ROM_PTR(&SecureContext___exit___obj)},
    {MP_ROM_QSTR(MP_QSTR_new), MP_ROM_PTR(&SecureContext_new_obj)},
    {MP_ROM_QSTR(MP_QSTR_concat), MP_ROM_PTR(&SecureContext_concat_obj)},
};
STATIC MP_DEFINE_CONST_DICT(SecureContext_locals_dict, SecureContext_locals_dict_table);

STATIC const mp_obj_type_t SecureContext_type = {
    {&mp_type_type},
    .name = MP_QSTR_SecureContext,
    .make_new = SecureContext_make_new,
    .locals_dict = (void *)&SecureContext_locals_dict,
};
