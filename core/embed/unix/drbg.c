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
#include "common.h"
#include "memzero.h"
#include "secbool.h"

static CHACHA_DRBG_CTX drbg_ctx;
static secbool initialized = secfalse;

void drbg_init(const uint8_t *nonce, size_t nonce_length) {
  assert(nonce_length == DRBG_INIT_NONCE_LENGTH);

  uint8_t entropy[DRBG_INIT_ENTROPY_LENGTH] = {0};
  chacha_drbg_init(&drbg_ctx, entropy, sizeof(entropy), nonce, nonce_length);
  memzero(entropy, sizeof(entropy));

  initialized = sectrue;
}

void drbg_set_seed(uint32_t seed) {
  chacha_drbg_init(&drbg_ctx, (uint8_t *)&seed, sizeof(seed), NULL, 0);

  initialized = sectrue;
}

void drbg_reseed() {
  ensure(initialized, "drbg not initialized");
  uint8_t entropy[DRBG_RESEED_ENTROPY_LENGTH] = {0};
  chacha_drbg_reseed(&drbg_ctx, entropy, sizeof(entropy), NULL, 0);
}

void drbg_generate(uint8_t *buffer, size_t length) {
  ensure(initialized, "drbg not initialized");

  if ((DRBG_RESEED_INTERVAL_CALLS != 0) &
      (drbg_ctx.reseed_counter > DRBG_RESEED_INTERVAL_CALLS)) {
    drbg_reseed();
  }

  chacha_drbg_generate(&drbg_ctx, buffer, length);
}

uint32_t drbg_random32(void) {
  uint32_t value;
  drbg_generate((uint8_t *)&value, sizeof(value));
  return value;
}
