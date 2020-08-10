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

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// necessary for the target functions
#include "bignum.h"
#include "ecdsa.h"
#include "hasher.h"
#include "rand.h"

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
int fuzz_bn_format() {
  bignum256 target_bignum;
  if (fuzzer_length < sizeof(target_bignum)) {
    return 0;
  }

  char buf[512];
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

int fuzz_base32_decode() {
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

int fuzz_base32_encode() {
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

int fuzz_base58_encode_check() {
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

int fuzz_base58_decode_check() {
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

int fuzz_xmr_base58_addr_decode_check() {
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

int fuzz_xmr_base58_addr_encode_check() {
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

int fuzz_xmr_serialize_varint() {
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

int fuzz_nem_validate_address() {
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

#define META_HEADER_SIZE 3

// main fuzzer entry
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  // reject input that is too short
  if (size < META_HEADER_SIZE) {
    return 0;
  }

  fuzzer_reset_state();

  uint8_t decision = data[0];

  // TODO use when necessary
  // uint8_t subdecision = data[1];

  // note: data[2] is reserved for future use

  // assign the fuzzer payload data for the target functions
  fuzzer_ptr = data + META_HEADER_SIZE;
  fuzzer_length = size - META_HEADER_SIZE;

  switch (decision) {
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
    default:
      // do nothing
      break;
  }
  return 0;
}
