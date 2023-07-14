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

#ifndef __TREZORHAL_RANDOM_DELAYS_H__
#define __TREZORHAL_RANDOM_DELAYS_H__

#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>

#include "chacha_drbg.h"

#include "common.h"

#define BUFFER_LENGTH 64

typedef struct {
  CHACHA_DRBG_CTX drbg_ctx;
  secbool drbg_initialized;
  uint8_t session_delay;
  bool refresh_session_delay;
  secbool rdi_disabled;

  // Since the function is called both from an interrupt (rdi_handler,
  // wait_random) and the main thread (wait_random), we use a lock to
  // synchronise access to global variables
  atomic_flag locked;
  size_t buffer_index;
  uint8_t buffer[BUFFER_LENGTH];
} rdi_data_t;

void random_delays_init(void);

void rdi_start(void);
void rdi_stop(void);
void rdi_refresh_session_delay(void);
void rdi_handler(rdi_data_t* rdi, uint32_t uw_tick);

void wait_random(void);
#endif
