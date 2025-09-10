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

#if USE_TROPIC

#include <sec/secret.h>
#include <sec/tropic.h>

#include "ed25519-donna/ed25519.h"

/// package: trezorcrypto.tropic

/// class TropicError(Exception):
///     """Error returned by the Tropic Square chip."""
MP_DEFINE_EXCEPTION(TropicError, Exception)

#define PING_MSG_MAX_LEN 64
#define ECC_SLOT_COUNT 32

#define CERT_SIZE 512

/// def ping(message: str) -> str:
///     """
///     Test the session by pinging the chip.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_ping(mp_obj_t message) {
  mp_buffer_info_t message_b = {0};
  mp_get_buffer_raise(message, &message_b, MP_BUFFER_READ);

  uint8_t msg_in[message_b.len];
  bool ret = tropic_ping(message_b.buf, msg_in, message_b.len);
  if (!ret) {
    mp_raise_msg(&mp_type_TropicError, MP_ERROR_TEXT("tropic_ping failed."));
  }

  vstr_t result = {0};
  vstr_init_len(&result, message_b.len);

  memcpy(result.buf, msg_in, message_b.len);

  return mp_obj_new_str_from_vstr(&mp_type_str, &result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_tropic_ping_obj,
                                 mod_trezorcrypto_tropic_ping);

/// def key_generate(
///     key_index: int,
/// ) -> None:
///     """
///     Generate ECC key in the device's ECC key slot.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_key_generate(mp_obj_t key_index) {
  mp_int_t idx = mp_obj_get_int(key_index);
  if (idx < 0 || idx >= ECC_SLOT_COUNT) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid index."));
  }

  bool ret = tropic_ecc_key_generate(idx);
  if (!ret) {
    mp_raise_msg(&mp_type_TropicError,
                 MP_ERROR_TEXT("tropic_ecc_key_generate failed."));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_tropic_key_generate_obj,
                                 mod_trezorcrypto_tropic_key_generate);

/// def sign(
///     key_index: int,
///     digest: bytes,
/// ) -> bytes:
///     """
///     Uses the private key at key_index to produce a signature of the digest.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_sign(mp_obj_t key_index,
                                             mp_obj_t digest) {
  mp_int_t idx = mp_obj_get_int(key_index);
  if (idx < 0 || idx >= ECC_SLOT_COUNT) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid index."));
  }

  mp_buffer_info_t dig = {0};
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);

  vstr_t sig = {0};
  vstr_init_len(&sig, sizeof(ed25519_signature));

  bool ret = tropic_ecc_sign(idx, (const uint8_t *)dig.buf, dig.len,
                             ((uint8_t *)sig.buf));
  if (!ret) {
    vstr_clear(&sig);
    mp_raise_msg(&mp_type_TropicError,
                 MP_ERROR_TEXT("lt_ecc_eddsa_sign failed."));
  }

  sig.len = sizeof(ed25519_signature);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_tropic_sign_obj,
                                 mod_trezorcrypto_tropic_sign);

/// DEVICE_KEY_SLOT: int
/// FIDO_KEY_SLOT: int

STATIC const mp_rom_map_elem_t mod_trezorcrypto_tropic_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tropic)},
    {MP_ROM_QSTR(MP_QSTR_DEVICE_KEY_SLOT), MP_ROM_INT(TROPIC_DEVICE_KEY_SLOT)},
    {MP_ROM_QSTR(MP_QSTR_FIDO_KEY_SLOT), MP_ROM_INT(TROPIC_FIDO_KEY_SLOT)},
    {MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&mod_trezorcrypto_tropic_ping_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_generate),
     MP_ROM_PTR(&mod_trezorcrypto_tropic_key_generate_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_trezorcrypto_tropic_sign_obj)},
    {MP_ROM_QSTR(MP_QSTR_TropicError), MP_ROM_PTR(&mp_type_TropicError)}};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_tropic_globals,
                            mod_trezorcrypto_tropic_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_tropic_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_tropic_globals,
};

#endif
