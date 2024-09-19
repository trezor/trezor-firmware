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

/// mock:global
/// def ping() -> bool:
///     """
///     Test the session by pinging the chip.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_ping() {
  lt_handle_t handle = {0};
  lt_ret_t ret = LT_FAIL;

  // Every time code calls init, !! it must also do deinit before initializing handle again !!
  ret = lt_init(&handle);

  // Get X509 certificate from chip
  uint8_t X509_cert[LT_L2_GET_INFO_REQ_CERT_SIZE] = {0};
  ret = lt_get_info_cert(&handle, X509_cert, LT_L2_GET_INFO_REQ_CERT_SIZE);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Parse STPUB out of certificate
  uint8_t stpub[32] = {0};
  ret = lt_cert_verify_and_parse(X509_cert, 512, stpub);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Establish secure session with TROPIC01
  uint8_t pkey_index = PKEY_INDEX_BYTE;
  uint8_t shipriv[] = SHiPRIV_BYTES;
  uint8_t shipub[] = SHiPUB_BYTES;
  ret = lt_handshake(&handle, stpub, pkey_index, shipriv, shipub);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Send test ping message, it will go through secure session and TROPIC01 will ping the content back
  uint8_t msg_out[PING_LEN_MAX] = {0};
  uint8_t msg_in[PING_LEN_MAX]  = {0};
  uint16_t len_ping = 258;// Note: Using PING_LEN_MAX here takes some time
  // Set some message
  for(int i=0; i<len_ping; i++) {
    msg_out[i] = 'T';
  }

  ret = lt_ping(&handle, msg_out, msg_in, len_ping);
  if(ret != LT_OK || memcmp(msg_out, msg_in, len_ping)) {
    return mp_obj_new_bool(false);
  }

  // Get some random from TROPIC01
  uint8_t buff[RANDOM_VALUE_GET_LEN_MAX] = {0};
  uint16_t len_rand = 70;//L3_RANDOM_VALUE_GET_LEN_MAX;//rand() % L3_RANDOM_VALUE_GET_LEN_MAX;
  ret = lt_random_get(&handle, buff, len_rand);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Generate ED25519 private key in SLOT 1
  ret = lt_ecc_key_generate(&handle, ECC_SLOT_1, CURVE_ED25519);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Read public key corresponding to key in SLOT 1
  uint8_t key[64] = {0};
  ecc_curve_type_t curve;
  ecc_key_origin_t origin;
  ret = lt_ecc_key_read(&handle, ECC_SLOT_1, key, 64, &curve, &origin);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Setup some message and let TROPIC01 sign it with privkey from SLOT 1
  uint8_t msg[17] = {0};
  uint8_t rs[64] = {0};
  memcpy(msg, (uint8_t*)"message_message_X", 17);
  ret = lt_ecc_eddsa_sign(&handle, ECC_SLOT_1, msg, 17, rs, 64);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Verify signature here on host side
  ret = lt_ecc_eddsa_sig_verify(msg, 17, key, rs);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Erase key from SLOT 1
  ret = lt_ecc_key_erase(&handle, ECC_SLOT_1);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // Deinit TROPIC01's handle
  ret = lt_deinit(&handle);
  if(ret != LT_OK) {
    return mp_obj_new_bool(false);
  }

  // If we got here, all is good so let's return true:
  return mp_obj_new_bool(true);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_tropic_ping_obj,
                                 mod_trezorcrypto_tropic_ping);

/// mock:global
/// def get_certificate() -> bytes:
///     """
///     Return the chip's certificate.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_get_certificate() {
  lt_handle_t handle = {0};
  lt_ret_t ret = LT_FAIL;

  ret = lt_init(&handle);

  uint8_t X509_cert[512] = {0};

  ret = lt_get_info_cert(&handle, X509_cert, 512);

  if (ret != LT_OK) {
    mp_raise_msg(&mp_type_TropicError, "Failed to read certificate.");
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, 512);

  memcpy(vstr.buf, X509_cert, 512);

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_tropic_get_certificate_obj,
                                 mod_trezorcrypto_tropic_get_certificate);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_tropic_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tropic)},
    {MP_ROM_QSTR(MP_QSTR_get_certificate),
     MP_ROM_PTR(&mod_trezorcrypto_tropic_get_certificate_obj)},
    {MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&mod_trezorcrypto_tropic_ping_obj)},
    {MP_ROM_QSTR(MP_QSTR_TropicError), MP_ROM_PTR(&mp_type_TropicError)}};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_tropic_globals,
                            mod_trezorcrypto_tropic_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_tropic_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_tropic_globals,
};

#endif
