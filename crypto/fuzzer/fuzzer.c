/**
 * Copyright (c) 2020-2021 Christian Reitter
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

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// includes for potential target functions
// based on test_check.c
#include "address.h"
#include "aes/aes.h"
#include "base32.h"
#include "base58.h"
#include "bignum.h"
#include "bip32.h"
#include "bip39.h"
#include "blake256.h"
#include "blake2b.h"
#include "blake2s.h"
#include "chacha_drbg.h"
#include "curves.h"
#include "ecdsa.h"
#include "ed25519-donna/ed25519-donna.h"
#include "ed25519-donna/ed25519-keccak.h"
#include "ed25519-donna/ed25519.h"
#include "hmac_drbg.h"
#include "memzero.h"
#include "monero/monero.h"
#include "nem.h"
#include "nist256p1.h"
#include "pbkdf2.h"
#include "rand.h"
#include "rc4.h"
#include "rfc6979.h"
#include "schnorr.h"
#include "script.h"
#include "secp256k1.h"
#include "sha2.h"
#include "sha3.h"
#include "shamir.h"
#include "slip39.h"
#include "slip39_wordlist.h"

/* fuzzer input data handling */
const uint8_t *fuzzer_ptr;
size_t fuzzer_length;

const uint8_t *fuzzer_input(size_t len) {
  if (fuzzer_length < len) {
    fuzzer_length = 0;
    return NULL;
  }
  const uint8_t *result = fuzzer_ptr;
  fuzzer_length -= len;
  fuzzer_ptr += len;
  return result;
}

/* fuzzer state handling */
void fuzzer_reset_state(void) {
  // reset the PRNGs to make individual fuzzer runs deterministic
  srand(0);
  random_reseed(0);
}

/* individual fuzzer harness functions */

int fuzz_bn_format(void) {
  bignum256 target_bignum;
  // we need some amount of data, bail if the input is too short
  if (fuzzer_length < sizeof(target_bignum)) {
    return 0;
  }

  char buf[512] = {0};
  int r;

  // mutate the struct contents
  memcpy(&target_bignum, fuzzer_ptr, sizeof(target_bignum));
  fuzzer_input(sizeof(target_bignum));

  uint8_t prefixlen = 0;
  if (fuzzer_length < 1) {
    return 0;
  }
  memcpy(&prefixlen, fuzzer_input(1), 1);
  char prefix[prefixlen];
  memset(&prefix, 0, prefixlen);

  if (prefixlen > 0 && prefixlen <= 128 && prefixlen <= fuzzer_length) {
    memcpy(&prefix, fuzzer_input(prefixlen), prefixlen);
    // force null termination
    prefix[prefixlen - 1] = 0;
  } else {
    return 0;
  }
  // TODO fuzzer idea: allow prefix=NULL

  uint8_t suffixlen = 0;
  if (fuzzer_length < 1) {
    return 0;
  }
  memcpy(&suffixlen, fuzzer_input(1), 1);
  char suffix[suffixlen];
  memset(&suffix, 0, suffixlen);

  if (suffixlen > 0 && suffixlen <= 128 && suffixlen <= fuzzer_length) {
    memcpy(&suffix, fuzzer_input(suffixlen), suffixlen);
    // force null termination
    suffix[suffixlen - 1] = 0;
  } else {
    return 0;
  }
  // TODO fuzzer idea: allow suffix=NULL
  uint32_t decimals = 0;
  int32_t exponent = 0;
  bool trailing = false;

  if (fuzzer_length >= 9) {
    memcpy(&decimals, fuzzer_input(4), 4);
    memcpy(&exponent, fuzzer_input(4), 4);

    trailing = (fuzzer_input(1)[0] & 1);
  } else {
    return 0;
  }

  r = bn_format(&target_bignum, prefix, suffix, decimals, exponent, trailing,
                buf, sizeof(buf));
  return 0;
}

// arbitrarily chosen maximum size
#define BASE32_DECODE_MAX_INPUT_LEN 512

int fuzz_base32_decode(void) {
  if (fuzzer_length < 2 || fuzzer_length > BASE32_DECODE_MAX_INPUT_LEN) {
    return 0;
  }

  char in_buffer[BASE32_DECODE_MAX_INPUT_LEN] = {0};
  uint8_t out_buffer[BASE32_DECODE_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);

  // mutate in_buffer
  size_t raw_inlen = fuzzer_length;
  memcpy(&in_buffer, fuzzer_ptr, raw_inlen);
  fuzzer_input(raw_inlen);

  // null-terminate input buffer to prevent issues with strlen()
  in_buffer[BASE32_DECODE_MAX_INPUT_LEN - 1] = 0;
  size_t inlen = strlen(in_buffer);

  base32_decode(in_buffer, inlen, out_buffer, outlen, BASE32_ALPHABET_RFC4648);
  return 0;
}

