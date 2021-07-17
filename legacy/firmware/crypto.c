/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "crypto.h"
#include <string.h>
#include "address.h"
#include "aes/aes.h"
#include "base58.h"
#include "bip32.h"
#include "cash_addr.h"
#include "coins.h"
#include "curves.h"
#include "hmac.h"
#include "layout.h"
#include "pbkdf2.h"
#include "secp256k1.h"
#include "segwit_addr.h"
#include "sha2.h"

#define PATH_MAX_ACCOUNT 100
#define PATH_MAX_CHANGE 1
#define PATH_MAX_ADDRESS_INDEX 1000000

// SLIP-44 hardened coin type for Bitcoin
#define SLIP44_BITCOIN 0x80000000

// SLIP-44 hardened coin type for all Testnet coins
#define SLIP44_TESTNET 0x80000001

uint32_t ser_length(uint32_t len, uint8_t *out) {
  if (len < 253) {
    out[0] = len & 0xFF;
    return 1;
  }
  if (len < 0x10000) {
    out[0] = 253;
    out[1] = len & 0xFF;
    out[2] = (len >> 8) & 0xFF;
    return 3;
  }
  out[0] = 254;
  out[1] = len & 0xFF;
  out[2] = (len >> 8) & 0xFF;
  out[3] = (len >> 16) & 0xFF;
  out[4] = (len >> 24) & 0xFF;
  return 5;
}

uint32_t ser_length_hash(Hasher *hasher, uint32_t len) {
  if (len < 253) {
    hasher_Update(hasher, (const uint8_t *)&len, 1);
    return 1;
  }
  if (len < 0x10000) {
    uint8_t d = 253;
    hasher_Update(hasher, &d, 1);
    hasher_Update(hasher, (const uint8_t *)&len, 2);
    return 3;
  }
  uint8_t d = 254;
  hasher_Update(hasher, &d, 1);
  hasher_Update(hasher, (const uint8_t *)&len, 4);
  return 5;
}

uint32_t deser_length(const uint8_t *in, uint32_t *out) {
  if (in[0] < 253) {
    *out = in[0];
    return 1;
  }
  if (in[0] == 253) {
    *out = in[1] + (in[2] << 8);
    return 1 + 2;
  }
  if (in[0] == 254) {
    *out = in[1] + (in[2] << 8) + (in[3] << 16) + ((uint32_t)in[4] << 24);
    return 1 + 4;
  }
  *out = 0;  // ignore 64 bit
  return 1 + 8;
}

int sshMessageSign(HDNode *node, const uint8_t *message, size_t message_len,
                   uint8_t *signature) {
  signature[0] = 0;  // prefix: pad with zero, so all signatures are 65 bytes
  return hdnode_sign(node, message, message_len, HASHER_SHA2, signature + 1,
                     NULL, NULL);
}

int gpgMessageSign(HDNode *node, const uint8_t *message, size_t message_len,
                   uint8_t *signature) {
  signature[0] = 0;  // prefix: pad with zero, so all signatures are 65 bytes
  const curve_info *ed25519_curve_info = get_curve_by_name(ED25519_NAME);
  if (ed25519_curve_info && node->curve == ed25519_curve_info) {
    // GPG supports variable size digest for Ed25519 signatures
    return hdnode_sign(node, message, message_len, 0, signature + 1, NULL,
                       NULL);
  } else {
    // Ensure 256-bit digest before proceeding
    if (message_len != 32) {
      return 1;
    }
    return hdnode_sign_digest(node, message, signature + 1, NULL, NULL);
  }
}

int signifyMessageSign(HDNode *node, const uint8_t *message, size_t message_len,
                       uint8_t *signature) {
  signature[0] = 0;  // prefix: pad with zero, so all signatures are 65 bytes
  const curve_info *ed25519_curve_info = get_curve_by_name(ED25519_NAME);
  // only ed25519 is supported
  if (!ed25519_curve_info || node->curve != ed25519_curve_info) {
    return 1;
  }
  return hdnode_sign(node, message, message_len, 0, signature + 1, NULL, NULL);
}

