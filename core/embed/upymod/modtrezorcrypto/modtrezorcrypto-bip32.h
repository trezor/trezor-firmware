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

#include "../trezorobj.h"
#include "hdnode.h"

#include "bip32.h"
#include "bip39.h"
#include "curves.h"
#include "ecdsa.h"
#include "memzero.h"
#include "sha3.h"
#if !BITCOIN_ONLY
#include "nem.h"
#endif

/// package: trezorcrypto.bip32
/// from trezorcrypto import secbytes

/// class HDNode:
///     """
///     BIP0032 HD node structure.
///     """

/// def __init__(
///     self,
///     depth: int,
///     fingerprint: int,
///     child_num: int,
///     chain_code: AnyBytes,
///     private_key: AnyBytes | None = None,
///     public_key: AnyBytes | None = None,
///     curve_name: str | None = None,
/// ) -> None:
///     """
///     """
static mp_obj_t mod_trezorcrypto_HDNode_make_new(const mp_obj_type_t *type,
                                                 size_t n_args, size_t n_kw,
                                                 const mp_obj_t *args) {
  static const mp_arg_t allowed_args[] = {
      {MP_QSTR_depth,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_none}},
      {MP_QSTR_fingerprint,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_none}},
      {MP_QSTR_child_num,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_none}},
      {MP_QSTR_chain_code,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_empty_bytes}},
      {MP_QSTR_private_key,
       MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_empty_bytes}},
      {MP_QSTR_public_key,
       MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_empty_bytes}},
      {MP_QSTR_curve_name,
       MP_ARG_KW_ONLY | MP_ARG_OBJ,
       {.u_obj = mp_const_empty_bytes}},
  };
  mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)] = {0};
  mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args),
                            allowed_args, vals);

  mp_buffer_info_t chain_code = {0};
  mp_buffer_info_t private_key = {0};
  mp_buffer_info_t public_key = {0};
  mp_buffer_info_t curve_name = {0};
  const uint32_t depth = trezor_obj_get_uint(vals[0].u_obj);
  const uint32_t fingerprint = trezor_obj_get_uint(vals[1].u_obj);
  const uint32_t child_num = trezor_obj_get_uint(vals[2].u_obj);
  mp_get_buffer_raise(vals[3].u_obj, &chain_code, MP_BUFFER_READ);
  mp_get_buffer_raise(vals[4].u_obj, &private_key, MP_BUFFER_READ);
  mp_get_buffer_raise(vals[5].u_obj, &public_key, MP_BUFFER_READ);
  mp_get_buffer_raise(vals[6].u_obj, &curve_name, MP_BUFFER_READ);

  if (32 != chain_code.len) {
    mp_raise_ValueError(MP_ERROR_TEXT("chain_code is invalid"));
  }
  if (0 == public_key.len && 0 == private_key.len) {
    mp_raise_ValueError(
        MP_ERROR_TEXT("either public_key or private_key is required"));
  }
  if (0 != private_key.len && 32 != private_key.len) {
    mp_raise_ValueError(MP_ERROR_TEXT("private_key is invalid"));
  }
  if (0 != public_key.len && 33 != public_key.len) {
    mp_raise_ValueError(MP_ERROR_TEXT("public_key is invalid"));
  }

  const curve_info *curve = NULL;
  if (0 == curve_name.len) {
    curve = get_curve_by_name(SECP256K1_NAME);
  } else {
    curve = get_curve_by_name(curve_name.buf);
  }
  if (NULL == curve) {
    mp_raise_ValueError(MP_ERROR_TEXT("curve_name is invalid"));
  }
  if (32 == private_key.len &&
      !hdnode_validate_private_key(curve, private_key.buf)) {
    mp_raise_ValueError(MP_ERROR_TEXT("private_key is invalid"));
  }
  if (33 == public_key.len &&
      !hdnode_validate_public_key(curve, public_key.buf)) {
    mp_raise_ValueError(MP_ERROR_TEXT("public_key is invalid"));
  }

  mp_obj_HDNode_t *o = hdnode_new();
  o->fingerprint = fingerprint;
  vault_request_t r = {.op = VAULT_IMPORT_NODE, .arg = depth, .length = 98};
  vault_response_t out = {0};
  r.child_num = child_num;
  if (curve_name.len >= sizeof(r.curve))
    mp_raise_ValueError(MP_ERROR_TEXT("Curve name too long"));
  memcpy(r.curve, curve_name.len ? curve_name.buf : SECP256K1_NAME,
         curve_name.len ? curve_name.len : strlen(SECP256K1_NAME));
  memcpy(r.data, chain_code.buf, 32);
  if (private_key.len) memcpy(r.data + 32, private_key.buf, 32);
  if (public_key.len) memcpy(r.data + 64, public_key.buf, 33);
  r.data[97] = (private_key.len ? 1 : 0) | (public_key.len ? 2 : 0);
  vault_raise(&r, &out);
  hdnode_set_blob(o, &out.blob);

  return MP_OBJ_FROM_PTR(o);
}

