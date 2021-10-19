/**
 * Copyright (c) SatoshiLabs
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdbool.h>
#include <string.h>

#include "memzero.h"
#include "zkp_context.h"

#include "vendor/secp256k1-zkp/include/secp256k1.h"
#include "vendor/secp256k1-zkp/include/secp256k1_extrakeys.h"
#include "vendor/secp256k1-zkp/include/secp256k1_schnorrsig.h"

#include "zkp_bip340.h"

// BIP340 Schnorr public key derivation
// private_key_bytes has 32 bytes
// public_key_bytes has 32 bytes
// returns 0 on success
int zkp_bip340_get_public_key(const uint8_t *private_key_bytes,
                              uint8_t *public_key_bytes) {
  int result = 0;

  secp256k1_pubkey pubkey = {0};

  if (result == 0) {
    secp256k1_context *context_writable = zkp_context_acquire_writable();
    secp256k1_context_writable_randomize(context_writable);
    if (secp256k1_ec_pubkey_create(context_writable, &pubkey,
                                   private_key_bytes) != 1) {
      result = -1;
    }
    zkp_context_release_writable();
  }

  secp256k1_xonly_pubkey xonly_pubkey = {0};
  const secp256k1_context *context_read_only = zkp_context_get_read_only();

  if (result == 0) {
    if (secp256k1_xonly_pubkey_from_pubkey(context_read_only, &xonly_pubkey,
                                           NULL, &pubkey) != 1) {
      result = -1;
    }
  }

  memzero(&pubkey, sizeof(pubkey));

  if (result == 0) {
    if (secp256k1_xonly_pubkey_serialize(context_read_only, public_key_bytes,
                                         &xonly_pubkey) != 1) {
      result = -1;
    }
  }

  memzero(&xonly_pubkey, sizeof(xonly_pubkey));

  return result;
}

// BIP340 Schnorr signature signing
// private_key_bytes has 32 bytes
// digest has 32 bytes
// signature_bytes has 64 bytes
// auxiliary_data has 32 bytes or is NULL
// returns 0 on success
int zkp_bip340_sign_digest(const uint8_t *private_key_bytes,
                           const uint8_t *digest, uint8_t *signature_bytes,
                           uint8_t *auxiliary_data) {
  int result = 0;

  secp256k1_keypair keypair = {0};

  if (result == 0) {
    secp256k1_context *context_writable = zkp_context_acquire_writable();
    secp256k1_context_writable_randomize(context_writable);
    if (secp256k1_keypair_create(context_writable, &keypair,
                                 private_key_bytes) != 1) {
      result = -1;
    }
    zkp_context_release_writable();
  }

  if (result == 0) {
    secp256k1_context *context_writable = zkp_context_acquire_writable();
    secp256k1_context_writable_randomize(context_writable);
    if (secp256k1_schnorrsig_sign(context_writable, signature_bytes, digest,
                                  &keypair, NULL, auxiliary_data) != 1) {
      result = -1;
    }
    zkp_context_release_writable();
  }

  memzero(&keypair, sizeof(keypair));

  return result;
}

// BIP340 Schnorr signature verification
// public_key_bytes has 32 bytes
// signature_bytes has 64 bytes
// digest has 32 bytes
// returns 0 if verification succeeded
int zkp_bip340_verify_digest(const uint8_t *public_key_bytes,
                             const uint8_t *signature_bytes,
                             const uint8_t *digest) {
  int result = 0;

  secp256k1_xonly_pubkey xonly_pubkey = {0};
  const secp256k1_context *context_read_only = zkp_context_get_read_only();

  if (result == 0) {
    if (secp256k1_xonly_pubkey_parse(context_read_only, &xonly_pubkey,
                                     public_key_bytes) != 1) {
      result = 1;
    }
  }

  if (result == 0) {
    if (secp256k1_schnorrsig_verify(context_read_only, signature_bytes, digest,
                                    &xonly_pubkey) != 1) {
      result = 5;
    }
  }

  memzero(&xonly_pubkey, sizeof(xonly_pubkey));

  return result;
}
