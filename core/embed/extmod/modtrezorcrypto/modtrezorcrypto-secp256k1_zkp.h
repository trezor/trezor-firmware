/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "common.h"
#include "py/objstr.h"

#include "vendor/secp256k1-zkp/include/secp256k1.h"
#include "vendor/secp256k1-zkp/include/secp256k1_ecdh.h"
#include "vendor/secp256k1-zkp/include/secp256k1_preallocated.h"
#include "vendor/secp256k1-zkp/include/secp256k1_recovery.h"

// The minimum buffer size can vary in future secp256k1-zkp revisions.
// It can always be determined by a call to
// secp256k1_context_preallocated_size(...) as below.
STATIC uint8_t g_buffer[(1UL << (ECMULT_WINDOW_SIZE + 4)) + 208] = {0};

void secp256k1_default_illegal_callback_fn(const char *str, void *data) {
  (void)data;
  mp_raise_ValueError(str);
  return;
}

void secp256k1_default_error_callback_fn(const char *str, void *data) {
  (void)data;
  __fatal_error(NULL, str, __FILE__, __LINE__, __func__);
  return;
}

STATIC const secp256k1_context *mod_trezorcrypto_secp256k1_context(void) {
  static secp256k1_context *ctx;
  if (ctx == NULL) {
    size_t sz = secp256k1_context_preallocated_size(SECP256K1_CONTEXT_SIGN |
                                                    SECP256K1_CONTEXT_VERIFY);
    if (sz > sizeof g_buffer) {
      mp_raise_ValueError("secp256k1 context is too large");
    }
    void *buf = (void *)g_buffer;
    ctx = secp256k1_context_preallocated_create(
        buf, SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);

    uint8_t rand[32];
    random_buffer(rand, 32);
    int ret = secp256k1_context_randomize(ctx, rand);
    if (ret != 1) {
      mp_raise_msg(&mp_type_RuntimeError, "secp256k1_context_randomize failed");
    }
  }
  return ctx;
}


/// package: trezorcrypto.secp256k1_zkp

/// def generate_secret() -> bytes:
///     """
///     Generate secret key.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_generate_secret() {
  uint8_t out[32];
  for (;;) {
    random_buffer(out, 32);
    // check whether secret > 0 && secret < curve_order
    if (0 == memcmp(out,
                    "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    "\x00\x00\x00\x00\x00\x00",
                    32))
      continue;
    if (0 <= memcmp(out,
                    "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
                    "\xFF\xFF\xFE\xBA\xAE\xDC\xE6\xAF\x48\xA0\x3B\xBF\xD2"
                    "\x5E\x8C\xD0\x36\x41\x41",
                    32))
      continue;
    break;
  }
  return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(
    mod_trezorcrypto_secp256k1_zkp_generate_secret_obj,
    mod_trezorcrypto_secp256k1_zkp_generate_secret);

/// def publickey(secret_key: bytes, compressed: bool = True) -> bytes:
///     """
///     Computes public key from secret key.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_publickey(size_t n_args,
                                                         const mp_obj_t *args) {
  const secp256k1_context *ctx = mod_trezorcrypto_secp256k1_context();
  mp_buffer_info_t sk;
  mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
  secp256k1_pubkey pk;
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (!secp256k1_ec_pubkey_create(ctx, &pk, (const unsigned char *)sk.buf)) {
    mp_raise_ValueError("Invalid secret key");
  }

  bool compressed = n_args < 2 || args[1] == mp_const_true;
  uint8_t out[65];
  size_t outlen = sizeof(out);
  secp256k1_ec_pubkey_serialize(
      ctx, out, &outlen, &pk,
      compressed ? SECP256K1_EC_COMPRESSED : SECP256K1_EC_UNCOMPRESSED);
  return mp_obj_new_bytes(out, outlen);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_secp256k1_zkp_publickey_obj, 1, 2,
    mod_trezorcrypto_secp256k1_zkp_publickey);

/// def sign(
///     secret_key: bytes, digest: bytes, compressed: bool = True
/// ) -> bytes:
///     """
///     Uses secret key to produce the signature of the digest.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_sign(size_t n_args,
                                                    const mp_obj_t *args) {
  const secp256k1_context *ctx = mod_trezorcrypto_secp256k1_context();
  mp_buffer_info_t sk, dig;
  mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &dig, MP_BUFFER_READ);
  bool compressed = n_args < 3 || args[2] == mp_const_true;
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (dig.len != 32) {
    mp_raise_ValueError("Invalid length of digest");
  }
  secp256k1_ecdsa_recoverable_signature sig;
  uint8_t out[65];
  int pby;
  if (!secp256k1_ecdsa_sign_recoverable(ctx, &sig, (const uint8_t *)dig.buf,
                                        (const uint8_t *)sk.buf, NULL, NULL)) {
    mp_raise_ValueError("Signing failed");
  }
  secp256k1_ecdsa_recoverable_signature_serialize_compact(ctx, &out[1], &pby,
                                                          &sig);
  out[0] = 27 + pby + compressed * 4;
  return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_secp256k1_zkp_sign_obj, 2, 3,
    mod_trezorcrypto_secp256k1_zkp_sign);

