
/**
 * `base64.h' - b64
 *
 * copyright (c) 2014 joseph werle
 */

#ifndef BASE64_H
#define BASE64_H 1

#ifndef BEAM_DEBUG
#include "mpconfigport.h"
#endif
#include <stddef.h>
/**
 *  Memory allocation functions to use. You can define b64_malloc and
 * b64_realloc to custom functions if you want.
 */

#ifndef b64_malloc
#define b64_malloc(ptr) malloc(ptr)
#endif
#ifndef b64_realloc
#define b64_realloc(ptr, size) realloc(ptr, size)
#endif

/**
 * Base64 index table.
 */

static const char b64_table[] = {
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'};

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Encode `unsigned char *' source with `size_t' size.
 * Returns a `char *' base64 encoded string.
 */

char *b64_encode(const unsigned char *, size_t);

/**
 * Dencode `char *' source with `size_t' size.
 * Returns a `unsigned char *' base64 decoded string.
 */
unsigned char *b64_decode(const char *, size_t);

/**
 * Dencode `char *' source with `size_t' size.
 * Returns a `unsigned char *' base64 decoded string + size of decoded string.
 */
unsigned char *b64_decode_ex(const char *, size_t, size_t *);

#ifdef __cplusplus
}
#endif

#endif
