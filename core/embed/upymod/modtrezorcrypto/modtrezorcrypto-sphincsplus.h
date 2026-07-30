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

#include "hkdf.h"
#include "memzero.h"
#include "sphincsplus_dispatch.h"

/*
 * SPHINCS+ key derivation and signing for the CKB post-quantum lock script.
 *
 * Supports all 12 SLH-DSA parameter sets via a runtime dispatch table.
 * Each variant is compiled with namespaced symbols (spx_{name}_*) and
 * selected at runtime by variant_id (48-59).
 *
 * Derivation flow (matching key-vault-wasm):
 *   1. Master seed (48/72/96 bytes) split into 3 equal parts
 *   2. Each part derived via HKDF-SHA256 with info path
 *   3. Concatenated → variant-specific keygen
 */

/// package: trezorcrypto.sphincsplus

/* Validate inputs and return the variant descriptor, filling `seed` and
 * `account_index`. Touches no secret material, so callers can allocate output
 * buffers (which may raise on OOM) before deriving any key bytes. Raises a
 * MicroPython exception on invalid input. */
STATIC const spx_variant_t *_sphincsplus_validate(
    mp_obj_t seed_obj, mp_obj_t index_obj, mp_obj_t variant_obj,
    mp_buffer_info_t *seed, int *account_index) {
  mp_get_buffer_raise(seed_obj, seed, MP_BUFFER_READ);
  *account_index = mp_obj_get_int(index_obj);
  int variant = mp_obj_get_int(variant_obj);

  if (*account_index < 0 || *account_index > 1000000) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid SPHINCS+ account index"));
  }

  const spx_variant_t *v = spx_get_variant(variant);
  if (v == NULL) {
    mp_raise_ValueError(MP_ERROR_TEXT("Unsupported SPHINCS+ variant"));
  }

  if (seed->len != (size_t)(3 * (int)v->spx_n)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid master seed length"));
  }
  return v;
}

/* Domain-separated HKDF derivation of the SPHINCS+ keypair seed into
 * derived_seed[3*n]. Must be called after the caller has allocated its output
 * buffers so an allocation failure cannot strand key material on the stack; the
 * caller is responsible for memzero(derived_seed) afterwards.
 *
 * The info string is part of the key-derivation consensus — keep it
 * byte-for-byte identical across firmware versions and host implementations.
 * All three parts share it, so equal parts derive equal values; the caller
 * must reject a seed whose parts repeat (see _split_extended_mnemonic_to_seed)
 * or SK_SEED would go on chain inside the published PUB_SEED. */
STATIC void _sphincsplus_derive(const spx_variant_t *v,
                                const mp_buffer_info_t *seed, int account_index,
                                uint8_t derived_seed[3 * SPX_MAX_N]) {
  int n = (int)v->spx_n;

  char info[64];
  int info_len = snprintf(info, sizeof(info),
                          "ckb/quantum-purse/sphincs-plus/%d", account_index);
  if (info_len < 0 || info_len >= (int)sizeof(info)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Account index too large"));
  }

  for (int i = 0; i < 3; i++) {
    hkdf_sha256(NULL, 0, (const uint8_t *)seed->buf + i * n, n,
                (const uint8_t *)info, info_len, derived_seed + i * n, n);
  }
}

/// def derive_public_key(
///     master_seed: AnyBytes, account_index: int, variant: int
/// ) -> bytes:
///     """
///     Derive SPHINCS+ public key from master seed and account index.
///     The secret key is computed in a stack-local buffer and zeroized
///     before this function returns — it is never exposed to Python.
///     Returns the public key bytes.
///     """
STATIC mp_obj_t mod_trezorcrypto_sphincsplus_derive_public_key(
    mp_obj_t seed_obj, mp_obj_t index_obj, mp_obj_t variant_obj) {
  mp_buffer_info_t seed = {0};
  int account_index = 0;
  const spx_variant_t *v = _sphincsplus_validate(seed_obj, index_obj,
                                                 variant_obj, &seed,
                                                 &account_index);

  /* Allocate the output before deriving any secret, so an OOM here cannot
   * strand key material on the stack. */
  vstr_t pk = {0};
  vstr_init_len(&pk, v->pk_bytes);

  uint8_t derived_seed[3 * SPX_MAX_N];
  _sphincsplus_derive(v, &seed, account_index, derived_seed);

  uint8_t sk_local[4 * SPX_MAX_N];
  int ret = v->seed_keypair((unsigned char *)pk.buf, sk_local, derived_seed);

  memzero(derived_seed, sizeof(derived_seed));
  memzero(sk_local, sizeof(sk_local));

  if (ret != 0) {
    vstr_clear(&pk);
    mp_raise_ValueError(MP_ERROR_TEXT("SPHINCS+ keygen failed"));
  }

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &pk);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(
    mod_trezorcrypto_sphincsplus_derive_public_key_obj,
    mod_trezorcrypto_sphincsplus_derive_public_key);