/// def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
///     """
///     Uses public key to verify the signature of the digest.
///     Returns True on success.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_verify(mp_obj_t public_key,
                                                      mp_obj_t signature,
                                                      mp_obj_t digest) {
  const secp256k1_context *ctx = mod_trezorcrypto_secp256k1_context();
  mp_buffer_info_t pk, sig, dig;
  mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
  mp_get_buffer_raise(signature, &sig, MP_BUFFER_READ);
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (pk.len != 33 && pk.len != 65) {
    return mp_const_false;
  }
  if (sig.len != 64 && sig.len != 65) {
    return mp_const_false;
  }
  int offset = sig.len - 64;
  if (dig.len != 32) {
    return mp_const_false;
  }
  secp256k1_ecdsa_signature ec_sig;
  if (!secp256k1_ecdsa_signature_parse_compact(
          ctx, &ec_sig, (const uint8_t *)sig.buf + offset)) {
    return mp_const_false;
  }
  secp256k1_pubkey ec_pk;
  if (!secp256k1_ec_pubkey_parse(ctx, &ec_pk, (const uint8_t *)pk.buf,
                                 pk.len)) {
    return mp_const_false;
  }
  return mp_obj_new_bool(1 == secp256k1_ecdsa_verify(ctx, &ec_sig,
                                                     (const uint8_t *)dig.buf,
                                                     &ec_pk));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_secp256k1_zkp_verify_obj,
                                 mod_trezorcrypto_secp256k1_zkp_verify);

/// def verify_recover(signature: bytes, digest: bytes) -> bytes:
///     """
///     Uses signature of the digest to verify the digest and recover the public
///     key. Returns public key on success, None if the signature is invalid.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_verify_recover(
    mp_obj_t signature, mp_obj_t digest) {
  const secp256k1_context *ctx = mod_trezorcrypto_secp256k1_context();
  mp_buffer_info_t sig, dig;
  mp_get_buffer_raise(signature, &sig, MP_BUFFER_READ);
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (sig.len != 65) {
    return mp_const_none;
  }
  if (dig.len != 32) {
    return mp_const_none;
  }
  int recid = ((const uint8_t *)sig.buf)[0] - 27;
  if (recid >= 8) {
    return mp_const_none;
  }
  bool compressed = (recid >= 4);
  recid &= 3;

  secp256k1_ecdsa_recoverable_signature ec_sig;
  if (!secp256k1_ecdsa_recoverable_signature_parse_compact(
          ctx, &ec_sig, (const uint8_t *)sig.buf + 1, recid)) {
    return mp_const_none;
  }
  secp256k1_pubkey pk;
  if (!secp256k1_ecdsa_recover(ctx, &pk, &ec_sig, (const uint8_t *)dig.buf)) {
    return mp_const_none;
  }
  uint8_t out[65];
  size_t pklen = sizeof(out);
  secp256k1_ec_pubkey_serialize(
      ctx, out, &pklen, &pk,
      compressed ? SECP256K1_EC_COMPRESSED : SECP256K1_EC_UNCOMPRESSED);
  return mp_obj_new_bytes(out, pklen);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(
    mod_trezorcrypto_secp256k1_zkp_verify_recover_obj,
    mod_trezorcrypto_secp256k1_zkp_verify_recover);

static int secp256k1_ecdh_hash_passthrough(uint8_t *output, const uint8_t *x,
                                           const uint8_t *y, void *data) {
  output[0] = 0x04;
  memcpy(&output[1], x, 32);
  memcpy(&output[33], y, 32);
  (void)data;
  return 1;
}

/// def multiply(secret_key: bytes, public_key: bytes) -> bytes:
///     """
///     Multiplies point defined by public_key with scalar defined by
///     secret_key. Useful for ECDH.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_multiply(mp_obj_t secret_key,
                                                        mp_obj_t public_key) {
  const secp256k1_context *ctx = mod_trezorcrypto_secp256k1_context();
  mp_buffer_info_t sk, pk;
  mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
  mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (pk.len != 33 && pk.len != 65) {
    mp_raise_ValueError("Invalid length of public key");
  }
  secp256k1_pubkey ec_pk;
  if (!secp256k1_ec_pubkey_parse(ctx, &ec_pk, (const uint8_t *)pk.buf,
                                 pk.len)) {
    mp_raise_ValueError("Invalid public key");
  }
  uint8_t out[65];
  if (!secp256k1_ecdh(ctx, out, &ec_pk, (const uint8_t *)sk.buf,
                      secp256k1_ecdh_hash_passthrough, NULL)) {
    mp_raise_ValueError("Multiply failed");
  }
  return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_secp256k1_zkp_multiply_obj,
                                 mod_trezorcrypto_secp256k1_zkp_multiply);

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_secp256k1_zkp_globals_table[] = {
        {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_secp256k1_zkp)},
        {MP_ROM_QSTR(MP_QSTR_generate_secret),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_generate_secret_obj)},
        {MP_ROM_QSTR(MP_QSTR_publickey),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_publickey_obj)},
        {MP_ROM_QSTR(MP_QSTR_sign),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_sign_obj)},
        {MP_ROM_QSTR(MP_QSTR_verify),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_verify_obj)},
        {MP_ROM_QSTR(MP_QSTR_verify_recover),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_verify_recover_obj)},
        {MP_ROM_QSTR(MP_QSTR_multiply),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_multiply_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_secp256k1_zkp_globals,
                            mod_trezorcrypto_secp256k1_zkp_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_secp256k1_zkp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_secp256k1_zkp_globals,
};
