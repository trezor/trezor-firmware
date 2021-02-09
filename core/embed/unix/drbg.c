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

#include "drbg.h"

#include "chacha_drbg.h"
#include "rand.h"

static CHACHA_DRBG_CTX drbg_ctx;

void drbg_init(void) {
  uint8_t entropy[48];
  random_buffer(entropy, sizeof(entropy));
  chacha_drbg_init(&drbg_ctx, entropy, sizeof(entropy), NULL, 0);
}

void drbg_reseed(const uint8_t *entropy, size_t len) {
  chacha_drbg_reseed(&drbg_ctx, entropy, len, NULL, 0);
}

void drbg_generate(uint8_t *buf, size_t len) {
  chacha_drbg_generate(&drbg_ctx, buf, len);
}

uint32_t drbg_random32(void) {
  uint32_t value;
  drbg_generate((uint8_t *)&value, sizeof(value));
  return value;
}