// arbitrarily chosen maximum size
#define BASE32_ENCODE_MAX_INPUT_LEN 512

int fuzz_base32_encode(void) {
  if (fuzzer_length > BASE32_ENCODE_MAX_INPUT_LEN) {
    return 0;
  }

  uint8_t in_buffer[BASE32_ENCODE_MAX_INPUT_LEN] = {0};
  char out_buffer[BASE32_ENCODE_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);

  // mutate in_buffer
  size_t raw_inlen = fuzzer_length;
  memcpy(&in_buffer, fuzzer_ptr, raw_inlen);
  fuzzer_input(raw_inlen);

  base32_encode(in_buffer, raw_inlen, out_buffer, outlen,
                BASE32_ALPHABET_RFC4648);
  return 0;
}

// internal limit is 128, try some extra bytes
#define BASE58_ENCODE_MAX_INPUT_LEN 140

int fuzz_base58_encode_check(void) {
  if (fuzzer_length > BASE58_ENCODE_MAX_INPUT_LEN) {
    return 0;
  }

  uint8_t in_buffer[BASE58_ENCODE_MAX_INPUT_LEN] = {0};
  char out_buffer[BASE58_ENCODE_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);

  // mutate in_buffer
  size_t raw_inlen = fuzzer_length;
  memcpy(&in_buffer, fuzzer_ptr, raw_inlen);
  fuzzer_input(raw_inlen);

  // run multiple hasher variants for the same input
  base58_encode_check(in_buffer, raw_inlen, HASHER_SHA2D, out_buffer, outlen);
  base58_encode_check(in_buffer, raw_inlen, HASHER_BLAKED, out_buffer, outlen);
  base58_encode_check(in_buffer, raw_inlen, HASHER_GROESTLD_TRUNC, out_buffer,
                      outlen);
  base58_encode_check(in_buffer, raw_inlen, HASHER_SHA3K, out_buffer, outlen);
  return 0;
}

// internal limit is 128, try some extra bytes
#define BASE58_DECODE_MAX_INPUT_LEN 140

int fuzz_base58_decode_check(void) {
  if (fuzzer_length > BASE58_DECODE_MAX_INPUT_LEN) {
    return 0;
  }

  // with null terminator
  uint8_t in_buffer[BASE58_DECODE_MAX_INPUT_LEN + 1] = {0};
  uint8_t out_buffer[BASE58_DECODE_MAX_INPUT_LEN] = {0};

  // mutate in_buffer
  size_t raw_inlen = fuzzer_length;
  memcpy(&in_buffer, fuzzer_ptr, raw_inlen);
  fuzzer_input(raw_inlen);

  // run multiple hasher variants for the same input
  base58_decode_check((const char *)in_buffer, HASHER_SHA2D, out_buffer,
                      MAX_ADDR_RAW_SIZE);
  base58_decode_check((const char *)in_buffer, HASHER_BLAKED, out_buffer,
                      MAX_ADDR_RAW_SIZE);
  base58_decode_check((const char *)in_buffer, HASHER_GROESTLD_TRUNC,
                      out_buffer, MAX_ADDR_RAW_SIZE);
  base58_decode_check((const char *)in_buffer, HASHER_SHA3K, out_buffer,
                      MAX_ADDR_RAW_SIZE);
  return 0;
}

// arbitrarily chosen maximum size
#define XMR_BASE58_ADDR_DECODE_MAX_INPUT_LEN 512

int fuzz_xmr_base58_addr_decode_check(void) {
  if (fuzzer_length > XMR_BASE58_ADDR_DECODE_MAX_INPUT_LEN) {
    return 0;
  }

  char in_buffer[XMR_BASE58_ADDR_DECODE_MAX_INPUT_LEN] = {0};
  char out_buffer[XMR_BASE58_ADDR_DECODE_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);

  // mutate in_buffer
  size_t raw_inlen = fuzzer_length;
  memcpy(&in_buffer, fuzzer_ptr, raw_inlen);
  fuzzer_input(raw_inlen);

  uint64_t tag;
  xmr_base58_addr_decode_check(in_buffer, raw_inlen, &tag, out_buffer, outlen);
  return 0;
}