static void cryptoMessageHash(const CoinInfo *coin, const uint8_t *message,
                              size_t message_len,
                              uint8_t hash[HASHER_DIGEST_LENGTH]) {
  Hasher hasher = {0};
  hasher_Init(&hasher, coin->curve->hasher_sign);
  hasher_Update(&hasher, (const uint8_t *)coin->signed_message_header,
                strlen(coin->signed_message_header));
  uint8_t varint[5] = {0};
  uint32_t l = ser_length(message_len, varint);
  hasher_Update(&hasher, varint, l);
  hasher_Update(&hasher, message, message_len);
  hasher_Final(&hasher, hash);
}

int cryptoMessageSign(const CoinInfo *coin, HDNode *node,
                      InputScriptType script_type, const uint8_t *message,
                      size_t message_len, uint8_t *signature) {
  uint8_t hash[HASHER_DIGEST_LENGTH] = {0};
  cryptoMessageHash(coin, message, message_len, hash);

  uint8_t pby = 0;
  int result = hdnode_sign_digest(node, hash, signature + 1, &pby, NULL);
  if (result == 0) {
    switch (script_type) {
      case InputScriptType_SPENDP2SHWITNESS:
        // segwit-in-p2sh
        signature[0] = 35 + pby;
        break;
      case InputScriptType_SPENDWITNESS:
        // segwit
        signature[0] = 39 + pby;
        break;
      case InputScriptType_SPENDTAPROOT:
        // taproot
        signature[0] = 43 + pby;
        break;
      default:
        // p2pkh
        signature[0] = 31 + pby;
        break;
    }
  }
  return result;
}

int cryptoMessageVerify(const CoinInfo *coin, const uint8_t *message,
                        size_t message_len, const char *address,
                        const uint8_t *signature) {
  // check for invalid signature prefix
  if (signature[0] < 27 || signature[0] > 43) {
    return 1;
  }

  uint8_t hash[HASHER_DIGEST_LENGTH] = {0};
  cryptoMessageHash(coin, message, message_len, hash);

  uint8_t recid = (signature[0] - 27) % 4;
  bool compressed = signature[0] >= 31;

  // check if signature verifies the digest and recover the public key
  uint8_t pubkey[65] = {0};
  if (ecdsa_recover_pub_from_sig(coin->curve->params, pubkey, signature + 1,
                                 hash, recid) != 0) {
    return 3;
  }
  // convert public key to compressed pubkey if necessary
  if (compressed) {
    pubkey[0] = 0x02 | (pubkey[64] & 1);
  }

  // check if the address is correct
  uint8_t addr_raw[MAX_ADDR_RAW_SIZE] = {0};
  uint8_t recovered_raw[MAX_ADDR_RAW_SIZE] = {0};

  // p2pkh
  if (signature[0] >= 27 && signature[0] <= 34) {
    size_t len = 0;
    if (coin->cashaddr_prefix) {
      if (!cash_addr_decode(addr_raw, &len, coin->cashaddr_prefix, address)) {
        return 2;
      }
    } else {
      len = base58_decode_check(address, coin->curve->hasher_base58, addr_raw,
                                MAX_ADDR_RAW_SIZE);
    }
    ecdsa_get_address_raw(pubkey, coin->address_type,
                          coin->curve->hasher_pubkey, recovered_raw);
    if (memcmp(recovered_raw, addr_raw, len) != 0 ||
        len != address_prefix_bytes_len(coin->address_type) + 20) {
      return 2;
    }
  } else
      // segwit-in-p2sh
      if (signature[0] >= 35 && signature[0] <= 38) {
    size_t len = base58_decode_check(address, coin->curve->hasher_base58,
                                     addr_raw, MAX_ADDR_RAW_SIZE);
    ecdsa_get_address_segwit_p2sh_raw(pubkey, coin->address_type_p2sh,
                                      coin->curve->hasher_pubkey,
                                      recovered_raw);
    if (memcmp(recovered_raw, addr_raw, len) != 0 ||
        len != address_prefix_bytes_len(coin->address_type_p2sh) + 20) {
      return 2;
    }
  } else
      // segwit
      if (signature[0] >= 39 && signature[0] <= 42) {
    int witver = 0;
    size_t len = 0;
    if (!coin->bech32_prefix ||
        !segwit_addr_decode(&witver, recovered_raw, &len, coin->bech32_prefix,
                            address)) {
      return 4;
    }
    if (witver != 0 || len != 20) {
      return 2;
    }
    ecdsa_get_pubkeyhash(pubkey, coin->curve->hasher_pubkey, addr_raw);
    if (memcmp(recovered_raw, addr_raw, len)) {
      return 2;
    }
  } else
      // taproot
      if (signature[0] >= 43 && signature[0] <= 46) {
    int witver = 0;
    size_t len = 0;
    if (!coin->bech32_prefix ||
        !segwit_addr_decode(&witver, recovered_raw, &len, coin->bech32_prefix,
                            address)) {
      return 4;
    }
    if (witver != 1 || len != 32) {
      return 2;
    }
    uint8_t tweaked_pubkey[32];
    // TODO: ecdsa_tweak_pubkey(pubkey, tweaked_pubkey);
    if (memcmp(tweaked_pubkey, addr_raw, len) != 0) {
      return 2;
    }
  } else {
    return 4;
  }

  return 0;
}

