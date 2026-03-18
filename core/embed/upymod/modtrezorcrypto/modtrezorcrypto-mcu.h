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

#ifdef USE_MCU_ATTESTATION

#include <sec/mcu_attestation.h>

/// package: trezorcrypto.mcu

/// def get_certificate() -> bytes:
///     """
///     Return MCU device certificate.
///     """
STATIC mp_obj_t mod_trezorcrypto_mcu_get_certificate(void) {
  size_t cert_size = 0;
  if (mcu_attestation_cert_size(&cert_size) != sectrue) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get certificate size."));
  }

  vstr_t cert = {0};
  vstr_init_len(&cert, cert_size);
  if (mcu_attestation_cert_read((uint8_t *)cert.buf, cert.alloc, &cert_size) !=
      sectrue) {
    vstr_clear(&cert);
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to read certificate."));
  }

  cert.len = cert_size;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &cert);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_mcu_get_certificate_obj,
                                 mod_trezorcrypto_mcu_get_certificate);

/// def sign(challenge: AnyBytes) -> bytes:
///     """
///     Sign challenge bytes with MCU device attestation key.
///     """
STATIC mp_obj_t mod_trezorcrypto_mcu_sign(mp_obj_t challenge) {
  mp_buffer_info_t challenge_buf = {0};
  mp_get_buffer_raise(challenge, &challenge_buf, MP_BUFFER_READ);

  vstr_t sig = {0};
  vstr_init_len(&sig, MCU_ATTESTATION_SIG_SIZE);
  if (mcu_attestation_sign((const uint8_t *)challenge_buf.buf,
                           challenge_buf.len, (uint8_t *)sig.buf) != sectrue) {
    vstr_clear(&sig);
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Signing failed."));
  }

  sig.len = MCU_ATTESTATION_SIG_SIZE;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_mcu_sign_obj,
                                 mod_trezorcrypto_mcu_sign);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_mcu_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mcu)},
    {MP_ROM_QSTR(MP_QSTR_get_certificate),
     MP_ROM_PTR(&mod_trezorcrypto_mcu_get_certificate_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_trezorcrypto_mcu_sign_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_mcu_globals,
                            mod_trezorcrypto_mcu_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_mcu_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_mcu_globals,
};

#endif  // USE_MCU_ATTESTATION
