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

#include "api.h"
#include "pq_signature.h"

/// package: trezorcrypto.pq_signature
/// public_key_size: int
/// secret_key_size: int
/// signature_size: int

/// def generate_keypair() -> Tuple[bytes, bytes]:
STATIC mp_obj_t mod_trezorcrypto_pq_signature_generate_keypair() {
  uint8_t public_key[CRYPTO_PUBLICKEYBYTES] = {};
  uint8_t secret_key[CRYPTO_SECRETKEYBYTES] = {};

#ifdef PQ_SIGNATURE_VERIFICATION_ONLY
  (void)secret_key;
  (void)public_key;
#else
  if (crypto_sign_keypair(public_key, secret_key) != 0) {
    mp_raise_ValueError("Keypair generation failed");
  }
#endif

  mp_obj_tuple_t *tuple = mp_obj_new_tuple(2, NULL);
  tuple->items[0] = mp_obj_new_bytes(secret_key, CRYPTO_SECRETKEYBYTES);
  tuple->items[1] = mp_obj_new_bytes(public_key, CRYPTO_PUBLICKEYBYTES);

  return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(
    mod_trezorcrypto_pq_signature_generate_keypair_obj,
    mod_trezorcrypto_pq_signature_generate_keypair);

/// def sign(
///     secret_key: bytes,
///     message: bytes
/// ) -> bytes:
STATIC mp_obj_t mod_trezorcrypto_pq_signature_sign(mp_obj_t secret_key,
                                                   mp_obj_t message) {
  mp_buffer_info_t secret_key_buffer = {0};
  mp_buffer_info_t message_buffer = {0};

  mp_get_buffer_raise(secret_key, &secret_key_buffer, MP_BUFFER_READ);
  mp_get_buffer_raise(message, &message_buffer, MP_BUFFER_READ);

  if (secret_key_buffer.len != CRYPTO_SECRETKEYBYTES) {
    mp_raise_ValueError("Invalid length of secret key");
  }

  uint8_t signature[CRYPTO_BYTES];
  size_t signature_length = sizeof(signature);

#ifdef PQ_SIGNATURE_VERIFICATION_ONLY
  (void)signature;
  (void)signature_length;
#else
  if (crypto_sign_signature(signature, &signature_length, message_buffer.buf,
                            message_buffer.len, secret_key_buffer.buf) != 0) {
    mp_raise_ValueError("Signing failed");
  }
#endif

  return mp_obj_new_bytes(signature, signature_length);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_pq_signature_sign_obj,
                                 mod_trezorcrypto_pq_signature_sign);

/// def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
STATIC mp_obj_t mod_trezorcrypto_pq_signature_verify(mp_obj_t public_key,
                                                     mp_obj_t signature,
                                                     mp_obj_t message) {
  mp_buffer_info_t public_key_buffer = {0};
  mp_buffer_info_t signature_buffer = {0};
  mp_buffer_info_t message_buffer = {0};

  mp_get_buffer_raise(public_key, &public_key_buffer, MP_BUFFER_READ);
  mp_get_buffer_raise(signature, &signature_buffer, MP_BUFFER_READ);
  mp_get_buffer_raise(message, &message_buffer, MP_BUFFER_READ);

  if (public_key_buffer.len != CRYPTO_PUBLICKEYBYTES) {
    mp_raise_ValueError("Invalid length of public key");
  }

  if (signature_buffer.len > CRYPTO_BYTES) {
    mp_raise_ValueError("Invalid length of signature");
  }

  if (crypto_sign_verify(signature_buffer.buf, signature_buffer.len,
                         message_buffer.buf, message_buffer.len,
                         public_key_buffer.buf) != 0) {
    return mp_const_false;
  }

  return mp_const_true;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_pq_signature_verify_obj,
                                 mod_trezorcrypto_pq_signature_verify);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_pq_signature_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pq_signature)},
    {MP_ROM_QSTR(MP_QSTR_generate_keypair),
     MP_ROM_PTR(&mod_trezorcrypto_pq_signature_generate_keypair_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign),
     MP_ROM_PTR(&mod_trezorcrypto_pq_signature_sign_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify),
     MP_ROM_PTR(&mod_trezorcrypto_pq_signature_verify_obj)},
    {MP_ROM_QSTR(MP_QSTR_public_key_size), MP_ROM_INT(CRYPTO_PUBLICKEYBYTES)},
    {MP_ROM_QSTR(MP_QSTR_secret_key_size), MP_ROM_INT(CRYPTO_SECRETKEYBYTES)},
    {MP_ROM_QSTR(MP_QSTR_signature_size), MP_ROM_INT(CRYPTO_BYTES)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_pq_signature_globals,
                            mod_trezorcrypto_pq_signature_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_pq_signature_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_pq_signature_globals,
};
