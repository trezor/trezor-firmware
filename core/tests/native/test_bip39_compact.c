/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bip39.h"

int main(void) {
  for (int index = 0; index < BIP39_WORD_COUNT; ++index) {
    char word[9] = {0};
    strcpy(word, BIP39_WORDLIST_ENGLISH[index]);
    found_word found = mnemonic_find_word(word);
    assert(found.index == index);
    assert(found.length == strlen(word));
    word[strlen(word) - 1] = '!';
    assert(mnemonic_find_word(word).index == -1);
  }
  for (size_t length = 16; length <= 32; length += 4) {
    uint8_t entropy[32] = {0}, bits[33] = {0};
    for (size_t i = 0; i < length; ++i) entropy[i] = i;
    const char *words = mnemonic_from_data(entropy, length);
    assert(words);
    assert(mnemonic_to_bits(words, bits) == length * 8 + length / 4);
    assert(memcmp(entropy, bits, length) == 0);
    if (length == 16 || length == 24 || length == 32)
      assert(mnemonic_check(words));
    mnemonic_clear();
  }
  puts(
      "all 2048 compact BIP39 words, invalid words and entropy round trips "
      "passed");
  return 0;
}

void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)footer;
  fprintf(stderr, "crypto fatal: %s: %s\n", title, message);
  abort();
}
