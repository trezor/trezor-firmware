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

#include "common.h"
#include "py/gc.h"
#include "py/objstr.h"

#include "vendor/secp256k1-zkp/include/secp256k1.h"
#include "vendor/secp256k1-zkp/include/secp256k1_ecdh.h"
#include "vendor/secp256k1-zkp/include/secp256k1_preallocated.h"
#include "vendor/secp256k1-zkp/include/secp256k1_recovery.h"

// "maybe" = do not fail if allocation fails
// "with_finaliser" = pass true to gc_alloc
// combination of "malloc_maybe" and "malloc_with_finaliser" does not exist in
// malloc.c, so we need to define our own version here.
#define m_new_obj_var_maybe_with_finaliser(obj_type, var_type, var_num) \
  gc_alloc(sizeof(obj_type) + sizeof(var_type) * (var_num), true)

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

/// package: trezorcrypto.secp256k1_zkp

/// class Context:
///     """
///     Owns a secp256k1 context.
///     Can be allocated once and re-used between subsequent operations.
///     """
///
typedef struct _mp_obj_secp256k1_context_t {
  mp_obj_base_t base;
  secp256k1_context *secp256k1_ctx;
  size_t secp256k1_ctx_size;
  uint8_t secp256k1_ctx_buf[0];  // to be allocate via m_new_obj_var_maybe().
} mp_obj_secp256k1_context_t;

/// def __init__(self) -> None:
///     """
///     Allocate and initialize secp256k1_context.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context_make_new(
    const mp_obj_type_t *type, size_t n_args, size_t n_kw,
    const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 0, false);

  const size_t secp256k1_ctx_size = secp256k1_context_preallocated_size(
      SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);

  mp_obj_secp256k1_context_t *o = m_new_obj_var_maybe_with_finaliser(
      mp_obj_secp256k1_context_t, uint8_t, secp256k1_ctx_size);
  if (!o) {
    mp_raise_ValueError("secp256k1_zkp context is too large");
  }
  o->base.type = type;
  o->secp256k1_ctx_size = secp256k1_ctx_size;
  o->secp256k1_ctx = secp256k1_context_preallocated_create(
      o->secp256k1_ctx_buf, SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);

  uint8_t rand[32] = {0};
  random_buffer(rand, 32);
  int ret = secp256k1_context_randomize(o->secp256k1_ctx, rand);
  if (ret != 1) {
    mp_raise_msg(&mp_type_RuntimeError, "secp256k1_context_randomize failed");
  }

  return MP_OBJ_FROM_PTR(o);
}

/// def __del__(self) -> None:
///     """
///     Destructor.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context___del__(mp_obj_t self) {
  mp_obj_secp256k1_context_t *o = MP_OBJ_TO_PTR(self);
  secp256k1_context_preallocated_destroy(o->secp256k1_ctx);
  memzero(o->secp256k1_ctx_buf, o->secp256k1_ctx_size);
  return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_secp256k1_context___del___obj,
                                 mod_trezorcrypto_secp256k1_context___del__);

/// def size(self) -> int:
///     """
///     Return the size in bytes of the internal secp256k1_ctx_buf buffer.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context_size(mp_obj_t self) {
  mp_obj_secp256k1_context_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_int_from_uint(o->secp256k1_ctx_size);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_secp256k1_context_size_obj,
                                 mod_trezorcrypto_secp256k1_context_size);

static const secp256k1_context *mod_trezorcrypto_get_secp256k1_context(
    mp_obj_t self) {
  mp_obj_secp256k1_context_t *o = MP_OBJ_TO_PTR(self);
  return o->secp256k1_ctx;
}

/// def generate_secret(self) -> bytes:
///     """
///     Generate secret key.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_zkp_generate_secret(mp_obj_t self) {
  const secp256k1_context *ctx = mod_trezorcrypto_get_secp256k1_context(self);
  uint8_t out[32] = {0};
  for (;;) {
    random_buffer(out, 32);
    // check whether secret > 0 && secret < curve_order
    if (secp256k1_ec_seckey_verify(ctx, out) == 1) {
      break;
    }
  }
  return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_secp256k1_zkp_generate_secret_obj,
    mod_trezorcrypto_secp256k1_zkp_generate_secret);

/// def publickey(self, secret_key: bytes, compressed: bool = True) -> bytes:
///     """
///     Computes public key from secret key.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context_publickey(
    size_t n_args, const mp_obj_t *args) {
  const secp256k1_context *ctx =
      mod_trezorcrypto_get_secp256k1_context(args[0]);
  mp_buffer_info_t sk = {0};
  mp_get_buffer_raise(args[1], &sk, MP_BUFFER_READ);
  secp256k1_pubkey pk;
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (!secp256k1_ec_pubkey_create(ctx, &pk, (const unsigned char *)sk.buf)) {
    mp_raise_ValueError("Invalid secret key");
  }

  bool compressed = n_args < 3 || args[2] == mp_const_true;
  uint8_t out[65] = {0};
  size_t outlen = sizeof(out);
  secp256k1_ec_pubkey_serialize(
      ctx, out, &outlen, &pk,
      compressed ? SECP256K1_EC_COMPRESSED : SECP256K1_EC_UNCOMPRESSED);
  return mp_obj_new_bytes(out, outlen);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_secp256k1_context_publickey_obj, 2, 3,
    mod_trezorcrypto_secp256k1_context_publickey);

