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

#include <trezor_rtl.h>

#include "py/runtime.h"

#if MICROPY_PY_TREZORCRYPTO

static mp_obj_t ui_wait_callback = mp_const_none;

static void wrapped_ui_wait_callback(uint32_t current, uint32_t total) {
  if (mp_obj_is_callable(ui_wait_callback)) {
    mp_call_function_2_protected(ui_wait_callback, mp_obj_new_int(current),
                                 mp_obj_new_int(total));
  }
}

extern const mp_obj_type_t mp_type_AuthenticationError;

#include "modtrezorcrypto-aes.h"
#ifdef USE_AES_GCM
#include "modtrezorcrypto-aesgcm.h"
#endif
#include "modtrezorcrypto-bech32.h"
#include "modtrezorcrypto-bip32.h"
/// package: trezorcrypto.__init__
#include "modtrezorcrypto-secbytes.h"
#ifdef USE_SECP256K1_ZKP
#include "modtrezorcrypto-bip340.h"
#endif
#include "modtrezorcrypto-bip39.h"
#include "modtrezorcrypto-blake256.h"
#include "modtrezorcrypto-blake2b.h"
#include "modtrezorcrypto-blake2s.h"
#include "modtrezorcrypto-chacha20poly1305.h"
#include "modtrezorcrypto-crc.h"
#include "modtrezorcrypto-curve25519.h"
#include "modtrezorcrypto-ed25519.h"
#if USE_THP
#include "modtrezorcrypto-elligator2.h"
#endif
#include "modtrezorcrypto-groestl.h"
#include "modtrezorcrypto-hmac.h"
#include "modtrezorcrypto-nist256p1.h"
#include "modtrezorcrypto-pbkdf2.h"
#include "modtrezorcrypto-random.h"
#include "modtrezorcrypto-ripemd160.h"
#include "modtrezorcrypto-secp256k1.h"
#include "modtrezorcrypto-secret-lifecycle.h"
#include "modtrezorcrypto-sha256.h"
#include "modtrezorcrypto-sha3-256.h"
#include "modtrezorcrypto-sha3-512.h"
#include "modtrezorcrypto-sha512.h"
#include "modtrezorcrypto-shamir.h"
#include "modtrezorcrypto-slip39.h"
#ifdef USE_OPTIGA
#include "modtrezorcrypto-optiga.h"
#endif
#ifdef USE_TROPIC
#include "modtrezorcrypto-tropic.h"
#endif
#ifdef USE_MCU_ATTESTATION
#include "modtrezorcrypto-mcu.h"
#endif
#if !BITCOIN_ONLY
#include "modtrezorcrypto-cardano.h"
#include "modtrezorcrypto-monero.h"
#include "modtrezorcrypto-nem.h"
#endif