/* ECIES disabled
int cryptoMessageEncrypt(curve_point *pubkey, const uint8_t *msg, size_t
msg_size, bool display_only, uint8_t *nonce, size_t *nonce_len, uint8_t
*payload, size_t *payload_len, uint8_t *hmac, size_t *hmac_len, const uint8_t
*privkey, const uint8_t *address_raw)
{
        if (privkey && address_raw) { // signing == true
                HDNode node = {0};
                payload[0] = display_only ? 0x81 : 0x01;
                uint32_t l = ser_length(msg_size, payload + 1);
                memcpy(payload + 1 + l, msg, msg_size);
                memcpy(payload + 1 + l + msg_size, address_raw, 21);
                hdnode_from_xprv(0, 0, 0, privkey, privkey, SECP256K1_NAME,
&node); if (cryptoMessageSign(&node, msg, msg_size, payload + 1 + l + msg_size +
21) != 0) { return 1;
                }
                *payload_len = 1 + l + msg_size + 21 + 65;
        } else {
                payload[0] = display_only ? 0x80 : 0x00;
                uint32_t l = ser_length(msg_size, payload + 1);
                memcpy(payload + 1 + l, msg, msg_size);
                *payload_len = 1 + l + msg_size;
        }
        // generate random nonce
        curve_point R = {0};
        bignum256 k = {0};
        if (generate_k_random(&secp256k1, &k) != 0) {
                return 2;
        }
        // compute k*G
        scalar_multiply(&secp256k1, &k, &R);
        nonce[0] = 0x02 | (R.y.val[0] & 0x01);
        bn_write_be(&R.x, nonce + 1);
        *nonce_len = 33;
        // compute shared secret
        point_multiply(&secp256k1, &k, pubkey, &R);
        uint8_t shared_secret[33] = {0};
        shared_secret[0] = 0x02 | (R.y.val[0] & 0x01);
        bn_write_be(&R.x, shared_secret + 1);
        // generate keying bytes
        uint8_t keying_bytes[80] = {0};
        uint8_t salt[22 + 33] = {0};
        memcpy(salt, "Bitcoin Secure Message", 22);
        memcpy(salt + 22, nonce, 33);
        pbkdf2_hmac_sha256(shared_secret, 33, salt, 22 + 33, 2048, keying_bytes,
80);
        // encrypt payload
        aes_encrypt_ctx ctx = {0};
        aes_encrypt_key256(keying_bytes, &ctx);
        aes_cfb_encrypt(payload, payload, *payload_len, keying_bytes + 64,
&ctx);
        // compute hmac
        uint8_t out[32] = {0};
        hmac_sha256(keying_bytes + 32, 32, payload, *payload_len, out);
        memcpy(hmac, out, 8);
        *hmac_len = 8;

        return 0;
}

int cryptoMessageDecrypt(curve_point *nonce, uint8_t *payload, size_t
payload_len, const uint8_t *hmac, size_t hmac_len, const uint8_t *privkey,
uint8_t *msg, size_t *msg_len, bool *display_only, bool *signing, uint8_t
*address_raw)
{
        if (hmac_len != 8) {
                return 1;
        }
        // compute shared secret
        curve_point R = {0};
        bignum256 k = {0};
        bn_read_be(privkey, &k);
        point_multiply(&secp256k1, &k, nonce, &R);
        uint8_t shared_secret[33] = {0};
        shared_secret[0] = 0x02 | (R.y.val[0] & 0x01);
        bn_write_be(&R.x, shared_secret + 1);
        // generate keying bytes
        uint8_t keying_bytes[80] = {0};
        uint8_t salt[22 + 33] = {0};
        memcpy(salt, "Bitcoin Secure Message", 22);
        salt[22] = 0x02 | (nonce->y.val[0] & 0x01);
        bn_write_be(&(nonce->x), salt + 23);
        pbkdf2_hmac_sha256(shared_secret, 33, salt, 22 + 33, 2048, keying_bytes,
80);
        // compute hmac
        uint8_t out[32] = {0};
        hmac_sha256(keying_bytes + 32, 32, payload, payload_len, out);
        if (memcmp(hmac, out, 8) != 0) {
                return 2;
        }
        // decrypt payload
        aes_encrypt_ctx ctx = {0};
        aes_encrypt_key256(keying_bytes, &ctx);
        aes_cfb_decrypt(payload, payload, payload_len, keying_bytes + 64, &ctx);
        // check first byte
        if (payload[0] != 0x00 && payload[0] != 0x01 && payload[0] != 0x80 &&
payload[0] != 0x81) { return 3;
        }
        *signing = payload[0] & 0x01;
        *display_only = payload[0] & 0x80;
        uint32_t l = 0; uint32_t o = 0;
        l = deser_length(payload + 1, &o);
        if (*signing) {
                // FIXME: assumes a raw address is 21 bytes (also below).
                if (1 + l + o + 21 + 65 != payload_len) {
                        return 4;
                }
                // FIXME: cryptoMessageVerify changed to take the address_type
as a parameter. if (cryptoMessageVerify(payload + 1 + l, o, payload + 1 + l + o,
payload + 1 + l + o + 21) != 0) { return 5;
                }
                memcpy(address_raw, payload + 1 + l + o, 21);
        } else {
                if (1 + l + o != payload_len) {
                        return 4;
                }
        }
        memcpy(msg, payload + 1 + l, o);
        *msg_len = o;
        return 0;
}
*/

