/**
 * Copyright (c) 2013-2014 Tomas Dzetkulic
 * Copyright (c) 2013-2014 Pavol Rusnak
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

#include "bip39.h"
#include "hmac.h"
#include "memzero.h"
#include "options.h"
#include "pbkdf2.h"
#include "rand.h"
#include "sha2.h"

#if USE_BIP39_CACHE

static int bip39_cache_index = 0;

static CONFIDENTIAL struct {
  bool set;
  char mnemonic[256];
  char passphrase[64];
  uint8_t seed[512 / 8];
} bip39_cache[BIP39_CACHE_SIZE];

void bip39_cache_clear(void) {
  memzero(bip39_cache, sizeof(bip39_cache));
  bip39_cache_index = 0;
}

#endif

static CONFIDENTIAL char mnemo[24 * 10];

const char *mnemonic_from_data(const uint8_t *data, int len) {
  if (len % 4 || len < 16 || len > 32) {
    return 0;
  }

  uint8_t bits[32 + 1] = {0};

  sha256_Raw(data, len, bits);
  // checksum
  bits[len] = bits[0];
  // data
  memcpy(bits, data, len);

  int mlen = len * 3 / 4;

  int i = 0, j = 0, idx = 0;
  char *p = mnemo;
  for (i = 0; i < mlen; i++) {
    idx = 0;
    for (j = 0; j < 11; j++) {
      idx <<= 1;
      idx += (bits[(i * 11 + j) / 8] & (1 << (7 - ((i * 11 + j) % 8)))) > 0;
    }
    strcpy(p, BIP39_WORDLIST_ENGLISH[idx]);
    p += strlen(BIP39_WORDLIST_ENGLISH[idx]);
    *p = (i < mlen - 1) ? ' ' : 0;
    p++;
  }
  memzero(bits, sizeof(bits));

  return mnemo;
}

void mnemonic_clear(void) { memzero(mnemo, sizeof(mnemo)); }

int mnemonic_to_bits(const char *mnemonic_orig, uint8_t *bits) {
  if (!mnemonic_orig) {
    return 0;
  }

  // Extended buffer to prevent reading out of bounds in `mnemonic_find_word()`
  // that requires at least BIP39_MAX_WORD_LEN bytes. The extra bytes in
  // `mnemonic` are not actually needed; however, they make this function more
  // robust and easier to analyze.
  char mnemonic[BIP39_MAX_MNEMONIC_LEN + BIP39_MAX_WORD_LEN + 1] = {0};
  uint8_t result[32 + 1] = {0};
  int result_bits = 0;

  size_t mnemonic_len = strlen(mnemonic_orig);
  if (mnemonic_len > BIP39_MAX_MNEMONIC_LEN) {
    goto cleanup;
  }

  // Copy the mnemonic into a larger buffer and replace spaces with null bytes
  // to allow comparison with null-terminated dictionary words.
  uint32_t word_count = 0;
  for (uint16_t i = 0; i < mnemonic_len; i++) {
    bool is_space = mnemonic_orig[i] == ' ';
    int8_t space_mask = (-is_space) & ' ';
    mnemonic[i] = mnemonic_orig[i] ^ space_mask;  // change ' ' to 0x00
    word_count += is_space;
  }
  word_count++;

  // check that number of words is valid for BIP-39:
  // (a) between 128 and 256 bits of initial entropy (12 - 24 words)
  // (b) number of bits divisible by 33 (1 checksum bit per 32 input bits)
  //     - that is, (word_count * 11) % 33 == 0, so word_count % 3 == 0
  if (word_count < 12 || word_count > 24 || (word_count % 3)) {
    goto cleanup;
  }

  memzero(result, sizeof(result));
  uint32_t bit_count = 0;
  uint32_t word_offset = 0;  // index of beginning of current word
  while (word_offset < mnemonic_len) {
    found_word found = mnemonic_find_word(&mnemonic[word_offset]);
    // move to next word (skip the 0x00 separator)
    word_offset += found.length + 1;

    int index = found.index;
    if (index < 0) {  // word not found
      goto cleanup;
    }
    for (uint32_t bit_in_index = 0; bit_in_index < BIP39_BITS_PER_WORD;
         bit_in_index++) {
      // 1. Extract the secret bit (result is 0 or 1)
      uint32_t secret_bit =
          (index >> (BIP39_BITS_PER_WORD - 1 - bit_in_index)) & 1;

      // 2. Create a mask based on the secret bit value
      // If secret_bit is 1, mask becomes -1 (0xFFFFFFFF)
      // If secret_bit is 0, mask becomes  0 (0x00000000)
      int32_t mask = -secret_bit;

      // 3. Apply the mask to the value and perform the OR operation
      // This operation is only effective if the mask is all 1s.
      result[bit_count / 8] |= ((1 << (7 - (bit_count % 8))) & mask);

      bit_count++;
    }
  }
  if (bit_count != word_count * BIP39_BITS_PER_WORD) {
    goto cleanup;
  }

  memcpy(bits, result, sizeof(result));
  result_bits = bit_count;

cleanup:
  memzero(result, sizeof(result));
  memzero(mnemonic, sizeof(mnemonic));
  return result_bits;
}

int mnemonic_check(const char *mnemonic) {
  uint8_t bits[32 + 1] = {0};
  int mnemonic_bits_len = mnemonic_to_bits(mnemonic, bits);
  if (mnemonic_bits_len != (12 * BIP39_BITS_PER_WORD) &&
      mnemonic_bits_len != (18 * BIP39_BITS_PER_WORD) &&
      mnemonic_bits_len != (24 * BIP39_BITS_PER_WORD)) {
    return 0;
  }
  int words = mnemonic_bits_len / BIP39_BITS_PER_WORD;

  uint8_t checksum = bits[words * 4 / 3];
  sha256_Raw(bits, words * 4 / 3, bits);
  if (words == 12) {
    return (bits[0] & 0xF0) == (checksum & 0xF0);  // compare first 4 bits
  } else if (words == 18) {
    return (bits[0] & 0xFC) == (checksum & 0xFC);  // compare first 6 bits
  } else if (words == 24) {
    return bits[0] == checksum;  // compare 8 bits
  }
  return 0;
}

// passphrase must be at most 256 characters otherwise it would be truncated
void mnemonic_to_seed(const char *mnemonic, const char *passphrase,
                      uint8_t seed[512 / 8],
                      void (*progress_callback)(uint32_t current,
                                                uint32_t total)) {
  int mnemoniclen = strlen(mnemonic);
  int passphraselen = strnlen(passphrase, 256);
#if USE_BIP39_CACHE
  // check cache
  if (mnemoniclen < 256 && passphraselen < 64) {
    for (int i = 0; i < BIP39_CACHE_SIZE; i++) {
      if (!bip39_cache[i].set) continue;
      if (strcmp(bip39_cache[i].mnemonic, mnemonic) != 0) continue;
      if (strcmp(bip39_cache[i].passphrase, passphrase) != 0) continue;
      // found the correct entry
      memcpy(seed, bip39_cache[i].seed, 512 / 8);
      return;
    }
  }
#endif
  uint8_t salt[8 + 256] = {0};
  memcpy(salt, "mnemonic", 8);
  memcpy(salt + 8, passphrase, passphraselen);
  LOCAL_CONFIDENTIAL PBKDF2_HMAC_SHA512_CTX pctx;
  pbkdf2_hmac_sha512_Init(&pctx, (const uint8_t *)mnemonic, mnemoniclen, salt,
                          passphraselen + 8, 1);
  if (progress_callback) {
    progress_callback(0, BIP39_PBKDF2_ROUNDS);
  }
  for (int i = 0; i < 16; i++) {
    pbkdf2_hmac_sha512_Update(&pctx, BIP39_PBKDF2_ROUNDS / 16);
    if (progress_callback) {
      progress_callback((i + 1) * BIP39_PBKDF2_ROUNDS / 16,
                        BIP39_PBKDF2_ROUNDS);
    }
  }
  pbkdf2_hmac_sha512_Final(&pctx, seed);
  memzero(salt, sizeof(salt));
#if USE_BIP39_CACHE
  // store to cache
  if (mnemoniclen < 256 && passphraselen < 64) {
    bip39_cache[bip39_cache_index].set = true;
    strcpy(bip39_cache[bip39_cache_index].mnemonic, mnemonic);
    strcpy(bip39_cache[bip39_cache_index].passphrase, passphrase);
    memcpy(bip39_cache[bip39_cache_index].seed, seed, 512 / 8);
    bip39_cache_index = (bip39_cache_index + 1) % BIP39_CACHE_SIZE;
  }
#endif
}

/**
 * @brief Constant-time memory comparison.
 * Compares 'n' bytes, but unlike memcmp, it does not short-circuit,
 * thus preventing timing attacks.
 * @return `true` if the memory areas are equal, `false` otherwise.
 */