/// package: trezorcrypto.__init__
/// def retain_secret(value: Any, owner: SecretOwner | None = None) -> None:
///     """Explicitly transfer a node or snapshot from this request to its
///     session, optionally requiring that exact cache owner."""
static mp_obj_t retain_secret(size_t n_args, const mp_obj_t *args) {
  mp_obj_t obj = args[0];
  bool check_owner = n_args > 1 && args[1] != mp_const_none;
  uint32_t expected = check_owner ? owner_object(args[1])->id : 0;
  vault_blob_t compact;
  vault_blob_t *h;
  secret_kind_t kind;
  if (mp_obj_is_type(obj, &mod_trezorcrypto_secbytes_type)) {
    compact = secbytes_blob(MP_OBJ_TO_PTR(obj));
    h = &compact;
    kind = SECRET_BYTES;
  } else if (mp_obj_is_type(obj, &mod_trezorcrypto_HDNode_type)) {
    compact = hdnode_blob(hdnode_object(obj));
    h = &compact;
    kind = SECRET_NODE;
  } else {
    mp_raise_TypeError(MP_ERROR_TEXT("Expected secret value"));
  }
  if (!secret_retain(h, secret_owner, kind))
    mp_raise_ValueError(MP_ERROR_TEXT("Cannot retain secret"));
  uint32_t actual = 0;
  for (size_t i = 0; i < 4; i++) actual |= (uint32_t)h->bytes[i] << (8 * i);
  if (check_owner && actual != expected) {
    memzero(&compact, sizeof(compact));
    mp_raise_ValueError(MP_ERROR_TEXT("Secret belongs to another cache"));
  }
  if (kind == SECRET_BYTES) secbytes_set_blob(MP_OBJ_TO_PTR(obj), h);
  if (kind == SECRET_NODE) hdnode_set_blob(hdnode_object(obj), h);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(retain_secret_obj, 1, 2,
                                           retain_secret);

MP_DEFINE_EXCEPTION(AuthenticationError, Exception)

/// package: trezorcrypto.__init__
/// def vault_chacha(
///     key: secbytes, nonce: AnyBytes, data: AnyBytes,
///     aad: AnyBytes = b"", tag: AnyBytes | None = None,
///     decrypt: bool = False,
/// ) -> tuple[bytes, bytes]:
///     """Encrypt/decrypt public credential data with an opaque key.
///     With decrypt=True and tag=None the result is unauthenticated metadata;
///     callers must authenticate before using it as a credential."""
static mp_obj_t vault_chacha(size_t n_args, const mp_obj_t *args) {
  if (!mp_obj_is_type(args[0], &mod_trezorcrypto_secbytes_type))
    mp_raise_TypeError(MP_ERROR_TEXT("Expected opaque key"));
  mp_buffer_info_t nonce = {0}, data = {0}, aad = {0}, tag = {0};
  mp_get_buffer_raise(args[1], &nonce, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &data, MP_BUFFER_READ);
  if (n_args > 3) mp_get_buffer_raise(args[3], &aad, MP_BUFFER_READ);
  if (n_args > 4 && args[4] != mp_const_none)
    mp_get_buffer_raise(args[4], &tag, MP_BUFFER_READ);
  bool decrypt = n_args > 5 && mp_obj_is_true(args[5]);
  if (nonce.len != 12 || aad.len > 32 ||
      data.len > VAULT_ED25519_MAX_MESSAGE - 32 || (tag.len && tag.len != 16))
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid credential data length"));
  vault_blob_t key = secbytes_blob(MP_OBJ_TO_PTR(args[0]));
  vstr_t output = {0};
  vstr_init_len(&output, data.len);
  vault_response_t out = {0};
  if (decrypt && tag.len && data.len && data.len <= VAULT_DATA_SIZE) {
    /* One kernel call authenticates, then decrypts. */
    vstr_t sealed = {0};
    vstr_init_len(&sealed, aad.len + data.len + tag.len);
    if (aad.len) memcpy(sealed.buf, aad.buf, aad.len);
    memcpy(sealed.buf + aad.len, data.buf, data.len);
    memcpy(sealed.buf + aad.len + data.len, tag.buf, tag.len);
    vault_message_request_t r = {.abi = VAULT_ABI,
                                 .op = VAULT_CHACHA_OPEN,
                                 .owner = secret_owner,
                                 .blob = key,
                                 .arg = aad.len};
    memcpy(r.extension.bytes, nonce.buf, 12);
    bool ok =
        vault_call_message(&r, (const uint8_t *)sealed.buf, sealed.len, &out);
    vstr_clear(&sealed);
    if (!ok) {
      vstr_clear(&output);
      mp_raise_msg(&mp_type_AuthenticationError,
                   MP_ERROR_TEXT("Invalid credential tag"));
    }
    memcpy(output.buf, out.data, data.len);
    memzero(&out, sizeof(out));
    mp_obj_t result[2] = {mp_obj_new_bytes_from_vstr(&output),
                          mp_obj_new_bytes(tag.buf, 16)};
    return mp_obj_new_tuple(2, result);
  }
  for (size_t offset = 0; offset < data.len; offset += VAULT_DATA_SIZE) {
    size_t n = MIN((size_t)VAULT_DATA_SIZE, data.len - offset);
    vault_request_t r = {.op = VAULT_CHACHA_BLOCK,
                         .blob = key,
                         .arg = decrypt,
                         .child_num = offset,
                         .length = n};
    memcpy(r.curve, nonce.buf, 12);
    memcpy(r.data, (const uint8_t *)data.buf + offset, n);
    if (!secret_rpc(&r, &out)) {
      vstr_clear(&output);
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid credential key"));
    }
    memcpy(output.buf + offset, out.data, n);
  }
  /* AAD and ciphertext are public and may remain in coreapp. The kernel
   * snapshots them before computing the authenticator. */
  vstr_t authenticated = {0};
  vstr_init_len(&authenticated, aad.len + data.len);
  if (aad.len) memcpy(authenticated.buf, aad.buf, aad.len);
  if (data.len)
    memcpy(authenticated.buf + aad.len, decrypt ? data.buf : output.buf,
           data.len);
  vault_message_request_t r = {.abi = VAULT_ABI,
                               .op = VAULT_CHACHA_TAG,
                               .owner = secret_owner,
                               .blob = key,
                               .arg = aad.len};
  memcpy(r.extension.bytes, nonce.buf, 12);
  bool ok = vault_call_message(&r, (const uint8_t *)authenticated.buf,
                               authenticated.len, &out);
  vstr_clear(&authenticated);
  if (!ok || (decrypt && tag.len && !consteq(tag.buf, out.signature, 16))) {
    vstr_clear(&output);
    mp_raise_msg(&mp_type_AuthenticationError,
                 MP_ERROR_TEXT("Invalid credential tag"));
  }
  mp_obj_t result[2] = {mp_obj_new_bytes_from_vstr(&output),
                        mp_obj_new_bytes(out.signature, 16)};
  memzero(&out, sizeof(out));
  return mp_obj_new_tuple(2, result);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vault_chacha_obj, 3, 6,
                                           vault_chacha);

/// package: trezorcrypto.__init__
/// from trezorcrypto.bip32 import HDNode
/// def cipher_key_value(
///     node: HDNode, label: AnyBytes, value: AnyBytes, encrypt: bool,
///     ask_on_encrypt: bool, ask_on_decrypt: bool, iv: AnyBytes = b"",
/// ) -> bytes:
///     """SLIP-0011 key derivation and AES-CBC with a protected HDNode."""
static mp_obj_t cipher_key_value(size_t n_args, const mp_obj_t *args) {
  mp_buffer_info_t label = {0}, input = {0}, supplied_iv = {0};
  mp_get_buffer_raise(args[1], &label, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &input, MP_BUFFER_READ);
  if (n_args > 6) mp_get_buffer_raise(args[6], &supplied_iv, MP_BUFFER_READ);
  if (label.len > VAULT_ED25519_MAX_MESSAGE - 4 || input.len % 16)
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid key-value length"));
  bool encrypt = mp_obj_is_true(args[3]);
  vstr_t derivation = {0};
  vstr_init_len(&derivation, label.len + 4);
  if (label.len) memcpy(derivation.buf, label.buf, label.len);
  memcpy(derivation.buf + label.len, mp_obj_is_true(args[4]) ? "E1" : "E0", 2);
  memcpy(derivation.buf + label.len + 2, mp_obj_is_true(args[5]) ? "D1" : "D0",
         2);
  vault_message_request_t request = {
      .abi = VAULT_ABI,
      .op = VAULT_KEYVALUE_DERIVE,
      .owner = secret_owner,
      .blob = hdnode_blob(hdnode_object(args[0]))};
  vstr_t output = {0};
  vstr_init_len(&output, input.len);
  vault_response_t out = {0};
  bool ok = vault_call_message(&request, (const uint8_t *)derivation.buf,
                               derivation.len, &out);
  vstr_clear(&derivation);
  if (!ok) {
    vstr_clear(&output);
    mp_raise_ValueError(MP_ERROR_TEXT("Key-value derivation failed"));
  }
  vault_blob_t key = out.blob;
  uint8_t iv[16] = {0};
  memcpy(iv, supplied_iv.len == 16 ? supplied_iv.buf : out.chain_code, 16);
  for (size_t offset = 0; offset < input.len; offset += VAULT_DATA_SIZE) {
    size_t n = MIN((size_t)VAULT_DATA_SIZE, input.len - offset);
    vault_request_t r = {
        .op = VAULT_AES_CBC, .arg = encrypt, .blob = key, .length = n};
    memcpy(r.curve, iv, 16);
    memcpy(r.data, (const uint8_t *)input.buf + offset, n);
    if (!encrypt) memcpy(iv, r.data + n - 16, 16);
    if (!secret_rpc(&r, &out)) {
      vstr_clear(&output);
      mp_raise_ValueError(MP_ERROR_TEXT("Key-value cipher failed"));
    }
    if (encrypt) memcpy(iv, out.data + n - 16, 16);
    memcpy(output.buf + offset, out.data, n);
  }
  memzero(&out, sizeof(out));
  memzero(&key, sizeof(key));
  return mp_obj_new_bytes_from_vstr(&output);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(cipher_key_value_obj, 6, 7,
                                           cipher_key_value);

static const mp_rom_map_elem_t mp_module_trezorcrypto_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorcrypto)},
    {MP_ROM_QSTR(MP_QSTR__secret_task_rebind),
     MP_ROM_PTR(&secret_task_rebind_obj)},
    {MP_ROM_QSTR(MP_QSTR__secret_task_register),
     MP_ROM_PTR(&secret_task_register_obj)},
    {MP_ROM_QSTR(MP_QSTR__secret_task_enter),
     MP_ROM_PTR(&secret_task_enter_obj)},
    {MP_ROM_QSTR(MP_QSTR__secret_task_finish),
     MP_ROM_PTR(&secret_task_finish_obj)},
    {MP_ROM_QSTR(MP_QSTR__secret_tasks_clear),
     MP_ROM_PTR(&secret_tasks_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_begin_preauthorized_request),
     MP_ROM_PTR(&begin_preauthorized_request_obj)},
    {MP_ROM_QSTR(MP_QSTR_begin_confirmed_request),
     MP_ROM_PTR(&begin_confirmed_request_obj)},
    {MP_ROM_QSTR(MP_QSTR_authorize_locked_session),
     MP_ROM_PTR(&authorize_locked_session_obj)},
    {MP_ROM_QSTR(MP_QSTR_retain_secret), MP_ROM_PTR(&retain_secret_obj)},
    {MP_ROM_QSTR(MP_QSTR_SecretOwner),
     MP_ROM_PTR(&mod_trezorcrypto_SecretOwner_type)},
    {MP_ROM_QSTR(MP_QSTR__secret_owner_activate),
     MP_ROM_PTR(&owner_activate_obj)},
    {MP_ROM_QSTR(MP_QSTR_cipher_key_value), MP_ROM_PTR(&cipher_key_value_obj)},
    {MP_ROM_QSTR(MP_QSTR_vault_chacha), MP_ROM_PTR(&vault_chacha_obj)},
    {MP_ROM_QSTR(MP_QSTR_secbytes),
     MP_ROM_PTR(&mod_trezorcrypto_secbytes_type)},
    {MP_ROM_QSTR(MP_QSTR_revoke_secrets), MP_ROM_PTR(&revoke_secrets_obj)},
    {MP_ROM_QSTR(MP_QSTR_slip21_derive), MP_ROM_PTR(&slip21_derive_obj)},
    {MP_ROM_QSTR(MP_QSTR_slip21_export), MP_ROM_PTR(&slip21_export_obj)},
    {MP_ROM_QSTR(MP_QSTR_AuthenticationError),
     MP_ROM_PTR(&mp_type_AuthenticationError)},
    {MP_ROM_QSTR(MP_QSTR_aes), MP_ROM_PTR(&mod_trezorcrypto_AES_type)},
