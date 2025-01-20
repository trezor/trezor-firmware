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

#include <ctype.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>

typedef struct {
  const char* start;
  const char* end;
} slice_t;

// Returns an empty slice
static inline slice_t slice_empty(void) {
  slice_t slice = {NULL, NULL};
  return slice;
}

// Trims leading whitespace from the slice
static inline slice_t slice_trim_left(slice_t slice) {
  while (slice.start < slice.end && isspace((unsigned char)*slice.start)) {
    slice.start++;
  }
  return slice;
}

// Trims trailing whitespace from the slice
static inline slice_t slice_trim_right(slice_t slice) {
  while (slice.start < slice.end && isspace((unsigned char)*(slice.end - 1))) {
    slice.end--;
  }
  return slice;
}

// Trims both leading and trailing whitespace from the slice
static inline slice_t slice_trim(slice_t slice) {
  return slice_trim_left(slice_trim_right(slice));
}

// Checks if the slice is empty
static inline bool slice_is_empty(slice_t slice) {
  return slice.start >= slice.end;
}

// Compares the slice with a C-string for equality
static inline bool slice_equals_cstr(slice_t slice, const char* str) {
  const char* p = slice.start;
  while (p < slice.end && *str != '\0' && *p == *str) {
    p++;
    str++;
  }
  return p == slice.end && *str == '\0';
}

// Parses the slice as a signed 32-bit integer in the specified base.
// Returns true if the entire slice was parsed successfully
static inline bool slice_parse_int32(slice_t slice, int base, int32_t* result) {
  char* endptr;
  *result = strtol(slice.start, &endptr, base);
  return endptr == slice.end;
}

// Parses the slice as an unsigned 32-bit integer in the specified base.
// Returns true if the entire slice was parsed successfully.
static inline bool slice_parse_uint32(slice_t slice, int base,
                                      uint32_t* result) {
  char* endptr;
  *result = strtoul(slice.start, &endptr, base);
  return endptr == slice.end;
}

// Parses the slice as a floating-point number (float).
// Returns true if the entire slice was parsed successfully.
static inline bool slice_parse_float(slice_t slice, float* result) {
  char* endptr;
  *result = strtof(slice.start, &endptr);
  return endptr == slice.end;
}

// Parses the slice as a double-precision floating-point number.
// Returns true if the entire slice was parsed successfully.
static inline bool slice_parse_double(slice_t slice, double* result) {
  char* endptr;
  *result = strtod(slice.start, &endptr);
  return endptr == slice.end;
}

// Extracts a token from the slice until the specified character is encountered.
// Updates the input slice to start after the token.
static inline slice_t tok_until_char(slice_t* slice, char c) {
  const char* p = slice->start;
  while (p < slice->end && *p != c) {
    p++;
  }
  slice_t result = {slice->start, p};
  slice->start = p;
  return result;
}

// Extracts a token from the slice until the end of the line (LF or CRLF).
static inline slice_t tok_until_eol(slice_t* slice) {
  slice_t result = tok_until_char(slice, '\n');

  // Trim the trailing '\r' character
  if (result.start < result.end && *(result.end - 1) == '\r') {
    result.end--;
    slice->start--;
  }

  return result;
}

// Skips a single character from the slice if it matches the specified
// character. Returns true if the character was skipped.
static inline bool tok_skip_char(slice_t* slice, char c) {
  if (slice->start < slice->end && *slice->start == c) {
    slice->start++;
    return true;
  } else {
    return false;
  }
}

// Skips an end-of-line sequence (LF or CRLF) in the slice.
// Returns true if an EOL sequence was skipped.
static inline bool tok_skip_eol(slice_t* slice) {
  size_t len = slice->end - slice->start;
  const char* p = slice->start;

  if (len > 0 && *p == '\n') {
    slice->start += 1;
    return true;
  } else if (len > 1 && *p == '\r' && *(p + 1) == '\n') {
    slice->start += 2;
    return true;
  } else {
    return false;
  }
}