static bool constant_time_memeq(const void *s1, const void *s2, size_t n) {
  const unsigned char *p1 = s1;
  const unsigned char *p2 = s2;
  int diff = 0;
  for (size_t i = 0; i < n; i++) {
    // Accumulate differences using OR to prevent early termination
    diff |= p1[i] ^ p2[i];
  }
  return diff == 0;
}

/**
 * @brief Constant-time linear search for a mnemonic word. Make sure the `word`
 * argument is provided within at least 9 characters big buffer to avoid
 * out-of-bounds reads.
 */
found_word mnemonic_find_word(const char *word) {
  int result_index = -1;
  size_t result_length = 0;
  for (int i = 0; i < BIP39_WORD_COUNT; i++) {
    const char *dict_word = BIP39_WORDLIST_ENGLISH[i];
    size_t dict_word_len = strlen(dict_word);
    bool is_match =  // 0 or 1 - 1 is match
        constant_time_memeq(word, dict_word, dict_word_len + 1);
    int8_t match_mask = -is_match;  // 0x00 or 0xFF - 0xFF is match
    result_index =
        (match_mask & i) + (~match_mask & result_index);  // take one of the two
    result_length =
        (match_mask & dict_word_len) + (~match_mask & result_length);
  }
  return (found_word){.index = result_index, .length = result_length};
}

const char *mnemonic_complete_word(const char *prefix, int len) {
  // we need to perform linear search,
  // because we want to return the first match
  for (int i = 0; i < BIP39_WORD_COUNT; i++) {
    if (strncmp(BIP39_WORDLIST_ENGLISH[i], prefix, len) == 0) {
      return BIP39_WORDLIST_ENGLISH[i];
    }
  }
  return NULL;
}

const char *mnemonic_get_word(int index) {
  if (index >= 0 && index < BIP39_WORD_COUNT) {
    return BIP39_WORDLIST_ENGLISH[index];
  } else {
    return NULL;
  }
}

uint32_t mnemonic_word_completion_mask(const char *prefix, int len) {
  if (len <= 0) {
    return 0x3ffffff;  // all letters (bits 1-26 set)
  }
  uint32_t res = 0;
  for (int i = 0; i < BIP39_WORD_COUNT; i++) {
    const char *word = BIP39_WORDLIST_ENGLISH[i];
    if (strncmp(word, prefix, len) == 0 && word[len] >= 'a' &&
        word[len] <= 'z') {
      res |= 1 << (word[len] - 'a');
    }
  }
  return res;
}