#if USE_AES_GCM
    {MP_ROM_QSTR(MP_QSTR_aesgcm_decrypt),
     MP_ROM_PTR(&mod_trezorcrypto_AesGcmDecrypt_type)},
    {MP_ROM_QSTR(MP_QSTR_aesgcm_encrypt),
     MP_ROM_PTR(&mod_trezorcrypto_AesGcmEncrypt_type)},
#endif
    {MP_ROM_QSTR(MP_QSTR_bech32), MP_ROM_PTR(&mod_trezorcrypto_bech32_module)},
    {MP_ROM_QSTR(MP_QSTR_bip32), MP_ROM_PTR(&mod_trezorcrypto_bip32_module)},
    {MP_ROM_QSTR(MP_QSTR_bip39), MP_ROM_PTR(&mod_trezorcrypto_bip39_module)},
    {MP_ROM_QSTR(MP_QSTR_blake256),
     MP_ROM_PTR(&mod_trezorcrypto_Blake256_type)},
    {MP_ROM_QSTR(MP_QSTR_blake2b), MP_ROM_PTR(&mod_trezorcrypto_Blake2b_type)},
    {MP_ROM_QSTR(MP_QSTR_blake2s), MP_ROM_PTR(&mod_trezorcrypto_Blake2s_type)},