/// def derive(self, index: int, public: bool = False) -> None:
///     """
///     Derive a BIP0032 child node in place.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_derive(size_t n_args,
                                               const mp_obj_t *args) {
  mp_obj_HDNode_t *o = hdnode_object(args[0]);
  uint32_t i = trezor_obj_get_uint(args[1]);
  vault_request_t r = {.op = VAULT_DERIVE,
                       .blob = hdnode_blob(o),
                       .arg = n_args > 2 && args[2] == mp_const_true,
                       .length = 4};
  vault_response_t out = {0};
  memcpy(r.data, &i, 4);
  vault_raise(&r, &out);
  hdnode_set_blob(o, &out.blob);
  o->fingerprint = out.value;

  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_HDNode_derive_obj,
                                           2, 3,
                                           mod_trezorcrypto_HDNode_derive);

/// def derive_path(self, path: Sequence[int]) -> None:
///     """
///     Go through a list of indexes and iteratively derive a child node in
///     place.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_derive_path(mp_obj_t self,
                                                    mp_obj_t path) {
  mp_obj_HDNode_t *o = hdnode_object(self);

  // get path objects and length
  size_t plen = 0;
  mp_obj_t *pitems = NULL;
  mp_obj_get_array(path, &plen, &pitems);
  if (plen > 32) {
    mp_raise_ValueError(MP_ERROR_TEXT("Path cannot be longer than 32 indexes"));
  }

  for (uint32_t pi = 0; pi < plen; pi++) {
    uint32_t index = trezor_obj_get_uint(pitems[pi]);
    vault_request_t r = {
        .op = VAULT_DERIVE, .blob = hdnode_blob(o), .length = 4};
    vault_response_t out = {0};
    memcpy(r.data, &index, 4);
    vault_raise(&r, &out);
    hdnode_set_blob(o, &out.blob);
    o->fingerprint = out.value;
  }

  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_derive_path_obj,
                                 mod_trezorcrypto_HDNode_derive_path);

/// def serialize_public(self, version: int) -> str:
///     """
///     Serialize the public info from HD node to base58 string.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_serialize_public(mp_obj_t self,
                                                         mp_obj_t version) {
  uint32_t ver = trezor_obj_get_uint(version);
  mp_obj_HDNode_t *o = hdnode_object(self);
  if (hdnode_fill_public_key(hdnode_require(o)) != 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to serialize"));
  }

  vstr_t xpub = {0};
  vstr_init_len(&xpub, XPUB_MAXLEN);
  size_t written = hdnode_serialize_public(hdnode_require(o), o->fingerprint,
                                           ver, xpub.buf, xpub.alloc);
  if (written == 0) {
    vstr_clear(&xpub);
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to serialize"));
  }
  // written includes NULL at the end of the string
  xpub.len = written - 1;
  return mp_obj_new_str_from_vstr(&xpub);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_serialize_public_obj,
                                 mod_trezorcrypto_HDNode_serialize_public);

/// def clone(self) -> HDNode:
///     """
///     Returns a copy of the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_clone(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  /* A blob copy shares the sealed node; no kernel memory. Still refuse to
   * clone a destroyed or revoked node, rather than return a dead copy. */
  vault_blob_t blob = hdnode_blob(o);
  if (!secret_blob_live(&blob))
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid or locked vault"));
  mp_obj_HDNode_t *copy = hdnode_new();
  copy->blob = o->blob;
  copy->fingerprint = o->fingerprint;
  return MP_OBJ_FROM_PTR(copy);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_clone_obj,
                                 mod_trezorcrypto_HDNode_clone);

/// def depth(self) -> int:
///     """
///     Returns a depth of the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_depth(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  return mp_obj_new_int_from_uint(hdnode_require(o)->depth);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_depth_obj,
                                 mod_trezorcrypto_HDNode_depth);