// arbitrarily chosen maximum size
#define XMR_BASE58_ADDR_ENCODE_MAX_INPUT_LEN 512

int fuzz_xmr_base58_addr_encode_check(void) {
  uint64_t tag_in;
  size_t tag_size = sizeof(tag_in);
  if (fuzzer_length < tag_size ||
      fuzzer_length > XMR_BASE58_ADDR_ENCODE_MAX_INPUT_LEN) {
    return 0;
  }

  uint8_t in_buffer[XMR_BASE58_ADDR_ENCODE_MAX_INPUT_LEN] = {0};
  char out_buffer[XMR_BASE58_ADDR_ENCODE_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);

  // mutate tag_in
  memcpy(&tag_in, fuzzer_ptr, tag_size);
  fuzzer_input(tag_size);

  // mutate in_buffer
  memcpy(&in_buffer, fuzzer_ptr, fuzzer_length);
  size_t raw_inlen = fuzzer_length;
  fuzzer_input(raw_inlen);

  xmr_base58_addr_encode_check(tag_in, in_buffer, raw_inlen, out_buffer,
                               outlen);
  return 0;
}

// arbitrarily chosen maximum size
#define XMR_SERIALIZE_VARINT_MAX_INPUT_LEN 128

int fuzz_xmr_serialize_varint(void) {
  uint64_t varint_in;
  size_t varint_in_size = sizeof(varint_in);
  if (fuzzer_length < varint_in_size ||
      fuzzer_length > XMR_SERIALIZE_VARINT_MAX_INPUT_LEN) {
    return 0;
  }

  uint8_t in_buffer[XMR_SERIALIZE_VARINT_MAX_INPUT_LEN] = {0};
  uint8_t out_buffer[XMR_SERIALIZE_VARINT_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);
  uint64_t varint_out = 0;

  // mutate varint_in
  memcpy(&varint_in, fuzzer_ptr, varint_in_size);
  fuzzer_input(varint_in_size);

  // mutate in_buffer
  memcpy(&in_buffer, fuzzer_ptr, fuzzer_length);
  size_t raw_inlen = fuzzer_length;
  fuzzer_input(raw_inlen);

  // call the actual xmr functions
  xmr_size_varint(varint_in);
  xmr_write_varint(out_buffer, outlen, varint_in);
  xmr_read_varint(in_buffer, raw_inlen, &varint_out);

  return 0;
}

// arbitrarily chosen maximum size
#define NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN 128

int fuzz_nem_validate_address(void) {
  if (fuzzer_length < (1 + 1) ||
      fuzzer_length > NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN) {
    return 0;
  }

  char in_buffer[NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN] = {0};

  uint8_t network = *fuzzer_ptr;
  fuzzer_input(1);

  // mutate the buffer with the remaining fuzzer input data
  memcpy(&in_buffer, fuzzer_ptr, fuzzer_length);
  size_t raw_inlen = fuzzer_length;
  fuzzer_input(raw_inlen);
  // TODO potential bug: is it clearly specified that the address has to be null
  // terminated?
  in_buffer[NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN - 1] = 0;

  nem_validate_address(in_buffer, network);

  return 0;
}

int fuzz_nem_get_address(void) {
  unsigned char ed25519_public_key[32] = {0};
  uint32_t network = 0;

  if (fuzzer_length != (sizeof(ed25519_public_key) + sizeof(network))) {
    return 0;
  }

  char address[NEM_ADDRESS_SIZE + 1] = {0};

  memcpy(ed25519_public_key, fuzzer_input(32), 32);
  memcpy(&network, fuzzer_input(4), 4);

  nem_get_address(ed25519_public_key, network, address);

  // TODO check return address for memory info leakage?
  return 0;
}

int fuzz_xmr_get_subaddress_secret_key(void) {
  bignum256modm m = {0};
  uint32_t major = 0;
  uint32_t minor = 0;
  if (fuzzer_length != (sizeof(bignum256modm) + 2 * sizeof(uint32_t))) {
    return 0;
  }

  bignum256modm output = {0};

  memcpy(m, fuzzer_input(sizeof(bignum256modm)), sizeof(bignum256modm));
  memcpy(&major, fuzzer_input(sizeof(uint32_t)), sizeof(uint32_t));
  memcpy(&minor, fuzzer_input(sizeof(uint32_t)), sizeof(uint32_t));

  xmr_get_subaddress_secret_key(output, major, minor, m);

  return 0;
}

