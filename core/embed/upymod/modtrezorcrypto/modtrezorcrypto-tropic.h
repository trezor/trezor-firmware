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

/// package: trezorcrypto.tropic

/// class TropicError(Exception):
///     """Error returned by the Tropic Square chip."""
MP_DEFINE_EXCEPTION(TropicError, Exception)

#define PING_MSG_MAX_LEN 64
#define ECC_SLOT_COUNT 32
#define SIG_SIZE 64

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
    mp_raise_msg(&mp_type_TropicError, "tropic_ping failed.");
  }

  vstr_t result = {0};
  vstr_init_len(&result, message_b.len);

  memcpy(result.buf, msg_in, message_b.len);

  return mp_obj_new_str_from_vstr(&mp_type_str, &result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_tropic_ping_obj,
                                 mod_trezorcrypto_tropic_ping);

/// def get_certificate() -> bytes:
///     """
///     Return the chip's certificate.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_get_certificate() {
  uint8_t X509_cert[CERT_SIZE] = {0};
  bool ret = tropic_get_cert(X509_cert, CERT_SIZE);
  if (!ret) {
    mp_raise_msg(&mp_type_TropicError, "tropic_get_cert failed.");
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, CERT_SIZE);

  memcpy(vstr.buf, X509_cert, CERT_SIZE);

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_tropic_get_certificate_obj,
                                 mod_trezorcrypto_tropic_get_certificate);

/// def key_generate(
///     key_index: int,
/// ) -> None:
///     """
///     Generate ECC key in the device's ECC key slot.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_key_generate(mp_obj_t key_index) {
  mp_int_t idx = mp_obj_get_int(key_index);
  if (idx < 0 || idx >= ECC_SLOT_COUNT) {
    mp_raise_ValueError("Invalid index.");
  }

  bool ret = tropic_ecc_key_generate(idx);
  if (!ret) {
    mp_raise_msg(&mp_type_TropicError, "tropic_ecc_key_generate failed.");
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
    mp_raise_ValueError("Invalid index.");
  }

  mp_buffer_info_t dig = {0};
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (dig.len != 32) {
    mp_raise_ValueError("Invalid length of digest.");
  }

  vstr_t sig = {0};
  vstr_init_len(&sig, SIG_SIZE);

  bool ret = tropic_ecc_sign(idx, (const uint8_t *)dig.buf, dig.len,
                             ((uint8_t *)sig.buf), SIG_SIZE);
  if (!ret) {
    vstr_clear(&sig);
    mp_raise_msg(&mp_type_TropicError, "lt_ecc_eddsa_sign failed.");
  }

  sig.len = SIG_SIZE;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_tropic_sign_obj,
                                 mod_trezorcrypto_tropic_sign);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_tropic_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tropic)},
    {MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&mod_trezorcrypto_tropic_ping_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_certificate),
     MP_ROM_PTR(&mod_trezorcrypto_tropic_get_certificate_obj)},
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