#if !BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_cardano),
     MP_ROM_PTR(&mod_trezorcrypto_cardano_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_chacha20poly1305_decrypt),
     MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305Decrypt_type)},
    {MP_ROM_QSTR(MP_QSTR_chacha20poly1305_encrypt),
     MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305Encrypt_type)},
    {MP_ROM_QSTR(MP_QSTR_crc), MP_ROM_PTR(&mod_trezorcrypto_crc_module)},
    {MP_ROM_QSTR(MP_QSTR_curve25519),
     MP_ROM_PTR(&mod_trezorcrypto_curve25519_module)},
    {MP_ROM_QSTR(MP_QSTR_ed25519),
     MP_ROM_PTR(&mod_trezorcrypto_ed25519_module)},
#if USE_THP
    {MP_ROM_QSTR(MP_QSTR_elligator2),
     MP_ROM_PTR(&mod_trezorcrypto_elligator2_module)},
#endif
#if !BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_monero), MP_ROM_PTR(&mod_trezorcrypto_monero_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_nist256p1),
     MP_ROM_PTR(&mod_trezorcrypto_nist256p1_module)},
    {MP_ROM_QSTR(MP_QSTR_groestl512),
     MP_ROM_PTR(&mod_trezorcrypto_Groestl512_type)},
    {MP_ROM_QSTR(MP_QSTR_hmac), MP_ROM_PTR(&mod_trezorcrypto_Hmac_type)},