const HDNode *cryptoMultisigPubkey(const CoinInfo *coin,
                                   const MultisigRedeemScriptType *multisig,
                                   uint32_t index) {
  const HDNodeType *node_ptr = NULL;
  const uint32_t *address_n = NULL;
  uint32_t address_n_count = 0;
  if (multisig->nodes_count) {  // use multisig->nodes
    if (index >= multisig->nodes_count) {
      return 0;
    }
    node_ptr = &(multisig->nodes[index]);
    address_n = multisig->address_n;
    address_n_count = multisig->address_n_count;
  } else if (multisig->pubkeys_count) {  // use multisig->pubkeys
    if (index >= multisig->pubkeys_count) {
      return 0;
    }
    node_ptr = &(multisig->pubkeys[index].node);
    address_n = multisig->pubkeys[index].address_n;
    address_n_count = multisig->pubkeys[index].address_n_count;
  } else {
    return 0;
  }
  if (node_ptr->chain_code.size != 32) return 0;
  if (node_ptr->public_key.size != 33) return 0;
  static HDNode node;
  if (!hdnode_from_xpub(node_ptr->depth, node_ptr->child_num,
                        node_ptr->chain_code.bytes, node_ptr->public_key.bytes,
                        coin->curve_name, &node)) {
    return 0;
  }
  layoutProgressUpdate(true);
  for (uint32_t i = 0; i < address_n_count; i++) {
    if (!hdnode_public_ckd(&node, address_n[i])) {
      return 0;
    }
    layoutProgressUpdate(true);
  }
  return &node;
}

