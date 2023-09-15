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

#include "embed/extmod/trezorobj.h"
#include "hdnode.h"

#include "bip32.h"
#include "bip39.h"
#include "curves.h"
#include "memzero.h"
#if !BITCOIN_ONLY
#include "nem.h"
#endif

/// package: trezorcrypto.bip32

/// class HDNode:
///     """
///     BIP0032 HD node structure.
///     """

/// def __init__(
///     self,
///     depth: int,
///     fingerprint: int,
///     child_num: int,
///     chain_code: bytes,
///     private_key: bytes | None = None,
///     public_key: bytes | None = None,
///     curve_name: str | None = None,
/// ) -> None:
///     """
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_make_new(const mp_obj_type_t *type,
                                                 size_t n_args, size_t n_kw,
                                                 const mp_obj_t *args) {
  STATIC const mp_arg_t allowed_args[] = {
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
    mp_raise_ValueError("chain_code is invalid");
  }
  if (0 == public_key.len && 0 == private_key.len) {
    mp_raise_ValueError("either public_key or private_key is required");
  }
  if (0 != private_key.len && 32 != private_key.len) {
    mp_raise_ValueError("private_key is invalid");
  }
  if (0 != public_key.len && 33 != public_key.len) {
    mp_raise_ValueError("public_key is invalid");
  }

  const curve_info *curve = NULL;
  if (0 == curve_name.len) {
    curve = get_curve_by_name(SECP256K1_NAME);
  } else {
    curve = get_curve_by_name(curve_name.buf);
  }
  if (NULL == curve) {
    mp_raise_ValueError("curve_name is invalid");
  }

  mp_obj_HDNode_t *o = m_new_obj_with_finaliser(mp_obj_HDNode_t);
  o->base.type = type;
  o->fingerprint = fingerprint;
  o->hdnode.depth = depth;
  o->hdnode.child_num = child_num;
  if (32 == chain_code.len) {
    memcpy(o->hdnode.chain_code, chain_code.buf, 32);
  } else {
    memzero(o->hdnode.chain_code, 32);
  }
  if (32 == private_key.len) {
    memcpy(o->hdnode.private_key, private_key.buf, 32);
  } else {
    memzero(o->hdnode.private_key, 32);
  }
  if (33 == public_key.len) {
    memcpy(o->hdnode.public_key, public_key.buf, 33);
  } else {
    memzero(o->hdnode.public_key, 33);
  }
  o->hdnode.curve = curve;

  return MP_OBJ_FROM_PTR(o);
}

/// def derive(self, index: int, public: bool = False) -> None:
///     """
///     Derive a BIP0032 child node in place.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_derive(size_t n_args,
                                               const mp_obj_t *args) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(args[0]);
  uint32_t i = trezor_obj_get_uint(args[1]);
  uint32_t fp = hdnode_fingerprint(&o->hdnode);
  bool public = n_args > 2 && args[2] == mp_const_true;

  int res = 0;
  if (public) {
    res = hdnode_public_ckd(&o->hdnode, i);
  } else {
    if (0 ==
        memcmp(
            o->hdnode.private_key,
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            32)) {
      memzero(&o->hdnode, sizeof(o->hdnode));
      mp_raise_ValueError("Failed to derive, private key not set");
    }
    res = hdnode_private_ckd(&o->hdnode, i);
  }
  if (!res) {
    memzero(&o->hdnode, sizeof(o->hdnode));
    mp_raise_ValueError("Failed to derive");
  }
  o->fingerprint = fp;

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_HDNode_derive_obj,
                                           2, 3,
                                           mod_trezorcrypto_HDNode_derive);

/// def derive_path(self, path: Sequence[int]) -> None:
///     """
///     Go through a list of indexes and iteratively derive a child node in
///     place.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_derive_path(mp_obj_t self,
                                                    mp_obj_t path) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

  // get path objects and length
  size_t plen = 0;
  mp_obj_t *pitems = NULL;
  mp_obj_get_array(path, &plen, &pitems);
  if (plen > 32) {
    mp_raise_ValueError("Path cannot be longer than 32 indexes");
  }

  for (uint32_t pi = 0; pi < plen; pi++) {
    if (pi == plen - 1) {
      // fingerprint is calculated from the parent of the final derivation
      o->fingerprint = hdnode_fingerprint(&o->hdnode);
    }
    uint32_t pitem = trezor_obj_get_uint(pitems[pi]);
    if (!hdnode_private_ckd(&o->hdnode, pitem)) {
      o->fingerprint = 0;
      memzero(&o->hdnode, sizeof(o->hdnode));
      mp_raise_ValueError("Failed to derive path");
    }
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_derive_path_obj,
                                 mod_trezorcrypto_HDNode_derive_path);