int fuzz_xmr_derive_private_key(void) {
  bignum256modm base = {0};
  ge25519 deriv = {0};
  uint32_t idx = 0;

  if (fuzzer_length !=
      (sizeof(bignum256modm) + sizeof(ge25519) + sizeof(uint32_t))) {
    return 0;
  }

  memcpy(base, fuzzer_input(sizeof(bignum256modm)), sizeof(bignum256modm));
  memcpy(&deriv, fuzzer_input(sizeof(ge25519)), sizeof(ge25519));
  memcpy(&idx, fuzzer_input(sizeof(uint32_t)), sizeof(uint32_t));

  bignum256modm output = {0};

  xmr_derive_private_key(output, &deriv, idx, base);

  return 0;
}

int fuzz_xmr_derive_public_key(void) {
  ge25519 base = {0};
  ge25519 deriv = {0};
  uint32_t idx = 0;

  if (fuzzer_length != (2 * sizeof(ge25519) + sizeof(uint32_t))) {
    return 0;
  }

  memcpy(&base, fuzzer_input(sizeof(ge25519)), sizeof(ge25519));
  memcpy(&deriv, fuzzer_input(sizeof(ge25519)), sizeof(ge25519));
  memcpy(&idx, fuzzer_input(sizeof(uint32_t)), sizeof(uint32_t));

  ge25519 output = {0};

  xmr_derive_public_key(&output, &deriv, idx, &base);

  return 0;
}

#define SHAMIR_MAX_SHARE_COUNT 16
#define SHAMIR_MAX_DATA_LEN (SHAMIR_MAX_SHARE_COUNT * SHAMIR_MAX_LEN)
int fuzz_shamir_interpolate(void) {
  if (fuzzer_length != (2 * sizeof(uint8_t) + SHAMIR_MAX_SHARE_COUNT +
                        SHAMIR_MAX_DATA_LEN + sizeof(size_t))) {
    return 0;
  }

  uint8_t result[SHAMIR_MAX_LEN] = {0};
  uint8_t result_index = 0;
  uint8_t share_indices[SHAMIR_MAX_SHARE_COUNT] = {0};
  uint8_t share_values_content[SHAMIR_MAX_SHARE_COUNT][SHAMIR_MAX_LEN] = {0};
  const uint8_t *share_values[SHAMIR_MAX_SHARE_COUNT] = {0};
  uint8_t share_count = 0;
  size_t len = 0;

  for (size_t i = 0; i < SHAMIR_MAX_SHARE_COUNT; i++) {
    share_values[i] = share_values_content[i];
  }

  memcpy(&result_index, fuzzer_input(sizeof(uint8_t)), sizeof(uint8_t));
  memcpy(&share_indices, fuzzer_input(SHAMIR_MAX_SHARE_COUNT),
         SHAMIR_MAX_SHARE_COUNT);
  memcpy(&share_values_content, fuzzer_input(SHAMIR_MAX_DATA_LEN),
         SHAMIR_MAX_DATA_LEN);
  memcpy(&share_count, fuzzer_input(sizeof(uint8_t)), sizeof(uint8_t));
  // note: this is platform specific via byte length of size_t
  memcpy(&len, fuzzer_input(sizeof(size_t)), sizeof(size_t));

  // mirror a check that the real code does
  if (share_count < 1 || share_count > SHAMIR_MAX_SHARE_COUNT) {
    return 0;
  }
  // (len > SHAMIR_MAX_LEN) is handled in the target function

  shamir_interpolate(result, result_index, share_indices, share_values,
                     share_count, len);
  return 0;
}

int fuzz_ecdsa_sign_digest(void) {
  uint8_t curve_decider = 0;
  uint8_t sig[64] = {0};
  uint8_t priv_key[32] = {0};
  uint8_t digest[32] = {0};

  if (fuzzer_length < 1 + sizeof(sig) + sizeof(priv_key) + sizeof(digest)) {
    return 0;
  }
  const ecdsa_curve *curve;
  uint8_t pby = 0;

  memcpy(&curve_decider, fuzzer_input(1), 1);
  memcpy(&sig, fuzzer_input(sizeof(sig)), sizeof(sig));
  memcpy(&priv_key, fuzzer_input(sizeof(priv_key)), sizeof(priv_key));
  memcpy(&digest, fuzzer_input(sizeof(digest)), sizeof(digest));

  // pick one of the standard curves
  if ((curve_decider & 0x1) == 1) {
    curve = &secp256k1;
  } else {
    curve = &nist256p1;
  }

  // TODO optionally set a function for is_canonical()
  int res = ecdsa_sign_digest(curve, priv_key, digest, sig, &pby, NULL);

  // successful signing
  if (res == 0) {
    uint8_t pub_key[33] = {0};
    ecdsa_get_public_key33(curve, priv_key, pub_key);
    res = ecdsa_verify_digest(curve, pub_key, sig, digest);

    if (res != 0) {
      // verification did not succeed

      // case: all zero pubkey value
      uint8_t pub_key_zero[33] =
          "\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
          "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";

      // case: all zero digest value
      uint8_t digest_zero[32] =
          "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
          "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";

      if (memcmp(&pub_key, &pub_key_zero, sizeof(pub_key_zero)) == 0 ||
          memcmp(&digest, &digest_zero, sizeof(digest_zero)) == 0) {
        return 0;
      }

      // handle as crash
      exit(1);
    }
  }
  return 0;
}

