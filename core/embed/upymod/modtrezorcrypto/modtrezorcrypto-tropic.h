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

// Default initial Tropic handshake keys
#define PKEY_INDEX_BYTE PAIRING_KEY_SLOT_INDEX_0
#define SHiPRIV_BYTES                                                \
  {0xf0, 0xc4, 0xaa, 0x04, 0x8f, 0x00, 0x13, 0xa0, 0x96, 0x84, 0xdf, \
   0x05, 0xe8, 0xa2, 0x2e, 0xf7, 0x21, 0x38, 0x98, 0x28, 0x2b, 0xa9, \
   0x43, 0x12, 0xf3, 0x13, 0xdf, 0x2d, 0xce, 0x8d, 0x41, 0x64};
#define SHiPUB_BYTES                                                 \
  {0x84, 0x2f, 0xe3, 0x21, 0xa8, 0x24, 0x74, 0x08, 0x37, 0x37, 0xff, \
   0x2b, 0x9b, 0x88, 0xa2, 0xaf, 0x42, 0x44, 0x2d, 0xb0, 0xd8, 0xaa, \
   0xcc, 0x6d, 0xc6, 0x9e, 0x99, 0x53, 0x33, 0x44, 0xb2, 0x46};

#include "libtropic.h"

/// package: trezorcrypto.tropic

/// class TropicError(Exception):
///     """Error returned by the Tropic Square chip."""
MP_DEFINE_EXCEPTION(TropicError, Exception)

#define PING_MSG_MAX_LEN 64
#define ECC_SLOT_COUNT 32
#define SIG_SIZE 64

STATIC bool lt_handle_initialized = false;
STATIC lt_handle_t lt_handle = {0};

STATIC void tropic_init(lt_handle_t *handle) {
  lt_ret_t ret = LT_FAIL;

  ret = lt_init(handle);
  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "lt_init failed.");
  }

  uint8_t X509_cert[LT_L2_GET_INFO_REQ_CERT_SIZE] = {0};

  ret = lt_get_info_cert(handle, X509_cert, LT_L2_GET_INFO_REQ_CERT_SIZE);
  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "lt_get_info_cert failed.");
  }

  uint8_t stpub[32] = {0};
  ret = lt_cert_verify_and_parse(X509_cert, 512, stpub);
  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "lt_cert_verify_and_parse failed.");
  }

  uint8_t pkey_index = PKEY_INDEX_BYTE;
  uint8_t shipriv[] = SHiPRIV_BYTES;
  uint8_t shipub[] = SHiPUB_BYTES;

  ret = lt_handshake(handle, stpub, pkey_index, shipriv, shipub);
  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "lt_handshake failed.");
  }
}

/// def ping(message: str) -> str:
///     """
///     Test the session by pinging the chip.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_ping(mp_obj_t message) {
  lt_ret_t ret = LT_FAIL;

  if (!lt_handle_initialized) {
    tropic_init(&lt_handle);
    lt_handle_initialized = true;
  }

  uint8_t msg_in[PING_MSG_MAX_LEN] = {0};

  mp_buffer_info_t message_b = {0};
  mp_get_buffer_raise(message, &message_b, MP_BUFFER_READ);
  if (message_b.len > 0) {
    ret = lt_ping(&lt_handle, (uint8_t *)message_b.buf, (uint8_t *)msg_in,
                  message_b.len);
    if (ret != LT_OK) {
      mp_raise_msg(&mp_type_TropicError, "lt_ping failed.");
    }
  } else {
    return mp_const_none;
  }

  vstr_t result = {0};
  vstr_init_len(&result, message_b.len);

  memcpy(result.buf, msg_in, message_b.len);
  result.len = strlen(result.buf);

  return mp_obj_new_str_from_vstr(&mp_type_str, &result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_tropic_ping_obj,
                                 mod_trezorcrypto_tropic_ping);

/// def get_certificate() -> bytes:
///     """
///     Return the chip's certificate.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_get_certificate() {
  lt_ret_t ret = LT_FAIL;

  if (!lt_handle_initialized) {
    tropic_init(&lt_handle);
    lt_handle_initialized = true;
  }

  uint8_t X509_cert[512] = {0};
  ret = lt_get_info_cert(&lt_handle, X509_cert, 512);
  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "lt_get_info_cert failed.");
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, 512);

  memcpy(vstr.buf, X509_cert, 512);

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

  lt_ret_t ret = LT_FAIL;

  if (!lt_handle_initialized) {
    tropic_init(&lt_handle);
    lt_handle_initialized = true;
  }

  ret = lt_ecc_key_generate(&lt_handle, idx, CURVE_ED25519);
  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "lt_ecc_key_generate failed.");
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

  lt_ret_t ret = LT_FAIL;

  if (!lt_handle_initialized) {
    tropic_init(&lt_handle);
    lt_handle_initialized = true;
  }

  vstr_t sig = {0};
  vstr_init_len(&sig, SIG_SIZE);

  ret = lt_ecc_eddsa_sign(&lt_handle, idx, (const uint8_t *)dig.buf, dig.len,
                          ((uint8_t *)sig.buf), SIG_SIZE);
  if (ret != LT_OK) {
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
