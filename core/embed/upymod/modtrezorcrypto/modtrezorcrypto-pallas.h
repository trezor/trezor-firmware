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

#include "memzero.h"
#include "pallas.h"
#include "../trezorobj.h"

/// package: trezorcrypto.pallas

// Helper: read a buffer argument and require exactly `expected` bytes.
STATIC void pallas_get_fixed(mp_obj_t obj, mp_buffer_info_t *buf,
                             size_t expected, mp_rom_error_text_t what) {
  mp_get_buffer_raise(obj, buf, MP_BUFFER_READ);
  if (buf->len != expected) {
    mp_raise_ValueError(what);
  }
}

/// def hd_account(seed: AnyBytes, account: int) -> bytes:
///     """
///     Derive the DarkFi account spend key sk = HD_account(seed, account)
///     using DarkFi's own hierarchical-deterministic scheme (crypto/hd.rs):
///     the hardened child at `account` of the master node derived from `seed`.
///     `seed` is the raw BIP-39 seed (any length). Returns sk as 32
///     little-endian bytes. Matches darkfi_sdk ExtendedSecretKey::account, so
///     the same mnemonic restores identically in the drk wallet.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_hd_account(mp_obj_t seed_obj,
                                                   mp_obj_t account_obj) {
  mp_buffer_info_t seed = {0};
  mp_get_buffer_raise(seed_obj, &seed, MP_BUFFER_READ);
  uint32_t account = trezor_obj_get_uint(account_obj);
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_hd_account((const uint8_t *)seed.buf, seed.len, account,
                    (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_pallas_hd_account_obj,
                                 mod_trezorcrypto_pallas_hd_account);

/// def derive_ask(sk: AnyBytes) -> bytes:
///     """
///     Derive the spend-auth secret ask = ToScalar(Expand(sk, 0x06)).
///     Returns a 32-byte little-endian scalar. Device-only secret.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_derive_ask(mp_obj_t sk_obj) {
  mp_buffer_info_t sk = {0};
  pallas_get_fixed(sk_obj, &sk, 32, MP_ERROR_TEXT("Invalid length of sk"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_drk_derive_ask((const uint8_t *)sk.buf, (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_pallas_derive_ask_obj,
                                 mod_trezorcrypto_pallas_derive_ask);

/// def derive_nk(sk: AnyBytes) -> bytes:
///     """
///     Derive the nullifier key nk = ToBase(Expand(sk, 0x07)).
///     Returns a 32-byte little-endian base-field element. Part of the FVK.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_derive_nk(mp_obj_t sk_obj) {
  mp_buffer_info_t sk = {0};
  pallas_get_fixed(sk_obj, &sk, 32, MP_ERROR_TEXT("Invalid length of sk"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_drk_derive_nk((const uint8_t *)sk.buf, (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_pallas_derive_nk_obj,
                                 mod_trezorcrypto_pallas_derive_nk);

/// def spend_auth_pubkey(ask: AnyBytes) -> bytes:
///     """
///     Compute ak = ask * NullifierK, the spend-auth public key, as a 32-byte
///     compressed Pallas point (DarkFi GroupEncoding).
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_spend_auth_pubkey(mp_obj_t ask_obj) {
  mp_buffer_info_t ask = {0};
  pallas_get_fixed(ask_obj, &ask, 32, MP_ERROR_TEXT("Invalid length of ask"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_spend_auth_pubkey((const uint8_t *)ask.buf, (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_pallas_spend_auth_pubkey_obj,
                                 mod_trezorcrypto_pallas_spend_auth_pubkey);

/// def derive_ivk(sk: AnyBytes) -> bytes:
///     """
///     Derive ivk = poseidon([ak_x, ak_y, nk]) from the spend key, kept as a
///     base-field element (a stock SecretKey). Returns 32 little-endian bytes
///     (the incoming view key).
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_derive_ivk(mp_obj_t sk_obj) {
  mp_buffer_info_t sk = {0};
  pallas_get_fixed(sk_obj, &sk, 32, MP_ERROR_TEXT("Invalid length of sk"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_drk_derive_ivk_from_sk((const uint8_t *)sk.buf, (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_pallas_derive_ivk_obj,
                                 mod_trezorcrypto_pallas_derive_ivk);

/// def address_pubkey(ivk: AnyBytes) -> bytes:
///     """
///     Compute the transmission key pk_d = ivk * NullifierK, as a 32-byte
///     compressed Pallas point. `ivk` is a 32-byte little-endian scalar.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_address_pubkey(mp_obj_t ivk_obj) {
  mp_buffer_info_t ivk = {0};
  pallas_get_fixed(ivk_obj, &ivk, 32, MP_ERROR_TEXT("Invalid length of ivk"));
  pallas_point pk_d = {0};
  pallas_point_mul((const uint8_t *)ivk.buf, &pallas_nullifier_k, &pk_d);
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_point_to_bytes(&pk_d, (uint8_t *)out.buf);
  memzero(&pk_d, sizeof(pk_d));
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_pallas_address_pubkey_obj,
                                 mod_trezorcrypto_pallas_address_pubkey);

/// def nullifier(nk: AnyBytes, coin: AnyBytes) -> bytes:
///     """
///     Compute the nullifier nf = poseidon([nk, coin]). All values are 32-byte
///     little-endian base-field elements.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_nullifier(mp_obj_t nk_obj,
                                                  mp_obj_t coin_obj) {
  mp_buffer_info_t nk = {0}, coin = {0};
  pallas_get_fixed(nk_obj, &nk, 32, MP_ERROR_TEXT("Invalid length of nk"));
  pallas_get_fixed(coin_obj, &coin, 32, MP_ERROR_TEXT("Invalid length of coin"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_drk_nullifier((const uint8_t *)nk.buf, (const uint8_t *)coin.buf,
                       (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_pallas_nullifier_obj,
                                 mod_trezorcrypto_pallas_nullifier);

/// def poseidon_hash2(a: AnyBytes, b: AnyBytes) -> bytes:
///     """
///     Poseidon P128Pow5T3 hash of two field elements: poseidon([a, b]).
///     All values are 32-byte little-endian base-field elements.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_poseidon_hash2(mp_obj_t a_obj,
                                                       mp_obj_t b_obj) {
  mp_buffer_info_t a = {0}, b = {0};
  pallas_get_fixed(a_obj, &a, 32, MP_ERROR_TEXT("Invalid length of a"));
  pallas_get_fixed(b_obj, &b, 32, MP_ERROR_TEXT("Invalid length of b"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_poseidon_hash2((const uint8_t *)a.buf, (const uint8_t *)b.buf,
                        (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_pallas_poseidon_hash2_obj,
                                 mod_trezorcrypto_pallas_poseidon_hash2);

/// def poseidon_hash3(a: AnyBytes, b: AnyBytes, c: AnyBytes) -> bytes:
///     """
///     Poseidon P128Pow5T3 hash of three field elements: poseidon([a, b, c]).
///     All values are 32-byte little-endian base-field elements.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_poseidon_hash3(mp_obj_t a_obj,
                                                       mp_obj_t b_obj,
                                                       mp_obj_t c_obj) {
  mp_buffer_info_t a = {0}, b = {0}, c = {0};
  pallas_get_fixed(a_obj, &a, 32, MP_ERROR_TEXT("Invalid length of a"));
  pallas_get_fixed(b_obj, &b, 32, MP_ERROR_TEXT("Invalid length of b"));
  pallas_get_fixed(c_obj, &c, 32, MP_ERROR_TEXT("Invalid length of c"));
  vstr_t out = {0};
  vstr_init_len(&out, 32);
  pallas_poseidon_hash3((const uint8_t *)a.buf, (const uint8_t *)b.buf,
                        (const uint8_t *)c.buf, (uint8_t *)out.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_pallas_poseidon_hash3_obj,
                                 mod_trezorcrypto_pallas_poseidon_hash3);

/// def sign_spend_auth(
///     ask: AnyBytes,
///     alpha: AnyBytes,
///     message: AnyBytes,
/// ) -> tuple[bytes, bytes, bytes]:
///     """
///     Produce a randomized Schnorr spend-authorization signature.
///
///     Returns (commit, rk, response): commit and rk are 32-byte compressed
///     Pallas points, response is a 32-byte little-endian scalar. The signature
///     verifies against rk = (ask + alpha) * NullifierK by the stock DarkFi
///     Schnorr verifier.
///     """
STATIC mp_obj_t mod_trezorcrypto_pallas_sign_spend_auth(mp_obj_t ask_obj,
                                                        mp_obj_t alpha_obj,
                                                        mp_obj_t msg_obj) {
  mp_buffer_info_t ask = {0}, alpha = {0}, msg = {0};
  pallas_get_fixed(ask_obj, &ask, 32, MP_ERROR_TEXT("Invalid length of ask"));
  pallas_get_fixed(alpha_obj, &alpha, 32,
                   MP_ERROR_TEXT("Invalid length of alpha"));
  mp_get_buffer_raise(msg_obj, &msg, MP_BUFFER_READ);

  vstr_t commit = {0}, rk = {0}, response = {0};
  vstr_init_len(&commit, 32);
  vstr_init_len(&rk, 32);
  vstr_init_len(&response, 32);

  pallas_spend_auth_sign((const uint8_t *)ask.buf, (const uint8_t *)alpha.buf,
                         (const uint8_t *)msg.buf, msg.len,
                         (uint8_t *)commit.buf, (uint8_t *)rk.buf,
                         (uint8_t *)response.buf);

  mp_obj_t tuple[3] = {
      mp_obj_new_str_from_vstr(&mp_type_bytes, &commit),
      mp_obj_new_str_from_vstr(&mp_type_bytes, &rk),
      mp_obj_new_str_from_vstr(&mp_type_bytes, &response),
  };
  return mp_obj_new_tuple(3, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_pallas_sign_spend_auth_obj,
                                 mod_trezorcrypto_pallas_sign_spend_auth);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_pallas_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pallas)},
    {MP_ROM_QSTR(MP_QSTR_hd_account),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_hd_account_obj)},
    {MP_ROM_QSTR(MP_QSTR_derive_ask),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_derive_ask_obj)},
    {MP_ROM_QSTR(MP_QSTR_derive_nk),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_derive_nk_obj)},
    {MP_ROM_QSTR(MP_QSTR_spend_auth_pubkey),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_spend_auth_pubkey_obj)},
    {MP_ROM_QSTR(MP_QSTR_derive_ivk),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_derive_ivk_obj)},
    {MP_ROM_QSTR(MP_QSTR_address_pubkey),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_address_pubkey_obj)},
    {MP_ROM_QSTR(MP_QSTR_nullifier),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_nullifier_obj)},
    {MP_ROM_QSTR(MP_QSTR_poseidon_hash2),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_poseidon_hash2_obj)},
    {MP_ROM_QSTR(MP_QSTR_poseidon_hash3),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_poseidon_hash3_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign_spend_auth),
     MP_ROM_PTR(&mod_trezorcrypto_pallas_sign_spend_auth_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_pallas_globals,
                            mod_trezorcrypto_pallas_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_pallas_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_pallas_globals,
};