/// def fingerprint(self) -> int:
///     """
///     Returns a fingerprint of the HD node (hash of the parent public key).
///     """
static mp_obj_t mod_trezorcrypto_HDNode_fingerprint(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  hdnode_require(o);
  return mp_obj_new_int_from_uint(o->fingerprint);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_fingerprint_obj,
                                 mod_trezorcrypto_HDNode_fingerprint);

/// def child_num(self) -> int:
///     """
///     Returns a child index of the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_child_num(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  return mp_obj_new_int_from_uint(hdnode_require(o)->child_num);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_child_num_obj,
                                 mod_trezorcrypto_HDNode_child_num);

/// def chain_code(self) -> bytes:
///     """
///     Returns a chain code of the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_chain_code(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  return mp_obj_new_bytes(hdnode_require(o)->chain_code,
                          sizeof(hdnode_require(o)->chain_code));
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_chain_code_obj,
                                 mod_trezorcrypto_HDNode_chain_code);

/// def private_key(self) -> secbytes:
///     """
///     Returns a private key of the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_private_key(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  mp_obj_secbytes_t *value = secbytes_new(32);
  vault_request_t r = {.op = VAULT_SNAPSHOT, .blob = hdnode_blob(o), .arg = 0};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  secbytes_set_blob(value, &out.blob);
  return MP_OBJ_FROM_PTR(value);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_private_key_obj,
                                 mod_trezorcrypto_HDNode_private_key);

/// def public_key(self) -> bytes:
///     """
///     Returns a public key of the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_public_key(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  if (hdnode_fill_public_key(hdnode_require(o)) != 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid private key"));
  }
  return mp_obj_new_bytes(hdnode_require(o)->public_key,
                          sizeof(hdnode_require(o)->public_key));
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_public_key_obj,
                                 mod_trezorcrypto_HDNode_public_key);

/// def address(self, version: int) -> str:
///     """
///     Compute a base58-encoded address string from the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_address(mp_obj_t self,
                                                mp_obj_t version) {
  mp_obj_HDNode_t *o = hdnode_object(self);

  uint32_t v = trezor_obj_get_uint(version);

  vstr_t address = {0};
  vstr_init_len(&address, ADDRESS_MAXLEN);
  if (hdnode_get_address(hdnode_require(o), v, address.buf, address.alloc) !=
      0) {
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to get address"));
  }
  address.len = strlen(address.buf);
  return mp_obj_new_str_from_vstr(&address);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_address_obj,
                                 mod_trezorcrypto_HDNode_address);

#if !BITCOIN_ONLY

#if USE_NEM
/// def nem_address(self, network: int) -> str:
///     """
///     Compute a NEM address string from the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_nem_address(mp_obj_t self,
                                                    mp_obj_t network) {
  mp_obj_HDNode_t *o = hdnode_object(self);

  uint8_t n = trezor_obj_get_uint8(network);

  vstr_t address = {0};
  vstr_init_len(&address, NEM_ADDRESS_SIZE);
  if (!hdnode_get_nem_address(hdnode_require(o), n, address.buf)) {
    vstr_clear(&address);
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to compute a NEM address"));
  }
  address.len = strlen(address.buf);
  return mp_obj_new_str_from_vstr(&address);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_nem_address_obj,
                                 mod_trezorcrypto_HDNode_nem_address);

