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

/*
Random delay interrupts (RDI) is a contermeasure against side channel attacks.
It consists of an interrupt handler that is supposed to be called every
millisecond or so. The handler waits for a random number of cpu ticks that is a
sample of so called floating mean distribution. That means that the number is
the sum of two numbers generated uniformly at random in the interval [0, 255].
The first number is generated freshly for each call of the handler, the other
number is supposed to be refreshed when the device performs an operation that
leaks the current state of the execution flow, such as sending or receiving an
usb packet.

See Differential Power Analysis in the Presence of Hardware Countermeasures by
Christophe Clavier, Jean-Sebastien Coron, Nora Dabbous and Efficient Use of
Random Delays in Embedded Software by Michael Tunstall, Olivier Benoit:
https://link.springer.com/content/pdf/10.1007%2F3-540-44499-8_20.pdf
https://link.springer.com/content/pdf/10.1007%2F978-3-540-72354-7_3.pdf
*/

#include "random_delays.h"

#include <stdatomic.h>
#include <stdbool.h>

#include "chacha_drbg.h"
#include "common.h"
#include "memzero.h"
#include "rand.h"
#include "shared_data.h"

// from util.s
extern void shutdown_privileged(void);

#define DRBG_RESEED_INTERVAL_CALLS 1000
#define DRBG_TRNG_ENTROPY_LENGTH 50
_Static_assert(CHACHA_DRBG_OPTIMAL_RESEED_LENGTH(1) == DRBG_TRNG_ENTROPY_LENGTH,
               "");

volatile rdi_data_t rdi_data = {
    .drbg_ctx = {0},
    .drbg_initialized = secfalse,
    .session_delay = 0,
    .refresh_session_delay = false,
    .rdi_disabled = sectrue,
    .locked = ATOMIC_FLAG_INIT,
    .buffer = {0},
    .buffer_index = 0,

};

static void drbg_init() {
  uint8_t entropy[DRBG_TRNG_ENTROPY_LENGTH] = {0};
  random_buffer(entropy, sizeof(entropy));
  chacha_drbg_init((CHACHA_DRBG_CTX *)&rdi_data.drbg_ctx, entropy,
                   sizeof(entropy), NULL, 0);
  memzero(entropy, sizeof(entropy));

  rdi_data.drbg_initialized = sectrue;
  shared_data_register(SHARED_DATA_RDI_DATA, (uint32_t)&rdi_data);
}

static void drbg_reseed(volatile rdi_data_t *rdi) {
  ensure(rdi->drbg_initialized, NULL);

  uint8_t entropy[DRBG_TRNG_ENTROPY_LENGTH] = {0};
  random_buffer(entropy, sizeof(entropy));
  chacha_drbg_reseed((CHACHA_DRBG_CTX *)(&rdi->drbg_ctx), entropy,
                     sizeof(entropy), NULL, 0);
  memzero(entropy, sizeof(entropy));
}

static void drbg_generate(volatile rdi_data_t *rdi, uint8_t *buffer,
                          size_t length) {
  ensure(rdi->drbg_initialized, NULL);

  if (rdi->drbg_ctx.reseed_counter > DRBG_RESEED_INTERVAL_CALLS) {
    drbg_reseed(rdi);
  }
  chacha_drbg_generate((CHACHA_DRBG_CTX *)&rdi->drbg_ctx, buffer, length);
}

// WARNING: Returns a constant if the function's critical section is locked
static uint32_t drbg_random8(volatile rdi_data_t *rdi) {
  if (atomic_flag_test_and_set(&rdi->locked))
  // locked_old = locked; locked = true; locked_old
  {
    // If the critical section is locked we return a non-random value, which
    // should be ok for our purposes
    return 128;
  }

  if (rdi->buffer_index == 0) {
    drbg_generate(rdi, (uint8_t *)rdi->buffer, sizeof(rdi->buffer));
  }

  // To be extra sure there is no buffer overflow, we use a local copy of
  // buffer_index
  size_t buffer_index_local = rdi->buffer_index % sizeof(rdi->buffer);
  uint8_t value = rdi->buffer[buffer_index_local];
  memzero((void *)&rdi->buffer[buffer_index_local], 1);
  rdi->buffer_index = (buffer_index_local + 1) % sizeof(rdi->buffer);

  atomic_flag_clear(&rdi->locked);  // locked = false
  return value;
}

static void wait(uint32_t delay) {
  // wait (30 + delay) ticks
  asm volatile(
      "ldr r0, %0;"  // r0 = delay
      "loop:"
      "subs r0, $3;"  // r0 -= 3
      "bhs loop;"     // if (r0 >= 3): goto loop
      // loop (delay // 3) times
      // every loop takes 3 ticks
      // r0 == (delay % 3) - 3
      "add r0, $3;"  // r0 += 3
      // r0 == delay % 3
      "and r0, r0, $3;"  // r0 %= 4, make sure that 0 <= r0 < 4
      "ldr r1, =table;"  // r1 = &table
      "tbb [r1, r0];"    // jump 2*r1[r0] bytes forward, that is goto wait_r0
      "base:"
      "table:"  // table of branch lengths
      ".byte (wait_0 - base)/2;"
      ".byte (wait_1 - base)/2;"
      ".byte (wait_2 - base)/2;"
      ".byte (wait_2 - base)/2;"  // next instruction must be 2-byte aligned
      "wait_2:"
      "add r0, $1;"  // wait one tick
      "wait_1:"
      "add r0, $1;"  // wait one tick
      "wait_0:"
      :
      : "m"(delay)
      : "r0", "r1");
}

void random_delays_init() { drbg_init(); }

void rdi_start(void) {
  ensure(rdi_data.drbg_initialized, NULL);

  if (rdi_data.rdi_disabled == sectrue) {  // if rdi disabled
    rdi_data.refresh_session_delay = true;
    rdi_data.rdi_disabled = secfalse;
  }
}

void rdi_stop(void) {
  if (rdi_data.rdi_disabled == secfalse) {  // if rdi enabled
    rdi_data.rdi_disabled = sectrue;
    rdi_data.session_delay = 0;
  }
}

void rdi_refresh_session_delay(void) {
  if (rdi_data.rdi_disabled == secfalse)  // if rdi enabled
    rdi_data.refresh_session_delay = true;
}

void rdi_handler(rdi_data_t *rdi, uint32_t uw_tick) {
  if (rdi->rdi_disabled == secfalse) {  // if rdi enabled
    if (rdi->refresh_session_delay) {
      rdi->session_delay = drbg_random8(rdi);
      rdi->refresh_session_delay = false;
    }

    wait(drbg_random8(rdi) + rdi->session_delay);

  } else {  // if rdi disabled or rdi_disabled corrupted
    ensure(rdi->rdi_disabled, "Fault detected");
  }
}

/*
 * Generates a delay of random length. Use this to protect sensitive code
 * against fault injection.
 */
void wait_random(void) {
  int wait = drbg_random8(&rdi_data);
  volatile int i = 0;
  volatile int j = wait;
  while (i < wait) {
    if (i + j != wait) {
      shutdown_privileged();
    }
    ++i;
    --j;
  }
  // Double-check loop completion.
  if (i != wait || j != 0) {
    shutdown_privileged();
  }
}