uint32_t cryptoMultisigPubkeyCount(const MultisigRedeemScriptType *multisig) {
  return multisig->nodes_count ? multisig->nodes_count
                               : multisig->pubkeys_count;
}

int cryptoMultisigPubkeyIndex(const CoinInfo *coin,
                              const MultisigRedeemScriptType *multisig,
                              const uint8_t *pubkey) {
  for (size_t i = 0; i < cryptoMultisigPubkeyCount(multisig); i++) {
    const HDNode *pubnode = cryptoMultisigPubkey(coin, multisig, i);
    if (pubnode && memcmp(pubnode->public_key, pubkey, 33) == 0) {
      return i;
    }
  }
  return -1;
}

int cryptoMultisigFingerprint(const MultisigRedeemScriptType *multisig,
                              uint8_t *hash) {
  static const HDNodeType *pubnodes[15], *swap;
  const uint32_t n = cryptoMultisigPubkeyCount(multisig);
  if (n < 1 || n > 15) {
    return 0;
  }
  if (multisig->m < 1 || multisig->m > 15) {
    return 0;
  }
  for (uint32_t i = 0; i < n; i++) {
    if (multisig->nodes_count) {  // use multisig->nodes
      pubnodes[i] = &(multisig->nodes[i]);
    } else if (multisig->pubkeys_count) {  // use multisig->pubkeys
      pubnodes[i] = &(multisig->pubkeys[i].node);
    } else {
      return 0;
    }
  }
  for (uint32_t i = 0; i < n; i++) {
    if (pubnodes[i]->public_key.size != 33) return 0;
    if (pubnodes[i]->chain_code.size != 32) return 0;
  }
  // minsort according to pubkey
  for (uint32_t i = 0; i < n - 1; i++) {
    for (uint32_t j = n - 1; j > i; j--) {
      if (memcmp(pubnodes[i]->public_key.bytes, pubnodes[j]->public_key.bytes,
                 33) > 0) {
        swap = pubnodes[i];
        pubnodes[i] = pubnodes[j];
        pubnodes[j] = swap;
      }
    }
  }
  // hash sorted nodes
  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);
  sha256_Update(&ctx, (const uint8_t *)&(multisig->m), sizeof(uint32_t));
  for (uint32_t i = 0; i < n; i++) {
    sha256_Update(&ctx, (const uint8_t *)&(pubnodes[i]->depth),
                  sizeof(uint32_t));
    sha256_Update(&ctx, (const uint8_t *)&(pubnodes[i]->fingerprint),
                  sizeof(uint32_t));
    sha256_Update(&ctx, (const uint8_t *)&(pubnodes[i]->child_num),
                  sizeof(uint32_t));
    sha256_Update(&ctx, pubnodes[i]->chain_code.bytes, 32);
    sha256_Update(&ctx, pubnodes[i]->public_key.bytes, 33);
  }
  sha256_Update(&ctx, (const uint8_t *)&n, sizeof(uint32_t));
  sha256_Final(&ctx, hash);
  layoutProgressUpdate(true);
  return 1;
}