/// def nem_encrypt(
///     self,
///     transfer_public_key: AnyBytes,
///     iv: AnyBytes,
///     salt: AnyBytes,
///     payload: AnyBytes,
/// ) -> bytes:
///     """
///     Encrypts payload using the transfer's public key
///     """
static mp_obj_t mod_trezorcrypto_HDNode_nem_encrypt(size_t n_args,
                                                    const mp_obj_t *args) {
  mp_obj_HDNode_t *o = hdnode_object(args[0]);

  mp_buffer_info_t transfer_pk = {0};
  mp_get_buffer_raise(args[1], &transfer_pk, MP_BUFFER_READ);
  if (transfer_pk.len != 32) {
    mp_raise_ValueError(
        MP_ERROR_TEXT("transfer_public_key has invalid length"));
  }

  mp_buffer_info_t iv = {0};
  mp_get_buffer_raise(args[2], &iv, MP_BUFFER_READ);
  if (iv.len != 16) {
    mp_raise_ValueError(MP_ERROR_TEXT("iv has invalid length"));
  }
  mp_buffer_info_t salt = {0};
  mp_get_buffer_raise(args[3], &salt, MP_BUFFER_READ);
  if (salt.len != NEM_SALT_SIZE) {
    mp_raise_ValueError(MP_ERROR_TEXT("salt has invalid length"));
  }
  mp_buffer_info_t payload = {0};
  mp_get_buffer_raise(args[4], &payload, MP_BUFFER_READ);
  if (payload.len == 0) {
    mp_raise_ValueError(MP_ERROR_TEXT("payload is empty"));
  }

  vault_request_t derive = {
      .op = VAULT_NEM_SHARED, .blob = hdnode_blob(o), .length = 64};
  memcpy(derive.data, transfer_pk.buf, 32);
  memcpy(derive.data + 32, salt.buf, 32);
  vault_response_t out = {0};
  vault_raise(&derive, &out);
  vault_blob_t key = out.blob;
  uint8_t current_iv[16] = {0};
  memcpy(current_iv, iv.buf, 16);
  vstr_t vstr = {0};
  vstr_init_len(&vstr, NEM_ENCRYPTED_SIZE(payload.len));
  for (size_t offset = 0; offset < vstr.len; offset += 16) {
    vault_request_t block = {
        .op = VAULT_AES_CBC, .arg = 1, .blob = key, .length = 16};
    memcpy(block.curve, current_iv, 16);
    size_t take = MIN((size_t)16, payload.len - offset);
    memset(block.data, 16 - take, 16);
    memcpy(block.data, (const uint8_t *)payload.buf + offset, take);
    vault_raise(&block, &out);
    memcpy(vstr.buf + offset, out.data, 16);
    memcpy(current_iv, out.data, 16);
  }
  memzero(&key, sizeof(key));
  memzero(current_iv, sizeof(current_iv));
  memzero(&out, sizeof(out));
  return mp_obj_new_bytes_from_vstr(&vstr);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_HDNode_nem_encrypt_obj, 5, 5,
    mod_trezorcrypto_HDNode_nem_encrypt);

#endif

/// def ethereum_pubkeyhash(self) -> bytes:
///     """
///     Compute an Ethereum pubkeyhash (aka address) from the HD node.
///     """
static mp_obj_t mod_trezorcrypto_HDNode_ethereum_pubkeyhash(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);

  /* The public view has no private key, so hash the vault's public key
   * rather than calling hdnode_get_ethereum_pubkeyhash(). */
  const HDNode *node = hdnode_require(o);
  uint8_t pub[65] = {0}, hash[32] = {0};
  if (node->curve != get_curve_by_name(SECP256K1_NAME) ||
      !ecdsa_uncompress_pubkey(node->curve->params, node->public_key, pub)) {
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to compute pubkeyhash"));
  }
  SHA3_CTX ctx = {0};
  sha3_256_Init(&ctx);
  sha3_Update(&ctx, pub + 1, 64);
  keccak_Final(&ctx, hash);
  return mp_obj_new_bytes(hash + 12, 20);
}
static MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_HDNode_ethereum_pubkeyhash_obj,
    mod_trezorcrypto_HDNode_ethereum_pubkeyhash);

#endif

/// def __del__(self) -> None:
///     """
///     Cleans up sensitive memory.
///     """
static mp_obj_t mod_trezorcrypto_HDNode___del__(mp_obj_t self) {
  mp_obj_HDNode_t *o = hdnode_object(self);
  o->fingerprint = 0;
  memzero(&o->blob, sizeof(o->blob));
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode___del___obj,
                                 mod_trezorcrypto_HDNode___del__);

static const mp_rom_map_elem_t mod_trezorcrypto_HDNode_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode___del___obj)},
    {MP_ROM_QSTR(MP_QSTR_derive),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_derive_obj)},
    {MP_ROM_QSTR(MP_QSTR_derive_path),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_derive_path_obj)},
    {MP_ROM_QSTR(MP_QSTR_serialize_public),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_serialize_public_obj)},
    {MP_ROM_QSTR(MP_QSTR_clone),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_clone_obj)},
    {MP_ROM_QSTR(MP_QSTR_depth),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_depth_obj)},
    {MP_ROM_QSTR(MP_QSTR_fingerprint),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_fingerprint_obj)},
    {MP_ROM_QSTR(MP_QSTR_child_num),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_child_num_obj)},
    {MP_ROM_QSTR(MP_QSTR_chain_code),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_chain_code_obj)},
    {MP_ROM_QSTR(MP_QSTR_private_key),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_private_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_public_key),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_public_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_address),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_address_obj)},
