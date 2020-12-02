/**
 * This file is part of the TREZOR project, https://trezor.io/
 *
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

#include "slip39.h"
#include <stdio.h>
#include <string.h>
#include "slip39_wordlist.h"

static uint16_t find(uint16_t prefix, bool find_index);

/**
 * Returns word at position `index`.
 */
const char* get_word(uint16_t index) {
  if (index >= WORDS_COUNT) {
    return NULL;
  }

  return wordlist[index];
}

/**
 * Finds the index of a given word.
 * Returns true on success and stores result in `index`.
 */
bool word_index(uint16_t* index, const char* word, uint8_t word_length) {
  uint16_t lo = 0;
  uint16_t hi = WORDS_COUNT;
  uint16_t mid = 0;

  while ((hi - lo) > 1) {
    mid = (hi + lo) / 2;
    if (strncmp(wordlist[mid], word, word_length) > 0) {
      hi = mid;
    } else {
      lo = mid;
    }
  }
  if (strncmp(wordlist[lo], word, word_length) != 0) {
    return false;
  }
  *index = lo;
  return true;
}

/**
 * Calculates which buttons on the T9 keyboard can still be pressed after the
 * prefix was entered. Returns a 9-bit bitmask, where each bit specifies which
 * buttons can be pressed (there are still words in this combination). The least
 * significant bit corresponds to the first button.
 *
 * Example: 110000110 - second, third, eighth and ninth button still can be
 * pressed.
 */
uint16_t slip39_word_completion_mask(uint16_t prefix) {
  return find(prefix, false);
}

/**
 * Returns the first word matching the button sequence prefix or NULL if no
 * match is found.
 */
const char* button_sequence_to_word(uint16_t prefix) {
  return get_word(find(prefix, true));
}

/**
 * Computes mask if find_index is false.
 * Otherwise finds the first word index that matches the prefix. Returns
 * WORDS_COUNT if no match is found.
 */
static uint16_t find(uint16_t prefix, bool find_index) {
  if (prefix == 0) {
    return find_index ? 0 : 0x1ff;
  }

  // Determine the range of sequences [min, max), which have the given prefix.
  uint16_t min = prefix;
  uint16_t max = prefix + 1;
  uint16_t divider = 1;
  while (max <= 1000) {
    min *= 10;
    max *= 10;
    divider *= 10;
  }
  divider /= 10;

  // Four char prefix -> the mask is zero
  if (!divider && !find_index) {
    return 0;
  }

  // We can't use binary search because the numbers are not sorted.
  // They are sorted using the words' alphabet (so we can use the index).
  // Example: axle (1953), beam (1315)
  // The first digit is sorted so we only need to search up to `max_search`.
  uint16_t max_search = min - (min % 1000) + 1000;
  uint16_t bitmap = 0;
  for (uint16_t i = 0; i < WORDS_COUNT; i++) {
    if (words_button_seq[i] >= max_search) {
      break;
    }

    if (words_button_seq[i] >= min && words_button_seq[i] < max) {
      if (find_index) {
        return i;
      }

      uint8_t digit = (words_button_seq[i] / divider) % 10;
      bitmap |= 1 << (digit - 1);
    }
  }

  if (find_index) {
    // Index not found.
    return WORDS_COUNT;
  } else {
    return bitmap;
  }
}