int fuzz_ecdsa_verify_digest(void) {
  uint8_t curve_decider = 0;
  uint8_t hash[32] = {0};
  uint8_t sig[64] = {0};
  uint8_t pub_key[65] = {0};

  if (fuzzer_length < 1 + sizeof(hash) + sizeof(sig) + sizeof(pub_key)) {
    return 0;
  }

  memcpy(&curve_decider, fuzzer_input(1), 1);
  memcpy(&hash, fuzzer_input(sizeof(hash)), sizeof(hash));
  memcpy(&sig, fuzzer_input(sizeof(sig)), sizeof(sig));
  memcpy(&pub_key, fuzzer_input(sizeof(pub_key)), sizeof(pub_key));

  const ecdsa_curve *curve;
  // pick one of the standard curves
  if ((curve_decider & 0x1) == 1) {
    curve = &secp256k1;
  } else {
    curve = &nist256p1;
  }

  int res = ecdsa_verify_digest(curve, (const uint8_t *)&pub_key,
                                (const uint8_t *)&sig, (const uint8_t *)&hash);

  if (res == 0) {
    // See if the fuzzer ever manages to get find a correct verification
    // intentionally trigger a crash to make this case observable
    // TODO this is not an actual problem, remove in the future
    exit(1);
  }

  return 0;
}

int fuzz_word_index(void) {
#define MAX_WORD_LENGTH 12

  // TODO exact match?
  if (fuzzer_length < MAX_WORD_LENGTH) {
    return 0;
  }

  char word[MAX_WORD_LENGTH + 1] = {0};
  memcpy(&word, fuzzer_ptr, MAX_WORD_LENGTH);
  size_t word_length = strlen(word);
  uint16_t index = 0;

  word_index(&index, (const char *)&word, word_length);

  return 0;
}

int fuzz_slip39_word_completion_mask(void) {
  if (fuzzer_length != 2) {
    return 0;
  }
  uint16_t sequence = (fuzzer_ptr[0] << 8) + fuzzer_ptr[1];
  fuzzer_input(2);

  slip39_word_completion_mask(sequence);

  return 0;
}

int fuzz_mnemonic_to_bits(void) {
  // length chosen somewhat arbitrarily
#define MAX_MNEMONIC_LENGTH 256

  if (fuzzer_length < MAX_MNEMONIC_LENGTH) {
    return 0;
  }

  char mnemonic[MAX_MNEMONIC_LENGTH + 1] = {0};
  memcpy(&mnemonic, fuzzer_ptr, MAX_MNEMONIC_LENGTH);
  uint8_t mnemonic_bits[32 + 1] = {0};

  mnemonic_to_bits((const char *)&mnemonic, mnemonic_bits);

  return 0;
}

