#ifndef __CONSTEQ_H__
#define __CONSTEQ_H__

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/**
 * @brief Constant-time memory comparison.
 * Compares 'n' bytes, but unlike memcmp, it does not short-circuit,
 * thus preventing timing attacks.
 * @return `true` if the memory areas are equal, `false` otherwise.
 */
bool consteq(const void *s1, const void *s2, size_t n)
#endif
