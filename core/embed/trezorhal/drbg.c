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
#include "irq.h"
#include "memzero.h"
#include "rand.h"
#include "secbool.h"
#include "systick.h"

extern __IO uint32_t uwTick;

static CHACHA_DRBG_CTX drbg_ctx;
static secbool initialized = secfalse;
static uint32_t last_reseeded_ms = 0;
static secbool reseeding_not_needed = sectrue;

void drbg_init(const uint8_t *nonce, size_t nonce_length) {
  assert(nonce_length == DRBG_INIT_NONCE_LENGTH);

  uint8_t entropy[DRBG_INIT_TRNG_ENTROPY_LENGTH] = {0};
  random_buffer(entropy, sizeof(entropy));
  chacha_drbg_init(&drbg_ctx, entropy, sizeof(entropy), nonce, nonce_length);
  memzero(entropy, sizeof(entropy));

  systick_enable_dispatch(SYSTICK_DISPATCH_DRBG, drbg_reseed_handler);
  initialized = sectrue;
}

static void drbg_reseed_with_trng(size_t trng_entropy_length,
                                  uint8_t *additional_input,
                                  size_t additional_input_length) {
  ensure(initialized, NULL);
  assert(trng_entropy_length <= DRBG_RESEED_MAX_TRNG_ENTROPY);

  uint8_t entropy[DRBG_RESEED_MAX_TRNG_ENTROPY] = {0};
  random_buffer(entropy, trng_entropy_length);
  chacha_drbg_reseed(&drbg_ctx, entropy, trng_entropy_length, additional_input,
                     additional_input_length);
  memzero(entropy, sizeof(entropy));
}

void drbg_mix_hw_entropy() {
  drbg_reseed_with_trng(DRBG_MIX_HW_ENTROPY_TRNG_ENTROPY_LENGTH,
                        HW_ENTROPY_DATA, HW_ENTROPY_LEN);
}

void drbg_reseed() {
  drbg_reseed_with_trng(DRBG_RESEED_TRNG_ENTROPY_LENGTH, SW_ENTROPY_DATA,
                        SW_ENTROPY_LEN);
}

void drbg_generate(uint8_t *buffer, size_t length) {
  ensure(initialized, NULL);

  if ((reseeding_not_needed != sectrue) ||
      ((DRBG_RESEED_INTERVAL_CALLS != 0) &
       (drbg_ctx.reseed_counter > DRBG_RESEED_INTERVAL_CALLS))) {
    drbg_reseed();
    reseeding_not_needed = sectrue;
    last_reseeded_ms = uwTick;
  }

  chacha_drbg_generate(&drbg_ctx, buffer, length);
}

uint32_t drbg_random32(void) {
  uint32_t value;
  drbg_generate((uint8_t *)&value, sizeof(value));
  return value;
}

void drbg_reseed_handler(uint32_t uw_tick) {
  if ((DRBG_RESEED_INTERVAL_MS != 0) &
      (last_reseeded_ms + DRBG_RESEED_INTERVAL_MS >= uw_tick)) {
    reseeding_not_needed = secfalse;
  }
}