int cryptoIdentityFingerprint(const IdentityType *identity, uint8_t *hash) {
  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);
  sha256_Update(&ctx, (const uint8_t *)&(identity->index), sizeof(uint32_t));
  if (identity->has_proto && identity->proto[0]) {
    sha256_Update(&ctx, (const uint8_t *)(identity->proto),
                  strlen(identity->proto));
    sha256_Update(&ctx, (const uint8_t *)"://", 3);
  }
  if (identity->has_user && identity->user[0]) {
    sha256_Update(&ctx, (const uint8_t *)(identity->user),
                  strlen(identity->user));
    sha256_Update(&ctx, (const uint8_t *)"@", 1);
  }
  if (identity->has_host && identity->host[0]) {
    sha256_Update(&ctx, (const uint8_t *)(identity->host),
                  strlen(identity->host));
  }
  if (identity->has_port && identity->port[0]) {
    sha256_Update(&ctx, (const uint8_t *)":", 1);
    sha256_Update(&ctx, (const uint8_t *)(identity->port),
                  strlen(identity->port));
  }
  if (identity->has_path && identity->path[0]) {
    sha256_Update(&ctx, (const uint8_t *)(identity->path),
                  strlen(identity->path));
  }
  sha256_Final(&ctx, hash);
  return 1;
}

static bool check_cointype(const CoinInfo *coin, uint32_t slip44, bool full) {
#if BITCOIN_ONLY
  (void)full;
#else
  if (!full) {
    // Some wallets such as Electron-Cash (BCH) store coins on Bitcoin paths.
    // We can allow spending these coins from Bitcoin paths if the coin has
    // implemented strong replay protection via SIGHASH_FORKID. However, we
    // cannot allow spending any testnet coins from Bitcoin paths, because
    // otherwise an attacker could trick the user into spending BCH on a Bitcoin
    // path by signing a seemingly harmless BCH Testnet transaction.
    if (slip44 == SLIP44_BITCOIN && coin->has_fork_id &&
        coin->coin_type != SLIP44_TESTNET) {
      return true;
    }
  }
#endif
  return coin->coin_type == slip44;
}