#if !BITCOIN_ONLY
#if USE_NEM
    {MP_ROM_QSTR(MP_QSTR_nem_address),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_nem_address_obj)},
    {MP_ROM_QSTR(MP_QSTR_nem_encrypt),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_nem_encrypt_obj)},
#endif
    {MP_ROM_QSTR(MP_QSTR_ethereum_pubkeyhash),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_ethereum_pubkeyhash_obj)},
#endif
};
static MP_DEFINE_CONST_DICT(mod_trezorcrypto_HDNode_locals_dict,
                            mod_trezorcrypto_HDNode_locals_dict_table);

// clang-format off
MP_DEFINE_CONST_OBJ_TYPE(mod_trezorcrypto_HDNode_type,
  MP_QSTR_HDNode, MP_TYPE_FLAG_NONE,
  make_new, mod_trezorcrypto_HDNode_make_new,
  locals_dict, &mod_trezorcrypto_HDNode_locals_dict);
// clang-format on

/// mock:global

/// def from_seed(seed: AnyBytes | secbytes, curve_name: str) -> HDNode:
///     """
///     Construct a BIP0032 HD node from a BIP0039 seed value.
///     """
static mp_obj_t mod_trezorcrypto_bip32_from_seed(mp_obj_t seed,
                                                 mp_obj_t curve_name) {
  mp_buffer_info_t seedb = {0}, curveb = {0};
  bool opaque = mp_obj_is_type(seed, &mod_trezorcrypto_secbytes_type);
  if (!opaque) mp_get_buffer_raise(seed, &seedb, MP_BUFFER_READ);
  mp_get_buffer_raise(curve_name, &curveb, MP_BUFFER_READ);
  if ((!opaque && (!seedb.len || seedb.len > VAULT_DATA_SIZE)) || !curveb.len ||
      curveb.len >= VAULT_CURVE_SIZE)
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid seed or curve"));
  mp_obj_HDNode_t *o = hdnode_new();
  vault_request_t r = {
      .op = VAULT_FROM_SEED, .arg = opaque, .length = seedb.len};
  vault_response_t out = {0};
  memcpy(r.curve, curveb.buf, curveb.len);
  if (opaque)
    r.blob = secbytes_blob(MP_OBJ_TO_PTR(seed));
  else
    memcpy(r.data, seedb.buf, seedb.len);
  vault_raise(&r, &out);
  hdnode_set_blob(o, &out.blob);

  o->fingerprint = 0;
  return MP_OBJ_FROM_PTR(o);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_bip32_from_seed_obj,
                                 mod_trezorcrypto_bip32_from_seed);

/// def from_storage(passphrase: str = "") -> secbytes:
///     """Derive a BIP39 seed inside the vault; return only an opaque
///     handle."""
static mp_obj_t mod_trezorcrypto_bip32_from_storage(size_t n_args,
                                                    const mp_obj_t *args) {
  mp_buffer_info_t passphrase = {0};
  if (n_args) mp_get_buffer_raise(args[0], &passphrase, MP_BUFFER_READ);
  if (passphrase.len > 200)
    mp_raise_ValueError(MP_ERROR_TEXT("Passphrase too long"));
  mp_obj_secbytes_t *value = secbytes_new(64);
  vault_request_t r = {.op = VAULT_SEED_STORAGE, .length = passphrase.len};
  vault_response_t out = {0};
  if (passphrase.len) memcpy(r.data, passphrase.buf, passphrase.len);
  vault_raise(&r, &out);
  secbytes_set_blob(value, &out.blob);
  return MP_OBJ_FROM_PTR(value);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_bip32_from_storage_obj, 0, 1,
    mod_trezorcrypto_bip32_from_storage);

static const mp_rom_map_elem_t mod_trezorcrypto_bip32_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bip32)},
    {MP_ROM_QSTR(MP_QSTR_from_storage),
     MP_ROM_PTR(&mod_trezorcrypto_bip32_from_storage_obj)},
    {MP_ROM_QSTR(MP_QSTR_HDNode), MP_ROM_PTR(&mod_trezorcrypto_HDNode_type)},
    {MP_ROM_QSTR(MP_QSTR_from_seed),
     MP_ROM_PTR(&mod_trezorcrypto_bip32_from_seed_obj)},
};
static MP_DEFINE_CONST_DICT(mod_trezorcrypto_bip32_globals,
                            mod_trezorcrypto_bip32_globals_table);

static const mp_obj_module_t mod_trezorcrypto_bip32_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_bip32_globals,
};
