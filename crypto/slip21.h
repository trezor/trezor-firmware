/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef TREZOR_CRYPTO_SLIP21_H
#define TREZOR_CRYPTO_SLIP21_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

void slip21_from_seed(const uint8_t *seed, size_t length, uint8_t node[64]);
/* One-byte-length-prefixed labels; malformed paths leave node unchanged. */
bool slip21_derive_path(uint8_t node[64], const uint8_t *path, size_t length);

#endif
