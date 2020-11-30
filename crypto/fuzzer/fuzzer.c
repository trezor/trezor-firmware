/**
 * Copyright (c) 2020 Christian Reitter
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

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// necessary for the target functions
#include "aes/aes.h"
#include "bignum.h"
#include "ecdsa.h"
#include "hasher.h"
#include "nist256p1.h"
#include "rand.h"
#include "secp256k1.h"

#include "ed25519-donna/ed25519-donna.h"
#include "ed25519-donna/ed25519.h"
#include "nem.h"
#include "shamir.h"

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

extern size_t bn_format(const bignum256 *amnt, const char *prefix,
                        const char *suffix, unsigned int decimals, int exponent,
                        bool trailing, char *out, size_t outlen);
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

extern const char *BASE32_ALPHABET_RFC4648;
extern uint8_t *base32_decode(const char *in, size_t inlen, uint8_t *out,
                              size_t outlen, const char *alphabet);

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

extern char *base32_encode(const uint8_t *in, size_t inlen, char *out,
                           size_t outlen, const char *alphabet);

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

extern int base58_encode_check(const uint8_t *data, int datalen,
                               HasherType hasher_type, char *str, int strsize);

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

extern int base58_decode_check(const char *str, HasherType hasher_type,
                               uint8_t *data, int datalen);

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

extern int xmr_base58_addr_decode_check(const char *addr, size_t sz,
                                        uint64_t *tag, void *data,
                                        size_t datalen);

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

extern int xmr_base58_addr_encode_check(uint64_t tag, const uint8_t *data,
                                        size_t binsz, char *b58, size_t b58sz);

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

extern int xmr_size_varint(uint64_t num);
extern int xmr_write_varint(uint8_t *buff, size_t buff_size, uint64_t num);
extern int xmr_read_varint(uint8_t *buff, size_t buff_size, uint64_t *val);

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

extern bool nem_validate_address(const char *address, uint8_t network);

// arbitrarily chosen maximum size
#define NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN 128

int fuzz_nem_validate_address(void) {
  if (fuzzer_length < (1 + 1) ||
      fuzzer_length > NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN) {
    return 0;
  }

  char in_buffer[NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN] = {0};

  // TODO potential BUG: is it clearly specified that the address has to be null
  // terminated?
  in_buffer[NEM_VALIDATE_ADDRESS_MAX_INPUT_LEN - 1] = 0;

  uint8_t network = *fuzzer_ptr;
  fuzzer_input(1);

  // mutate the buffer
  memcpy(&in_buffer, fuzzer_ptr, fuzzer_length);
  size_t raw_inlen = fuzzer_length;
  fuzzer_input(raw_inlen);

  nem_validate_address(in_buffer, network);

  return 0;
}

extern bool nem_get_address(const ed25519_public_key public_key,
                            uint8_t version, char *address);

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

extern void xmr_get_subaddress_secret_key(bignum256modm r, uint32_t major,
                                          uint32_t minor,
                                          const bignum256modm m);

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

extern void xmr_derive_private_key(bignum256modm s, const ge25519 *deriv,
                                   uint32_t idx, const bignum256modm base);

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

extern void xmr_derive_public_key(ge25519 *r, const ge25519 *deriv,
                                  uint32_t idx, const ge25519 *base);

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

extern bool shamir_interpolate(uint8_t *result, uint8_t result_index,
                               const uint8_t *share_indices,
                               const uint8_t **share_values,
                               uint8_t share_count, size_t len);

#define SHAMIR_MAX_SHARE_COUNT 16
#define SHAMIR_MAX_DATA_LEN (SHAMIR_MAX_SHARE_COUNT * SHAMIR_MAX_LEN)
int fuzz_shamir_interpolate(void) {
  if (fuzzer_length != (2 * sizeof(uint8_t) + SHAMIR_MAX_SHARE_COUNT +
                        SHAMIR_MAX_DATA_LEN + 2)) {
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

  // the target function checks for (len > SHAMIR_MAX_LEN),
  // so we don't have to test the whole size_t length value
  len = (fuzzer_ptr[0] << 8) + fuzzer_ptr[1];
  fuzzer_input(2);

  // mirror the checks in mod_trezorcrypto_shamir_interpolate()
  if (share_count < 1 || share_count > SHAMIR_MAX_SHARE_COUNT) {
    return 0;
  }

  shamir_interpolate(result, result_index, share_indices, share_values,
                     share_count, len);
  return 0;
}

extern int ecdsa_verify_digest(const ecdsa_curve *curve, const uint8_t *pub_key,
                               const uint8_t *sig, const uint8_t *digest);

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

  // TODO check if the fuzzer ever manages to get the return value to 0
  (void)res;

  return 0;
}

extern bool word_index(uint16_t *index, const char *word, uint8_t word_length);

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

extern uint16_t slip39_word_completion_mask(uint16_t sequence);

int fuzz_slip39_word_completion_mask(void) {
  if (fuzzer_length != 2) {
    return 0;
  }
  uint16_t sequence = (fuzzer_ptr[0] << 8) + fuzzer_ptr[1];
  fuzzer_input(2);

  // TODO perform additional checks on the output?
  slip39_word_completion_mask(sequence);

  return 0;
}

extern int mnemonic_to_bits(const char *mnemonic, uint8_t *mnemonic_bits);

int fuzz_mnemonic_to_bits(void) {
  // slightly longer than MAX_MNEMONIC_LEN from config.h
#define MAX_MNEMONIC_LENGTH 256

  if (fuzzer_length < MAX_MNEMONIC_LENGTH) {
    return 0;
  }

  char mnemonic[MAX_MNEMONIC_LENGTH + 1] = {0};
  memcpy(&mnemonic, fuzzer_ptr, MAX_MNEMONIC_LENGTH);
  uint8_t mnemonic_bits[32 + 1] = {0};

  int number_of_bits = mnemonic_to_bits((const char *)&mnemonic, mnemonic_bits);
  assert(0 <= number_of_bits && number_of_bits <= 264);

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

extern int base58gph_encode_check(const uint8_t *data, int datalen, char *str,
                                  int strsize);

extern int base58gph_decode_check(const char *str, uint8_t *data, int datalen);

int fuzz_b58gph_encode_decode(void) {
  // note: encode and decode have an internal limit of 128
#define BASE58_GPH_MAX_INPUT_LEN 140

  if (fuzzer_length > BASE58_GPH_MAX_INPUT_LEN) {
    return 0;
  }

  uint8_t encode_in_buffer[BASE58_GPH_MAX_INPUT_LEN] = {0};
  // with null termination
  char decode_in_buffer[BASE58_GPH_MAX_INPUT_LEN + 1] = {0};
  char out_buffer[BASE58_GPH_MAX_INPUT_LEN] = {0};
  size_t outlen = sizeof(out_buffer);

  size_t raw_inlen = fuzzer_length;
  memcpy(&encode_in_buffer, fuzzer_input(raw_inlen), raw_inlen);
  memcpy(&decode_in_buffer, &encode_in_buffer, raw_inlen);

  base58gph_encode_check(encode_in_buffer, raw_inlen, out_buffer, outlen);
  base58gph_decode_check(decode_in_buffer, (uint8_t *)&out_buffer, outlen);

  // TODO do logical encode<>decode comparison checks?

  return 0;
}

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

    default:
      // do nothing
      break;
  }
  return 0;
}