/// def serialize_public(self, version: int) -> str:
///     """
///     Serialize the public info from HD node to base58 string.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_serialize_public(mp_obj_t self,
                                                         mp_obj_t version) {
  uint32_t ver = trezor_obj_get_uint(version);
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  if (hdnode_fill_public_key(&o->hdnode) != 0) {
    mp_raise_ValueError("Failed to serialize");
  }

  vstr_t xpub = {0};
  vstr_init_len(&xpub, XPUB_MAXLEN);
  int written = hdnode_serialize_public(&o->hdnode, o->fingerprint, ver,
                                        xpub.buf, xpub.alloc);
  if (written <= 0) {
    vstr_clear(&xpub);
    mp_raise_ValueError("Failed to serialize");
  }
  // written includes NULL at the end of the string
  xpub.len = written - 1;
  return mp_obj_new_str_from_vstr(&mp_type_str, &xpub);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_serialize_public_obj,
                                 mod_trezorcrypto_HDNode_serialize_public);

/// def clone(self) -> HDNode:
///     """
///     Returns a copy of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_clone(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  mp_obj_HDNode_t *copy = m_new_obj_with_finaliser(mp_obj_HDNode_t);
  copy->base.type = &mod_trezorcrypto_HDNode_type;
  copy->hdnode = o->hdnode;
  copy->fingerprint = o->fingerprint;
  return MP_OBJ_FROM_PTR(copy);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_clone_obj,
                                 mod_trezorcrypto_HDNode_clone);

/// def depth(self) -> int:
///     """
///     Returns a depth of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_depth(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_int_from_uint(o->hdnode.depth);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_depth_obj,
                                 mod_trezorcrypto_HDNode_depth);

/// def fingerprint(self) -> int:
///     """
///     Returns a fingerprint of the HD node (hash of the parent public key).
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_fingerprint(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_int_from_uint(o->fingerprint);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_fingerprint_obj,
                                 mod_trezorcrypto_HDNode_fingerprint);

/// def child_num(self) -> int:
///     """
///     Returns a child index of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_child_num(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_int_from_uint(o->hdnode.child_num);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_child_num_obj,
                                 mod_trezorcrypto_HDNode_child_num);

/// def chain_code(self) -> bytes:
///     """
///     Returns a chain code of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_chain_code(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_bytes(o->hdnode.chain_code, sizeof(o->hdnode.chain_code));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_chain_code_obj,
                                 mod_trezorcrypto_HDNode_chain_code);

/// def private_key(self) -> bytes:
///     """
///     Returns a private key of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_private_key(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_bytes(o->hdnode.private_key, sizeof(o->hdnode.private_key));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_private_key_obj,
                                 mod_trezorcrypto_HDNode_private_key);

/// def private_key_ext(self) -> bytes:
///     """
///     Returns a private key extension of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_private_key_ext(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  return mp_obj_new_bytes(o->hdnode.private_key_extension,
                          sizeof(o->hdnode.private_key_extension));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_private_key_ext_obj,
                                 mod_trezorcrypto_HDNode_private_key_ext);

/// def public_key(self) -> bytes:
///     """
///     Returns a public key of the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_public_key(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  if (hdnode_fill_public_key(&o->hdnode) != 0) {
    mp_raise_ValueError("Invalid private key");
  }
  return mp_obj_new_bytes(o->hdnode.public_key, sizeof(o->hdnode.public_key));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode_public_key_obj,
                                 mod_trezorcrypto_HDNode_public_key);

/// def address(self, version: int) -> str:
///     """
///     Compute a base58-encoded address string from the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_address(mp_obj_t self,
                                                mp_obj_t version) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

  uint32_t v = trezor_obj_get_uint(version);

  vstr_t address = {0};
  vstr_init_len(&address, ADDRESS_MAXLEN);
  if (hdnode_get_address(&o->hdnode, v, address.buf, address.alloc) != 0) {
    mp_raise_ValueError("Failed to get address");
  }
  address.len = strlen(address.buf);
  return mp_obj_new_str_from_vstr(&mp_type_str, &address);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_address_obj,
                                 mod_trezorcrypto_HDNode_address);

#if !BITCOIN_ONLY

#if USE_NEM
/// def nem_address(self, network: int) -> str:
///     """
///     Compute a NEM address string from the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_nem_address(mp_obj_t self,
                                                    mp_obj_t network) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

  uint8_t n = trezor_obj_get_uint8(network);

  vstr_t address = {0};
  vstr_init_len(&address, NEM_ADDRESS_SIZE);
  if (!hdnode_get_nem_address(&o->hdnode, n, address.buf)) {
    vstr_clear(&address);
    mp_raise_ValueError("Failed to compute a NEM address");
  }
  address.len = strlen(address.buf);
  return mp_obj_new_str_from_vstr(&mp_type_str, &address);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_HDNode_nem_address_obj,
                                 mod_trezorcrypto_HDNode_nem_address);