int fuzz_aes(void) {
  if (fuzzer_length < 1 + 16 + 16 + 32) {
    return 0;
  }

  aes_encrypt_ctx ctxe;
  aes_decrypt_ctx ctxd;
  uint8_t ibuf[16] = {0};
  uint8_t obuf[16] = {0};
  uint8_t iv[16] = {0};
  uint8_t cbuf[16] = {0};

  const uint8_t *keylength_decider = fuzzer_input(1);

  // note: the unit test uses the fixed 32 byte key
  // 603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4
  uint8_t keybuf[32] = {0};
  memcpy(&keybuf, fuzzer_input(32), 32);

#ifdef AES_VAR
  // try 128, 192, 256 bit key lengths

  size_t keylength = 32;
  switch (keylength_decider[0] & 0x3) {
    case 0:
      // invalid length
      keylength = 1;
      break;
    case 1:
      keylength = 16;
      break;
    case 2:
      keylength = 24;
      break;
    case 3:
      keylength = 32;
      break;
  }

  if (aes_encrypt_key((const unsigned char *)&keybuf, keylength, &ctxe) ||
      aes_decrypt_key((const unsigned char *)&keybuf, keylength, &ctxd)) {
    // initialization problems, stop processing
    // we expect this to happen with the invalid key length
    return 0;
  }
#else
  // use a 256 bit key length
  (void)keylength_decider;
  aes_encrypt_key256((const unsigned char *)&keybuf, &ctxe);
  aes_decrypt_key256((const unsigned char *)&keybuf, &ctxd);
#endif

  memcpy(ibuf, fuzzer_input(16), 16);
  memcpy(iv, fuzzer_input(16), 16);

  aes_ecb_encrypt(ibuf, obuf, 16, &ctxe);
  aes_ecb_decrypt(ibuf, obuf, 16, &ctxd);

  aes_cbc_encrypt(ibuf, obuf, 16, iv, &ctxe);
  aes_cbc_decrypt(ibuf, obuf, 16, iv, &ctxd);

  aes_cfb_encrypt(ibuf, obuf, 16, iv, &ctxe);
  aes_cfb_decrypt(ibuf, obuf, 16, iv, &ctxe);

  aes_ofb_encrypt(ibuf, obuf, 16, iv, &ctxe);
  aes_ofb_decrypt(ibuf, obuf, 16, iv, &ctxe);

  aes_ctr_encrypt(ibuf, obuf, 16, cbuf, aes_ctr_cbuf_inc, &ctxe);
  aes_ctr_decrypt(ibuf, obuf, 16, cbuf, aes_ctr_cbuf_inc, &ctxe);
  return 0;
}

int fuzz_b58gph_encode_decode(void) {
  // note: encode and decode functions have an internal limit of 128
#define BASE58_GPH_MAX_INPUT_LEN 130

  if (fuzzer_length < 1 + 1 + BASE58_GPH_MAX_INPUT_LEN) {
    return 0;
  }

  // use a flexible output buffer target size
  uint8_t chosen_outlen = 0;
  memcpy(&chosen_outlen, fuzzer_input(1), 1);
  if (chosen_outlen > BASE58_GPH_MAX_INPUT_LEN) {
    return 0;
  }
  // use a flexible input buffer target size
  uint8_t chosen_inlen = 0;
  memcpy(&chosen_inlen, fuzzer_input(1), 1);
  if (chosen_inlen > BASE58_GPH_MAX_INPUT_LEN) {
    return 0;
  }

  // TODO switch to malloc()'ed buffers for better out of bounds access
  // detection?

  uint8_t encode_in_buffer[BASE58_GPH_MAX_INPUT_LEN] = {0};
  // with null termination
  char decode_in_buffer[BASE58_GPH_MAX_INPUT_LEN + 1] = {0};
  char out_buffer[BASE58_GPH_MAX_INPUT_LEN] = {0};

  memcpy(&encode_in_buffer, fuzzer_input(chosen_inlen), chosen_inlen);
  memcpy(&decode_in_buffer, &encode_in_buffer, chosen_inlen);

  int ret = 0;
  ret = base58gph_encode_check(encode_in_buffer, chosen_inlen, out_buffer,
                               chosen_outlen);

  if (ret != 0) {
    // successful encode, try decode
    uint8_t dummy_buffer[BASE58_GPH_MAX_INPUT_LEN] = {0};
    ret = base58gph_decode_check(out_buffer, (uint8_t *)&dummy_buffer,
                                 chosen_outlen);
    if (ret == 0) {
      // mark as exception
      // TODO POTENTIAL BUG - followup
      // exit(1);
    }
  }

  // do a second operation with the same input, without relationship to the
  // previously computed output
  base58gph_decode_check(decode_in_buffer, (uint8_t *)&out_buffer,
                         chosen_outlen);
  return 0;
}

#define SCHNORR_VERIFY_PUBKEY_DATA_LENGTH 33
#define SCHNORR_VERIFY_PRIVKEY_DATA_LENGTH 32