/// def sign(
///     self, secret_key: bytes, digest: bytes, compressed: bool = True
/// ) -> bytes:
///     """
///     Uses secret key to produce the signature of the digest.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context_sign(size_t n_args,
                                                        const mp_obj_t *args) {
  const secp256k1_context *ctx =
      mod_trezorcrypto_get_secp256k1_context(args[0]);
  mp_buffer_info_t sk = {0}, dig = {0};
  mp_get_buffer_raise(args[1], &sk, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &dig, MP_BUFFER_READ);
  bool compressed = n_args < 4 || args[3] == mp_const_true;
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (dig.len != 32) {
    mp_raise_ValueError("Invalid length of digest");
  }
  secp256k1_ecdsa_recoverable_signature sig;
  uint8_t out[65] = {0};
  int pby = 0;
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
    mod_trezorcrypto_secp256k1_context_sign_obj, 3, 4,
    mod_trezorcrypto_secp256k1_context_sign);

/// def verify(
///     self, public_key: bytes, signature: bytes, digest: bytes
/// ) -> bool:
///     """
///     Uses public key to verify the signature of the digest.
///     Returns True on success.
///     """
STATIC mp_obj_t
mod_trezorcrypto_secp256k1_context_verify(size_t n_args, const mp_obj_t *args) {
  const secp256k1_context *ctx =
      mod_trezorcrypto_get_secp256k1_context(args[0]);
  mp_buffer_info_t pk = {0}, sig = {0}, dig = {0};
  mp_get_buffer_raise(args[1], &pk, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &sig, MP_BUFFER_READ);
  mp_get_buffer_raise(args[3], &dig, MP_BUFFER_READ);
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
  bool ret = (1 == secp256k1_ecdsa_verify(ctx, &ec_sig,
                                          (const uint8_t *)dig.buf, &ec_pk));
  return mp_obj_new_bool(ret);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_secp256k1_context_verify_obj, 4, 4,
    mod_trezorcrypto_secp256k1_context_verify);

/// def verify_recover(self, signature: bytes, digest: bytes) -> bytes:
///     """
///     Uses signature of the digest to verify the digest and recover the public
///     key. Returns public key on success, None if the signature is invalid.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context_verify_recover(
    mp_obj_t self, mp_obj_t signature, mp_obj_t digest) {
  const secp256k1_context *ctx = mod_trezorcrypto_get_secp256k1_context(self);
  mp_buffer_info_t sig = {0}, dig = {0};
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
  uint8_t out[65] = {0};
  size_t pklen = sizeof(out);
  secp256k1_ec_pubkey_serialize(
      ctx, out, &pklen, &pk,
      compressed ? SECP256K1_EC_COMPRESSED : SECP256K1_EC_UNCOMPRESSED);
  return mp_obj_new_bytes(out, pklen);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(
    mod_trezorcrypto_secp256k1_context_verify_recover_obj,
    mod_trezorcrypto_secp256k1_context_verify_recover);

static int secp256k1_ecdh_hash_passthrough(uint8_t *output, const uint8_t *x,
                                           const uint8_t *y, void *data) {
  output[0] = 0x04;
  memcpy(&output[1], x, 32);
  memcpy(&output[33], y, 32);
  (void)data;
  return 1;
}

/// def multiply(self, secret_key: bytes, public_key: bytes) -> bytes:
///     """
///     Multiplies point defined by public_key with scalar defined by
///     secret_key. Useful for ECDH.
///     """
STATIC mp_obj_t mod_trezorcrypto_secp256k1_context_multiply(
    mp_obj_t self, mp_obj_t secret_key, mp_obj_t public_key) {
  const secp256k1_context *ctx = mod_trezorcrypto_get_secp256k1_context(self);
  mp_buffer_info_t sk = {0}, pk = {0};
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
  uint8_t out[65] = {0};
  if (!secp256k1_ecdh(ctx, out, &ec_pk, (const uint8_t *)sk.buf,
                      secp256k1_ecdh_hash_passthrough, NULL)) {
    mp_raise_ValueError("Multiply failed");
  }
  return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(
    mod_trezorcrypto_secp256k1_context_multiply_obj,
    mod_trezorcrypto_secp256k1_context_multiply);

//////////////////////////////////////////////////////////////////////////////

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_secp256k1_context_locals_dict_table[] = {
        {MP_ROM_QSTR(MP_QSTR___del__),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context___del___obj)},
        {MP_ROM_QSTR(MP_QSTR_size),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_size_obj)},
        {MP_ROM_QSTR(MP_QSTR_generate_secret),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_zkp_generate_secret_obj)},
        {MP_ROM_QSTR(MP_QSTR_publickey),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_publickey_obj)},
        {MP_ROM_QSTR(MP_QSTR_sign),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_sign_obj)},
        {MP_ROM_QSTR(MP_QSTR_verify),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_verify_obj)},
        {MP_ROM_QSTR(MP_QSTR_verify_recover),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_verify_recover_obj)},
        {MP_ROM_QSTR(MP_QSTR_multiply),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_multiply_obj)},
};

STATIC MP_DEFINE_CONST_DICT(
    mod_trezorcrypto_secp256k1_context_locals_dict,
    mod_trezorcrypto_secp256k1_context_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_secp256k1_context_type = {
    {&mp_type_type},
    .name = MP_QSTR_Context,
    .make_new = mod_trezorcrypto_secp256k1_context_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_secp256k1_context_locals_dict,
};

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_secp256k1_zkp_globals_table[] = {
        {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_secp256k1_zkp)},
        {MP_ROM_QSTR(MP_QSTR_Context),
         MP_ROM_PTR(&mod_trezorcrypto_secp256k1_context_type)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_secp256k1_zkp_globals,
                            mod_trezorcrypto_secp256k1_zkp_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_secp256k1_zkp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_secp256k1_zkp_globals,
};
