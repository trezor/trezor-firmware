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

#include "py/objstr.h"

#include "mlkem.h"
#include "rand.h"

/// package: trezorcrypto.mlkem

/// def generate_keypair() -> Tuple[bytes, bytes]:
///     """
///     Returns a tuple of secret key and public key.
///     """
STATIC mp_obj_t mod_trezorcrypto_mlkem_generate_keypair() {
  vstr_t dk, pub_key = {0};
  vstr_init_len(&dk, MLKEM_DECAPSULATION_KEY_SIZE);
  vstr_init_len(&pub_key, MLKEM_ENCAPSULATION_KEY_SIZE);
  if (mlkem_generate_keypair((uint8_t *)pub_key.buf, (uint8_t *)dk.buf) != 0) {
    mp_raise_msg(&mp_type_ValueError, "Failed to generate keypair");
  }
  mp_obj_t tuple[2] = {
      mp_obj_new_str_from_vstr(&mp_type_bytes, &dk),
      mp_obj_new_str_from_vstr(&mp_type_bytes, &pub_key),
  };
  return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_mlkem_generate_keypair_obj,
                                 mod_trezorcrypto_mlkem_generate_keypair);

/// def encapsulate(encapsulation_key: bytes) -> Tuple[bytes, bytes]:
///     """
///     Returns a tuple of ciphertext and shared secret.
///     """
STATIC mp_obj_t mod_trezorcrypto_mlkem_encapsulate(mp_obj_t encapsulation_key) {
  mp_buffer_info_t pub_key = {0};
  mp_get_buffer_raise(encapsulation_key, &pub_key, MP_BUFFER_READ);
  if (pub_key.len != MLKEM_ENCAPSULATION_KEY_SIZE) {
    mp_raise_ValueError("Invalid length of public key");
  }
  vstr_t ct, ss = {0};
  vstr_init_len(&ct, MLKEM_CIPHERTEXT_SIZE);
  vstr_init_len(&ss, MLKEM_SHARED_SECRET_SIZE);
  if (mlkem_encapsulate((uint8_t *)ct.buf, (uint8_t *)ss.buf, pub_key.buf) !=
      0) {
    mp_raise_msg(&mp_type_ValueError, "Failed to encapsulate");
  }
  mp_obj_t tuple[2] = {
      mp_obj_new_str_from_vstr(&mp_type_bytes, &ct),
      mp_obj_new_str_from_vstr(&mp_type_bytes, &ss),
  };
  return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_mlkem_encapsulate_obj,
                                 mod_trezorcrypto_mlkem_encapsulate);

/// def decapsulate(decapsulation_key: bytes, ciphertext: bytes) -> bytes:
///     """
///     Returns shared secret.
///     """
STATIC mp_obj_t mod_trezorcrypto_mlkem_decapsulate(mp_obj_t decapsulation_key,
                                                   mp_obj_t ciphertext) {
  mp_buffer_info_t dk, ct = {0};
  mp_get_buffer_raise(decapsulation_key, &dk, MP_BUFFER_READ);
  if (dk.len != MLKEM_DECAPSULATION_KEY_SIZE) {
    mp_raise_ValueError("Invalid length of public key");
  }
  mp_get_buffer_raise(ciphertext, &ct, MP_BUFFER_READ);
  if (ct.len != MLKEM_CIPHERTEXT_SIZE) {
    mp_raise_ValueError("Invalid length of ciphertext");
  }
  vstr_t ss = {0};
  vstr_init_len(&ss, MLKEM_SHARED_SECRET_SIZE);
  if (mlkem_decapsulate((uint8_t *)ss.buf, (uint8_t *)ct.buf,
                        (uint8_t *)dk.buf) != 0) {
    mp_raise_msg(&mp_type_ValueError, "Failed to decapsulate");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &ss);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_mlkem_decapsulate_obj,
                                 mod_trezorcrypto_mlkem_decapsulate);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_mlkem_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mlkem)},
    {MP_ROM_QSTR(MP_QSTR_generate_keypair),
     MP_ROM_PTR(&mod_trezorcrypto_mlkem_generate_keypair_obj)},
    {MP_ROM_QSTR(MP_QSTR_decapsulate),
     MP_ROM_PTR(&mod_trezorcrypto_mlkem_decapsulate_obj)},
    {MP_ROM_QSTR(MP_QSTR_encapsulate),
     MP_ROM_PTR(&mod_trezorcrypto_mlkem_encapsulate_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_mlkem_globals,
                            mod_trezorcrypto_mlkem_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_mlkem_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_mlkem_globals,
};