int fuzz_schnorr_verify_digest(void) {
  if (fuzzer_length < SHA256_DIGEST_LENGTH + SCHNORR_VERIFY_PUBKEY_DATA_LENGTH +
                          SCHNORR_SIG_LENGTH) {
    return 0;
  }

  // TODO optionally try nist256p1 ?
  const ecdsa_curve *curve = &secp256k1;
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  uint8_t pub_key[SCHNORR_VERIFY_PUBKEY_DATA_LENGTH] = {0};
  uint8_t signature[SCHNORR_SIG_LENGTH] = {0};

  memcpy(&digest, fuzzer_input(SHA256_DIGEST_LENGTH), SHA256_DIGEST_LENGTH);
  memcpy(&pub_key, fuzzer_input(SCHNORR_VERIFY_PUBKEY_DATA_LENGTH),
         SCHNORR_VERIFY_PUBKEY_DATA_LENGTH);
  memcpy(&signature, fuzzer_input(SCHNORR_SIG_LENGTH), SCHNORR_SIG_LENGTH);

  // TODO this limitation is a bug workaround
  if (pub_key[0] != 0x04) {
    int ret = schnorr_verify_digest(curve, pub_key, digest, signature);
    if (ret == 0) {
      // assuming that the fuzzer can't puzzle together validly signed inputs,
      // exit with a forced crash if a successful verification is observed
      exit(1);
    }
  }

  return 0;
}

int fuzz_schnorr_sign_digest(void) {
  if (fuzzer_length <
      1 + SHA256_DIGEST_LENGTH + SCHNORR_VERIFY_PRIVKEY_DATA_LENGTH) {
    return 0;
  }

  const ecdsa_curve *curve;
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  uint8_t priv_key[SCHNORR_VERIFY_PRIVKEY_DATA_LENGTH] = {0};
  uint8_t signature[SCHNORR_SIG_LENGTH] = {0};
  int ret = 0;

  uint8_t curve_decider = 0;
  memcpy(&curve_decider, fuzzer_input(1), 1);

  if ((curve_decider & 0x1) == 1) {
    curve = &secp256k1;
  } else {
    curve = &nist256p1;
  }

  memcpy(&digest, fuzzer_input(SHA256_DIGEST_LENGTH), SHA256_DIGEST_LENGTH);
  memcpy(&priv_key, fuzzer_input(SCHNORR_VERIFY_PRIVKEY_DATA_LENGTH),
         SCHNORR_VERIFY_PRIVKEY_DATA_LENGTH);

  ret = schnorr_sign_digest(curve, priv_key, digest, signature);

  if (ret == 0) {
    // signing was successful, check if the verification works

    // compute matching pubkey
    uint8_t pub_key[33] = {0};
    ecdsa_get_public_key33(curve, priv_key, pub_key);

    if (schnorr_verify_digest(curve, pub_key, digest, signature) != 0) {
      // ignore known case
      uint8_t pub_key_null[33] =
          "\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
          "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
      if (memcmp(&pub_key, &pub_key_null, 33) == 0) {
        return 0;
      }

      // something is wrong, mark as crash
      exit(1);
    }
  }
  return 0;
}

int fuzz_chacha_drbg(void) {
#define CHACHA_DRBG_ENTROPY_LENGTH 32
#define CHACHA_DRBG_RESEED_LENGTH 32
#define CHACHA_DRBG_NONCE_LENGTH 16
#define CHACHA_DRBG_RESULT_LENGTH 16

  if (fuzzer_length < CHACHA_DRBG_ENTROPY_LENGTH + CHACHA_DRBG_RESEED_LENGTH +
                          CHACHA_DRBG_NONCE_LENGTH) {
    return 0;
  }

  uint8_t entropy[CHACHA_DRBG_ENTROPY_LENGTH] = {0};
  uint8_t reseed[CHACHA_DRBG_RESEED_LENGTH] = {0};
  uint8_t nonce_bytes[CHACHA_DRBG_NONCE_LENGTH] = {0};
  uint8_t result[CHACHA_DRBG_RESULT_LENGTH] = {0};
  CHACHA_DRBG_CTX ctx;

  // TODO improvement idea: switch to variable input sizes
  memcpy(&entropy, fuzzer_input(CHACHA_DRBG_ENTROPY_LENGTH),
         CHACHA_DRBG_ENTROPY_LENGTH);
  memcpy(&reseed, fuzzer_input(CHACHA_DRBG_RESEED_LENGTH),
         CHACHA_DRBG_RESEED_LENGTH);
  memcpy(&nonce_bytes, fuzzer_input(CHACHA_DRBG_NONCE_LENGTH),
         CHACHA_DRBG_NONCE_LENGTH);

  chacha_drbg_init(&ctx, entropy, sizeof(entropy), nonce_bytes,
                   sizeof(nonce_bytes));
  chacha_drbg_reseed(&ctx, reseed, sizeof(reseed), NULL, 0);
  chacha_drbg_generate(&ctx, result, sizeof(result));

  return 0;
}