/// def derive_and_sign(
///     master_seed: AnyBytes, account_index: int, variant: int, message: AnyBytes
/// ) -> tuple[bytes, bytes]:
///     """
///     Derive a SPHINCS+ keypair, sign `message`, and return
///     (public_key, signature). The secret key is computed in a stack-local
///     buffer and zeroized before this function returns — it is never exposed
///     to Python. A sign-then-verify check is performed internally to guard
///     against fault-injection attacks; if verification fails, ValueError is
///     raised and no signature is returned.
///     """
STATIC mp_obj_t mod_trezorcrypto_sphincsplus_derive_and_sign(
    size_t n_args, const mp_obj_t *args) {
  (void)n_args;
  mp_buffer_info_t msg = {0};
  mp_get_buffer_raise(args[3], &msg, MP_BUFFER_READ);
  if (msg.len == 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Empty message"));
  }

  mp_buffer_info_t seed = {0};
  int account_index = 0;
  const spx_variant_t *v = _sphincsplus_validate(args[0], args[1], args[2],
                                                 &seed, &account_index);

  /* Allocate outputs before deriving any secret, so an OOM here cannot strand
   * key material on the stack. */
  vstr_t pk = {0};
  vstr_init_len(&pk, v->pk_bytes);
  vstr_t sig = {0};
  vstr_init_len(&sig, v->sig_bytes);

  uint8_t derived_seed[3 * SPX_MAX_N];
  _sphincsplus_derive(v, &seed, account_index, derived_seed);

  uint8_t sk_local[4 * SPX_MAX_N];

  int ret_kg = v->seed_keypair((unsigned char *)pk.buf, sk_local, derived_seed);
  memzero(derived_seed, sizeof(derived_seed));

  if (ret_kg != 0) {
    memzero(sk_local, sizeof(sk_local));
    vstr_clear(&pk);
    vstr_clear(&sig);
    mp_raise_ValueError(MP_ERROR_TEXT("SPHINCS+ keygen failed"));
  }

  size_t actual_sig_len = 0;
  int ret_sign = v->sign((uint8_t *)sig.buf, &actual_sig_len,
                         (const uint8_t *)msg.buf, msg.len, sk_local);
  memzero(sk_local, sizeof(sk_local));

  if (ret_sign != 0) {
    vstr_clear(&pk);
    vstr_clear(&sig);
    mp_raise_ValueError(MP_ERROR_TEXT("SPHINCS+ signing failed"));
  }

  sig.len = actual_sig_len;

  /* Sign-then-verify guards against fault-injection that could leak SK bits
   * via a faulty signature. Doing it in C keeps the verify on the same
   * trusted bytes that signing produced — Python cannot tamper with the
   * signature between sign and verify. */
  int ret_verify = v->verify((const uint8_t *)sig.buf, sig.len,
                             (const uint8_t *)msg.buf, msg.len,
                             (const uint8_t *)pk.buf);
  if (ret_verify != 0) {
    vstr_clear(&pk);
    vstr_clear(&sig);
    mp_raise_ValueError(
        MP_ERROR_TEXT("SPHINCS+ verify failed after sign (possible fault)"));
  }

  mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
  tuple->items[0] = mp_obj_new_str_from_vstr(&mp_type_bytes, &pk);
  tuple->items[1] = mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
  return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_sphincsplus_derive_and_sign_obj, 4, 4,
    mod_trezorcrypto_sphincsplus_derive_and_sign);

/// def verify(
///     public_key: AnyBytes, signature: AnyBytes, message: AnyBytes, variant: int
/// ) -> bool:
///     """
///     Verify a SPHINCS+ signature of `message` under `public_key`. `message`
///     must already carry whatever domain wrapping the signer applied.
///     """
STATIC mp_obj_t mod_trezorcrypto_sphincsplus_verify(size_t n_args,
                                                     const mp_obj_t *args) {
  (void)n_args;
  mp_buffer_info_t pk = {0}, sig = {0}, msg = {0};
  mp_get_buffer_raise(args[0], &pk, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &sig, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &msg, MP_BUFFER_READ);
  int variant = mp_obj_get_int(args[3]);

  const spx_variant_t *v = spx_get_variant(variant);
  if (v == NULL) {
    mp_raise_ValueError(MP_ERROR_TEXT("Unsupported SPHINCS+ variant"));
  }
  if (pk.len != v->pk_bytes) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid public key length"));
  }

  int ret = v->verify((const uint8_t *)sig.buf, sig.len, (const uint8_t *)msg.buf,
                      msg.len, (const uint8_t *)pk.buf);
  return mp_obj_new_bool(ret == 0);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_sphincsplus_verify_obj, 4, 4,
    mod_trezorcrypto_sphincsplus_verify);

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_sphincsplus_globals_table[] = {
        {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sphincsplus)},
        {MP_ROM_QSTR(MP_QSTR_derive_public_key),
         MP_ROM_PTR(&mod_trezorcrypto_sphincsplus_derive_public_key_obj)},
        {MP_ROM_QSTR(MP_QSTR_derive_and_sign),
         MP_ROM_PTR(&mod_trezorcrypto_sphincsplus_derive_and_sign_obj)},
        {MP_ROM_QSTR(MP_QSTR_verify),
         MP_ROM_PTR(&mod_trezorcrypto_sphincsplus_verify_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_sphincsplus_globals,
                            mod_trezorcrypto_sphincsplus_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_sphincsplus_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_sphincsplus_globals,
};