bool coin_path_check(const CoinInfo *coin, InputScriptType script_type,
                     uint32_t address_n_count, const uint32_t *address_n,
                     bool has_multisig, CoinPathCheckLevel level) {
  // For level BASIC this function checks that a coin without strong replay
  // protection doesn't access paths that are known to be used by another coin.
  // Used by SignTx to ensure that a user cannot be coerced into signing a
  // testnet transaction or a Litecoin transaction which in fact spends Bitcoin.
  // For level KNOWN this function checks that the path is a recognized path for
  // the given coin. Used by GetAddress to prevent ransom attacks where a user
  // could be coerced to use an address with an unenumerable path.
  // For level SCRIPT_TYPE this function makes the same checks as in level
  // KNOWN, but includes script type checks.

  const bool check_known = (level >= CoinPathCheckLevel_KNOWN);
  const bool check_script_type = (level >= CoinPathCheckLevel_SCRIPT_TYPE);

  bool valid = true;
  // m/44' : BIP44 Legacy
  // m / purpose' / coin_type' / account' / change / address_index
  if (address_n_count > 0 && address_n[0] == (0x80000000 + 44)) {
    if (check_known) {
      valid = valid && (address_n_count == 5);
    } else {
      valid = valid && (address_n_count >= 2);
    }
    valid = valid && check_cointype(coin, address_n[1], check_known);
    if (check_script_type) {
      valid = valid && (script_type == InputScriptType_SPENDADDRESS);
      valid = valid && (!has_multisig);
    }
    if (check_known) {
      valid = valid && ((address_n[2] & 0x80000000) == 0x80000000);
      valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
      valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
      valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  if (address_n_count > 0 && address_n[0] == (0x80000000 + 45)) {
    if (check_script_type) {
      valid = valid && has_multisig;
    }

    if (address_n_count == 4) {
      // m/45' - BIP45 Copay Abandoned Multisig P2SH
      // m / purpose' / cosigner_index / change / address_index
      // Patterns without a coin_type field must be treated as Bitcoin paths.
      valid = valid && check_cointype(coin, SLIP44_BITCOIN, check_known);
      if (check_script_type) {
        valid = valid && (script_type == InputScriptType_SPENDMULTISIG);
      }
      if (check_known) {
        valid = valid && (address_n[1] <= 100);
        valid = valid && (address_n[2] <= PATH_MAX_CHANGE);
        valid = valid && (address_n[3] <= PATH_MAX_ADDRESS_INDEX);
      }
    } else if (address_n_count == 5) {
      // Unchained Capital compatibility pattern. Will be removed in the
      // future.
      // m / 45' / coin_type' / account' / [0-1000000] / address_index
      valid = valid && check_cointype(coin, address_n[1], check_known);
      if (check_script_type) {
        valid = valid && (script_type == InputScriptType_SPENDADDRESS ||
                          script_type == InputScriptType_SPENDMULTISIG);
      }
      if (check_known) {
        valid = valid && ((address_n[2] & 0x80000000) == 0x80000000);
        valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
        valid = valid && (address_n[3] <= 1000000);
        valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
      }
    } else if (address_n_count == 6) {
      // Unchained Capital compatibility pattern. Will be removed in the
      // future.
      // m/45'/coin_type'/account'/[0-1000000]/change/address_index
      // m/45'/coin_type/account/[0-1000000]/change/address_index
      valid =
          valid && check_cointype(coin, 0x80000000 | address_n[1], check_known);
      if (check_script_type) {
        valid = valid && (script_type == InputScriptType_SPENDADDRESS ||
                          script_type == InputScriptType_SPENDMULTISIG);
      }
      if (check_known) {
        valid = valid &&
                ((address_n[1] & 0x80000000) == (address_n[2] & 0x80000000));
        valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
        valid = valid && (address_n[3] <= 1000000);
        valid = valid && (address_n[4] <= PATH_MAX_CHANGE);
        valid = valid && (address_n[5] <= PATH_MAX_ADDRESS_INDEX);
      }
    } else {
      if (check_known) {
        return false;
      }
    }

    return valid;
  }

  // m/48' - BIP48 Copay Multisig P2SH
  // m / purpose' / coin_type' / account' / change / address_index
  // Electrum:
  // m / purpose' / coin_type' / account' / type' / change / address_index
  if (address_n_count > 0 && address_n[0] == (0x80000000 + 48)) {
    if (check_known) {
      valid = valid && (address_n_count == 5 || address_n_count == 6);
    } else {
      valid = valid && (address_n_count >= 2);
    }
    valid = valid && check_cointype(coin, address_n[1], check_known);
    if (check_script_type) {
      valid = valid && has_multisig;
      // we do not support Multisig with Taproot yet
      valid = valid && (script_type == InputScriptType_SPENDMULTISIG ||
                        script_type == InputScriptType_SPENDP2SHWITNESS ||
                        script_type == InputScriptType_SPENDWITNESS);
    }
    if (check_known) {
      valid = valid && ((address_n[2] & 0x80000000) == 0x80000000);
      valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
      if (address_n_count == 5) {
        valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
        valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
      } else if (address_n_count == 6) {
        valid = valid && ((address_n[3] & 0x80000000) == 0x80000000);
        valid = valid && ((address_n[3] & 0x7fffffff) <= 3);
        valid = valid && (address_n[4] <= PATH_MAX_CHANGE);
        valid = valid && (address_n[5] <= PATH_MAX_ADDRESS_INDEX);
      } else {
        return false;
      }
    }
    return valid;
  }

  // m/49' : BIP49 SegWit
  // m / purpose' / coin_type' / account' / change / address_index
  if (address_n_count > 0 && address_n[0] == (0x80000000 + 49)) {
    valid = valid && coin->has_segwit;
    if (check_known) {
      valid = valid && (address_n_count == 5);
    } else {
      valid = valid && (address_n_count >= 2);
    }
    valid = valid && check_cointype(coin, address_n[1], check_known);
    if (check_script_type) {
      valid = valid && (script_type == InputScriptType_SPENDP2SHWITNESS);
    }
    if (check_known) {
      valid = valid && ((address_n[2] & 0x80000000) == 0x80000000);
      valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
      valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
      valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  // m/84' : BIP84 Native SegWit
  // m / purpose' / coin_type' / account' / change / address_index
  if (address_n_count > 0 && address_n[0] == (0x80000000 + 84)) {
    valid = valid && coin->has_segwit;
    valid = valid && (coin->bech32_prefix != NULL);
    if (check_known) {
      valid = valid && (address_n_count == 5);
    } else {
      valid = valid && (address_n_count >= 2);
    }
    valid = valid && check_cointype(coin, address_n[1], check_known);
    if (check_script_type) {
      valid = valid && (script_type == InputScriptType_SPENDWITNESS);
    }
    if (check_known) {
      valid = valid && ((address_n[2] & 0x80000000) == 0x80000000);
      valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
      valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
      valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  // m/86' : BIP86 Taproot
  // m / purpose' / coin_type' / account' / change / address_index
  if (address_n_count > 0 && address_n[0] == (0x80000000 + 86)) {
    valid = valid && coin->has_taproot;
    valid = valid && (coin->bech32_prefix != NULL);
    if (check_known) {
      valid = valid && (address_n_count == 5);
    } else {
      valid = valid && (address_n_count >= 2);
    }
    valid = valid && check_cointype(coin, address_n[1], check_known);
    if (check_script_type) {
      valid = valid && (script_type == InputScriptType_SPENDTAPROOT);
    }
    if (check_known) {
      valid = valid && ((address_n[2] & 0x80000000) == 0x80000000);
      valid = valid && ((address_n[2] & 0x7fffffff) <= PATH_MAX_ACCOUNT);
      valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
      valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  // Green Address compatibility pattern. Will be removed in the future.
  // m / [1,4] / address_index
  if (address_n_count > 0 && (address_n[0] == 1 || address_n[0] == 4)) {
    valid = valid && (coin->coin_type == SLIP44_BITCOIN);
    if (check_known) {
      valid = valid && (address_n_count == 2);
      valid = valid && (address_n[1] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  // Green Address compatibility pattern. Will be removed in the future.
  // m / 3' / [1-100]' / [1,4] / address_index
  if (address_n_count > 0 && address_n[0] == (0x80000000 + 3)) {
    valid = valid && (coin->coin_type == SLIP44_BITCOIN);
    if (check_known) {
      valid = valid && (address_n_count == 4);
      valid = valid && ((address_n[1] & 0x80000000) == 0x80000000);
      valid = valid && ((address_n[1] & 0x7fffffff) <= 100);
      valid = valid && (address_n[2] == 1 || address_n[2] == 4);
      valid = valid && (address_n[3] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  // Green Address compatibility patterns. Will be removed in the future.
  // m / 1195487518
  // m / 1195487518 / 6 / address_index
  if (address_n_count > 0 && address_n[0] == 1195487518) {
    valid = valid && (coin->coin_type == SLIP44_BITCOIN);
    if (check_known) {
      if (address_n_count == 3) {
        valid = valid && (address_n[1] == 6);
        valid = valid && (address_n[2] <= PATH_MAX_ADDRESS_INDEX);
      } else if (address_n_count != 1) {
        return false;
      }
    }
    return valid;
  }

  // Casa compatibility pattern. Will be removed in the future.
  // m / 49 / coin_type / account / change / address_index
  if (address_n_count > 0 && address_n[0] == 49) {
    if (check_known) {
      valid = valid && (address_n_count == 5);
    } else {
      valid = valid && (address_n_count >= 2);
    }
    valid =
        valid && check_cointype(coin, 0x80000000 | address_n[1], check_known);
    if (check_script_type) {
      valid = valid && (script_type == InputScriptType_SPENDP2SHWITNESS);
    }
    if (check_known) {
      valid = valid && ((address_n[1] & 0x80000000) == 0);
      valid = valid && (address_n[2] <= PATH_MAX_ACCOUNT);
      valid = valid && (address_n[3] <= PATH_MAX_CHANGE);
      valid = valid && (address_n[4] <= PATH_MAX_ADDRESS_INDEX);
    }
    return valid;
  }

  // we allow unknown paths only when a full check is not required
  return level == CoinPathCheckLevel_BASIC;
}