int fuzz_ed25519_sign_verify(void) {
  ed25519_secret_key secret_key;
  ed25519_signature signature;
  ed25519_public_key public_key;
  // length chosen arbitrarily
  uint8_t message[32] = {0};
  int ret = 0;

  if (fuzzer_length <
      sizeof(secret_key) + sizeof(signature) + sizeof(message)) {
    return 0;
  }

  memcpy(&secret_key, fuzzer_input(sizeof(secret_key)), sizeof(secret_key));
  memcpy(&signature, fuzzer_input(sizeof(signature)), sizeof(signature));
  memcpy(&message, fuzzer_input(sizeof(message)), sizeof(message));

  ed25519_publickey(secret_key, public_key);
  // sign message, this should always succeed
  ed25519_sign(message, sizeof(message), secret_key, public_key, signature);

  // verify message, we expect this to work
  ret = ed25519_sign_open(message, sizeof(message), public_key, signature);

  // TODO are there other error values?
  if (ret == -1) {
    // mark as exception
    exit(1);
  }

  return 0;
}

// TODO more XMR functions
// extern void xmr_hash_to_ec(ge25519 *P, const void *data, size_t length);

// this function directly calls
// hasher_Raw(HASHER_SHA3K, data, length, hash)
// is this interesting at all?
// extern void xmr_fast_hash(uint8_t *hash, const void *data, size_t length);

// TODO target idea: re-create openssl_check() from test_openssl.c
// to do differential fuzzing against OpenSSL functions

#define META_HEADER_SIZE 3

// main fuzzer entry
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  // reject input that is too short
  if (size < META_HEADER_SIZE) {
    return 0;
  }

  fuzzer_reset_state();

  uint8_t target_decision = data[0];

  // TODO use once necessary
  // uint8_t subdecision = data[1];

  // note: data[2] is reserved for future use

  // assign the fuzzer payload data for the target functions
  fuzzer_ptr = data + META_HEADER_SIZE;
  fuzzer_length = size - META_HEADER_SIZE;

  // if active: reject all other inputs that are not the selected target
  // this is helpful for directing the fuzzing focus on a specific case
#ifdef FUZZER_EXCLUSIVE_TARGET
  if (target_decision != FUZZER_EXCLUSIVE_TARGET) {
    return 0;
  }
#endif

  // TODO reorder and regroup target functions
  switch (target_decision) {
    case 0:
      fuzz_bn_format();
      break;
    case 1:
      fuzz_base32_decode();
      break;
    case 2:
      fuzz_base32_encode();
      break;
    case 3:
      fuzz_base58_encode_check();
      break;
    case 4:
      fuzz_base58_decode_check();
      break;
    case 5:
      fuzz_xmr_base58_addr_decode_check();
      break;
    case 6:
      fuzz_xmr_base58_addr_encode_check();
      break;
    case 7:
      fuzz_xmr_serialize_varint();
      break;
    case 8:
      fuzz_nem_validate_address();
      break;
    case 9:
      fuzz_nem_get_address();
      break;
    case 10:
      fuzz_xmr_get_subaddress_secret_key();
      break;
    case 11:
      fuzz_xmr_derive_private_key();
      break;
    case 12:
      fuzz_xmr_derive_public_key();
      break;
    case 13:
      fuzz_shamir_interpolate();
      break;
    case 14:
#ifdef FUZZ_ALLOW_SLOW
      // slow through expensive bignum operations
      fuzz_ecdsa_verify_digest();
#endif
      break;
    case 15:
      fuzz_word_index();
      break;
    case 16:
      fuzz_slip39_word_completion_mask();
      break;
    case 17:
      fuzz_mnemonic_to_bits();
      break;
    case 18:
#ifdef FUZZ_ALLOW_SLOW
      fuzz_aes();
#endif
      break;
    case 19:
      fuzz_b58gph_encode_decode();
      break;
    case 20:
      fuzz_schnorr_verify_digest();
      break;
    case 21:
      fuzz_schnorr_sign_digest();
      break;
    case 22:
      fuzz_chacha_drbg();
      break;
    case 23:
#ifdef FUZZ_ALLOW_SLOW
      // slow through expensive bignum operations
      fuzz_ecdsa_sign_digest();
#endif
      break;
    case 24:
      fuzz_ed25519_sign_verify();
      break;

    default:
      // do nothing
      break;
  }
  return 0;
}
