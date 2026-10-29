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

#ifndef __HDNODE_H__
#define __HDNODE_H__

#include "py/obj.h"

#include "bip32.h"
#include "curves.h"
#include "modtrezorcrypto-secbytes.h"

typedef struct _mp_obj_HDNode_t {
  mp_obj_base_t base;
  uint32_t fingerprint;
  struct {
    uint8_t bytes[VAULT_NODE_BLOB_SIZE];
  } blob;
} mp_obj_HDNode_t;

extern const mp_obj_type_t mod_trezorcrypto_HDNode_type;

/* Expand compact ciphertext into the canonical zero-padded syscall envelope.
 * Neither helper opens a node or puts private plaintext in coreapp. */
static vault_blob_t hdnode_blob(const mp_obj_HDNode_t *o) {
  vault_blob_t blob = {0};
  memcpy(blob.bytes, o->blob.bytes, sizeof(o->blob.bytes));
  return blob;
}
static void hdnode_set_blob(mp_obj_HDNode_t *o, const vault_blob_t *blob) {
  memcpy(o->blob.bytes, blob->bytes, sizeof(o->blob.bytes));
}

static mp_obj_HDNode_t *hdnode_object(mp_obj_t self) {
  if (!mp_obj_is_type(self, &mod_trezorcrypto_HDNode_type))
    mp_raise_TypeError(MP_ERROR_TEXT("Expected HDNode"));
  return MP_OBJ_TO_PTR(self);
}

/* Public-only view. No private bytes or kernel pointers cross the ABI. */
static HDNode *hdnode_require(mp_obj_HDNode_t *o) {
  static HDNode public_view;
  vault_request_t r = {.op = VAULT_PUBLIC, .blob = hdnode_blob(o)};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  /* The kernel returns a blob when it computed the public key; keep it. */
  if (!secret_blob_empty(&out.blob)) hdnode_set_blob(o, &out.blob);
  memzero(&public_view, sizeof(public_view));
  public_view.depth = out.depth;
  public_view.child_num = out.child_num;
  /* VAULT_PUBLIC reports the node's curve; the view carries no private key. */
  static const char *const curves[] = {
      SECP256K1_NAME,         NIST256P1_NAME,         ED25519_NAME,
      SECP256K1_DECRED_NAME,  SECP256K1_GROESTL_NAME, SECP256K1_SMART_NAME,
      "ed25519 cardano seed", ED25519_SHA3_NAME,      ED25519_KECCAK_NAME,
      CURVE25519_NAME};
  if (out.value >= sizeof(curves) / sizeof(curves[0]))
    mp_raise_ValueError(MP_ERROR_TEXT("Unknown node curve"));
  public_view.curve = get_curve_by_name(curves[out.value]);
  memcpy(public_view.chain_code, out.chain_code, 32);
  memcpy(public_view.public_key, out.public_key, 33);
  public_view.is_public_key_set = true;
  return &public_view;
}
static mp_obj_HDNode_t *hdnode_new(void) {
  mp_obj_HDNode_t *o = mp_obj_malloc_with_finaliser(
      mp_obj_HDNode_t, &mod_trezorcrypto_HDNode_type);
  memzero(&o->blob, sizeof(o->blob));
  o->fingerprint = 0;
  return o;
}
#endif