/// def nem_encrypt(
///     self, transfer_public_key: bytes, iv: bytes, salt: bytes, payload: bytes
/// ) -> bytes:
///     """
///     Encrypts payload using the transfer's public key
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_nem_encrypt(size_t n_args,
                                                    const mp_obj_t *args) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(args[0]);

  mp_buffer_info_t transfer_pk = {0};
  mp_get_buffer_raise(args[1], &transfer_pk, MP_BUFFER_READ);
  if (transfer_pk.len != 32) {
    mp_raise_ValueError("transfer_public_key has invalid length");
  }

  mp_buffer_info_t iv = {0};
  mp_get_buffer_raise(args[2], &iv, MP_BUFFER_READ);
  if (iv.len != 16) {
    mp_raise_ValueError("iv has invalid length");
  }
  mp_buffer_info_t salt = {0};
  mp_get_buffer_raise(args[3], &salt, MP_BUFFER_READ);
  if (salt.len != NEM_SALT_SIZE) {
    mp_raise_ValueError("salt has invalid length");
  }
  mp_buffer_info_t payload = {0};
  mp_get_buffer_raise(args[4], &payload, MP_BUFFER_READ);
  if (payload.len == 0) {
    mp_raise_ValueError("payload is empty");
  }

  vstr_t vstr = {0};
  vstr_init_len(&vstr, NEM_ENCRYPTED_SIZE(payload.len));
  if (!hdnode_nem_encrypt(
          &o->hdnode, *(const ed25519_public_key *)transfer_pk.buf, iv.buf,
          salt.buf, payload.buf, payload.len, (uint8_t *)vstr.buf)) {
    mp_raise_ValueError("HDNode nem encrypt failed");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_HDNode_nem_encrypt_obj, 5, 5,
    mod_trezorcrypto_HDNode_nem_encrypt);

#endif

/// def ethereum_pubkeyhash(self) -> bytes:
///     """
///     Compute an Ethereum pubkeyhash (aka address) from the HD node.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode_ethereum_pubkeyhash(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);

  vstr_t pkh = {0};
  vstr_init_len(&pkh, 20);
  hdnode_get_ethereum_pubkeyhash(&o->hdnode, (uint8_t *)pkh.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &pkh);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_HDNode_ethereum_pubkeyhash_obj,
    mod_trezorcrypto_HDNode_ethereum_pubkeyhash);

#endif

/// def __del__(self) -> None:
///     """
///     Cleans up sensitive memory.
///     """
STATIC mp_obj_t mod_trezorcrypto_HDNode___del__(mp_obj_t self) {
  mp_obj_HDNode_t *o = MP_OBJ_TO_PTR(self);
  o->fingerprint = 0;
  memzero(&o->hdnode, sizeof(o->hdnode));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_HDNode___del___obj,
                                 mod_trezorcrypto_HDNode___del__);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_HDNode_locals_dict_table[] = {
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
    {MP_ROM_QSTR(MP_QSTR_private_key_ext),
     MP_ROM_PTR(&mod_trezorcrypto_HDNode_private_key_ext_obj)},
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
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_HDNode_locals_dict,
                            mod_trezorcrypto_HDNode_locals_dict_table);

const mp_obj_type_t mod_trezorcrypto_HDNode_type = {
    {&mp_type_type},
    .name = MP_QSTR_HDNode,
    .make_new = mod_trezorcrypto_HDNode_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_HDNode_locals_dict,
};

/// mock:global

/// def from_seed(seed: bytes, curve_name: str) -> HDNode:
///     """
///     Construct a BIP0032 HD node from a BIP0039 seed value.
///     """
STATIC mp_obj_t mod_trezorcrypto_bip32_from_seed(mp_obj_t seed,
                                                 mp_obj_t curve_name) {
  mp_buffer_info_t seedb = {0};
  mp_get_buffer_raise(seed, &seedb, MP_BUFFER_READ);
  if (seedb.len == 0) {
    mp_raise_ValueError("Invalid seed");
  }
  mp_buffer_info_t curveb = {0};
  mp_get_buffer_raise(curve_name, &curveb, MP_BUFFER_READ);
  if (curveb.len == 0) {
    mp_raise_ValueError("Invalid curve name");
  }

  HDNode hdnode = {0};
  int res = hdnode_from_seed(seedb.buf, seedb.len, curveb.buf, &hdnode);

  if (!res) {
    mp_raise_ValueError("Failed to derive the root node");
  }

  mp_obj_HDNode_t *o = m_new_obj_with_finaliser(mp_obj_HDNode_t);
  o->base.type = &mod_trezorcrypto_HDNode_type;
  o->hdnode = hdnode;
  o->fingerprint = 0;
  return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_bip32_from_seed_obj,
                                 mod_trezorcrypto_bip32_from_seed);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_bip32_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bip32)},
    {MP_ROM_QSTR(MP_QSTR_HDNode), MP_ROM_PTR(&mod_trezorcrypto_HDNode_type)},
    {MP_ROM_QSTR(MP_QSTR_from_seed),
     MP_ROM_PTR(&mod_trezorcrypto_bip32_from_seed_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_bip32_globals,
                            mod_trezorcrypto_bip32_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_bip32_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_bip32_globals,
};