#if !BITCOIN_ONLY
    {MP_ROM_QSTR(MP_QSTR_nem), MP_ROM_PTR(&mod_trezorcrypto_nem_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_pbkdf2), MP_ROM_PTR(&mod_trezorcrypto_Pbkdf2_type)},
    {MP_ROM_QSTR(MP_QSTR_random), MP_ROM_PTR(&mod_trezorcrypto_random_module)},
    {MP_ROM_QSTR(MP_QSTR_ripemd160),
     MP_ROM_PTR(&mod_trezorcrypto_Ripemd160_type)},
    {MP_ROM_QSTR(MP_QSTR_secp256k1),
     MP_ROM_PTR(&mod_trezorcrypto_secp256k1_module)},
#if USE_SECP256K1_ZKP
    {MP_ROM_QSTR(MP_QSTR_bip340), MP_ROM_PTR(&mod_trezorcrypto_bip340_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_sha256), MP_ROM_PTR(&mod_trezorcrypto_Sha256_type)},
    {MP_ROM_QSTR(MP_QSTR_sha512), MP_ROM_PTR(&mod_trezorcrypto_Sha512_type)},
    {MP_ROM_QSTR(MP_QSTR_sha3_256),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_256_type)},
    {MP_ROM_QSTR(MP_QSTR_sha3_512),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_512_type)},
    {MP_ROM_QSTR(MP_QSTR_shamir), MP_ROM_PTR(&mod_trezorcrypto_shamir_module)},
    {MP_ROM_QSTR(MP_QSTR_slip39), MP_ROM_PTR(&mod_trezorcrypto_slip39_module)},
#if USE_OPTIGA
    {MP_ROM_QSTR(MP_QSTR_optiga), MP_ROM_PTR(&mod_trezorcrypto_optiga_module)},
#endif
#if USE_TROPIC
    {MP_ROM_QSTR(MP_QSTR_tropic), MP_ROM_PTR(&mod_trezorcrypto_tropic_module)},
#endif
#ifdef USE_MCU_ATTESTATION
    {MP_ROM_QSTR(MP_QSTR_mcu), MP_ROM_PTR(&mod_trezorcrypto_mcu_module)},
#endif
};
static MP_DEFINE_CONST_DICT(mp_module_trezorcrypto_globals,
                            mp_module_trezorcrypto_globals_table);

const mp_obj_module_t mp_module_trezorcrypto = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorcrypto_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorcrypto, mp_module_trezorcrypto);

#endif  // MICROPY_PY_TREZORCRYPTO
