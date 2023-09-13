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

#if USE_OPTIGA

#include "py/objstr.h"

#include "optiga.h"
#include "optiga_commands.h"

/// package: trezorcrypto.optiga

#define MAX_DER_SIGNATURE_SIZE 72

/// class OptigaError(Exception):
///     """Error returned by the Optiga chip."""
MP_DEFINE_EXCEPTION(OptigaError, Exception)
/// class SigningInaccessible(OptigaError):
///     """The signing key is inaccessible.
///     Typically, this will happen after the bootloader has been unlocked.
///     """
MP_DEFINE_EXCEPTION(SigningInaccessible, OptigaError)

/// mock:global
/// def get_certificate(cert_index: int) -> bytes:
///     """
///     Return the certificate stored at the given index.
///     """
STATIC mp_obj_t mod_trezorcrypto_optiga_get_certificate(mp_obj_t cert_index) {
  mp_int_t idx = mp_obj_get_int(cert_index);
  if (idx < 0 || idx >= OPTIGA_CERT_COUNT) {
    mp_raise_ValueError("Invalid index.");
  }

  size_t cert_size = 0;
  if (!optiga_cert_size(idx, &cert_size)) {
    mp_raise_msg(&mp_type_OptigaError, "Failed to get certificate size.");
  }

  vstr_t cert = {0};
  vstr_init_len(&cert, cert_size);
  if (!optiga_read_cert(idx, (uint8_t *)cert.buf, cert.alloc, &cert_size)) {
    vstr_clear(&cert);
    mp_raise_msg(&mp_type_OptigaError, "Failed to read certificate.");
  }

  cert.len = cert_size;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &cert);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_optiga_get_certificate_obj,
                                 mod_trezorcrypto_optiga_get_certificate);

/// def sign(
///     key_index: int,
///     digest: bytes,
/// ) -> bytes:
///     """
///     Uses the private key at key_index to produce a DER-encoded signature of
///     the digest.
///     """
STATIC mp_obj_t mod_trezorcrypto_optiga_sign(mp_obj_t key_index,
                                             mp_obj_t digest) {
  mp_int_t idx = mp_obj_get_int(key_index);
  if (idx < 0 || idx >= OPTIGA_ECC_KEY_COUNT) {
    mp_raise_ValueError("Invalid index.");
  }

  mp_buffer_info_t dig = {0};
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (dig.len != 32) {
    mp_raise_ValueError("Invalid length of digest.");
  }

  vstr_t sig = {0};
  vstr_init_len(&sig, MAX_DER_SIGNATURE_SIZE);
  size_t sig_size = 0;
  int ret = optiga_sign(idx, (const uint8_t *)dig.buf, dig.len,
                        ((uint8_t *)sig.buf), sig.alloc, &sig_size);
  if (ret != 0) {
    vstr_clear(&sig);
    if (ret == OPTIGA_ERR_ACCESS_COND_NOT_SAT) {
      mp_raise_msg(&mp_type_SigningInaccessible, "Signing inaccessible.");
    } else {
      mp_raise_msg(&mp_type_OptigaError, "Signing failed.");
    }
  }

  sig.len = sig_size;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_optiga_sign_obj,
                                 mod_trezorcrypto_optiga_sign);

/// DEVICE_CERT_INDEX: int
/// DEVICE_ECC_KEY_INDEX: int

STATIC const mp_rom_map_elem_t mod_trezorcrypto_optiga_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_optiga)},
    {MP_ROM_QSTR(MP_QSTR_get_certificate),
     MP_ROM_PTR(&mod_trezorcrypto_optiga_get_certificate_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_trezorcrypto_optiga_sign_obj)},
    {MP_ROM_QSTR(MP_QSTR_DEVICE_CERT_INDEX),
     MP_ROM_INT(OPTIGA_DEVICE_CERT_INDEX)},
    {MP_ROM_QSTR(MP_QSTR_DEVICE_ECC_KEY_INDEX),
     MP_ROM_INT(OPTIGA_DEVICE_ECC_KEY_INDEX)},
    {MP_ROM_QSTR(MP_QSTR_OptigaError), MP_ROM_PTR(&mp_type_OptigaError)},
    {MP_ROM_QSTR(MP_QSTR_SigningInaccessible),
     MP_ROM_PTR(&mp_type_SigningInaccessible)}};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_optiga_globals,
                            mod_trezorcrypto_optiga_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_optiga_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_optiga_globals,
};

#endif
